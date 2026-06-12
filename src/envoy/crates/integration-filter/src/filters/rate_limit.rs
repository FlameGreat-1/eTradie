use crate::context::RequestContext;
use etradie_envoy_common::{FilterDecision, Logger, MetricsCollector};
use etradie_envoy_rate_limiter::{RateLimitConfig, RateLimiter};
use std::time::SystemTime;

pub struct RateLimitFilterIntegration {
    limiter: RateLimiter,
    logger: Logger,
    metrics: MetricsCollector,
}

impl RateLimitFilterIntegration {
    pub fn new(config: RateLimitConfig) -> Result<Self, String> {
        let limiter = RateLimiter::new(config)?;

        Ok(Self {
            limiter,
            logger: Logger::new("rate_limit_filter"),
            metrics: MetricsCollector::new("rate_limit_filter"),
        })
    }

    pub fn with_defaults() -> Result<Self, String> {
        Self::new(RateLimitConfig::new())
    }

    pub fn execute(&mut self, context: &RequestContext) -> FilterDecision {
        let start_time = current_timestamp_ms();

        self.logger.debug(
            context.trace_id(),
            &format!(
                "Executing rate limit filter for {} {}",
                context.method(),
                context.path()
            ),
        );

        let decision = self
            .limiter
            .check_limits(context.trace_id(), context.client_ip());

        let duration_ms = current_timestamp_ms().saturating_sub(start_time);
        self.record_metrics(&decision, duration_ms);

        if !decision.allowed {
            self.logger.warn(
                context.trace_id(),
                &format!(
                    "Rate limit exceeded: {}",
                    decision.reason.as_ref().unwrap_or(&"Unknown".to_string())
                ),
            );
        }

        decision
    }

    fn record_metrics(&self, decision: &FilterDecision, duration_ms: u64) {
        self.metrics
            .record_histogram("execution_duration_ms", duration_ms);

        if decision.allowed {
            self.metrics.increment_counter("requests_allowed");
        } else {
            self.metrics.increment_counter("requests_blocked");
        }
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
    fn test_rate_limit_filter_creation() {
        let filter = RateLimitFilterIntegration::with_defaults();
        assert!(filter.is_ok());
    }

    #[test]
    fn test_rate_limit_filter_execution() {
        let mut filter = RateLimitFilterIntegration::with_defaults().unwrap();

        let headers = vec![("x-forwarded-for".to_string(), "192.168.1.1".to_string())];

        let context = crate::context::RequestContext::new(
            "GET".to_string(),
            "/api/v1/users".to_string(),
            &headers,
        );

        let decision = filter.execute(&context);
        assert!(decision.allowed);
    }

    #[test]
    fn test_rate_limit_execution_multiple_requests() {
        let mut filter = RateLimitFilterIntegration::with_defaults().unwrap();

        let headers = vec![("x-forwarded-for".to_string(), "192.168.1.1".to_string())];

        let context = crate::context::RequestContext::new(
            "GET".to_string(),
            "/api/v1/users".to_string(),
            &headers,
        );

        // First request should be allowed
        let decision = filter.execute(&context);
        assert!(decision.allowed);

        // Subsequent requests should also be allowed (within limits)
        let decision = filter.execute(&context);
        assert!(decision.allowed);
    }

    #[test]
    fn test_custom_config() {
        let config = RateLimitConfig::new()
            .with_global_limit(5000, 60)
            .with_ip_limit(500, 60);

        let filter = RateLimitFilterIntegration::new(config);
        assert!(filter.is_ok());
    }
}
