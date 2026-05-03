use etradie_envoy_common::{FilterError, FilterResult};
use std::time::SystemTime;

#[derive(Debug, Clone)]
pub struct TokenBucket {
    capacity: u64,
    tokens: u64,
    refill_rate: u64,
    last_refill_ms: u64,
}

impl TokenBucket {
    pub fn new(capacity: u64, refill_rate_per_sec: u64) -> Self {
        Self {
            capacity,
            tokens: capacity,
            refill_rate: refill_rate_per_sec,
            last_refill_ms: current_timestamp_ms(),
        }
    }

    pub fn try_consume(&mut self, tokens: u64) -> FilterResult<()> {
        self.refill();

        if self.tokens >= tokens {
            self.tokens -= tokens;
            Ok(())
        } else {
            let retry_after_secs = self.calculate_retry_after(tokens);
            Err(FilterError::RateLimitExceeded {
                limit_type: "Token bucket".to_string(),
                retry_after_secs,
            })
        }
    }

    pub fn available_tokens(&self) -> u64 {
        self.tokens
    }

    pub fn capacity(&self) -> u64 {
        self.capacity
    }

    fn refill(&mut self) {
        let now_ms = current_timestamp_ms();
        let elapsed_ms = now_ms.saturating_sub(self.last_refill_ms);

        if elapsed_ms == 0 {
            return;
        }

        let tokens_to_add = (elapsed_ms * self.refill_rate) / 1000;

        if tokens_to_add > 0 {
            self.tokens = (self.tokens + tokens_to_add).min(self.capacity);
            self.last_refill_ms = now_ms;
        }
    }

    fn calculate_retry_after(&self, required_tokens: u64) -> u64 {
        if required_tokens > self.capacity {
            return 60;
        }

        let tokens_needed = required_tokens.saturating_sub(self.tokens);
        let seconds_needed = (tokens_needed * 1000) / self.refill_rate.max(1);

        seconds_needed.max(1).min(60)
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
    fn test_token_bucket_creation() {
        let bucket = TokenBucket::new(100, 10);
        assert_eq!(bucket.capacity(), 100);
        assert_eq!(bucket.available_tokens(), 100);
    }

    #[test]
    fn test_token_consumption() {
        let mut bucket = TokenBucket::new(100, 10);
        assert!(bucket.try_consume(50).is_ok());
        assert_eq!(bucket.available_tokens(), 50);
    }

    #[test]
    fn test_token_bucket_overflow() {
        let mut bucket = TokenBucket::new(100, 10);
        assert!(bucket.try_consume(150).is_err());
    }
}
