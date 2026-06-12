use etradie_envoy_common::{
    utils::validation::validate_http_method, FilterResult, ALLOWED_HTTP_METHODS,
};

pub struct MethodValidator {
    allowed_methods: Vec<String>,
}

impl MethodValidator {
    pub fn new(allowed_methods: Vec<String>) -> Self {
        Self { allowed_methods }
    }

    pub fn with_default_methods() -> Self {
        Self {
            allowed_methods: ALLOWED_HTTP_METHODS.iter().map(|s| s.to_string()).collect(),
        }
    }

    pub fn validate(&self, method: &str) -> FilterResult<()> {
        let method_upper = method.to_uppercase();

        validate_http_method(
            &method_upper,
            &self
                .allowed_methods
                .iter()
                .map(|s| s.as_str())
                .collect::<Vec<_>>(),
        )?;

        Ok(())
    }

    pub fn is_method_allowed(&self, method: &str) -> bool {
        self.allowed_methods
            .iter()
            .any(|m| m.eq_ignore_ascii_case(method))
    }

    pub fn allowed_methods(&self) -> &[String] {
        &self.allowed_methods
    }
}

pub fn is_safe_method(method: &str) -> bool {
    matches!(method.to_uppercase().as_str(), "GET" | "HEAD" | "OPTIONS")
}

pub fn is_idempotent_method(method: &str) -> bool {
    matches!(
        method.to_uppercase().as_str(),
        "GET" | "HEAD" | "PUT" | "DELETE" | "OPTIONS"
    )
}

pub fn requires_body(method: &str) -> bool {
    matches!(method.to_uppercase().as_str(), "POST" | "PUT" | "PATCH")
}

pub fn normalize_method(method: &str) -> String {
    method.to_uppercase()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validator_creation() {
        let validator = MethodValidator::with_default_methods();
        // Default set covers the full gateway surface plus CORS preflight.
        assert_eq!(
            validator.allowed_methods().len(),
            ALLOWED_HTTP_METHODS.len()
        );
    }

    #[test]
    fn test_allowed_methods() {
        let validator = MethodValidator::with_default_methods();
        assert!(validator.validate("GET").is_ok());
        assert!(validator.validate("POST").is_ok());
        assert!(validator.validate("PUT").is_ok());
        assert!(validator.validate("DELETE").is_ok());
        assert!(validator.validate("PATCH").is_ok());
        assert!(validator.validate("HEAD").is_ok());
        assert!(validator.validate("OPTIONS").is_ok());
        assert!(validator.validate("get").is_ok());
        assert!(validator.validate("post").is_ok());
        assert!(validator.validate("put").is_ok());
    }

    #[test]
    fn test_disallowed_methods() {
        let validator = MethodValidator::with_default_methods();
        // Methods we deliberately do NOT allow (debug/proxy semantics).
        assert!(validator.validate("TRACE").is_err());
        assert!(validator.validate("CONNECT").is_err());
        assert!(validator.validate("PROPFIND").is_err());
    }

    #[test]
    fn test_is_method_allowed() {
        let validator = MethodValidator::with_default_methods();
        assert!(validator.is_method_allowed("GET"));
        assert!(validator.is_method_allowed("get"));
        assert!(validator.is_method_allowed("PUT"));
        assert!(validator.is_method_allowed("DELETE"));
        assert!(!validator.is_method_allowed("TRACE"));
    }

    #[test]
    fn test_is_safe_method() {
        assert!(is_safe_method("GET"));
        assert!(is_safe_method("HEAD"));
        assert!(is_safe_method("OPTIONS"));
        assert!(!is_safe_method("POST"));
        assert!(!is_safe_method("PUT"));
    }

    #[test]
    fn test_is_idempotent_method() {
        assert!(is_idempotent_method("GET"));
        assert!(is_idempotent_method("PUT"));
        assert!(is_idempotent_method("DELETE"));
        assert!(!is_idempotent_method("POST"));
    }

    #[test]
    fn test_requires_body() {
        assert!(requires_body("POST"));
        assert!(requires_body("PUT"));
        assert!(requires_body("PATCH"));
        assert!(!requires_body("GET"));
        assert!(!requires_body("DELETE"));
    }

    #[test]
    fn test_normalize_method() {
        assert_eq!(normalize_method("get"), "GET");
        assert_eq!(normalize_method("Post"), "POST");
        assert_eq!(normalize_method("DELETE"), "DELETE");
    }

    #[test]
    fn test_custom_allowed_methods() {
        let validator = MethodValidator::new(vec![
            "GET".to_string(),
            "POST".to_string(),
            "PUT".to_string(),
        ]);

        assert!(validator.validate("GET").is_ok());
        assert!(validator.validate("POST").is_ok());
        assert!(validator.validate("PUT").is_ok());
        assert!(validator.validate("DELETE").is_err());
    }
}
