use crate::context::RequestContext;
use etradie_envoy_common::{FilterDecision, Logger, MetricsCollector};
use etradie_envoy_header_validator::{HeaderValidator, ValidationRules};
use std::time::SystemTime;

pub struct HeaderFilterIntegration {
    validator: HeaderValidator,
    logger: Logger,
    metrics: MetricsCollector,
}

impl HeaderFilterIntegration {
    pub fn new(rules: ValidationRules) -> Result<Self, String> {
        let validator = HeaderValidator::new(rules).map_err(|e| e.message())?;

        Ok(Self {
            validator,
            logger: Logger::new("header_filter"),
            metrics: MetricsCollector::new("header_filter"),
        })
    }

    pub fn with_defaults() -> Result<Self, String> {
        Self::new(ValidationRules::new())
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
                "Executing header validation filter for {} {}",
                context.method(),
                context.path()
            ),
        );

        let decision = self
            .validator
            .validate(context.trace_id(), headers, context.method());

        let duration_ms = current_timestamp_ms().saturating_sub(start_time);
        self.record_metrics(&decision, duration_ms);

        if !decision.allowed {
            self.logger.warn(
                context.trace_id(),
                &format!(
                    "Header validation failed: {}",
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
    fn test_header_filter_creation() {
        let filter = HeaderFilterIntegration::with_defaults();
        assert!(filter.is_ok());
    }

    #[test]
    fn test_header_filter_execution_valid() {
        let filter = HeaderFilterIntegration::with_defaults().unwrap();

        let headers = vec![
            ("user-agent".to_string(), "test-agent".to_string()),
            ("content-type".to_string(), "application/json".to_string()),
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
    fn test_header_filter_execution_invalid() {
        let filter = HeaderFilterIntegration::with_defaults().unwrap();

        let headers = vec![("content-type".to_string(), "application/json".to_string())];

        let context = crate::context::RequestContext::new(
            "POST".to_string(),
            "/api/v1/users".to_string(),
            &headers,
        );

        let decision = filter.execute(&context, &headers);
        assert!(!decision.allowed);
    }

    #[test]
    fn test_header_filter_execution_multiple_headers() {
        let filter = HeaderFilterIntegration::with_defaults().unwrap();

        let headers = vec![
            ("user-agent".to_string(), "test-agent".to_string()),
            ("content-type".to_string(), "application/json".to_string()),
            ("accept".to_string(), "application/json".to_string()),
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
    fn test_custom_validation_rules() {
        let rules = ValidationRules::new()
            .with_max_header_size(4096)
            .with_max_header_count(50);

        let filter = HeaderFilterIntegration::new(rules);
        assert!(filter.is_ok());
    }
}
