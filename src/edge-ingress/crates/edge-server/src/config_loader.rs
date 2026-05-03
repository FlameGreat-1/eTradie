use edge_ingress_common::{EdgeError, Result};
use edge_ingress_connection_limiter::ConnectionLimiter;
use edge_ingress_geo_router::GeoIpLookup;
use edge_ingress_tls::TlsConfig;
use edge_ingress_upstream::{HealthChecker, RetryPolicy, UpstreamPool, UpstreamProxy};
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use std::path::{Path, PathBuf};
use std::time::Duration;
use tracing::info;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EdgeServerConfig {
    pub server: ServerConfig,
    pub tls: TlsConfig,
    pub upstream: UpstreamConfig,
    pub connection_limits: ConnectionLimitsConfig,
    pub health_check: HealthCheckConfig,
    pub retry: RetryConfig,
    pub geoip: GeoIpConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    pub tls_bind_address: SocketAddr,
    pub metrics_bind_address: SocketAddr,
    pub idle_timeout_secs: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpstreamConfig {
    pub endpoints: Vec<UpstreamEndpointConfig>,
    pub connect_timeout_secs: u64,
    pub request_timeout_secs: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpstreamEndpointConfig {
    pub region: String,
    pub address: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConnectionLimitsConfig {
    pub max_global_connections: usize,
    pub max_connections_per_ip: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthCheckConfig {
    pub interval_secs: u64,
    pub timeout_secs: u64,
    pub unhealthy_threshold: u32,
    pub healthy_threshold: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetryConfig {
    pub max_attempts: u8,
    pub backoff_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeoIpConfig {
    pub database_path: PathBuf,
}

impl EdgeServerConfig {
    pub fn from_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let contents = std::fs::read_to_string(path.as_ref()).map_err(|e| {
            EdgeError::Configuration(format!(
                "Failed to read config file {}: {}",
                path.as_ref().display(),
                e
            ))
        })?;

        let config: EdgeServerConfig = serde_yaml::from_str(&contents).map_err(|e| {
            EdgeError::Configuration(format!("Failed to parse config file: {}", e))
        })?;

        config.validate()?;

        info!(
            config_path = %path.as_ref().display(),
            "configuration loaded successfully"
        );

        Ok(config)
    }

    pub fn validate(&self) -> Result<()> {
        self.tls.validate()?;

        if self.upstream.endpoints.is_empty() {
            return Err(EdgeError::Configuration(
                "At least one upstream endpoint must be configured".to_string(),
            ));
        }

        if self.connection_limits.max_global_connections == 0 {
            return Err(EdgeError::Configuration(
                "max_global_connections must be greater than 0".to_string(),
            ));
        }

        if self.connection_limits.max_connections_per_ip == 0 {
            return Err(EdgeError::Configuration(
                "max_connections_per_ip must be greater than 0".to_string(),
            ));
        }

        if self.health_check.interval_secs == 0 {
            return Err(EdgeError::Configuration(
                "health_check.interval_secs must be greater than 0".to_string(),
            ));
        }

        if self.health_check.timeout_secs == 0 {
            return Err(EdgeError::Configuration(
                "health_check.timeout_secs must be greater than 0".to_string(),
            ));
        }

        if self.health_check.unhealthy_threshold == 0 {
            return Err(EdgeError::Configuration(
                "health_check.unhealthy_threshold must be greater than 0".to_string(),
            ));
        }

        if self.health_check.healthy_threshold == 0 {
            return Err(EdgeError::Configuration(
                "health_check.healthy_threshold must be greater than 0".to_string(),
            ));
        }

        if self.retry.max_attempts > 10 {
            return Err(EdgeError::Configuration(
                "retry.max_attempts cannot exceed 10".to_string(),
            ));
        }

        if !self.geoip.database_path.exists() {
            return Err(EdgeError::Configuration(format!(
                "GeoIP database not found at {}",
                self.geoip.database_path.display()
            )));
        }

        Ok(())
    }

    pub fn build_connection_limiter(&self) -> ConnectionLimiter {
        ConnectionLimiter::new(
            self.connection_limits.max_global_connections,
            self.connection_limits.max_connections_per_ip,
        )
    }

    pub fn build_geoip_lookup(&self) -> Result<GeoIpLookup> {
        GeoIpLookup::new(&self.geoip.database_path)
    }

    pub fn build_upstream_proxy(&self) -> Result<UpstreamProxy> {
        let pool = UpstreamPool::new();
        
        let health_checker = HealthChecker::with_config(
            Duration::from_secs(self.health_check.interval_secs),
            Duration::from_secs(self.health_check.timeout_secs),
            self.health_check.unhealthy_threshold,
            self.health_check.healthy_threshold,
        );

        let retry_policy = RetryPolicy::new(
            self.retry.max_attempts,
            self.retry.backoff_ms,
        );

        let connect_timeout = Duration::from_secs(self.upstream.connect_timeout_secs);

        Ok(UpstreamProxy::with_config(
            pool,
            health_checker,
            retry_policy,
            connect_timeout,
        ))
    }

    pub fn idle_timeout(&self) -> Duration {
        Duration::from_secs(self.server.idle_timeout_secs)
    }

    pub fn upstream_request_timeout(&self) -> Duration {
        Duration::from_secs(self.upstream.request_timeout_secs)
    }
}

impl Default for EdgeServerConfig {
    fn default() -> Self {
        Self {
            server: ServerConfig {
                tls_bind_address: "0.0.0.0:443".parse().unwrap(),
                metrics_bind_address: "0.0.0.0:9902".parse().unwrap(),
                idle_timeout_secs: 300,
            },
            tls: TlsConfig::default(),
            upstream: UpstreamConfig {
                endpoints: vec![],
                connect_timeout_secs: 5,
                request_timeout_secs: 60,
            },
            connection_limits: ConnectionLimitsConfig {
                max_global_connections: 100_000,
                max_connections_per_ip: 1_000,
            },
            health_check: HealthCheckConfig {
                interval_secs: 10,
                timeout_secs: 3,
                unhealthy_threshold: 3,
                healthy_threshold: 2,
            },
            retry: RetryConfig {
                max_attempts: 1,
                backoff_ms: 100,
            },
            geoip: GeoIpConfig {
                database_path: PathBuf::from("/data/geoip/GeoLite2-City.mmdb"),
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = EdgeServerConfig::default();
        assert_eq!(config.server.tls_bind_address.port(), 443);
        assert_eq!(config.server.metrics_bind_address.port(), 9902);
    }

    #[test]
    fn test_validate_empty_endpoints() {
        let config = EdgeServerConfig::default();
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_validate_zero_global_connections() {
        let mut config = EdgeServerConfig::default();
        config.upstream.endpoints.push(UpstreamEndpointConfig {
            region: "us-east-1".to_string(),
            address: "127.0.0.1:8080".to_string(),
        });
        config.connection_limits.max_global_connections = 0;
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_validate_zero_per_ip_connections() {
        let mut config = EdgeServerConfig::default();
        config.upstream.endpoints.push(UpstreamEndpointConfig {
            region: "us-east-1".to_string(),
            address: "127.0.0.1:8080".to_string(),
        });
        config.connection_limits.max_connections_per_ip = 0;
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_validate_excessive_retry_attempts() {
        let mut config = EdgeServerConfig::default();
        config.upstream.endpoints.push(UpstreamEndpointConfig {
            region: "us-east-1".to_string(),
            address: "127.0.0.1:8080".to_string(),
        });
        config.retry.max_attempts = 15;
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_build_connection_limiter() {
        let config = EdgeServerConfig::default();
        let limiter = config.build_connection_limiter();
        assert_eq!(limiter.max_global_connections(), 100_000);
        assert_eq!(limiter.max_per_ip_connections(), 1_000);
    }

    #[test]
    fn test_idle_timeout() {
        let config = EdgeServerConfig::default();
        assert_eq!(config.idle_timeout(), Duration::from_secs(300));
    }

    #[test]
    fn test_upstream_request_timeout() {
        let config = EdgeServerConfig::default();
        assert_eq!(config.upstream_request_timeout(), Duration::from_secs(60));
    }
}
