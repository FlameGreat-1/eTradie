use edge_ingress_common::{
    types::{Region, UpstreamEndpoint},
    EdgeError, Result,
};
use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{debug, info, warn};

pub struct UpstreamPool {
    endpoints: Arc<RwLock<HashMap<Region, Vec<UpstreamEndpoint>>>>,
}

impl UpstreamPool {
    pub fn new() -> Self {
        Self {
            endpoints: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub async fn add_endpoint(&self, endpoint: UpstreamEndpoint) {
        let mut endpoints = self.endpoints.write().await;
        endpoints
            .entry(endpoint.region)
            .or_insert_with(Vec::new)
            .push(endpoint.clone());

        info!(
            region = %endpoint.region,
            address = %endpoint.address,
            "upstream endpoint added to pool"
        );
    }

    pub async fn remove_endpoint(&self, region: Region, address: SocketAddr) {
        let mut endpoints = self.endpoints.write().await;
        if let Some(region_endpoints) = endpoints.get_mut(&region) {
            region_endpoints.retain(|e| e.address != address);
            
            info!(
                region = %region,
                address = %address,
                "upstream endpoint removed from pool"
            );
        }
    }

    pub async fn get_endpoints(&self, region: Region) -> Vec<UpstreamEndpoint> {
        let endpoints = self.endpoints.read().await;
        endpoints
            .get(&region)
            .cloned()
            .unwrap_or_default()
    }

    pub async fn get_healthy_endpoint(&self, region: Region) -> Result<UpstreamEndpoint> {
        let endpoints = self.endpoints.read().await;
        
        endpoints
            .get(&region)
            .and_then(|eps| eps.iter().find(|e| e.status.is_healthy()).cloned())
            .ok_or_else(|| {
                warn!(
                    region = %region,
                    "no healthy upstream endpoint found"
                );
                EdgeError::UpstreamUnavailable {
                    region: region.to_string(),
                }
            })
    }

    pub async fn update_endpoint_health(&self, region: Region, address: SocketAddr, is_healthy: bool) {
        let mut endpoints = self.endpoints.write().await;
        
        if let Some(region_endpoints) = endpoints.get_mut(&region) {
            if let Some(endpoint) = region_endpoints.iter_mut().find(|e| e.address == address) {
                if is_healthy {
                    endpoint.mark_healthy();
                } else {
                    endpoint.mark_unhealthy();
                }

                debug!(
                    region = %region,
                    address = %address,
                    is_healthy = is_healthy,
                    consecutive_failures = endpoint.consecutive_failures,
                    consecutive_successes = endpoint.consecutive_successes,
                    "upstream endpoint health updated"
                );
            }
        }
    }

    pub async fn get_all_endpoints(&self) -> HashMap<Region, Vec<UpstreamEndpoint>> {
        self.endpoints.read().await.clone()
    }

    pub async fn get_regions(&self) -> Vec<Region> {
        self.endpoints.read().await.keys().copied().collect()
    }

    pub async fn total_endpoints(&self) -> usize {
        self.endpoints
            .read()
            .await
            .values()
            .map(|v| v.len())
            .sum()
    }

    pub async fn healthy_endpoints_count(&self, region: Region) -> usize {
        self.endpoints
            .read()
            .await
            .get(&region)
            .map(|eps| eps.iter().filter(|e| e.status.is_healthy()).count())
            .unwrap_or(0)
    }
}

impl Default for UpstreamPool {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    

    #[tokio::test]
    async fn test_new_pool() {
        let pool = UpstreamPool::new();
        assert_eq!(pool.total_endpoints().await, 0);
    }

    #[tokio::test]
    async fn test_add_endpoint() {
        let pool = UpstreamPool::new();
        let endpoint = UpstreamEndpoint::new(
            Region::UsEast1,
            "127.0.0.1:8080".parse().unwrap(),
        );
        
        pool.add_endpoint(endpoint).await;
        assert_eq!(pool.total_endpoints().await, 1);
    }

    #[tokio::test]
    async fn test_get_endpoints() {
        let pool = UpstreamPool::new();
        let endpoint = UpstreamEndpoint::new(
            Region::UsEast1,
            "127.0.0.1:8080".parse().unwrap(),
        );
        
        pool.add_endpoint(endpoint).await;
        let endpoints = pool.get_endpoints(Region::UsEast1).await;
        assert_eq!(endpoints.len(), 1);
    }

    #[tokio::test]
    async fn test_remove_endpoint() {
        let pool = UpstreamPool::new();
        let addr: SocketAddr = "127.0.0.1:8080".parse().unwrap();
        let endpoint = UpstreamEndpoint::new(Region::UsEast1, addr);
        
        pool.add_endpoint(endpoint).await;
        assert_eq!(pool.total_endpoints().await, 1);
        
        pool.remove_endpoint(Region::UsEast1, addr).await;
        assert_eq!(pool.total_endpoints().await, 0);
    }

    #[tokio::test]
    async fn test_get_healthy_endpoint() {
        let pool = UpstreamPool::new();
        let addr: SocketAddr = "127.0.0.1:8080".parse().unwrap();
        let mut endpoint = UpstreamEndpoint::new(Region::UsEast1, addr);
        endpoint.mark_healthy();
        
        pool.add_endpoint(endpoint).await;
        let result = pool.get_healthy_endpoint(Region::UsEast1).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_get_healthy_endpoint_none_available() {
        let pool = UpstreamPool::new();
        let result = pool.get_healthy_endpoint(Region::UsEast1).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_update_endpoint_health() {
        let pool = UpstreamPool::new();
        let addr: SocketAddr = "127.0.0.1:8080".parse().unwrap();
        let endpoint = UpstreamEndpoint::new(Region::UsEast1, addr);
        
        pool.add_endpoint(endpoint).await;
        pool.update_endpoint_health(Region::UsEast1, addr, true).await;
        
        let healthy_count = pool.healthy_endpoints_count(Region::UsEast1).await;
        assert_eq!(healthy_count, 1);
    }

    #[tokio::test]
    async fn test_get_regions() {
        let pool = UpstreamPool::new();
        pool.add_endpoint(UpstreamEndpoint::new(
            Region::UsEast1,
            "127.0.0.1:8080".parse().unwrap(),
        )).await;
        pool.add_endpoint(UpstreamEndpoint::new(
            Region::EuWest1,
            "127.0.0.1:8081".parse().unwrap(),
        )).await;
        
        let regions = pool.get_regions().await;
        assert_eq!(regions.len(), 2);
    }
}
