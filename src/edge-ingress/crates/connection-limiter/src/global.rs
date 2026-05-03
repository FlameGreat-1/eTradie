use edge_ingress_common::{
    constants::MAX_GLOBAL_CONNECTIONS,
    metrics::{decrement_active_connections, increment_active_connections},
    EdgeError, Result,
};
use std::sync::atomic::{AtomicUsize, Ordering};
use tracing::{debug, warn};

#[derive(Debug)]
pub struct GlobalConnectionLimiter {
    active_connections: AtomicUsize,
    max_connections: usize,
}

impl GlobalConnectionLimiter {
    pub fn new(max_connections: usize) -> Self {
        Self {
            active_connections: AtomicUsize::new(0),
            max_connections,
        }
    }

    pub fn with_default_limit() -> Self {
        Self::new(MAX_GLOBAL_CONNECTIONS)
    }

    pub fn acquire(&self) -> Result<GlobalConnectionGuard> {
        let current = self.active_connections.fetch_add(1, Ordering::SeqCst);

        if current >= self.max_connections {
            self.active_connections.fetch_sub(1, Ordering::SeqCst);
            
            warn!(
                current_connections = current,
                max_connections = self.max_connections,
                "global connection limit exceeded"
            );

            return Err(EdgeError::ConnectionLimitExceeded {
                limit: self.max_connections,
            });
        }

        increment_active_connections();

        debug!(
            active_connections = current + 1,
            max_connections = self.max_connections,
            "global connection acquired"
        );

        Ok(GlobalConnectionGuard {
            limiter: self,
            released: false,
        })
    }

    pub fn active_connections(&self) -> usize {
        self.active_connections.load(Ordering::SeqCst)
    }

    pub fn max_connections(&self) -> usize {
        self.max_connections
    }

    pub fn available_connections(&self) -> usize {
        self.max_connections.saturating_sub(self.active_connections())
    }

    fn release(&self) {
        let previous = self.active_connections.fetch_sub(1, Ordering::SeqCst);
        decrement_active_connections();

        debug!(
            active_connections = previous.saturating_sub(1),
            "global connection released"
        );
    }
}

#[derive(Debug)]
pub struct GlobalConnectionGuard<'a> {
    limiter: &'a GlobalConnectionLimiter,
    released: bool,
}

impl<'a> Drop for GlobalConnectionGuard<'a> {
    fn drop(&mut self) {
        if !self.released {
            self.limiter.release();
            self.released = true;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new_limiter() {
        let limiter = GlobalConnectionLimiter::new(100);
        assert_eq!(limiter.max_connections(), 100);
        assert_eq!(limiter.active_connections(), 0);
    }

    #[test]
    fn test_with_default_limit() {
        let limiter = GlobalConnectionLimiter::with_default_limit();
        assert_eq!(limiter.max_connections(), MAX_GLOBAL_CONNECTIONS);
    }

    #[test]
    fn test_acquire_success() {
        let limiter = GlobalConnectionLimiter::new(10);
        let guard = limiter.acquire();
        assert!(guard.is_ok());
        assert_eq!(limiter.active_connections(), 1);
    }

    #[test]
    fn test_acquire_multiple() {
        let limiter = GlobalConnectionLimiter::new(10);
        let _guard1 = limiter.acquire().unwrap();
        let _guard2 = limiter.acquire().unwrap();
        let _guard3 = limiter.acquire().unwrap();
        assert_eq!(limiter.active_connections(), 3);
    }

    #[test]
    fn test_acquire_exceeds_limit() {
        let limiter = GlobalConnectionLimiter::new(2);
        let _guard1 = limiter.acquire().unwrap();
        let _guard2 = limiter.acquire().unwrap();
        let result = limiter.acquire();
        assert!(result.is_err());
        assert!(matches!(
            result.unwrap_err(),
            EdgeError::ConnectionLimitExceeded { .. }
        ));
    }

    #[test]
    fn test_guard_drop_releases() {
        let limiter = GlobalConnectionLimiter::new(10);
        {
            let _guard = limiter.acquire().unwrap();
            assert_eq!(limiter.active_connections(), 1);
        }
        assert_eq!(limiter.active_connections(), 0);
    }

    #[test]
    fn test_available_connections() {
        let limiter = GlobalConnectionLimiter::new(10);
        assert_eq!(limiter.available_connections(), 10);
        let _guard = limiter.acquire().unwrap();
        assert_eq!(limiter.available_connections(), 9);
    }
}
