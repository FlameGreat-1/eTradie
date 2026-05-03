use edge_ingress_common::{
    constants::MAX_CONNECTIONS_PER_IP,
    EdgeError, Result,
};
use dashmap::DashMap;
use std::net::IpAddr;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use tracing::{debug, warn};

#[derive(Debug)]
pub struct PerIpConnectionLimiter {
    connections: Arc<DashMap<IpAddr, AtomicUsize>>,
    max_connections_per_ip: usize,
}

impl PerIpConnectionLimiter {
    pub fn new(max_connections_per_ip: usize) -> Self {
        Self {
            connections: Arc::new(DashMap::new()),
            max_connections_per_ip,
        }
    }

    pub fn with_default_limit() -> Self {
        Self::new(MAX_CONNECTIONS_PER_IP)
    }

    pub fn acquire(&self, ip: IpAddr) -> Result<PerIpConnectionGuard> {
        let counter = self
            .connections
            .entry(ip)
            .or_insert_with(|| AtomicUsize::new(0));

        let current = counter.fetch_add(1, Ordering::SeqCst);

        if current >= self.max_connections_per_ip {
            counter.fetch_sub(1, Ordering::SeqCst);

            warn!(
                ip = %ip,
                current_connections = current,
                max_connections = self.max_connections_per_ip,
                "per-IP connection limit exceeded"
            );

            return Err(EdgeError::PerIpConnectionLimitExceeded {
                ip: ip.to_string(),
                limit: self.max_connections_per_ip,
            });
        }

        debug!(
            ip = %ip,
            active_connections = current + 1,
            max_connections = self.max_connections_per_ip,
            "per-IP connection acquired"
        );

        Ok(PerIpConnectionGuard {
            limiter: Arc::clone(&self.connections),
            ip,
            released: false,
        })
    }

    pub fn active_connections(&self, ip: IpAddr) -> usize {
        self.connections
            .get(&ip)
            .map(|counter| counter.load(Ordering::SeqCst))
            .unwrap_or(0)
    }

    pub fn max_connections_per_ip(&self) -> usize {
        self.max_connections_per_ip
    }

    pub fn total_tracked_ips(&self) -> usize {
        self.connections.len()
    }

    pub fn cleanup_idle_ips(&self) {
        self.connections.retain(|_, counter| {
            counter.load(Ordering::SeqCst) > 0
        });
    }
}

#[derive(Debug)]
pub struct PerIpConnectionGuard {
    limiter: Arc<DashMap<IpAddr, AtomicUsize>>,
    ip: IpAddr,
    released: bool,
}

impl Drop for PerIpConnectionGuard {
    fn drop(&mut self) {
        if !self.released {
            if let Some(counter) = self.limiter.get(&self.ip) {
                let previous = counter.fetch_sub(1, Ordering::SeqCst);

                debug!(
                    ip = %self.ip,
                    active_connections = previous.saturating_sub(1),
                    "per-IP connection released"
                );

                if previous <= 1 {
                    drop(counter);
                    self.limiter.remove(&self.ip);
                }
            }
            self.released = true;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new_limiter() {
        let limiter = PerIpConnectionLimiter::new(100);
        assert_eq!(limiter.max_connections_per_ip(), 100);
    }

    #[test]
    fn test_with_default_limit() {
        let limiter = PerIpConnectionLimiter::with_default_limit();
        assert_eq!(limiter.max_connections_per_ip(), MAX_CONNECTIONS_PER_IP);
    }

    #[test]
    fn test_acquire_success() {
        let limiter = PerIpConnectionLimiter::new(10);
        let ip: IpAddr = "192.168.1.1".parse().unwrap();
        let guard = limiter.acquire(ip);
        assert!(guard.is_ok());
        assert_eq!(limiter.active_connections(ip), 1);
    }

    #[test]
    fn test_acquire_multiple_same_ip() {
        let limiter = PerIpConnectionLimiter::new(10);
        let ip: IpAddr = "192.168.1.1".parse().unwrap();
        let _guard1 = limiter.acquire(ip).unwrap();
        let _guard2 = limiter.acquire(ip).unwrap();
        assert_eq!(limiter.active_connections(ip), 2);
    }

    #[test]
    fn test_acquire_different_ips() {
        let limiter = PerIpConnectionLimiter::new(10);
        let ip1: IpAddr = "192.168.1.1".parse().unwrap();
        let ip2: IpAddr = "192.168.1.2".parse().unwrap();
        let _guard1 = limiter.acquire(ip1).unwrap();
        let _guard2 = limiter.acquire(ip2).unwrap();
        assert_eq!(limiter.active_connections(ip1), 1);
        assert_eq!(limiter.active_connections(ip2), 1);
        assert_eq!(limiter.total_tracked_ips(), 2);
    }

    #[test]
    fn test_acquire_exceeds_limit() {
        let limiter = PerIpConnectionLimiter::new(2);
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
        let limiter = PerIpConnectionLimiter::new(10);
        let ip: IpAddr = "192.168.1.1".parse().unwrap();
        {
            let _guard = limiter.acquire(ip).unwrap();
            assert_eq!(limiter.active_connections(ip), 1);
        }
        assert_eq!(limiter.active_connections(ip), 0);
    }

    #[test]
    fn test_cleanup_idle_ips() {
        let limiter = PerIpConnectionLimiter::new(10);
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
