use crate::context::RequestContext;
use etradie_envoy_common::{FilterDecision, Logger, MetricsCollector};
use etradie_envoy_request_validator::RequestValidator;
use std::time::SystemTime;

pub struct RequestFilterIntegration {
    validator: RequestValidator,
    logger: Logger,
    metrics: MetricsCollector,
}

impl RequestFilterIntegration {
    pub fn new(validator: RequestValidator) -> Self {
        Self {
            validator,
            logger: Logger::new("request_filter"),
            metrics: MetricsCollector::new("request_filter"),
        }
    }

    pub fn with_defaults() -> Self {
        Self::new(RequestValidator::new())
    }

    pub fn execute(
        &self,
        context: &RequestContext,
        headers: &[(String, String)],
    ) -> FilterDecision {
        let start_time = current_timestamp_ms();

        self.logger.debug(
            context.trace_id(),
            &format!(
                "Executing request validation filter for {} {}",
                context.method(),
                context.path()
            ),
        );

        let decision = self.validator.validate(
            context.trace_id(),
            context.method(),
            context.path(),
            headers,
        );

        let duration_ms = current_timestamp_ms().saturating_sub(start_time);
        self.record_metrics(&decision, duration_ms);

        if !decision.allowed {
            self.logger.warn(
                context.trace_id(),
                &format!(
                    "Request validation failed: {}",
                    decision.reason.as_ref().unwrap_or(&"Unknown".to_string())
                ),
            );
        }

        decision
    }

    fn record_metrics(&self, decision: &FilterDecision, duration_ms: u64) {
        self.metrics.record_histogram("execution_duration_ms", duration_ms);

        if decision.allowed {
            self.metrics.increment_counter("validations_passed");
        } else {
            self.metrics.increment_counter("validations_failed");
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
    fn test_request_filter_creation() {
        let filter = RequestFilterIntegration::with_defaults();
        assert_eq!(std::mem::size_of_val(&filter), std::mem::size_of::<RequestFilterIntegration>());
    }

    #[test]
    fn test_request_filter_execution_valid() {
        let filter = RequestFilterIntegration::with_defaults();
        
        let headers = vec![
            ("user-agent".to_string(), "test-agent".to_string()),
            ("content-type".to_string(), "application/json".to_string()),
            ("content-length".to_string(), "1024".to_string()),
        ];
        
        let context = crate::context::RequestContext::new(
            "POST".to_string(),
            "/api/v1/users".to_string(),
            &headers,
        );

        let decision = filter.execute(&context, &headers);
        assert!(decision.allowed);
    }

    #[test]
    fn test_request_filter_invalid_method() {
        let filter = RequestFilterIntegration::with_defaults();
        
        let headers = vec![
            ("user-agent".to_string(), "test-agent".to_string()),
        ];
        
        let context = crate::context::RequestContext::new(
            "DELETE".to_string(),
            "/api/v1/users".to_string(),
            &headers,
        );

        let decision = filter.execute(&context, &headers);
        assert!(!decision.allowed);
    }

    #[test]
    fn test_request_filter_payload_too_large() {
        let filter = RequestFilterIntegration::with_defaults();
        
        let headers = vec![
            ("user-agent".to_string(), "test-agent".to_string()),
            ("content-length".to_string(), "20000000".to_string()),
        ];
        
        let context = crate::context::RequestContext::new(
            "POST".to_string(),
            "/api/v1/users".to_string(),
            &headers,
        );

        let decision = filter.execute(&context, &headers);
        assert!(!decision.allowed);
    }

    #[test]
    fn test_request_filter_invalid_path() {
        let filter = RequestFilterIntegration::with_defaults();
        
        let headers = vec![
            ("user-agent".to_string(), "test-agent".to_string()),
        ];
        
        let context = crate::context::RequestContext::new(
            "GET".to_string(),
            "/api/../etc/passwd".to_string(),
            &headers,
        );

        let decision = filter.execute(&context, &headers);
        assert!(!decision.allowed);
    }

    #[test]
    fn test_request_filter_get_method() {
        let filter = RequestFilterIntegration::with_defaults();
        
        let headers = vec![
            ("user-agent".to_string(), "test-agent".to_string()),
        ];
        
        let context = crate::context::RequestContext::new(
            "GET".to_string(),
            "/api/v1/users".to_string(),
            &headers,
        );

        let decision = filter.execute(&context, &headers);
        assert!(decision.allowed);
    }
}
