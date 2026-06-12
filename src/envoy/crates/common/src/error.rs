use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum FilterError {
    InvalidHeader {
        header: String,
        reason: String,
    },
    InvalidMethod {
        method: String,
    },
    PayloadTooLarge {
        size: usize,
        max_size: usize,
    },
    RateLimitExceeded {
        limit_type: String,
        retry_after_secs: u64,
    },
    InvalidContentType {
        content_type: String,
    },
    MissingRequiredHeader {
        header: String,
    },
    HeaderSizeLimitExceeded {
        size: usize,
        max_size: usize,
    },
    HeaderCountLimitExceeded {
        count: usize,
        max_count: usize,
    },
    InvalidTraceId {
        trace_id: String,
        reason: String,
    },
    CircuitBreakerOpen {
        reason: String,
    },
    InternalError {
        message: String,
    },
}

impl FilterError {
    pub fn http_status(&self) -> u32 {
        use crate::constants::*;
        match self {
            Self::InvalidHeader { .. } => HTTP_STATUS_BAD_REQUEST,
            Self::InvalidMethod { .. } => HTTP_STATUS_BAD_REQUEST,
            Self::PayloadTooLarge { .. } => HTTP_STATUS_PAYLOAD_TOO_LARGE,
            Self::RateLimitExceeded { .. } => HTTP_STATUS_TOO_MANY_REQUESTS,
            Self::InvalidContentType { .. } => HTTP_STATUS_BAD_REQUEST,
            Self::MissingRequiredHeader { .. } => HTTP_STATUS_BAD_REQUEST,
            Self::HeaderSizeLimitExceeded { .. } => HTTP_STATUS_BAD_REQUEST,
            Self::HeaderCountLimitExceeded { .. } => HTTP_STATUS_BAD_REQUEST,
            Self::InvalidTraceId { .. } => HTTP_STATUS_BAD_REQUEST,
            Self::CircuitBreakerOpen { .. } => HTTP_STATUS_SERVICE_UNAVAILABLE,
            Self::InternalError { .. } => HTTP_STATUS_INTERNAL_SERVER_ERROR,
        }
    }

    pub fn error_code(&self) -> &'static str {
        match self {
            Self::InvalidHeader { .. } => "ERR-1001",
            Self::InvalidMethod { .. } => "ERR-1002",
            Self::PayloadTooLarge { .. } => "ERR-1003",
            Self::RateLimitExceeded { .. } => "ERR-1004",
            Self::InvalidContentType { .. } => "ERR-1005",
            Self::MissingRequiredHeader { .. } => "ERR-1006",
            Self::HeaderSizeLimitExceeded { .. } => "ERR-1007",
            Self::HeaderCountLimitExceeded { .. } => "ERR-1008",
            Self::InvalidTraceId { .. } => "ERR-1009",
            Self::CircuitBreakerOpen { .. } => "ERR-1010",
            Self::InternalError { .. } => "ERR-5000",
        }
    }

    pub fn message(&self) -> String {
        match self {
            Self::InvalidHeader { header, reason } => {
                format!("Invalid header '{}': {}", header, reason)
            }
            Self::InvalidMethod { method } => {
                format!("HTTP method '{}' not allowed", method)
            }
            Self::PayloadTooLarge { size, max_size } => {
                format!(
                    "Request payload too large: {} bytes (max: {} bytes)",
                    size, max_size
                )
            }
            Self::RateLimitExceeded {
                limit_type,
                retry_after_secs,
            } => {
                format!(
                    "{} rate limit exceeded. Retry after {} seconds",
                    limit_type, retry_after_secs
                )
            }
            Self::InvalidContentType { content_type } => {
                format!("Content-Type '{}' not allowed", content_type)
            }
            Self::MissingRequiredHeader { header } => {
                format!("Required header '{}' is missing", header)
            }
            Self::HeaderSizeLimitExceeded { size, max_size } => {
                format!(
                    "Header size {} bytes exceeds maximum {} bytes",
                    size, max_size
                )
            }
            Self::HeaderCountLimitExceeded { count, max_count } => {
                format!("Header count {} exceeds maximum {}", count, max_count)
            }
            Self::InvalidTraceId { trace_id, reason } => {
                format!("Invalid trace ID '{}': {}", trace_id, reason)
            }
            Self::CircuitBreakerOpen { reason } => {
                format!("Circuit breaker open: {}", reason)
            }
            Self::InternalError { message } => {
                format!("Internal error: {}", message)
            }
        }
    }
}

pub type FilterResult<T> = Result<T, FilterError>;
