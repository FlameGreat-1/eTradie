use crate::region::{RegionInfo, RegionSelector};
use edge_ingress_common::{
    constants::GEOIP_DATABASE_PATH,
    metrics::{record_geoip_lookup, record_geoip_lookup_duration},
    types::Region,
    EdgeError, Result,
};
use maxminddb::{geoip2, MaxMindDBError, Reader};
use std::net::IpAddr;
use std::path::Path;
use std::sync::Arc;
use std::time::Instant;
use tracing::{debug, info, warn};

pub struct GeoIpLookup {
    reader: Arc<Reader<Vec<u8>>>,
    region_selector: RegionSelector,
}

impl GeoIpLookup {
    pub fn new<P: AsRef<Path>>(database_path: P) -> Result<Self> {
        let reader = Reader::open_readfile(database_path.as_ref()).map_err(|e| {
            EdgeError::GeoIpLookupFailed(format!(
                "Failed to open GeoIP database at {}: {}",
                database_path.as_ref().display(),
                e
            ))
        })?;

        let region_selector = RegionSelector::new()?;

        info!(
            database_path = %database_path.as_ref().display(),
            "GeoIP database loaded successfully"
        );

        Ok(Self {
            reader: Arc::new(reader),
            region_selector,
        })
    }

    pub fn from_default_path() -> Result<Self> {
        Self::new(GEOIP_DATABASE_PATH)
    }

    pub fn lookup(&self, ip: IpAddr) -> Result<RegionInfo> {
        let start = Instant::now();

        let city_result: std::result::Result<geoip2::City, _> = self.reader.lookup(ip);

        let city = match city_result {
            Ok(c) => {
                record_geoip_lookup("hit");
                record_geoip_lookup_duration(start.elapsed().as_secs_f64());
                c
            }
            Err(MaxMindDBError::AddressNotFoundError(_)) => {
                record_geoip_lookup("miss");
                record_geoip_lookup_duration(start.elapsed().as_secs_f64());
                debug!(ip = %ip, "IP address not found in GeoIP database, using default region");
                return Err(EdgeError::GeoIpLookupFailed(format!("IP {} not found in database", ip)));
            }
            Err(e) => {
                record_geoip_lookup("error");
                record_geoip_lookup_duration(start.elapsed().as_secs_f64());
                return Err(EdgeError::GeoIpLookupFailed(format!("GeoIP lookup failed for {}: {}", ip, e)));
            }
        };

        let country_code = city
            .country
            .as_ref()
            .and_then(|c| c.iso_code)
            .map(|s| s.to_string());

        let city_name = city
            .city
            .as_ref()
            .and_then(|c| c.names.as_ref())
            .and_then(|names| names.get("en"))
            .map(|s| s.to_string());

        let location = city.location.as_ref();
        let latitude = location.and_then(|l| l.latitude);
        let longitude = location.and_then(|l| l.longitude);

        let region = self.determine_region(&country_code, latitude, longitude);

        debug!(
            ip = %ip,
            region = %region,
            country_code = ?country_code,
            city = ?city_name,
            "GeoIP lookup successful"
        );

        Ok(RegionInfo::with_location(
            region,
            country_code,
            city_name,
            latitude,
            longitude,
        ))
    }

    pub fn lookup_or_default(&self, ip: IpAddr) -> RegionInfo {
        match self.lookup(ip) {
            Ok(info) => info,
            Err(e) => {
                warn!(
                    ip = %ip,
                    error = %e,
                    default_region = %self.region_selector.get_default_region(),
                    "GeoIP lookup failed, using default region"
                );
                RegionInfo::new(self.region_selector.get_default_region())
            }
        }
    }

    fn determine_region(
        &self,
        country_code: &Option<String>,
        latitude: Option<f64>,
        longitude: Option<f64>,
    ) -> Region {
        if let Some(code) = country_code {
            return self.region_selector.select_region_by_country(code);
        }
        if let (Some(lat), Some(lon)) = (latitude, longitude) {
            return self.region_selector.select_region_by_coordinates(lat, lon);
        }
        self.region_selector.get_default_region()
    }

    pub fn get_default_region(&self) -> Region {
        self.region_selector.get_default_region()
    }

    pub fn get_fallback_regions(&self) -> &[Region] {
        self.region_selector.get_fallback_regions()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_lookup_or_default_with_invalid_ip() {
        let lookup = GeoIpLookup::from_default_path();
        if lookup.is_err() {
            return;
        }
        let lookup = lookup.unwrap();
        let ip: IpAddr = "127.0.0.1".parse().unwrap();
        let info = lookup.lookup_or_default(ip);
        assert_eq!(info.region(), lookup.get_default_region());
    }

    #[test]
    fn test_get_default_region() {
        let lookup = GeoIpLookup::from_default_path();
        if lookup.is_err() {
            return;
        }
        let lookup = lookup.unwrap();
        assert_eq!(lookup.get_default_region(), Region::UsEast1);
    }

    #[test]
    fn test_get_fallback_regions() {
        let lookup = GeoIpLookup::from_default_path();
        if lookup.is_err() {
            return;
        }
        let lookup = lookup.unwrap();
        let fallbacks = lookup.get_fallback_regions();
        assert!(!fallbacks.is_empty());
    }
}
