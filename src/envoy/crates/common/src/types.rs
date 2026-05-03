use serde::{Deserialize, Serialize};
use std::time::SystemTime;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SecurityEventCode {
    RateLimitGlobal,
    RateLimitIp,
    InvalidHeader,
    InvalidMethod,
    PayloadTooLarge,
    InvalidContentType,
    MissingRequiredHeader,
    HeaderSizeLimitExceeded,
    HeaderCountLimitExceeded,
    InvalidTraceId,
    CircuitBreakerTriggered,
}

impl SecurityEventCode {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::RateLimitGlobal => "SEC-3001",
            Self::RateLimitIp => "SEC-3002",
            Self::InvalidHeader => "SEC-3003",
            Self::InvalidMethod => "SEC-3004",
            Self::PayloadTooLarge => "SEC-3005",
            Self::InvalidContentType => "SEC-3006",
            Self::MissingRequiredHeader => "SEC-3007",
            Self::HeaderSizeLimitExceeded => "SEC-3008",
            Self::HeaderCountLimitExceeded => "SEC-3009",
            Self::InvalidTraceId => "SEC-3010",
            Self::CircuitBreakerTriggered => "SEC-3011",
        }
    }

    pub fn description(&self) -> &'static str {
        match self {
            Self::RateLimitGlobal => "Global rate limit exceeded",
            Self::RateLimitIp => "IP-based rate limit exceeded",
            Self::InvalidHeader => "Invalid header detected",
            Self::InvalidMethod => "Invalid HTTP method",
            Self::PayloadTooLarge => "Request payload too large",
            Self::InvalidContentType => "Invalid Content-Type",
            Self::MissingRequiredHeader => "Missing required header",
            Self::HeaderSizeLimitExceeded => "Header size limit exceeded",
            Self::HeaderCountLimitExceeded => "Header count limit exceeded",
            Self::InvalidTraceId => "Invalid trace ID format",
            Self::CircuitBreakerTriggered => "Circuit breaker triggered",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityEvent {
    pub code: SecurityEventCode,
    pub trace_id: String,
    pub timestamp_ms: u64,
    pub details: String,
}

impl SecurityEvent {
    pub fn new(code: SecurityEventCode, trace_id: String, details: String) -> Self {
        Self {
            code,
            trace_id,
            timestamp_ms: current_timestamp_ms(),
            details,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FilterDecision {
    pub allowed: bool,
    pub reason: Option<String>,
    pub event: Option<SecurityEvent>,
}

impl FilterDecision {
    pub fn allow() -> Self {
        Self {
            allowed: true,
            reason: None,
            event: None,
        }
    }

    pub fn deny(reason: String, event: SecurityEvent) -> Self {
        Self {
            allowed: false,
            reason: Some(reason),
            event: Some(event),
        }
    }
}

fn current_timestamp_ms() -> u64 {
    use proxy_wasm::hostcalls;
    match hostcalls::get_current_time() {
        Ok(time) => time
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64,
        Err(_) => 0,
    }
}
