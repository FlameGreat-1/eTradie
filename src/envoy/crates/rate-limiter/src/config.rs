use etradie_envoy_common::{
    GLOBAL_RATE_LIMIT_PERIOD_SECS, GLOBAL_RATE_LIMIT_REQUESTS, IP_RATE_LIMIT_PERIOD_SECS,
    IP_RATE_LIMIT_REQUESTS,
};

#[derive(Debug, Clone)]
pub struct RateLimitConfig {
    pub global_enabled: bool,
    pub global_requests: u64,
    pub global_period_secs: u64,
    pub ip_enabled: bool,
    pub ip_requests: u64,
    pub ip_period_secs: u64,
}

impl RateLimitConfig {
    pub fn new() -> Self {
        Self {
            global_enabled: true,
            global_requests: GLOBAL_RATE_LIMIT_REQUESTS,
            global_period_secs: GLOBAL_RATE_LIMIT_PERIOD_SECS,
            ip_enabled: true,
            ip_requests: IP_RATE_LIMIT_REQUESTS,
            ip_period_secs: IP_RATE_LIMIT_PERIOD_SECS,
        }
    }

    pub fn with_global_limit(mut self, requests: u64, period_secs: u64) -> Self {
        self.global_requests = requests;
        self.global_period_secs = period_secs;
        self
    }

    pub fn with_ip_limit(mut self, requests: u64, period_secs: u64) -> Self {
        self.ip_requests = requests;
        self.ip_period_secs = period_secs;
        self
    }

    pub fn disable_global(mut self) -> Self {
        self.global_enabled = false;
        self
    }

    pub fn disable_ip(mut self) -> Self {
        self.ip_enabled = false;
        self
    }

    pub fn global_refill_rate(&self) -> u64 {
        if self.global_period_secs == 0 {
            return self.global_requests;
        }
        self.global_requests / self.global_period_secs
    }

    pub fn ip_refill_rate(&self) -> u64 {
        if self.ip_period_secs == 0 {
            return self.ip_requests;
        }
        self.ip_requests / self.ip_period_secs
    }

    pub fn validate(&self) -> Result<(), String> {
        if self.global_enabled {
            if self.global_requests == 0 {
                return Err("Global rate limit requests must be greater than 0".to_string());
            }
            if self.global_period_secs == 0 {
                return Err("Global rate limit period must be greater than 0".to_string());
            }
        }

        if self.ip_enabled {
            if self.ip_requests == 0 {
                return Err("IP rate limit requests must be greater than 0".to_string());
            }
            if self.ip_period_secs == 0 {
                return Err("IP rate limit period must be greater than 0".to_string());
            }
        }

        Ok(())
    }
}

impl Default for RateLimitConfig {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = RateLimitConfig::new();
        assert_eq!(config.global_requests, GLOBAL_RATE_LIMIT_REQUESTS);
        assert_eq!(config.ip_requests, IP_RATE_LIMIT_REQUESTS);
        assert!(config.global_enabled);
        assert!(config.ip_enabled);
    }

    #[test]
    fn test_custom_config() {
        let config = RateLimitConfig::new()
            .with_global_limit(5000, 30)
            .with_ip_limit(500, 30);

        assert_eq!(config.global_requests, 5000);
        assert_eq!(config.global_period_secs, 30);
        assert_eq!(config.ip_requests, 500);
        assert_eq!(config.ip_period_secs, 30);
    }

    #[test]
    fn test_refill_rate_calculation() {
        let config = RateLimitConfig::new()
            .with_global_limit(10000, 60)
            .with_ip_limit(1000, 60);

        assert_eq!(config.global_refill_rate(), 166);
        assert_eq!(config.ip_refill_rate(), 16);
    }

    #[test]
    fn test_validation() {
        let config = RateLimitConfig::new();
        assert!(config.validate().is_ok());

        let invalid_config = RateLimitConfig::new().with_global_limit(0, 60);
        assert!(invalid_config.validate().is_err());
    }
}
