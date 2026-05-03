use crate::region::RegionSelector;
use edge_ingress_common::{
    types::{FallbackReason, Region, UpstreamEndpoint, UpstreamStatus},
    EdgeError, Result,
};
use std::collections::HashMap;
use tracing::{debug, warn};

pub struct FallbackPolicy {
    region_selector: RegionSelector,
}

impl FallbackPolicy {
    pub fn new(region_selector: RegionSelector) -> Self {
        Self { region_selector }
    }

    pub fn select_region_with_fallback(
        &self,
        preferred_region: Region,
        upstream_health: &HashMap<Region, UpstreamStatus>,
    ) -> Result<(Region, Option<FallbackReason>)> {
        if self.is_region_healthy(preferred_region, upstream_health) {
            debug!(
                region = %preferred_region,
                "preferred region is healthy"
            );
            return Ok((preferred_region, None));
        }

        warn!(
            preferred_region = %preferred_region,
            "preferred region unavailable, attempting fallback"
        );

        for fallback_region in self.region_selector.get_fallback_regions() {
            if self.is_region_healthy(*fallback_region, upstream_health) {
                debug!(
                    fallback_region = %fallback_region,
                    "fallback region selected"
                );
                return Ok((*fallback_region, Some(FallbackReason::PreferredUnavailable)));
            }
        }

        let default_region = self.region_selector.get_default_region();
        if self.is_region_healthy(default_region, upstream_health) {
            warn!(
                default_region = %default_region,
                "all fallback regions unavailable, using default"
            );
            return Ok((default_region, Some(FallbackReason::SecondaryUnavailable)));
        }

        Err(EdgeError::AllUpstreamsUnavailable)
    }

    pub fn select_healthy_endpoint<'a>(
        &self,
        region: Region,
        endpoints: &'a [UpstreamEndpoint],
    ) -> Result<&'a UpstreamEndpoint> {
        endpoints
            .iter()
            .find(|e| e.region == region && e.status.is_healthy())
            .ok_or_else(|| EdgeError::UpstreamUnavailable {
                region: region.to_string(),
            })
    }

    pub fn get_ordered_regions(&self, preferred_region: Region) -> Vec<Region> {
        let mut regions = vec![preferred_region];
        regions.extend_from_slice(self.region_selector.get_fallback_regions());
        
        let default = self.region_selector.get_default_region();
        if !regions.contains(&default) {
            regions.push(default);
        }
        
        regions
    }

    fn is_region_healthy(
        &self,
        region: Region,
        upstream_health: &HashMap<Region, UpstreamStatus>,
    ) -> bool {
        upstream_health
            .get(&region)
            .map(|status| status.is_healthy())
            .unwrap_or(false)
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
    fn test_select_region_preferred_healthy() {
        let selector = RegionSelector::new().unwrap();
        let policy = FallbackPolicy::new(selector);
        let health = create_health_map(&[Region::UsEast1]);

        let result = policy.select_region_with_fallback(Region::UsEast1, &health);
        assert!(result.is_ok());
        let (region, fallback_reason) = result.unwrap();
        assert_eq!(region, Region::UsEast1);
        assert!(fallback_reason.is_none());
    }

    #[test]
    fn test_select_region_fallback_to_secondary() {
        let selector = RegionSelector::new().unwrap();
        let policy = FallbackPolicy::new(selector);
        let health = create_health_map(&[Region::UsWest2]);

        let result = policy.select_region_with_fallback(Region::UsEast1, &health);
        assert!(result.is_ok());
        let (region, fallback_reason) = result.unwrap();
        assert_eq!(region, Region::UsWest2);
        assert_eq!(fallback_reason, Some(FallbackReason::PreferredUnavailable));
    }

    #[test]
    fn test_select_region_all_unavailable() {
        let selector = RegionSelector::new().unwrap();
        let policy = FallbackPolicy::new(selector);
        let health = create_health_map(&[]);

        let result = policy.select_region_with_fallback(Region::UsEast1, &health);
        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), EdgeError::AllUpstreamsUnavailable));
    }

    #[test]
    fn test_select_healthy_endpoint() {
        let selector = RegionSelector::new().unwrap();
        let policy = FallbackPolicy::new(selector);

        let mut endpoint = UpstreamEndpoint::new(
            Region::UsEast1,
            "127.0.0.1:8080".parse().unwrap(),
        );
        endpoint.mark_healthy();

        let endpoints = vec![endpoint];
        let result = policy.select_healthy_endpoint(Region::UsEast1, &endpoints);
        assert!(result.is_ok());
    }

    #[test]
    fn test_select_healthy_endpoint_not_found() {
        let selector = RegionSelector::new().unwrap();
        let policy = FallbackPolicy::new(selector);

        let endpoint = UpstreamEndpoint::new(
            Region::UsEast1,
            "127.0.0.1:8080".parse().unwrap(),
        );

        let endpoints = vec![endpoint];
        let result = policy.select_healthy_endpoint(Region::UsEast1, &endpoints);
        assert!(result.is_err());
    }

    #[test]
    fn test_get_ordered_regions() {
        let selector = RegionSelector::new().unwrap();
        let policy = FallbackPolicy::new(selector);

        let regions = policy.get_ordered_regions(Region::EuWest1);
        assert!(!regions.is_empty());
        assert_eq!(regions[0], Region::EuWest1);
    }
}
