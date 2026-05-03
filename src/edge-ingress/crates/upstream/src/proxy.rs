use crate::{
    health::HealthChecker,
    pool::UpstreamPool,
    retry::RetryPolicy,
};
use edge_ingress_common::{
    constants::UPSTREAM_CONNECT_TIMEOUT,
    metrics::{record_upstream_connect_duration, record_upstream_connect_error},
    types::{Region, UpstreamEndpoint},
    EdgeError, Result,
};
use std::net::SocketAddr;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::net::TcpStream;
use tokio::time::timeout;
use tracing::{debug, info, warn};

#[derive(Clone)]
pub struct UpstreamProxy {
    pool: Arc<UpstreamPool>,
    health_checker: Arc<HealthChecker>,
    retry_policy: RetryPolicy,
    connect_timeout: Duration,
}

impl UpstreamProxy {
    pub fn new(pool: UpstreamPool, health_checker: HealthChecker) -> Self {
        Self {
            pool: Arc::new(pool),
            health_checker: Arc::new(health_checker),
            retry_policy: RetryPolicy::with_default(),
            connect_timeout: UPSTREAM_CONNECT_TIMEOUT,
        }
    }

    pub fn with_config(
        pool: UpstreamPool,
        health_checker: HealthChecker,
        retry_policy: RetryPolicy,
        connect_timeout: Duration,
    ) -> Self {
        Self {
            pool: Arc::new(pool),
            health_checker: Arc::new(health_checker),
            retry_policy,
            connect_timeout,
        }
    }

    pub async fn connect(&self, region: Region) -> Result<TcpStream> {
        let pool = Arc::clone(&self.pool);
        let connect_timeout = self.connect_timeout;

        self.retry_policy
            .execute(|| async {
                let endpoint = pool.get_healthy_endpoint(region).await?;
                self.connect_to_endpoint(region, &endpoint, connect_timeout).await
            })
            .await
    }

    async fn connect_to_endpoint(
        &self,
        region: Region,
        endpoint: &UpstreamEndpoint,
        connect_timeout: Duration,
    ) -> Result<TcpStream> {
        let start = Instant::now();
        let address = endpoint.address;

        debug!(
            region = %region,
            address = %address,
            "attempting upstream connection"
        );

        let result = timeout(connect_timeout, TcpStream::connect(address)).await;

        let duration = start.elapsed();
        record_upstream_connect_duration(region, duration.as_secs_f64());

        match result {
            Ok(Ok(stream)) => {
                info!(
                    region = %region,
                    address = %address,
                    duration_ms = duration.as_millis(),
                    "upstream connection established"
                );

                self.pool.update_endpoint_health(region, address, true).await;
                self.health_checker.update_metrics(region, endpoint.status);

                Ok(stream)
            }
            Ok(Err(e)) => {
                warn!(
                    region = %region,
                    address = %address,
                    error = %e,
                    duration_ms = duration.as_millis(),
                    "upstream connection failed"
                );

                record_upstream_connect_error(region, "connection_failed");
                self.pool.update_endpoint_health(region, address, false).await;

                Err(EdgeError::UpstreamConnectionFailed(format!(
                    "Failed to connect to {}: {}",
                    address, e
                )))
            }
            Err(_) => {
                warn!(
                    region = %region,
                    address = %address,
                    timeout_ms = connect_timeout.as_millis(),
                    "upstream connection timeout"
                );

                record_upstream_connect_error(region, "timeout");
                self.pool.update_endpoint_health(region, address, false).await;

                Err(EdgeError::UpstreamTimeout(format!(
                    "Connection to {} timed out after {:?}",
                    address, connect_timeout
                )))
            }
        }
    }

    pub async fn add_endpoint(&self, endpoint: UpstreamEndpoint) {
        self.pool.add_endpoint(endpoint).await;
    }

    pub async fn remove_endpoint(&self, region: Region, address: SocketAddr) {
        self.pool.remove_endpoint(region, address).await;
    }

    pub async fn get_pool(&self) -> Arc<UpstreamPool> {
        Arc::clone(&self.pool)
    }

    pub fn get_health_checker(&self) -> Arc<HealthChecker> {
        Arc::clone(&self.health_checker)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_new_upstream_proxy() {
        let pool = UpstreamPool::new();
        let health_checker = HealthChecker::new();
        let proxy = UpstreamProxy::new(pool, health_checker);
        
        assert_eq!(proxy.connect_timeout, UPSTREAM_CONNECT_TIMEOUT);
    }

    #[tokio::test]
    async fn test_connect_no_healthy_endpoint() {
        let pool = UpstreamPool::new();
        let health_checker = HealthChecker::new();
        let proxy = UpstreamProxy::new(pool, health_checker);

        let result = proxy.connect(Region::UsEast1).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_add_endpoint() {
        let pool = UpstreamPool::new();
        let health_checker = HealthChecker::new();
        let proxy = UpstreamProxy::new(pool, health_checker);

        let endpoint = UpstreamEndpoint::new(
            Region::UsEast1,
            "127.0.0.1:8080".parse().unwrap(),
        );

        proxy.add_endpoint(endpoint).await;
        
        let pool = proxy.get_pool().await;
        let endpoints = pool.get_endpoints(Region::UsEast1).await;
        assert_eq!(endpoints.len(), 1);
    }

    #[tokio::test]
    async fn test_remove_endpoint() {
        let pool = UpstreamPool::new();
        let health_checker = HealthChecker::new();
        let proxy = UpstreamProxy::new(pool, health_checker);

        let addr: SocketAddr = "127.0.0.1:8080".parse().unwrap();
        let endpoint = UpstreamEndpoint::new(Region::UsEast1, addr);

        proxy.add_endpoint(endpoint).await;
        proxy.remove_endpoint(Region::UsEast1, addr).await;

        let pool = proxy.get_pool().await;
        let endpoints = pool.get_endpoints(Region::UsEast1).await;
        assert_eq!(endpoints.len(), 0);
    }
}
