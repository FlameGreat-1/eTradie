use crate::bucket::TokenBucket;
use etradie_envoy_common::{FilterError, FilterResult};
use std::collections::HashMap;
use std::time::SystemTime;

const CLEANUP_THRESHOLD: usize = 90_000;

#[derive(Debug)]
pub struct RateLimitStorage {
    global_bucket: TokenBucket,
    ip_buckets: HashMap<String, IpBucketEntry>,
}

#[derive(Debug, Clone)]
struct IpBucketEntry {
    bucket: TokenBucket,
    last_access_ms: u64,
}

impl RateLimitStorage {
    pub fn new(
        global_capacity: u64,
        global_refill_rate: u64,
        _ip_capacity: u64,
        _ip_refill_rate: u64,
    ) -> Self {
        Self {
            global_bucket: TokenBucket::new(global_capacity, global_refill_rate),
            ip_buckets: HashMap::with_capacity(1024),
        }
    }

    pub fn check_global_limit(&mut self) -> FilterResult<()> {
        self.global_bucket.try_consume(1).map_err(|e| {
            if let FilterError::RateLimitExceeded {
                retry_after_secs, ..
            } = e
            {
                FilterError::RateLimitExceeded {
                    limit_type: "Global".to_string(),
                    retry_after_secs,
                }
            } else {
                e
            }
        })
    }

    pub fn check_ip_limit(
        &mut self,
        ip: &str,
        capacity: u64,
        refill_rate: u64,
    ) -> FilterResult<()> {
        if self.ip_buckets.len() >= CLEANUP_THRESHOLD {
            self.cleanup_stale_entries();
        }

        let now_ms = current_timestamp_ms();

        let entry = self
            .ip_buckets
            .entry(ip.to_string())
            .or_insert_with(|| IpBucketEntry {
                bucket: TokenBucket::new(capacity, refill_rate),
                last_access_ms: now_ms,
            });

        entry.last_access_ms = now_ms;

        entry.bucket.try_consume(1).map_err(|e| {
            if let FilterError::RateLimitExceeded {
                retry_after_secs, ..
            } = e
            {
                FilterError::RateLimitExceeded {
                    limit_type: format!("IP ({})", ip),
                    retry_after_secs,
                }
            } else {
                e
            }
        })
    }

    pub fn global_tokens_remaining(&self) -> u64 {
        self.global_bucket.available_tokens()
    }

    pub fn ip_tokens_remaining(&self, ip: &str) -> Option<u64> {
        self.ip_buckets
            .get(ip)
            .map(|entry| entry.bucket.available_tokens())
    }

    pub fn tracked_ip_count(&self) -> usize {
        self.ip_buckets.len()
    }

    fn cleanup_stale_entries(&mut self) {
        let now_ms = current_timestamp_ms();
        let stale_threshold_ms = 300_000;

        self.ip_buckets
            .retain(|_, entry| now_ms.saturating_sub(entry.last_access_ms) < stale_threshold_ms);
    }
}

fn current_timestamp_ms() -> u64 {
    use proxy_wasm::hostcalls;
    match hostcalls::get_current_time() {
        Ok(time) => time
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64,
        Err(_) => 0,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_storage_creation() {
        let _storage = RateLimitStorage::new(10000, 166, 1000, 16);
    }

    #[test]
    fn test_global_limit() {
        let mut storage = RateLimitStorage::new(10, 1, 10, 1);
        for _ in 0..10 {
            assert!(storage.check_global_limit().is_ok());
        }
        assert!(storage.check_global_limit().is_err());
    }

    #[test]
    fn test_ip_limit() {
        let mut storage = RateLimitStorage::new(10000, 166, 10, 1);
        for _ in 0..10 {
            assert!(storage.check_ip_limit("192.168.1.1", 10, 1).is_ok());
        }
        assert!(storage.check_ip_limit("192.168.1.1", 10, 1).is_err());
    }

    #[test]
    fn test_multiple_ips() {
        let mut storage = RateLimitStorage::new(10000, 166, 10, 1);
        assert!(storage.check_ip_limit("192.168.1.1", 10, 1).is_ok());
        assert!(storage.check_ip_limit("192.168.1.2", 10, 1).is_ok());
        assert!(storage.check_ip_limit("192.168.1.1", 10, 1).is_ok());
        assert!(storage.check_ip_limit("192.168.1.2", 10, 1).is_ok());
    }

    #[test]
    fn test_global_tokens_remaining() {
        let mut storage = RateLimitStorage::new(10, 1, 10, 1);
        assert_eq!(storage.global_tokens_remaining(), 10);
        storage.check_global_limit().ok();
        assert_eq!(storage.global_tokens_remaining(), 9);
    }

    #[test]
    fn test_ip_tokens_remaining() {
        let mut storage = RateLimitStorage::new(10000, 166, 10, 1);
        assert_eq!(storage.ip_tokens_remaining("192.168.1.1"), None);
        storage.check_ip_limit("192.168.1.1", 10, 1).ok();
        assert!(storage.ip_tokens_remaining("192.168.1.1").is_some());
    }

    #[test]
    fn test_tracked_ip_count() {
        let mut storage = RateLimitStorage::new(10000, 166, 10, 1);
        assert_eq!(storage.tracked_ip_count(), 0);
        storage.check_ip_limit("192.168.1.1", 10, 1).ok();
        assert_eq!(storage.tracked_ip_count(), 1);
        storage.check_ip_limit("192.168.1.2", 10, 1).ok();
        assert_eq!(storage.tracked_ip_count(), 2);
    }

    #[test]
    fn test_cleanup_stale_entries() {
        let mut storage = RateLimitStorage::new(10000, 166, 10, 1);
        for i in 0..100 {
            let ip = format!("192.168.1.{}", i);
            assert!(storage.check_ip_limit(&ip, 10, 1).is_ok());
        }
        storage.cleanup_stale_entries();
    }
}
