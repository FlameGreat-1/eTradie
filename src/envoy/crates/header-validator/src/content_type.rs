use crate::rules::ValidationRules;
use etradie_envoy_common::{FilterError, FilterResult, HEADER_CONTENT_TYPE};

pub struct ContentTypeValidator {
    rules: ValidationRules,
}

impl ContentTypeValidator {
    pub fn new(rules: ValidationRules) -> Self {
        Self { rules }
    }

    pub fn validate(
        &self,
        headers: &[(String, String)],
        method: &str,
    ) -> FilterResult<()> {
        let content_type = self.find_content_type(headers);

        if crate::rules::is_method_requiring_content_type(method) {
            if let Some(ct) = content_type {
                self.validate_content_type(ct)?;
            } else {
                return Err(FilterError::MissingRequiredHeader {
                    header: HEADER_CONTENT_TYPE.to_string(),
                });
            }
        } else if let Some(ct) = content_type {
            self.validate_content_type(ct)?;
        }

        Ok(())
    }

    fn find_content_type<'a>(&self, headers: &'a [(String, String)]) -> Option<&'a str> {
        headers
            .iter()
            .find(|(name, _)| name.eq_ignore_ascii_case(HEADER_CONTENT_TYPE))
            .map(|(_, value)| value.as_str())
    }

    fn validate_content_type(&self, content_type: &str) -> FilterResult<()> {
        if content_type.is_empty() {
            return Err(FilterError::InvalidContentType {
                content_type: "(empty)".to_string(),
            });
        }

        if !self.rules.is_content_type_allowed(content_type) {
            return Err(FilterError::InvalidContentType {
                content_type: content_type.to_string(),
            });
        }

        Ok(())
    }
}

pub fn parse_content_type(content_type: &str) -> (String, Vec<(String, String)>) {
    let parts: Vec<&str> = content_type.split(';').collect();
    
    let media_type = parts.first().unwrap_or(&"").trim().to_lowercase();
    
    let mut parameters = Vec::new();
    for part in parts.iter().skip(1) {
        if let Some((key, value)) = part.split_once('=') {
            parameters.push((
                key.trim().to_lowercase(),
                value.trim().trim_matches('"').to_string(),
            ));
        }
    }

    (media_type, parameters)
}

pub fn get_charset(content_type: &str) -> Option<String> {
    let (_, parameters) = parse_content_type(content_type);
    
    parameters
        .iter()
        .find(|(key, _)| key == "charset")
        .map(|(_, value)| value.clone())
}

pub fn is_json_content_type(content_type: &str) -> bool {
    let (media_type, _) = parse_content_type(content_type);
    media_type == "application/json" || media_type.ends_with("+json")
}

pub fn is_form_content_type(content_type: &str) -> bool {
    let (media_type, _) = parse_content_type(content_type);
    media_type == "application/x-www-form-urlencoded" || media_type == "multipart/form-data"
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_content_type_validation() {
        let rules = ValidationRules::new();
        let validator = ContentTypeValidator::new(rules);

        let headers = vec![
            ("content-type".to_string(), "application/json".to_string()),
        ];

        assert!(validator.validate(&headers, "POST").is_ok());
    }

    #[test]
    fn test_missing_content_type_for_post() {
        let rules = ValidationRules::new();
        let validator = ContentTypeValidator::new(rules);

        let headers = vec![];
        assert!(validator.validate(&headers, "POST").is_err());
    }

    #[test]
    fn test_invalid_content_type() {
        let rules = ValidationRules::new();
        let validator = ContentTypeValidator::new(rules);

        let headers = vec![
            ("content-type".to_string(), "application/xml".to_string()),
        ];

        assert!(validator.validate(&headers, "POST").is_err());
    }

    #[test]
    fn test_parse_content_type() {
        let (media_type, params) = parse_content_type("application/json; charset=utf-8");
        assert_eq!(media_type, "application/json");
        assert_eq!(params.len(), 1);
        assert_eq!(params[0].0, "charset");
        assert_eq!(params[0].1, "utf-8");
    }

    #[test]
    fn test_get_charset() {
        let charset = get_charset("application/json; charset=utf-8");
        assert_eq!(charset, Some("utf-8".to_string()));

        let no_charset = get_charset("application/json");
        assert_eq!(no_charset, None);
    }

    #[test]
    fn test_is_json_content_type() {
        assert!(is_json_content_type("application/json"));
        assert!(is_json_content_type("application/json; charset=utf-8"));
        assert!(is_json_content_type("application/vnd.api+json"));
        assert!(!is_json_content_type("text/plain"));
    }

    #[test]
    fn test_is_form_content_type() {
        assert!(is_form_content_type("application/x-www-form-urlencoded"));
        assert!(is_form_content_type("multipart/form-data"));
        assert!(!is_form_content_type("application/json"));
    }
}
