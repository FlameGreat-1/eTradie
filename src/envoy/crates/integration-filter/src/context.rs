use etradie_envoy_common::{
    extract_trace_id_from_traceparent, extract_span_id_from_traceparent,
    generate_trace_id, generate_span_id, validate_trace_id,
    HEADER_X_REQUEST_ID, HEADER_X_TRACE_ID, HEADER_TRACEPARENT,
};

#[derive(Debug, Clone)]
pub struct RequestContext {
    trace_id: String,
    span_id: String,
    request_id: String,
    method: String,
    path: String,
    client_ip: Option<String>,
    start_time_ms: u64,
}

impl RequestContext {
    pub fn new(
        method: String,
        path: String,
        headers: &[(String, String)],
    ) -> Self {
        let (trace_id, span_id) = Self::extract_trace_context(headers);
        let request_id = Self::extract_or_generate_request_id(headers);
        let client_ip = Self::extract_client_ip(headers);
        let start_time_ms = current_timestamp_ms();

        Self {
            trace_id,
            span_id,
            request_id,
            method,
            path,
            client_ip,
            start_time_ms,
        }
    }

    pub fn trace_id(&self) -> &str {
        &self.trace_id
    }

    pub fn span_id(&self) -> &str {
        &self.span_id
    }

    pub fn request_id(&self) -> &str {
        &self.request_id
    }

    pub fn method(&self) -> &str {
        &self.method
    }

    pub fn path(&self) -> &str {
        &self.path
    }

    pub fn client_ip(&self) -> Option<&str> {
        self.client_ip.as_deref()
    }

    pub fn start_time_ms(&self) -> u64 {
        self.start_time_ms
    }

    pub fn elapsed_ms(&self) -> u64 {
        current_timestamp_ms().saturating_sub(self.start_time_ms)
    }

    fn extract_trace_context(headers: &[(String, String)]) -> (String, String) {
        if let Some((_, tp_value)) = headers.iter().find(|(name, _)| name.eq_ignore_ascii_case(HEADER_TRACEPARENT)) {
            if let Some(tid) = extract_trace_id_from_traceparent(tp_value) {
                let sid = extract_span_id_from_traceparent(tp_value)
                    .unwrap_or_else(generate_span_id);
                return (tid, sid);
            }
        }

        if let Some((_, trace_value)) = headers.iter().find(|(name, _)| name.eq_ignore_ascii_case(HEADER_X_TRACE_ID)) {
            if validate_trace_id(trace_value).is_ok() {
                return (trace_value.clone(), generate_span_id());
            }
        }

        (generate_trace_id(), generate_span_id())
    }

    fn extract_or_generate_request_id(headers: &[(String, String)]) -> String {
        headers
            .iter()
            .find(|(name, _)| name.eq_ignore_ascii_case(HEADER_X_REQUEST_ID))
            .map(|(_, value)| value.clone())
            .unwrap_or_else(generate_trace_id)
    }

    fn extract_client_ip(headers: &[(String, String)]) -> Option<String> {
        etradie_envoy_rate_limiter::extract_client_ip(headers)
    }
}

fn current_timestamp_ms() -> u64 {
    use proxy_wasm::hostcalls;
    use std::time::SystemTime;
    match hostcalls::get_current_time() {
        Ok(time) => time
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64,
        Err(_) => 0,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_context_creation() {
        let headers = vec![
            ("user-agent".to_string(), "test-agent".to_string()),
        ];
        let context = RequestContext::new("GET".to_string(), "/api/v1/users".to_string(), &headers);

        assert_eq!(context.method(), "GET");
        assert_eq!(context.path(), "/api/v1/users");
        assert!(!context.trace_id().is_empty());
        assert!(!context.request_id().is_empty());
        assert!(!context.span_id().is_empty());
    }

    #[test]
    fn test_context_with_trace_id() {
        let headers = vec![
            ("x-trace-id".to_string(), "abc123def456".to_string()),
        ];
        let context = RequestContext::new("POST".to_string(), "/api/v1/data".to_string(), &headers);

        assert_eq!(context.trace_id(), "abc123def456");
    }

    #[test]
    fn test_context_with_client_ip() {
        let headers = vec![
            ("x-forwarded-for".to_string(), "192.168.1.1".to_string()),
        ];
        let context = RequestContext::new("GET".to_string(), "/".to_string(), &headers);

        assert_eq!(context.client_ip(), Some("192.168.1.1"));
    }

    #[test]
    fn test_context_without_client_ip() {
        let headers = vec![
            ("user-agent".to_string(), "test-agent".to_string()),
        ];
        let context = RequestContext::new("GET".to_string(), "/".to_string(), &headers);

        assert_eq!(context.client_ip(), None);
    }

    #[test]
    fn test_context_with_request_id() {
        let headers = vec![
            ("x-request-id".to_string(), "req-123-456".to_string()),
        ];
        let context = RequestContext::new("GET".to_string(), "/".to_string(), &headers);

        assert_eq!(context.request_id(), "req-123-456");
    }
}
