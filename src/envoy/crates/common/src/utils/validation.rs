use crate::constants::{MAX_HEADER_COUNT, MAX_HEADER_SIZE, MAX_USER_AGENT_SIZE};
use crate::error::{FilterError, FilterResult};

pub fn validate_ascii(value: &str, field_name: &str) -> FilterResult<()> {
    if !value.is_ascii() {
        return Err(FilterError::InvalidHeader {
            header: field_name.to_string(),
            reason: "Contains non-ASCII characters".to_string(),
        });
    }

    if value.chars().any(|c| c.is_control() && c != '\t') {
        return Err(FilterError::InvalidHeader {
            header: field_name.to_string(),
            reason: "Contains control characters".to_string(),
        });
    }

    Ok(())
}

pub fn validate_header_size(headers: &[(String, String)]) -> FilterResult<()> {
    let total_size: usize = headers
        .iter()
        .map(|(name, value)| name.len() + value.len() + 4)
        .sum();

    if total_size > MAX_HEADER_SIZE {
        return Err(FilterError::HeaderSizeLimitExceeded {
            size: total_size,
            max_size: MAX_HEADER_SIZE,
        });
    }

    Ok(())
}

pub fn validate_header_count(count: usize) -> FilterResult<()> {
    if count > MAX_HEADER_COUNT {
        return Err(FilterError::HeaderCountLimitExceeded {
            count,
            max_count: MAX_HEADER_COUNT,
        });
    }

    Ok(())
}

pub fn validate_user_agent(user_agent: &str) -> FilterResult<()> {
    if user_agent.is_empty() {
        return Err(FilterError::MissingRequiredHeader {
            header: "User-Agent".to_string(),
        });
    }

    if user_agent.len() > MAX_USER_AGENT_SIZE {
        return Err(FilterError::InvalidHeader {
            header: "User-Agent".to_string(),
            reason: format!(
                "Exceeds maximum length of {} characters",
                MAX_USER_AGENT_SIZE
            ),
        });
    }

    validate_ascii(user_agent, "User-Agent")?;

    Ok(())
}

pub fn validate_content_type(content_type: &str, allowed_types: &[&str]) -> FilterResult<()> {
    let normalized = content_type
        .split(';')
        .next()
        .unwrap_or("")
        .trim()
        .to_lowercase();

    if !allowed_types
        .iter()
        .any(|&allowed| normalized == allowed.to_lowercase())
    {
        return Err(FilterError::InvalidContentType {
            content_type: content_type.to_string(),
        });
    }

    Ok(())
}

pub fn validate_http_method(method: &str, allowed_methods: &[&str]) -> FilterResult<()> {
    if !allowed_methods.contains(&method) {
        return Err(FilterError::InvalidMethod {
            method: method.to_string(),
        });
    }

    Ok(())
}

pub fn sanitize_header_value(value: &str) -> String {
    value
        .chars()
        .filter(|c| !c.is_control() || *c == '\t')
        .collect()
}

pub fn is_valid_header_name(name: &str) -> bool {
    !name.is_empty()
        && name.is_ascii()
        && name
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
}
