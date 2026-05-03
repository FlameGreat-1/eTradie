use edge_ingress_common::{
    constants::regions::{DEFAULT_REGION, FALLBACK_REGIONS},
    types::Region,
    EdgeError, Result,
};

#[derive(Debug, Clone)]
pub struct RegionInfo {
    pub region: Region,
    pub country_code: Option<String>,
    pub city: Option<String>,
    pub latitude: Option<f64>,
    pub longitude: Option<f64>,
}

impl RegionInfo {
    pub fn new(region: Region) -> Self {
        Self {
            region,
            country_code: None,
            city: None,
            latitude: None,
            longitude: None,
        }
    }

    pub fn with_location(
        region: Region,
        country_code: Option<String>,
        city: Option<String>,
        latitude: Option<f64>,
        longitude: Option<f64>,
    ) -> Self {
        Self {
            region,
            country_code,
            city,
            latitude,
            longitude,
        }
    }

    pub fn region(&self) -> Region {
        self.region
    }
}

pub struct RegionSelector {
    default_region: Region,
    fallback_regions: Vec<Region>,
}

impl RegionSelector {
    pub fn new() -> Result<Self> {
        let default_region = Region::from_str(DEFAULT_REGION).ok_or_else(|| {
            EdgeError::Configuration(format!("Invalid default region: {}", DEFAULT_REGION))
        })?;

        let fallback_regions: Result<Vec<Region>> = FALLBACK_REGIONS
            .iter()
            .map(|r| {
                Region::from_str(r).ok_or_else(|| {
                    EdgeError::Configuration(format!("Invalid fallback region: {}", r))
                })
            })
            .collect();

        Ok(Self {
            default_region,
            fallback_regions: fallback_regions?,
        })
    }

    pub fn select_nearest_region(&self, region_info: &RegionInfo) -> Region {
        region_info.region
    }

    pub fn get_default_region(&self) -> Region {
        self.default_region
    }

    pub fn get_fallback_regions(&self) -> &[Region] {
        &self.fallback_regions
    }

    pub fn select_region_by_country(&self, country_code: &str) -> Region {
        match country_code {
            "US" => Region::UsEast1,
            "CA" => Region::UsEast1,
            "GB" | "FR" | "DE" | "IT" | "ES" | "NL" | "BE" | "CH" | "AT" | "IE" => {
                Region::EuWest1
            }
            "SG" | "MY" | "TH" | "ID" | "PH" | "VN" => Region::ApSoutheast1,
            "AU" | "NZ" => Region::ApSoutheast1,
            "JP" | "KR" | "CN" | "TW" | "HK" => Region::ApSoutheast1,
            "BR" | "AR" | "CL" | "CO" | "PE" => Region::UsEast1,
            "IN" => Region::ApSoutheast1,
            "ZA" => Region::EuWest1,
            "RU" => Region::EuWest1,
            "MX" => Region::UsEast1,
            _ => self.default_region,
        }
    }

    pub fn select_region_by_coordinates(&self, latitude: f64, longitude: f64) -> Region {
        let distances = vec![
            (Region::UsEast1, self.calculate_distance(latitude, longitude, 37.7749, -77.0369)),
            (Region::UsWest2, self.calculate_distance(latitude, longitude, 47.6062, -122.3321)),
            (Region::EuWest1, self.calculate_distance(latitude, longitude, 53.3498, -6.2603)),
            (Region::ApSoutheast1, self.calculate_distance(latitude, longitude, 1.3521, 103.8198)),
        ];

        distances
            .into_iter()
            .min_by(|a, b| a.1.partial_cmp(&b.1).unwrap())
            .map(|(region, _)| region)
            .unwrap_or(self.default_region)
    }

    fn calculate_distance(&self, lat1: f64, lon1: f64, lat2: f64, lon2: f64) -> f64 {
        let r = 6371.0;

        let lat1_rad = lat1.to_radians();
        let lat2_rad = lat2.to_radians();
        let delta_lat = (lat2 - lat1).to_radians();
        let delta_lon = (lon2 - lon1).to_radians();

        let a = (delta_lat / 2.0).sin().powi(2)
            + lat1_rad.cos() * lat2_rad.cos() * (delta_lon / 2.0).sin().powi(2);
        let c = 2.0 * a.sqrt().atan2((1.0 - a).sqrt());

        r * c
    }
}

impl Default for RegionSelector {
    fn default() -> Self {
        Self::new().expect("Failed to create default RegionSelector")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_region_info_new() {
        let info = RegionInfo::new(Region::UsEast1);
        assert_eq!(info.region(), Region::UsEast1);
        assert!(info.country_code.is_none());
        assert!(info.city.is_none());
    }

    #[test]
    fn test_region_info_with_location() {
        let info = RegionInfo::with_location(
            Region::UsEast1,
            Some("US".to_string()),
            Some("New York".to_string()),
            Some(40.7128),
            Some(-74.0060),
        );
        assert_eq!(info.region(), Region::UsEast1);
        assert_eq!(info.country_code.as_deref(), Some("US"));
        assert_eq!(info.city.as_deref(), Some("New York"));
    }

    #[test]
    fn test_region_selector_new() {
        let selector = RegionSelector::new();
        assert!(selector.is_ok());
    }

    #[test]
    fn test_get_default_region() {
        let selector = RegionSelector::new().unwrap();
        assert_eq!(selector.get_default_region(), Region::UsEast1);
    }

    #[test]
    fn test_get_fallback_regions() {
        let selector = RegionSelector::new().unwrap();
        let fallbacks = selector.get_fallback_regions();
        assert!(!fallbacks.is_empty());
        assert!(fallbacks.contains(&Region::UsWest2));
    }

    #[test]
    fn test_select_region_by_country_us() {
        let selector = RegionSelector::new().unwrap();
        assert_eq!(selector.select_region_by_country("US"), Region::UsEast1);
    }

    #[test]
    fn test_select_region_by_country_eu() {
        let selector = RegionSelector::new().unwrap();
        assert_eq!(selector.select_region_by_country("GB"), Region::EuWest1);
        assert_eq!(selector.select_region_by_country("DE"), Region::EuWest1);
    }

    #[test]
    fn test_select_region_by_country_asia() {
        let selector = RegionSelector::new().unwrap();
        assert_eq!(selector.select_region_by_country("SG"), Region::ApSoutheast1);
        assert_eq!(selector.select_region_by_country("JP"), Region::ApSoutheast1);
    }

    #[test]
    fn test_select_region_by_country_unknown() {
        let selector = RegionSelector::new().unwrap();
        assert_eq!(selector.select_region_by_country("XX"), Region::UsEast1);
    }

    #[test]
    fn test_select_region_by_coordinates_us_east() {
        let selector = RegionSelector::new().unwrap();
        let region = selector.select_region_by_coordinates(40.7128, -74.0060);
        assert_eq!(region, Region::UsEast1);
    }

    #[test]
    fn test_select_region_by_coordinates_eu() {
        let selector = RegionSelector::new().unwrap();
        let region = selector.select_region_by_coordinates(51.5074, -0.1278);
        assert_eq!(region, Region::EuWest1);
    }

    #[test]
    fn test_select_region_by_coordinates_asia() {
        let selector = RegionSelector::new().unwrap();
        let region = selector.select_region_by_coordinates(1.3521, 103.8198);
        assert_eq!(region, Region::ApSoutheast1);
    }

    #[test]
    fn test_calculate_distance() {
        let selector = RegionSelector::new().unwrap();
        let distance = selector.calculate_distance(40.7128, -74.0060, 37.7749, -77.0369);
        assert!(distance > 0.0);
        assert!(distance < 1000.0);
    }
}
