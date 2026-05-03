use etradie_envoy_common::{FilterError, FilterResult, MAX_REQUEST_BODY_SIZE};

pub struct SizeValidator {
    max_body_size: usize,
}

impl SizeValidator {
    pub fn new(max_body_size: usize) -> Self {
        Self { max_body_size }
    }

    pub fn with_default_limit() -> Self {
        Self {
            max_body_size: MAX_REQUEST_BODY_SIZE,
        }
    }

    pub fn validate_body_size(&self, size: usize) -> FilterResult<()> {
        if size > self.max_body_size {
            return Err(FilterError::PayloadTooLarge {
                size,
                max_size: self.max_body_size,
            });
        }

        Ok(())
    }

    pub fn max_body_size(&self) -> usize {
        self.max_body_size
    }

    pub fn is_size_allowed(&self, size: usize) -> bool {
        size <= self.max_body_size
    }
}

pub fn calculate_content_length(headers: &[(String, String)]) -> Option<usize> {
    headers
        .iter()
        .find(|(name, _)| name.eq_ignore_ascii_case("content-length"))
        .and_then(|(_, value)| value.parse::<usize>().ok())
}

pub fn has_content_length(headers: &[(String, String)]) -> bool {
    headers
        .iter()
        .any(|(name, _)| name.eq_ignore_ascii_case("content-length"))
}

pub fn format_size(bytes: usize) -> String {
    const KB: usize = 1024;
    const MB: usize = KB * 1024;
    const GB: usize = MB * 1024;

    if bytes >= GB {
        format!("{:.2} GB", bytes as f64 / GB as f64)
    } else if bytes >= MB {
        format!("{:.2} MB", bytes as f64 / MB as f64)
    } else if bytes >= KB {
        format!("{:.2} KB", bytes as f64 / KB as f64)
    } else {
        format!("{} bytes", bytes)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validator_creation() {
        let validator = SizeValidator::with_default_limit();
        assert_eq!(validator.max_body_size(), MAX_REQUEST_BODY_SIZE);
    }

    #[test]
    fn test_valid_body_size() {
        let validator = SizeValidator::with_default_limit();
        assert!(validator.validate_body_size(1024).is_ok());
        assert!(validator.validate_body_size(1024 * 1024).is_ok());
    }

    #[test]
    fn test_invalid_body_size() {
        let validator = SizeValidator::new(1024);
        assert!(validator.validate_body_size(2048).is_err());
    }

    #[test]
    fn test_is_size_allowed() {
        let validator = SizeValidator::new(1024);
        assert!(validator.is_size_allowed(512));
        assert!(validator.is_size_allowed(1024));
        assert!(!validator.is_size_allowed(2048));
    }

    #[test]
    fn test_calculate_content_length() {
        let headers = vec![
            ("content-type".to_string(), "application/json".to_string()),
            ("content-length".to_string(), "1024".to_string()),
        ];

        let length = calculate_content_length(&headers);
        assert_eq!(length, Some(1024));
    }

    #[test]
    fn test_calculate_content_length_missing() {
        let headers = vec![
            ("content-type".to_string(), "application/json".to_string()),
        ];

        let length = calculate_content_length(&headers);
        assert_eq!(length, None);
    }

    #[test]
    fn test_has_content_length() {
        let headers_with = vec![
            ("content-length".to_string(), "1024".to_string()),
        ];
        assert!(has_content_length(&headers_with));

        let headers_without = vec![
            ("content-type".to_string(), "application/json".to_string()),
        ];
        assert!(!has_content_length(&headers_without));
    }

    #[test]
    fn test_format_size() {
        assert_eq!(format_size(512), "512 bytes");
        assert_eq!(format_size(1024), "1.00 KB");
        assert_eq!(format_size(1024 * 1024), "1.00 MB");
        assert_eq!(format_size(1024 * 1024 * 1024), "1.00 GB");
    }

    #[test]
    fn test_custom_max_size() {
        let validator = SizeValidator::new(5 * 1024 * 1024);
        assert_eq!(validator.max_body_size(), 5 * 1024 * 1024);
        assert!(validator.validate_body_size(4 * 1024 * 1024).is_ok());
        assert!(validator.validate_body_size(6 * 1024 * 1024).is_err());
    }
}
