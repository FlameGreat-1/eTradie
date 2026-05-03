use etradie_envoy_common::{
    utils::validation::{is_valid_header_name, sanitize_header_value, validate_ascii},
    FilterError, FilterResult,
};

pub struct HeaderSanitizer {
    strict_mode: bool,
}

impl HeaderSanitizer {
    pub fn new(strict_mode: bool) -> Self {
        Self { strict_mode }
    }

    pub fn sanitize_headers(
        &self,
        headers: Vec<(String, String)>,
    ) -> FilterResult<Vec<(String, String)>> {
        let mut sanitized = Vec::with_capacity(headers.len());

        for (name, value) in headers {
            if !is_valid_header_name(&name) {
                if self.strict_mode {
                    return Err(FilterError::InvalidHeader {
                        header: name.clone(),
                        reason: "Invalid header name format".to_string(),
                    });
                }
                continue;
            }

            if self.strict_mode {
                validate_ascii(&value, &name)?;
            }

            let sanitized_value = if self.strict_mode {
                value
            } else {
                sanitize_header_value(&value)
            };

            sanitized.push((name, sanitized_value));
        }

        Ok(sanitized)
    }

    pub fn validate_header_value(&self, name: &str, value: &str) -> FilterResult<()> {
        if value.is_empty() {
            return Err(FilterError::InvalidHeader {
                header: name.to_string(),
                reason: "Header value is empty".to_string(),
            });
        }

        if self.strict_mode {
            validate_ascii(value, name)?;
        }

        if contains_null_bytes(value) {
            return Err(FilterError::InvalidHeader {
                header: name.to_string(),
                reason: "Header value contains null bytes".to_string(),
            });
        }

        if contains_crlf(value) {
            return Err(FilterError::InvalidHeader {
                header: name.to_string(),
                reason: "Header value contains CRLF injection attempt".to_string(),
            });
        }

        Ok(())
    }

    pub fn remove_dangerous_headers(
        &self,
        headers: Vec<(String, String)>,
    ) -> Vec<(String, String)> {
        const DANGEROUS_HEADERS: &[&str] = &[
            "proxy-connection",
            "proxy-authorization",
            "te",
            "transfer-encoding",
            "upgrade",
        ];

        headers
            .into_iter()
            .filter(|(name, _)| {
                !DANGEROUS_HEADERS
                    .iter()
                    .any(|h| h.eq_ignore_ascii_case(name))
            })
            .collect()
    }
}

fn contains_null_bytes(value: &str) -> bool {
    value.contains('\0')
}

fn contains_crlf(value: &str) -> bool {
    value.contains('\r') || value.contains('\n')
}

pub fn strip_whitespace(value: &str) -> String {
    value.trim().to_string()
}

pub fn normalize_header_value(value: &str) -> String {
    let stripped = strip_whitespace(value);
    
    stripped
        .chars()
        .filter(|c| !c.is_control() || *c == '\t')
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sanitizer_creation() {
        let sanitizer = HeaderSanitizer::new(true);
        assert!(sanitizer.strict_mode);
    }

    #[test]
    fn test_sanitize_headers() {
        let sanitizer = HeaderSanitizer::new(false);
        let headers = vec![
            ("content-type".to_string(), "application/json".to_string()),
            ("user-agent".to_string(), "test-agent".to_string()),
        ];

        let result = sanitizer.sanitize_headers(headers);
        assert!(result.is_ok());
        assert_eq!(result.unwrap().len(), 2);
    }

    #[test]
    fn test_invalid_header_name() {
        let sanitizer = HeaderSanitizer::new(true);
        let headers = vec![
            ("invalid header".to_string(), "value".to_string()),
        ];

        let result = sanitizer.sanitize_headers(headers);
        assert!(result.is_err());
    }

    #[test]
    fn test_validate_header_value() {
        let sanitizer = HeaderSanitizer::new(true);
        assert!(sanitizer.validate_header_value("test", "valid-value").is_ok());
        assert!(sanitizer.validate_header_value("test", "").is_err());
    }

    #[test]
    fn test_null_bytes_detection() {
        assert!(contains_null_bytes("test\0value"));
        assert!(!contains_null_bytes("test-value"));
    }

    #[test]
    fn test_crlf_detection() {
        assert!(contains_crlf("test\r\nvalue"));
        assert!(contains_crlf("test\nvalue"));
        assert!(!contains_crlf("test-value"));
    }

    #[test]
    fn test_remove_dangerous_headers() {
        let sanitizer = HeaderSanitizer::new(true);
        let headers = vec![
            ("content-type".to_string(), "application/json".to_string()),
            ("proxy-connection".to_string(), "keep-alive".to_string()),
            ("user-agent".to_string(), "test".to_string()),
        ];

        let result = sanitizer.remove_dangerous_headers(headers);
        assert_eq!(result.len(), 2);
        assert!(!result.iter().any(|(name, _)| name == "proxy-connection"));
    }

    #[test]
    fn test_normalize_header_value() {
        assert_eq!(normalize_header_value("  value  "), "value");
        assert_eq!(normalize_header_value("value\x01test"), "valuetest");
    }
}
