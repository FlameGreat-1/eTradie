use crate::constants::{
    HEADER_CONTENT_SECURITY_POLICY, HEADER_REFERRER_POLICY, HEADER_RETRY_AFTER,
    HEADER_X_CONTENT_TYPE_OPTIONS, HEADER_X_FRAME_OPTIONS, HEADER_X_TRACE_ID,
    VALUE_CONTENT_SECURITY_POLICY, VALUE_REFERRER_POLICY, VALUE_X_CONTENT_TYPE_OPTIONS,
    VALUE_X_FRAME_OPTIONS,
};
use crate::error::FilterError;
use crate::types::SecurityEvent;
use serde::Serialize;
use std::time::SystemTime;

#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    pub error: ErrorDetail,
    pub trace_id: String,
    pub timestamp_ms: u64,
}

#[derive(Debug, Serialize)]
pub struct ErrorDetail {
    pub code: String,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub details: Option<serde_json::Value>,
}

impl ErrorResponse {
    pub fn from_filter_error(error: &FilterError, trace_id: &str) -> Self {
        Self {
            error: ErrorDetail {
                code: error.error_code().to_string(),
                message: error.message(),
                details: None,
            },
            trace_id: trace_id.to_string(),
            timestamp_ms: current_timestamp_ms(),
        }
    }

    pub fn from_security_event(event: &SecurityEvent) -> Self {
        Self {
            error: ErrorDetail {
                code: event.code.as_str().to_string(),
                message: event.code.description().to_string(),
                details: Some(serde_json::json!({ "details": event.details })),
            },
            trace_id: event.trace_id.clone(),
            timestamp_ms: event.timestamp_ms,
        }
    }

    pub fn to_json(&self) -> String {
        serde_json::to_string(self).unwrap_or_else(|_| {
            format!(
                r#"{{"error":{{"code":"{}","message":"{}"}}, "trace_id":"{}","timestamp_ms":{}}}"#,
                self.error.code, self.error.message, self.trace_id, self.timestamp_ms
            )
        })
    }
}

pub struct ResponseBuilder {
    status: u32,
    headers: Vec<(String, String)>,
    body: Option<String>,
}

impl ResponseBuilder {
    pub fn new(status: u32) -> Self {
        Self {
            status,
            headers: vec![
                ("content-type".to_string(), "application/json".to_string()),
                (
                    HEADER_X_CONTENT_TYPE_OPTIONS.to_string(),
                    VALUE_X_CONTENT_TYPE_OPTIONS.to_string(),
                ),
                (
                    HEADER_X_FRAME_OPTIONS.to_string(),
                    VALUE_X_FRAME_OPTIONS.to_string(),
                ),
                (
                    HEADER_REFERRER_POLICY.to_string(),
                    VALUE_REFERRER_POLICY.to_string(),
                ),
                (
                    HEADER_CONTENT_SECURITY_POLICY.to_string(),
                    VALUE_CONTENT_SECURITY_POLICY.to_string(),
                ),
            ],
            body: None,
        }
    }

    pub fn with_trace_id(mut self, trace_id: &str) -> Self {
        self.headers
            .push((HEADER_X_TRACE_ID.to_string(), trace_id.to_string()));
        self
    }

    pub fn with_retry_after(mut self, seconds: u64) -> Self {
        self.headers
            .push((HEADER_RETRY_AFTER.to_string(), seconds.to_string()));
        self
    }

    pub fn with_header(mut self, name: &str, value: &str) -> Self {
        self.headers.push((name.to_string(), value.to_string()));
        self
    }

    pub fn with_body(mut self, body: String) -> Self {
        self.body = Some(body);
        self
    }

    pub fn with_error_response(mut self, error_response: &ErrorResponse) -> Self {
        self.body = Some(error_response.to_json());
        self
    }

    pub fn build(self) -> (u32, Vec<(String, String)>, Option<String>) {
        (self.status, self.headers, self.body)
    }
}

pub fn build_error_response(
    error: &FilterError,
    trace_id: &str,
) -> (u32, Vec<(String, String)>, String) {
    let status = error.http_status();
    let error_response = ErrorResponse::from_filter_error(error, trace_id);

    let mut builder = ResponseBuilder::new(status)
        .with_trace_id(trace_id)
        .with_error_response(&error_response);

    if let FilterError::RateLimitExceeded {
        retry_after_secs, ..
    } = error
    {
        builder = builder.with_retry_after(*retry_after_secs);
    }

    let (status, headers, body) = builder.build();
    (status, headers, body.unwrap_or_default())
}

pub fn build_security_event_response(
    event: &SecurityEvent,
    status: u32,
) -> (u32, Vec<(String, String)>, String) {
    let error_response = ErrorResponse::from_security_event(event);

    let builder = ResponseBuilder::new(status)
        .with_trace_id(&event.trace_id)
        .with_error_response(&error_response);

    let (status, headers, body) = builder.build();
    (status, headers, body.unwrap_or_default())
}

pub fn build_internal_error_response(
    trace_id: &str,
    message: &str,
) -> (u32, Vec<(String, String)>, String) {
    let error = FilterError::InternalError {
        message: message.to_string(),
    };
    build_error_response(&error, trace_id)
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
