use crate::content_type::ContentTypeValidator;
use crate::rules::ValidationRules;
use crate::sanitizer::HeaderSanitizer;
use etradie_envoy_common::{
    utils::validation::{validate_header_count, validate_header_size, validate_user_agent},
    FilterDecision, FilterError, FilterResult, Logger, MetricsCollector, SecurityEvent,
    SecurityEventCode, HEADER_USER_AGENT, HEADER_X_TRACE_ID,
};

pub struct HeaderValidator {
    rules: ValidationRules,
    content_type_validator: ContentTypeValidator,
    sanitizer: HeaderSanitizer,
    logger: Logger,
    metrics: MetricsCollector,
}

impl HeaderValidator {
    pub fn new(rules: ValidationRules) -> FilterResult<Self> {
        rules.validate().map_err(|e| FilterError::InternalError {
            message: format!("Invalid validation rules: {}", e),
        })?;

        let content_type_validator = ContentTypeValidator::new(rules.clone());
        let sanitizer = HeaderSanitizer::new(rules.validate_ascii);

        Ok(Self {
            rules,
            content_type_validator,
            sanitizer,
            logger: Logger::new("header_validator"),
            metrics: MetricsCollector::new("header_validator"),
        })
    }

    pub fn validate(
        &self,
        trace_id: &str,
        headers: &[(String, String)],
        method: &str,
    ) -> FilterDecision {
        if let Err(e) = self.validate_header_constraints(headers) {
            return self.create_deny_decision(trace_id, e);
        }

        if let Err(e) = self.validate_required_headers(headers) {
            return self.create_deny_decision(trace_id, e);
        }

        if let Err(e) = self.validate_header_values(headers) {
            return self.create_deny_decision(trace_id, e);
        }

        if let Err(e) = self.content_type_validator.validate(headers, method) {
            return self.create_deny_decision(trace_id, e);
        }

        if let Err(e) = self.validate_trace_id(headers) {
            return self.create_deny_decision(trace_id, e);
        }

        self.logger.debug(trace_id, "Header validation passed");
        self.metrics.increment_counter("validations_passed");
        FilterDecision::allow()
    }

    fn validate_header_constraints(&self, headers: &[(String, String)]) -> FilterResult<()> {
        validate_header_count(headers.len())?;
        validate_header_size(headers)?;
        Ok(())
    }

    fn validate_required_headers(&self, headers: &[(String, String)]) -> FilterResult<()> {
        for required in &self.rules.required_headers {
            let found = headers
                .iter()
                .any(|(name, _)| name.eq_ignore_ascii_case(required));

            if !found {
                return Err(FilterError::MissingRequiredHeader {
                    header: required.clone(),
                });
            }
        }

        Ok(())
    }

    fn validate_header_values(&self, headers: &[(String, String)]) -> FilterResult<()> {
        for (name, value) in headers {
            self.sanitizer.validate_header_value(name, value)?;

            if name.eq_ignore_ascii_case(HEADER_USER_AGENT) {
                validate_user_agent(value)?;
            }
        }

        Ok(())
    }

    fn validate_trace_id(&self, headers: &[(String, String)]) -> FilterResult<()> {
        if let Some((_, trace_id)) = headers
            .iter()
            .find(|(name, _)| name.eq_ignore_ascii_case(HEADER_X_TRACE_ID))
        {
            etradie_envoy_common::validate_trace_id(trace_id)?;
        }

        Ok(())
    }

    fn create_deny_decision(&self, trace_id: &str, error: FilterError) -> FilterDecision {
        let event_code = match &error {
            FilterError::InvalidHeader { .. } => SecurityEventCode::InvalidHeader,
            FilterError::MissingRequiredHeader { .. } => SecurityEventCode::MissingRequiredHeader,
            FilterError::InvalidContentType { .. } => SecurityEventCode::InvalidContentType,
            FilterError::HeaderSizeLimitExceeded { .. } => {
                SecurityEventCode::HeaderSizeLimitExceeded
            }
            FilterError::HeaderCountLimitExceeded { .. } => {
                SecurityEventCode::HeaderCountLimitExceeded
            }
            FilterError::InvalidTraceId { .. } => SecurityEventCode::InvalidTraceId,
            _ => SecurityEventCode::InvalidHeader,
        };

        let event = SecurityEvent::new(event_code, trace_id.to_string(), error.message());

        self.logger.warn(
            trace_id,
            &format!("Header validation failed: {}", error.message()),
        );
        self.metrics.record_security_event(event_code);
        self.metrics.increment_counter("validations_failed");

        FilterDecision::deny(error.message(), event)
    }

    pub fn sanitize_headers(
        &self,
        headers: Vec<(String, String)>,
    ) -> FilterResult<Vec<(String, String)>> {
        if !self.rules.sanitize_headers {
            return Ok(headers);
        }

        let sanitized = self.sanitizer.sanitize_headers(headers)?;
        let cleaned = self.sanitizer.remove_dangerous_headers(sanitized);

        Ok(cleaned)
    }
}

pub fn extract_header_value<'a>(
    headers: &'a [(String, String)],
    header_name: &str,
) -> Option<&'a str> {
    headers
        .iter()
        .find(|(name, _)| name.eq_ignore_ascii_case(header_name))
        .map(|(_, value)| value.as_str())
}

pub fn has_header(headers: &[(String, String)], header_name: &str) -> bool {
    headers
        .iter()
        .any(|(name, _)| name.eq_ignore_ascii_case(header_name))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validator_creation() {
        let rules = ValidationRules::new();
        let validator = HeaderValidator::new(rules);
        assert!(validator.is_ok());
    }

    #[test]
    fn test_valid_headers() {
        let rules = ValidationRules::new();
        let validator = HeaderValidator::new(rules).unwrap();

        let headers = vec![
            ("user-agent".to_string(), "test-agent".to_string()),
            ("content-type".to_string(), "application/json".to_string()),
        ];

        let decision = validator.validate("trace-123", &headers, "POST");
        assert!(decision.allowed);
    }

    #[test]
    fn test_missing_required_header() {
        let rules = ValidationRules::new();
        let validator = HeaderValidator::new(rules).unwrap();

        let headers = vec![("content-type".to_string(), "application/json".to_string())];

        let decision = validator.validate("trace-123", &headers, "POST");
        assert!(!decision.allowed);
    }

    #[test]
    fn test_invalid_content_type() {
        let rules = ValidationRules::new();
        let validator = HeaderValidator::new(rules).unwrap();

        let headers = vec![
            ("user-agent".to_string(), "test-agent".to_string()),
            ("content-type".to_string(), "application/xml".to_string()),
        ];

        let decision = validator.validate("trace-123", &headers, "POST");
        assert!(!decision.allowed);
    }

    #[test]
    fn test_extract_header_value() {
        let headers = vec![
            ("user-agent".to_string(), "test-agent".to_string()),
            ("content-type".to_string(), "application/json".to_string()),
        ];

        let value = extract_header_value(&headers, "user-agent");
        assert_eq!(value, Some("test-agent"));

        let missing = extract_header_value(&headers, "missing-header");
        assert_eq!(missing, None);
    }

    #[test]
    fn test_has_header() {
        let headers = vec![("user-agent".to_string(), "test-agent".to_string())];

        assert!(has_header(&headers, "user-agent"));
        assert!(has_header(&headers, "User-Agent"));
        assert!(!has_header(&headers, "missing-header"));
    }
}
