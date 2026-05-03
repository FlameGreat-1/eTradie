use edge_ingress_common::{
    constants::{
        HEALTH_CHECK_HEALTHY_THRESHOLD, HEALTH_CHECK_INTERVAL, HEALTH_CHECK_TIMEOUT,
        HEALTH_CHECK_UNHEALTHY_THRESHOLD,
    },
    metrics::update_upstream_health,
    types::{Region, UpstreamEndpoint, UpstreamStatus},
};
use hyper::Request;
use hyper_util::client::legacy::Client;
use hyper_util::rt::TokioExecutor;
use std::net::SocketAddr;
use std::time::Duration;
use tokio::time::timeout;
use tracing::{debug, warn};

pub struct HealthChecker {
    client: Client<hyper_util::client::legacy::connect::HttpConnector, String>,
    check_interval: Duration,
    check_timeout: Duration,
    unhealthy_threshold: u32,
    healthy_threshold: u32,
}

impl HealthChecker {
    pub fn new() -> Self {
        let client = Client::builder(TokioExecutor::new()).build_http();

        Self {
            client,
            check_interval: HEALTH_CHECK_INTERVAL,
            check_timeout: HEALTH_CHECK_TIMEOUT,
            unhealthy_threshold: HEALTH_CHECK_UNHEALTHY_THRESHOLD,
            healthy_threshold: HEALTH_CHECK_HEALTHY_THRESHOLD,
        }
    }

    pub fn with_config(
        check_interval: Duration,
        check_timeout: Duration,
        unhealthy_threshold: u32,
        healthy_threshold: u32,
    ) -> Self {
        let client = Client::builder(TokioExecutor::new()).build_http();

        Self {
            client,
            check_interval,
            check_timeout,
            unhealthy_threshold,
            healthy_threshold,
        }
    }

    pub async fn check_endpoint(&self, address: SocketAddr) -> bool {
        let uri = format!("http://{}/healthz", address);

        let request = match Request::builder()
            .method("GET")
            .uri(&uri)
            .body(String::new())
        {
            Ok(req) => req,
            Err(e) => {
                warn!(
                    address = %address,
                    error = %e,
                    "failed to build health check request"
                );
                return false;
            }
        };

        let result = timeout(self.check_timeout, self.client.request(request)).await;

        match result {
            Ok(Ok(response)) => {
                let is_healthy = response.status().is_success();
                debug!(
                    address = %address,
                    status = %response.status(),
                    is_healthy = is_healthy,
                    "health check completed"
                );
                is_healthy
            }
            Ok(Err(e)) => {
                debug!(
                    address = %address,
                    error = %e,
                    "health check request failed"
                );
                false
            }
            Err(_) => {
                debug!(
                    address = %address,
                    timeout_ms = self.check_timeout.as_millis(),
                    "health check timeout"
                );
                false
            }
        }
    }

    pub fn should_mark_healthy(&self, endpoint: &UpstreamEndpoint) -> bool {
        endpoint.consecutive_successes >= self.healthy_threshold
    }

    pub fn should_mark_unhealthy(&self, endpoint: &UpstreamEndpoint) -> bool {
        endpoint.consecutive_failures >= self.unhealthy_threshold
    }

    pub fn check_interval(&self) -> Duration {
        self.check_interval
    }

    pub fn update_metrics(&self, region: Region, status: UpstreamStatus) {
        update_upstream_health(region, status);
    }
}

impl Default for HealthChecker {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new_health_checker() {
        let checker = HealthChecker::new();
        assert_eq!(checker.check_interval, HEALTH_CHECK_INTERVAL);
        assert_eq!(checker.check_timeout, HEALTH_CHECK_TIMEOUT);
        assert_eq!(checker.unhealthy_threshold, HEALTH_CHECK_UNHEALTHY_THRESHOLD);
        assert_eq!(checker.healthy_threshold, HEALTH_CHECK_HEALTHY_THRESHOLD);
    }

    #[test]
    fn test_with_config() {
        let checker = HealthChecker::with_config(
            Duration::from_secs(5),
            Duration::from_secs(2),
            2,
            3,
        );
        assert_eq!(checker.check_interval, Duration::from_secs(5));
        assert_eq!(checker.check_timeout, Duration::from_secs(2));
        assert_eq!(checker.unhealthy_threshold, 2);
        assert_eq!(checker.healthy_threshold, 3);
    }

    #[test]
    fn test_should_mark_healthy() {
        let checker = HealthChecker::new();
        let mut endpoint = UpstreamEndpoint::new(
            Region::UsEast1,
            "127.0.0.1:8080".parse().unwrap(),
        );
        
        assert!(!checker.should_mark_healthy(&endpoint));
        
        endpoint.consecutive_successes = HEALTH_CHECK_HEALTHY_THRESHOLD;
        assert!(checker.should_mark_healthy(&endpoint));
    }

    #[test]
    fn test_should_mark_unhealthy() {
        let checker = HealthChecker::new();
        let mut endpoint = UpstreamEndpoint::new(
            Region::UsEast1,
            "127.0.0.1:8080".parse().unwrap(),
        );
        
        assert!(!checker.should_mark_unhealthy(&endpoint));
        
        endpoint.consecutive_failures = HEALTH_CHECK_UNHEALTHY_THRESHOLD;
        assert!(checker.should_mark_unhealthy(&endpoint));
    }

    #[tokio::test]
    async fn test_check_endpoint_invalid_address() {
        let checker = HealthChecker::new();
        let addr: SocketAddr = "127.0.0.1:9999".parse().unwrap();
        let is_healthy = checker.check_endpoint(addr).await;
        assert!(!is_healthy);
    }
}
