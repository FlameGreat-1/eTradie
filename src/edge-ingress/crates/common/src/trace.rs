use crate::constants::{
    TRACE_ID_LENGTH, W3C_TRACEPARENT_HEADER, W3C_TRACEPARENT_VERSION, W3C_TRACE_FLAGS_SAMPLED,
};
use crate::types::ConnectionInfo;
use std::net::SocketAddr;
use uuid::Uuid;

pub fn generate_trace_id() -> String {
    let uuid = Uuid::new_v4();
    let hex = uuid.as_simple().to_string();
    hex[..TRACE_ID_LENGTH.min(hex.len())].to_string()
}

pub fn generate_span_id() -> String {
    let uuid = Uuid::new_v4();
    let hex = uuid.as_simple().to_string();
    hex[..16.min(hex.len())].to_string()
}

pub fn extract_or_generate_trace_id(existing: Option<&str>) -> String {
    existing
        .filter(|id| is_valid_trace_id(id))
        .map(|id| id.to_string())
        .unwrap_or_else(generate_trace_id)
}

pub fn is_valid_trace_id(trace_id: &str) -> bool {
    if trace_id.len() != TRACE_ID_LENGTH {
        return false;
    }
    trace_id.chars().all(|c| c.is_ascii_hexdigit())
}

pub fn extract_trace_id_from_traceparent(traceparent: &str) -> Option<String> {
    let parts: Vec<&str> = traceparent.split('-').collect();
    if parts.len() != 4 {
        return None;
    }
    if parts[0] != W3C_TRACEPARENT_VERSION {
        return None;
    }
    let trace_id = parts[1];
    if trace_id.len() != 32 || !trace_id.chars().all(|c| c.is_ascii_hexdigit()) {
        return None;
    }
    if trace_id == "00000000000000000000000000000000" {
        return None;
    }
    Some(trace_id.to_string())
}

pub fn extract_span_id_from_traceparent(traceparent: &str) -> Option<String> {
    let parts: Vec<&str> = traceparent.split('-').collect();
    if parts.len() != 4 {
        return None;
    }
    let span_id = parts[2];
    if span_id.len() != 16 || !span_id.chars().all(|c| c.is_ascii_hexdigit()) {
        return None;
    }
    if span_id == "0000000000000000" {
        return None;
    }
    Some(span_id.to_string())
}

pub fn build_traceparent(trace_id: &str, span_id: &str) -> String {
    format!(
        "{}-{}-{}-{}",
        W3C_TRACEPARENT_VERSION, trace_id, span_id, W3C_TRACE_FLAGS_SAMPLED
    )
}

pub fn extract_trace_from_headers(
    traceparent: Option<&str>,
    request_id: Option<&str>,
) -> (String, String) {
    if let Some(tp) = traceparent {
        if let Some(tid) = extract_trace_id_from_traceparent(tp) {
            let sid = extract_span_id_from_traceparent(tp)
                .unwrap_or_else(generate_span_id);
            return (tid, sid);
        }
    }
    if let Some(rid) = request_id {
        if is_valid_trace_id(rid) {
            return (rid.to_string(), generate_span_id());
        }
    }
    (generate_trace_id(), generate_span_id())
}

pub fn create_connection_info(
    client_addr: SocketAddr,
    existing_trace_id: Option<&str>,
) -> ConnectionInfo {
    let trace_id = extract_or_generate_trace_id(existing_trace_id);
    ConnectionInfo::new(client_addr, trace_id)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generate_trace_id_length() {
        let trace_id = generate_trace_id();
        assert_eq!(trace_id.len(), TRACE_ID_LENGTH);
    }

    #[test]
    fn test_generate_trace_id_is_hex() {
        let trace_id = generate_trace_id();
        assert!(trace_id.chars().all(|c| c.is_ascii_hexdigit()));
    }

    #[test]
    fn test_generate_span_id_length() {
        let span_id = generate_span_id();
        assert_eq!(span_id.len(), 16);
    }

    #[test]
    fn test_is_valid_trace_id() {
        assert!(is_valid_trace_id("a1b2c3d4e5f67890a1b2c3d4e5f67890"));
        assert!(!is_valid_trace_id("invalid"));
        assert!(!is_valid_trace_id("a1b2c3d4e5f67890"));
        assert!(!is_valid_trace_id("g1b2c3d4e5f67890a1b2c3d4e5f67890"));
    }

    #[test]
    fn test_extract_or_generate_trace_id_with_valid() {
        let existing = "a1b2c3d4e5f67890a1b2c3d4e5f67890";
        let result = extract_or_generate_trace_id(Some(existing));
        assert_eq!(result, existing);
    }

    #[test]
    fn test_extract_or_generate_trace_id_with_invalid() {
        let result = extract_or_generate_trace_id(Some("invalid"));
        assert_eq!(result.len(), TRACE_ID_LENGTH);
        assert_ne!(result, "invalid");
    }

    #[test]
    fn test_extract_or_generate_trace_id_with_none() {
        let result = extract_or_generate_trace_id(None);
        assert_eq!(result.len(), TRACE_ID_LENGTH);
    }

    #[test]
    fn test_create_connection_info() {
        let addr = "127.0.0.1:8080".parse().unwrap();
        let conn_info = create_connection_info(addr, None);
        assert_eq!(conn_info.client_addr, addr);
        assert_eq!(conn_info.trace_id.len(), TRACE_ID_LENGTH);
    }

    #[test]
    fn test_create_connection_info_with_existing_trace() {
        let addr = "127.0.0.1:8080".parse().unwrap();
        let existing = "a1b2c3d4e5f67890a1b2c3d4e5f67890";
        let conn_info = create_connection_info(addr, Some(existing));
        assert_eq!(conn_info.trace_id, existing);
    }

    #[test]
    fn test_extract_trace_id_from_traceparent_valid() {
        let tp = "00-a1b2c3d4e5f67890a1b2c3d4e5f67890-b1c2d3e4f5a67890-01";
        let result = extract_trace_id_from_traceparent(tp);
        assert_eq!(result, Some("a1b2c3d4e5f67890a1b2c3d4e5f67890".to_string()));
    }

    #[test]
    fn test_extract_trace_id_from_traceparent_invalid_version() {
        let tp = "01-a1b2c3d4e5f67890a1b2c3d4e5f67890-b1c2d3e4f5a67890-01";
        assert!(extract_trace_id_from_traceparent(tp).is_none());
    }

    #[test]
    fn test_extract_trace_id_from_traceparent_all_zeros() {
        let tp = "00-00000000000000000000000000000000-b1c2d3e4f5a67890-01";
        assert!(extract_trace_id_from_traceparent(tp).is_none());
    }

    #[test]
    fn test_extract_trace_id_from_traceparent_malformed() {
        assert!(extract_trace_id_from_traceparent("invalid").is_none());
        assert!(extract_trace_id_from_traceparent("00-short-id-01").is_none());
    }

    #[test]
    fn test_build_traceparent() {
        let tp = build_traceparent(
            "a1b2c3d4e5f67890a1b2c3d4e5f67890",
            "b1c2d3e4f5a67890",
        );
        assert_eq!(tp, "00-a1b2c3d4e5f67890a1b2c3d4e5f67890-b1c2d3e4f5a67890-01");
    }

    #[test]
    fn test_extract_trace_from_headers_w3c_priority() {
        let tp = "00-a1b2c3d4e5f67890a1b2c3d4e5f67890-b1c2d3e4f5a67890-01";
        let rid = "ffffffffffffffffffffffffffffffff";
        let (trace_id, span_id) = extract_trace_from_headers(Some(tp), Some(rid));
        assert_eq!(trace_id, "a1b2c3d4e5f67890a1b2c3d4e5f67890");
        assert_eq!(span_id, "b1c2d3e4f5a67890");
    }

    #[test]
    fn test_extract_trace_from_headers_fallback_to_request_id() {
        let rid = "a1b2c3d4e5f67890a1b2c3d4e5f67890";
        let (trace_id, span_id) = extract_trace_from_headers(None, Some(rid));
        assert_eq!(trace_id, rid);
        assert_eq!(span_id.len(), 16);
    }

    #[test]
    fn test_extract_trace_from_headers_generate_new() {
        let (trace_id, span_id) = extract_trace_from_headers(None, None);
        assert_eq!(trace_id.len(), 32);
        assert_eq!(span_id.len(), 16);
    }
}
