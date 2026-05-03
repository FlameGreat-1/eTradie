use crate::{
    global::{GlobalConnectionGuard, GlobalConnectionLimiter},
    per_ip::{PerIpConnectionGuard, PerIpConnectionLimiter},
};
use edge_ingress_common::{
    constants::{MAX_CONNECTIONS_PER_IP, MAX_GLOBAL_CONNECTIONS},
    metrics::record_connection_rejected, Result,
};
use std::net::IpAddr;
use tracing::{debug, info};

#[derive(Debug)]
pub struct ConnectionLimiter {
    global_limiter: GlobalConnectionLimiter,
    per_ip_limiter: PerIpConnectionLimiter,
}

impl ConnectionLimiter {
    pub fn new(max_global: usize, max_per_ip: usize) -> Self {
        info!(
            max_global_connections = max_global,
            max_per_ip_connections = max_per_ip,
            "connection limiter initialized"
        );

        Self {
            global_limiter: GlobalConnectionLimiter::new(max_global),
            per_ip_limiter: PerIpConnectionLimiter::new(max_per_ip),
        }
    }

    pub fn with_default_limits() -> Self {
        Self::new(MAX_GLOBAL_CONNECTIONS, MAX_CONNECTIONS_PER_IP)
    }

    pub fn acquire(&self, ip: IpAddr) -> Result<ConnectionGuard> {
        let global_guard = self.global_limiter.acquire().map_err(|e| {
            record_connection_rejected("global_limit");
            e
        })?;

        let per_ip_guard = self.per_ip_limiter.acquire(ip).map_err(|e| {
            record_connection_rejected("per_ip_limit");
            e
        })?;

        debug!(
            ip = %ip,
            global_active = self.global_limiter.active_connections(),
            per_ip_active = self.per_ip_limiter.active_connections(ip),
            "connection limits acquired"
        );

        Ok(ConnectionGuard {
            _global_guard: global_guard,
            _per_ip_guard: per_ip_guard,
        })
    }

    pub fn global_active_connections(&self) -> usize {
        self.global_limiter.active_connections()
    }

    pub fn per_ip_active_connections(&self, ip: IpAddr) -> usize {
        self.per_ip_limiter.active_connections(ip)
    }

    pub fn global_available_connections(&self) -> usize {
        self.global_limiter.available_connections()
    }

    pub fn total_tracked_ips(&self) -> usize {
        self.per_ip_limiter.total_tracked_ips()
    }

    pub fn cleanup_idle_ips(&self) {
        self.per_ip_limiter.cleanup_idle_ips();
    }

    pub fn max_global_connections(&self) -> usize {
        self.global_limiter.max_connections()
    }

    pub fn max_per_ip_connections(&self) -> usize {
        self.per_ip_limiter.max_connections_per_ip()
    }
}

#[derive(Debug)]
pub struct ConnectionGuard<'a> {
    _global_guard: GlobalConnectionGuard<'a>,
    _per_ip_guard: PerIpConnectionGuard,
}

#[cfg(test)]
mod tests {
    use super::*;
    use edge_ingress_common::EdgeError;

    #[test]
    fn test_new_limiter() {
        let limiter = ConnectionLimiter::new(1000, 100);
        assert_eq!(limiter.max_global_connections(), 1000);
        assert_eq!(limiter.max_per_ip_connections(), 100);
    }

    #[test]
    fn test_with_default_limits() {
        let limiter = ConnectionLimiter::with_default_limits();
        assert_eq!(limiter.max_global_connections(), MAX_GLOBAL_CONNECTIONS);
        assert_eq!(limiter.max_per_ip_connections(), MAX_CONNECTIONS_PER_IP);
    }

    #[test]
    fn test_acquire_success() {
        let limiter = ConnectionLimiter::new(100, 10);
        let ip: IpAddr = "192.168.1.1".parse().unwrap();
        let guard = limiter.acquire(ip);
        assert!(guard.is_ok());
        assert_eq!(limiter.global_active_connections(), 1);
        assert_eq!(limiter.per_ip_active_connections(ip), 1);
    }

    #[test]
    fn test_acquire_multiple_ips() {
        let limiter = ConnectionLimiter::new(100, 10);
        let ip1: IpAddr = "192.168.1.1".parse().unwrap();
        let ip2: IpAddr = "192.168.1.2".parse().unwrap();
        
        let _guard1 = limiter.acquire(ip1).unwrap();
        let _guard2 = limiter.acquire(ip2).unwrap();
        
        assert_eq!(limiter.global_active_connections(), 2);
        assert_eq!(limiter.per_ip_active_connections(ip1), 1);
        assert_eq!(limiter.per_ip_active_connections(ip2), 1);
        assert_eq!(limiter.total_tracked_ips(), 2);
    }

    #[test]
    fn test_acquire_exceeds_global_limit() {
        let limiter = ConnectionLimiter::new(2, 10);
        let ip1: IpAddr = "192.168.1.1".parse().unwrap();
        let ip2: IpAddr = "192.168.1.2".parse().unwrap();
        let ip3: IpAddr = "192.168.1.3".parse().unwrap();
        
        let _guard1 = limiter.acquire(ip1).unwrap();
        let _guard2 = limiter.acquire(ip2).unwrap();
        let result = limiter.acquire(ip3);
        
        assert!(result.is_err());
        assert!(matches!(
            result.unwrap_err(),
            EdgeError::ConnectionLimitExceeded { .. }
        ));
    }

    #[test]
    fn test_acquire_exceeds_per_ip_limit() {
        let limiter = ConnectionLimiter::new(100, 2);
        let ip: IpAddr = "192.168.1.1".parse().unwrap();
        
        let _guard1 = limiter.acquire(ip).unwrap();
        let _guard2 = limiter.acquire(ip).unwrap();
        let result = limiter.acquire(ip);
        
        assert!(result.is_err());
        assert!(matches!(
            result.unwrap_err(),
            EdgeError::PerIpConnectionLimitExceeded { .. }
        ));
    }

    #[test]
    fn test_guard_drop_releases() {
        let limiter = ConnectionLimiter::new(100, 10);
        let ip: IpAddr = "192.168.1.1".parse().unwrap();
        
        {
            let _guard = limiter.acquire(ip).unwrap();
            assert_eq!(limiter.global_active_connections(), 1);
            assert_eq!(limiter.per_ip_active_connections(ip), 1);
        }
        
        assert_eq!(limiter.global_active_connections(), 0);
        assert_eq!(limiter.per_ip_active_connections(ip), 0);
    }

    #[test]
    fn test_global_available_connections() {
        let limiter = ConnectionLimiter::new(10, 5);
        assert_eq!(limiter.global_available_connections(), 10);
        
        let ip: IpAddr = "192.168.1.1".parse().unwrap();
        let _guard = limiter.acquire(ip).unwrap();
        assert_eq!(limiter.global_available_connections(), 9);
    }

    #[test]
    fn test_cleanup_idle_ips() {
        let limiter = ConnectionLimiter::new(100, 10);
        let ip1: IpAddr = "192.168.1.1".parse().unwrap();
        let ip2: IpAddr = "192.168.1.2".parse().unwrap();
        
        let _guard1 = limiter.acquire(ip1).unwrap();
        {
            let _guard2 = limiter.acquire(ip2).unwrap();
            assert_eq!(limiter.total_tracked_ips(), 2);
        }
        
        limiter.cleanup_idle_ips();
        assert_eq!(limiter.total_tracked_ips(), 1);
    }
}
