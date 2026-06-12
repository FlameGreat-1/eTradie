use crate::constants::{
    TRACE_ID_CHARSET, TRACE_ID_LENGTH, W3C_TRACEPARENT_VERSION, W3C_TRACE_FLAGS_SAMPLED,
};
use crate::error::{FilterError, FilterResult};
use std::time::SystemTime;

pub fn generate_trace_id() -> String {
    let mut trace_id = String::with_capacity(TRACE_ID_LENGTH);
    let timestamp = get_timestamp_hex();

    trace_id.push_str(&timestamp);

    let remaining = TRACE_ID_LENGTH - timestamp.len();
    for _ in 0..remaining {
        let idx = get_random_byte() as usize % TRACE_ID_CHARSET.len();
        trace_id.push(TRACE_ID_CHARSET[idx] as char);
    }

    trace_id
}

pub fn generate_span_id() -> String {
    let mut span_id = String::with_capacity(16);
    for _ in 0..16 {
        let idx = get_random_byte() as usize % TRACE_ID_CHARSET.len();
        span_id.push(TRACE_ID_CHARSET[idx] as char);
    }
    span_id
}

pub fn validate_trace_id(trace_id: &str) -> FilterResult<()> {
    if trace_id.is_empty() {
        return Err(FilterError::InvalidTraceId {
            trace_id: trace_id.to_string(),
            reason: "Trace ID cannot be empty".to_string(),
        });
    }

    if trace_id.len() > TRACE_ID_LENGTH * 2 {
        return Err(FilterError::InvalidTraceId {
            trace_id: trace_id.to_string(),
            reason: format!("Trace ID too long (max {} characters)", TRACE_ID_LENGTH * 2),
        });
    }

    if !trace_id
        .chars()
        .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
    {
        return Err(FilterError::InvalidTraceId {
            trace_id: trace_id.to_string(),
            reason:
                "Trace ID contains invalid characters (only alphanumeric, dash, underscore allowed)"
                    .to_string(),
        });
    }

    Ok(())
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

fn get_timestamp_hex() -> String {
    use proxy_wasm::hostcalls;

    match hostcalls::get_current_time() {
        Ok(time) => {
            let timestamp = time
                .duration_since(SystemTime::UNIX_EPOCH)
                .unwrap_or_default()
                .as_millis() as u64;
            format!("{:x}", timestamp)
        }
        Err(_) => String::from("0"),
    }
}

fn get_random_byte() -> u8 {
    let mut buf = [0u8; 1];
    if getrandom::getrandom(&mut buf).is_ok() {
        buf[0]
    } else {
        use proxy_wasm::hostcalls;
        match hostcalls::get_current_time() {
            Ok(time) => {
                let nanos = time
                    .duration_since(SystemTime::UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_nanos();
                (nanos % 256) as u8
            }
            Err(_) => 42,
        }
    }
}

#[cfg(target_arch = "wasm32")]
fn custom_getrandom(buf: &mut [u8]) -> Result<(), getrandom::Error> {
    use proxy_wasm::hostcalls;

    for byte in buf.iter_mut() {
        match hostcalls::get_current_time() {
            Ok(time) => {
                let nanos = time
                    .duration_since(SystemTime::UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_nanos();
                *byte = (nanos % 256) as u8;
            }
            Err(_) => {
                *byte = 0;
            }
        }
    }
    Ok(())
}

#[cfg(target_arch = "wasm32")]
getrandom::register_custom_getrandom!(custom_getrandom);
