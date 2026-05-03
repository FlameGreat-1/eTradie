use crate::{
    fallback::FallbackPolicy,
    geoip::GeoIpLookup,
    region::{RegionInfo, RegionSelector},
};
use edge_ingress_common::{
    metrics::{record_fallback_selection, record_region_selection},
    types::{FallbackReason, Region, UpstreamEndpoint, UpstreamStatus},
    Result,
};
use std::collections::HashMap;
use std::net::IpAddr;
use std::sync::Arc;
use tracing::{debug, info};

pub struct GeoRouter {
    geoip_lookup: Arc<GeoIpLookup>,
    fallback_policy: FallbackPolicy,
}

impl GeoRouter {
    pub fn new(geoip_lookup: GeoIpLookup) -> Self {
        let region_selector = RegionSelector::new().expect("Failed to create RegionSelector");
        let fallback_policy = FallbackPolicy::new(region_selector);

        info!("GeoRouter initialized");

        Self {
            geoip_lookup: Arc::new(geoip_lookup),
            fallback_policy,
        }
    }

    pub fn route(
        &self,
        client_ip: IpAddr,
        upstream_health: &HashMap<Region, UpstreamStatus>,
    ) -> Result<(Region, Option<FallbackReason>)> {
        let region_info = self.geoip_lookup.lookup_or_default(client_ip);
        let preferred_region = region_info.region();

        debug!(
            client_ip = %client_ip,
            preferred_region = %preferred_region,
            country_code = ?region_info.country_code,
            "routing request"
        );

        let (selected_region, fallback_reason) = self
            .fallback_policy
            .select_region_with_fallback(preferred_region, upstream_health)?;

        record_region_selection(selected_region);

        if let Some(reason) = fallback_reason {
            record_fallback_selection(reason);
        }

        Ok((selected_region, fallback_reason))
    }

    pub fn select_endpoint<'a>(
        &self,
        region: Region,
        endpoints: &'a [UpstreamEndpoint],
    ) -> Result<&'a UpstreamEndpoint> {
        self.fallback_policy.select_healthy_endpoint(region, endpoints)
    }

    pub fn get_region_info(&self, client_ip: IpAddr) -> RegionInfo {
        self.geoip_lookup.lookup_or_default(client_ip)
    }

    pub fn get_ordered_regions(&self, preferred_region: Region) -> Vec<Region> {
        self.fallback_policy.get_ordered_regions(preferred_region)
    }

    pub fn get_default_region(&self) -> Region {
        self.geoip_lookup.get_default_region()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_health_map(healthy_regions: &[Region]) -> HashMap<Region, UpstreamStatus> {
        let mut map = HashMap::new();
        for region in &[
            Region::UsEast1,
            Region::UsWest2,
            Region::EuWest1,
            Region::ApSoutheast1,
        ] {
            let status = if healthy_regions.contains(region) {
                UpstreamStatus::Healthy
            } else {
                UpstreamStatus::Unhealthy
            };
            map.insert(*region, status);
        }
        map
    }

    #[test]
    fn test_get_default_region() {
        let lookup = GeoIpLookup::from_default_path();
        if lookup.is_err() {
            return;
        }
        let router = GeoRouter::new(lookup.unwrap());
        assert_eq!(router.get_default_region(), Region::UsEast1);
    }

    #[test]
    fn test_get_region_info() {
        let lookup = GeoIpLookup::from_default_path();
        if lookup.is_err() {
            return;
        }
        let router = GeoRouter::new(lookup.unwrap());
        let ip: IpAddr = "8.8.8.8".parse().unwrap();
        let info = router.get_region_info(ip);
        assert_eq!(info.region(), router.get_default_region());
    }

    #[test]
    fn test_route_with_healthy_preferred() {
        let lookup = GeoIpLookup::from_default_path();
        if lookup.is_err() {
            return;
        }
        let router = GeoRouter::new(lookup.unwrap());
        let health = create_health_map(&[Region::UsEast1]);
        let ip: IpAddr = "8.8.8.8".parse().unwrap();

        let result = router.route(ip, &health);
        assert!(result.is_ok());
    }

    #[test]
    fn test_select_endpoint() {
        let lookup = GeoIpLookup::from_default_path();
        if lookup.is_err() {
            return;
        }
        let router = GeoRouter::new(lookup.unwrap());

        let mut endpoint = UpstreamEndpoint::new(
            Region::UsEast1,
            "127.0.0.1:8080".parse().unwrap(),
        );
        endpoint.mark_healthy();

        let endpoints = vec![endpoint];
        let result = router.select_endpoint(Region::UsEast1, &endpoints);
        assert!(result.is_ok());
    }

    #[test]
    fn test_get_ordered_regions() {
        let lookup = GeoIpLookup::from_default_path();
        if lookup.is_err() {
            return;
        }
        let router = GeoRouter::new(lookup.unwrap());
        let regions = router.get_ordered_regions(Region::UsEast1);
        assert!(!regions.is_empty());
        assert_eq!(regions[0], Region::UsEast1);
    }
}
