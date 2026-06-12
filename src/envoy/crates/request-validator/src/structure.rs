use etradie_envoy_common::{FilterError, FilterResult};

pub struct StructureValidator {
    validate_path: bool,
    validate_query: bool,
}

impl StructureValidator {
    pub fn new(validate_path: bool, validate_query: bool) -> Self {
        Self {
            validate_path,
            validate_query,
        }
    }

    pub fn with_defaults() -> Self {
        Self {
            validate_path: true,
            validate_query: true,
        }
    }

    pub fn validate(&self, path: &str, method: &str) -> FilterResult<()> {
        if self.validate_path {
            self.validate_path_structure(path)?;
        }

        if self.validate_query {
            if let Some(query) = extract_query_string(path) {
                self.validate_query_string(query)?;
            }
        }

        self.validate_method_path_combination(method, path)?;

        Ok(())
    }

    fn validate_path_structure(&self, path: &str) -> FilterResult<()> {
        if path.is_empty() {
            return Err(FilterError::InternalError {
                message: "Request path is empty".to_string(),
            });
        }

        if !path.starts_with('/') {
            return Err(FilterError::InternalError {
                message: "Request path must start with /".to_string(),
            });
        }

        if path.contains("..") {
            return Err(FilterError::InternalError {
                message: "Path traversal attempt detected".to_string(),
            });
        }

        if path.contains('\0') {
            return Err(FilterError::InternalError {
                message: "Null byte in path".to_string(),
            });
        }

        if path.len() > 2048 {
            return Err(FilterError::InternalError {
                message: "Request path too long".to_string(),
            });
        }

        Ok(())
    }

    fn validate_query_string(&self, query: &str) -> FilterResult<()> {
        if query.len() > 4096 {
            return Err(FilterError::InternalError {
                message: "Query string too long".to_string(),
            });
        }

        if query.contains('\0') {
            return Err(FilterError::InternalError {
                message: "Null byte in query string".to_string(),
            });
        }

        Ok(())
    }

    fn validate_method_path_combination(&self, method: &str, path: &str) -> FilterResult<()> {
        let method_upper = method.to_uppercase();

        if method_upper == "GET" && path.contains('?') {
            let query = extract_query_string(path).unwrap_or("");
            if query.len() > 2048 {
                return Err(FilterError::InternalError {
                    message: "Query string too long for GET request".to_string(),
                });
            }
        }

        Ok(())
    }
}

pub fn extract_query_string(path: &str) -> Option<&str> {
    path.split_once('?').map(|(_, query)| query)
}

pub fn extract_path_without_query(path: &str) -> &str {
    path.split('?').next().unwrap_or(path)
}

pub fn parse_query_params(query: &str) -> Vec<(String, String)> {
    query
        .split('&')
        .filter_map(|pair| {
            let mut parts = pair.splitn(2, '=');
            let key = parts.next()?.to_string();
            let value = parts.next().unwrap_or("").to_string();
            Some((key, value))
        })
        .collect()
}

pub fn is_valid_path_segment(segment: &str) -> bool {
    !segment.is_empty()
        && !segment.contains("..")
        && !segment.contains('\0')
        && segment.chars().all(|c| {
            c.is_ascii_alphanumeric() || c == '-' || c == '_' || c == '.' || c == '~' || c == '/'
        })
}

pub fn normalize_path(path: &str) -> String {
    let without_query = extract_path_without_query(path);

    let segments: Vec<&str> = without_query
        .split('/')
        .filter(|s| !s.is_empty() && *s != ".")
        .collect();

    let mut normalized = String::from("/");
    normalized.push_str(&segments.join("/"));

    if let Some(query) = extract_query_string(path) {
        normalized.push('?');
        normalized.push_str(query);
    }

    normalized
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validator_creation() {
        let validator = StructureValidator::with_defaults();
        assert!(validator.validate_path);
        assert!(validator.validate_query);
    }

    #[test]
    fn test_valid_path() {
        let validator = StructureValidator::with_defaults();
        assert!(validator.validate("/api/v1/users", "GET").is_ok());
        assert!(validator.validate("/api/v1/users?page=1", "GET").is_ok());
    }

    #[test]
    fn test_invalid_path_empty() {
        let validator = StructureValidator::with_defaults();
        assert!(validator.validate("", "GET").is_err());
    }

    #[test]
    fn test_invalid_path_no_leading_slash() {
        let validator = StructureValidator::with_defaults();
        assert!(validator.validate("api/users", "GET").is_err());
    }

    #[test]
    fn test_path_traversal_detection() {
        let validator = StructureValidator::with_defaults();
        assert!(validator.validate("/api/../etc/passwd", "GET").is_err());
        assert!(validator.validate("/api/../../secret", "GET").is_err());
    }

    #[test]
    fn test_null_byte_detection() {
        let validator = StructureValidator::with_defaults();
        assert!(validator.validate("/api/users\0", "GET").is_err());
    }

    #[test]
    fn test_path_too_long() {
        let validator = StructureValidator::with_defaults();
        let long_path = format!("/{}", "a".repeat(2049));
        assert!(validator.validate(&long_path, "GET").is_err());
    }

    #[test]
    fn test_query_string_too_long() {
        let validator = StructureValidator::with_defaults();
        let long_query = format!("/api?{}", "a".repeat(4097));
        assert!(validator.validate(&long_query, "GET").is_err());
    }

    #[test]
    fn test_extract_query_string() {
        assert_eq!(extract_query_string("/api?page=1"), Some("page=1"));
        assert_eq!(extract_query_string("/api"), None);
        assert_eq!(
            extract_query_string("/api?page=1&limit=10"),
            Some("page=1&limit=10")
        );
    }

    #[test]
    fn test_extract_path_without_query() {
        assert_eq!(extract_path_without_query("/api?page=1"), "/api");
        assert_eq!(extract_path_without_query("/api"), "/api");
    }

    #[test]
    fn test_parse_query_params() {
        let params = parse_query_params("page=1&limit=10");
        assert_eq!(params.len(), 2);
        assert_eq!(params[0], ("page".to_string(), "1".to_string()));
        assert_eq!(params[1], ("limit".to_string(), "10".to_string()));
    }

    #[test]
    fn test_is_valid_path_segment() {
        assert!(is_valid_path_segment("users"));
        assert!(is_valid_path_segment("api-v1"));
        assert!(is_valid_path_segment("file.txt"));
        assert!(!is_valid_path_segment("../etc"));
        assert!(!is_valid_path_segment("file\0"));
    }

    #[test]
    fn test_normalize_path() {
        assert_eq!(normalize_path("/api/./users"), "/api/users");
        assert_eq!(normalize_path("/api//users"), "/api/users");
        assert_eq!(normalize_path("/api/users?page=1"), "/api/users?page=1");
    }
}
