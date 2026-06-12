use etradie_envoy_common::{
    ALLOWED_CONTENT_TYPES, HEADER_USER_AGENT, MAX_HEADER_COUNT, MAX_HEADER_SIZE,
    MAX_USER_AGENT_SIZE,
};

#[derive(Debug, Clone)]
pub struct ValidationRules {
    pub required_headers: Vec<String>,
    pub allowed_content_types: Vec<String>,
    pub max_header_size: usize,
    pub max_header_count: usize,
    pub max_user_agent_size: usize,
    pub validate_ascii: bool,
    pub sanitize_headers: bool,
}

impl ValidationRules {
    pub fn new() -> Self {
        Self {
            required_headers: vec![HEADER_USER_AGENT.to_string()],
            allowed_content_types: ALLOWED_CONTENT_TYPES
                .iter()
                .map(|s| s.to_string())
                .collect(),
            max_header_size: MAX_HEADER_SIZE,
            max_header_count: MAX_HEADER_COUNT,
            max_user_agent_size: MAX_USER_AGENT_SIZE,
            validate_ascii: true,
            sanitize_headers: true,
        }
    }

    pub fn with_required_headers(mut self, headers: Vec<String>) -> Self {
        self.required_headers = headers;
        self
    }

    pub fn with_allowed_content_types(mut self, content_types: Vec<String>) -> Self {
        self.allowed_content_types = content_types;
        self
    }

    pub fn with_max_header_size(mut self, size: usize) -> Self {
        self.max_header_size = size;
        self
    }

    pub fn with_max_header_count(mut self, count: usize) -> Self {
        self.max_header_count = count;
        self
    }

    pub fn disable_ascii_validation(mut self) -> Self {
        self.validate_ascii = false;
        self
    }

    pub fn disable_sanitization(mut self) -> Self {
        self.sanitize_headers = false;
        self
    }

    pub fn is_required_header(&self, header_name: &str) -> bool {
        self.required_headers
            .iter()
            .any(|h| h.eq_ignore_ascii_case(header_name))
    }

    pub fn is_content_type_allowed(&self, content_type: &str) -> bool {
        let normalized = content_type
            .split(';')
            .next()
            .unwrap_or("")
            .trim()
            .to_lowercase();

        self.allowed_content_types
            .iter()
            .any(|allowed| normalized == allowed.to_lowercase())
    }

    pub fn validate(&self) -> Result<(), String> {
        if self.max_header_size == 0 {
            return Err("Max header size must be greater than 0".to_string());
        }

        if self.max_header_count == 0 {
            return Err("Max header count must be greater than 0".to_string());
        }

        if self.max_user_agent_size == 0 {
            return Err("Max User-Agent size must be greater than 0".to_string());
        }

        if self.allowed_content_types.is_empty() {
            return Err("At least one Content-Type must be allowed".to_string());
        }

        Ok(())
    }
}

impl Default for ValidationRules {
    fn default() -> Self {
        Self::new()
    }
}

pub fn is_method_requiring_content_type(method: &str) -> bool {
    matches!(method.to_uppercase().as_str(), "POST" | "PUT" | "PATCH")
}

pub fn normalize_header_name(name: &str) -> String {
    name.to_lowercase()
}

pub fn is_sensitive_header(name: &str) -> bool {
    const SENSITIVE_HEADERS: &[&str] = &[
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-auth-token",
    ];

    SENSITIVE_HEADERS
        .iter()
        .any(|h| h.eq_ignore_ascii_case(name))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_rules() {
        let rules = ValidationRules::new();
        assert!(rules.is_required_header("user-agent"));
        assert!(rules.is_content_type_allowed("application/json"));
        assert_eq!(rules.max_header_size, MAX_HEADER_SIZE);
    }

    #[test]
    fn test_custom_rules() {
        let rules = ValidationRules::new()
            .with_max_header_size(4096)
            .with_max_header_count(50);

        assert_eq!(rules.max_header_size, 4096);
        assert_eq!(rules.max_header_count, 50);
    }

    #[test]
    fn test_content_type_validation() {
        let rules = ValidationRules::new();
        assert!(rules.is_content_type_allowed("application/json"));
        assert!(rules.is_content_type_allowed("application/json; charset=utf-8"));
        assert!(!rules.is_content_type_allowed("application/xml"));
    }

    #[test]
    fn test_method_requiring_content_type() {
        assert!(is_method_requiring_content_type("POST"));
        assert!(is_method_requiring_content_type("PUT"));
        assert!(is_method_requiring_content_type("PATCH"));
        assert!(!is_method_requiring_content_type("GET"));
        assert!(!is_method_requiring_content_type("DELETE"));
    }

    #[test]
    fn test_sensitive_header_detection() {
        assert!(is_sensitive_header("authorization"));
        assert!(is_sensitive_header("Authorization"));
        assert!(is_sensitive_header("cookie"));
        assert!(!is_sensitive_header("content-type"));
    }
}
