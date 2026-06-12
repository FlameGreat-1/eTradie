mod method;
mod size;
mod structure;

pub use method::{
    is_idempotent_method, is_safe_method, normalize_method, requires_body, MethodValidator,
};
pub use size::{calculate_content_length, format_size, has_content_length, SizeValidator};
pub use structure::{
    extract_path_without_query, extract_query_string, is_valid_path_segment, normalize_path,
    parse_query_params, StructureValidator,
};

use etradie_envoy_common::{
    FilterDecision, FilterError, FilterResult, Logger, MetricsCollector, SecurityEvent,
    SecurityEventCode,
};

pub struct RequestValidator {
    method_validator: MethodValidator,
    size_validator: SizeValidator,
    structure_validator: StructureValidator,
    logger: Logger,
    metrics: MetricsCollector,
}

impl RequestValidator {
    pub fn new() -> Self {
        Self {
            method_validator: MethodValidator::with_default_methods(),
            size_validator: SizeValidator::with_default_limit(),
            structure_validator: StructureValidator::with_defaults(),
            logger: Logger::new("request_validator"),
            metrics: MetricsCollector::new("request_validator"),
        }
    }

    pub fn with_custom_config(
        method_validator: MethodValidator,
        size_validator: SizeValidator,
        structure_validator: StructureValidator,
    ) -> Self {
        Self {
            method_validator,
            size_validator,
            structure_validator,
            logger: Logger::new("request_validator"),
            metrics: MetricsCollector::new("request_validator"),
        }
    }

    pub fn validate(
        &self,
        trace_id: &str,
        method: &str,
        path: &str,
        headers: &[(String, String)],
    ) -> FilterDecision {
        if let Err(e) = self.validate_method(trace_id, method) {
            return self.create_deny_decision(trace_id, e);
        }

        if let Err(e) = self.validate_structure(trace_id, path, method) {
            return self.create_deny_decision(trace_id, e);
        }

        if let Err(e) = self.validate_size(trace_id, headers) {
            return self.create_deny_decision(trace_id, e);
        }

        self.logger.debug(trace_id, "Request validation passed");
        self.metrics.increment_counter("validations_passed");
        FilterDecision::allow()
    }

    fn validate_method(&self, trace_id: &str, method: &str) -> FilterResult<()> {
        self.method_validator.validate(method).map_err(|e| {
            self.logger
                .warn(trace_id, &format!("Invalid method: {}", method));
            e
        })
    }

    fn validate_structure(&self, trace_id: &str, path: &str, method: &str) -> FilterResult<()> {
        self.structure_validator
            .validate(path, method)
            .map_err(|e| {
                self.logger.warn(
                    trace_id,
                    &format!("Invalid request structure: {}", e.message()),
                );
                e
            })
    }

    fn validate_size(&self, trace_id: &str, headers: &[(String, String)]) -> FilterResult<()> {
        if let Some(content_length) = calculate_content_length(headers) {
            self.size_validator
                .validate_body_size(content_length)
                .map_err(|e| {
                    self.logger.warn(
                        trace_id,
                        &format!("Request body too large: {} bytes", content_length),
                    );
                    e
                })?;
        }

        Ok(())
    }

    fn create_deny_decision(&self, trace_id: &str, error: FilterError) -> FilterDecision {
        let event_code = match &error {
            FilterError::InvalidMethod { .. } => SecurityEventCode::InvalidMethod,
            FilterError::PayloadTooLarge { .. } => SecurityEventCode::PayloadTooLarge,
            _ => SecurityEventCode::InvalidHeader,
        };

        let event = SecurityEvent::new(event_code, trace_id.to_string(), error.message());

        self.metrics.record_security_event(event_code);
        self.metrics.increment_counter("validations_failed");

        FilterDecision::deny(error.message(), event)
    }
}

impl Default for RequestValidator {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validator_creation() {
        let validator = RequestValidator::new();
        assert!(validator.method_validator.is_method_allowed("GET"));
    }

    #[test]
    fn test_valid_request() {
        let validator = RequestValidator::new();
        let headers = vec![
            ("content-type".to_string(), "application/json".to_string()),
            ("content-length".to_string(), "1024".to_string()),
        ];

        let decision = validator.validate("trace-123", "POST", "/api/v1/users", &headers);
        assert!(decision.allowed);
    }

    #[test]
    fn test_invalid_method() {
        let validator = RequestValidator::new();
        let headers = vec![];

        let decision = validator.validate("trace-123", "DELETE", "/api/v1/users", &headers);
        assert!(!decision.allowed);
    }

    #[test]
    fn test_payload_too_large() {
        let validator = RequestValidator::new();
        let headers = vec![("content-length".to_string(), "20000000".to_string())];

        let decision = validator.validate("trace-123", "POST", "/api/v1/users", &headers);
        assert!(!decision.allowed);
    }

    #[test]
    fn test_invalid_path() {
        let validator = RequestValidator::new();
        let headers = vec![];

        let decision = validator.validate("trace-123", "GET", "/api/../etc/passwd", &headers);
        assert!(!decision.allowed);
    }
}
