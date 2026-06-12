use crate::constants::{DEFAULT_ENVIRONMENT, SERVICE_NAME, SERVICE_VERSION};
use crate::types::SecurityEvent;
use proxy_wasm::hostcalls;
use serde::Serialize;
use std::time::SystemTime;

static mut ENVIRONMENT: Option<String> = None;

pub fn set_environment(env: &str) {
    unsafe {
        ENVIRONMENT = Some(env.to_string());
    }
}

fn get_environment() -> String {
    unsafe {
        ENVIRONMENT
            .clone()
            .unwrap_or_else(|| DEFAULT_ENVIRONMENT.to_string())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LogLevel {
    Debug,
    Info,
    Warn,
    Error,
}

impl LogLevel {
    fn as_str(&self) -> &'static str {
        match self {
            Self::Debug => "DEBUG",
            Self::Info => "INFO",
            Self::Warn => "WARN",
            Self::Error => "ERROR",
        }
    }

    fn to_proxy_level(&self) -> proxy_wasm::types::LogLevel {
        match self {
            Self::Debug => proxy_wasm::types::LogLevel::Debug,
            Self::Info => proxy_wasm::types::LogLevel::Info,
            Self::Warn => proxy_wasm::types::LogLevel::Warn,
            Self::Error => proxy_wasm::types::LogLevel::Error,
        }
    }
}

#[derive(Debug, Serialize)]
struct LogEntry {
    level: String,
    timestamp_ms: u64,
    service: String,
    version: String,
    environment: String,
    trace_id: String,
    message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    component: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    client_ip: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    event_code: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    details: Option<serde_json::Value>,
}

pub struct Logger {
    component: String,
}

impl Logger {
    pub fn new(component: &str) -> Self {
        Self {
            component: component.to_string(),
        }
    }

    pub fn debug(&self, trace_id: &str, message: &str) {
        self.log(LogLevel::Debug, trace_id, message, None, None);
    }

    pub fn info(&self, trace_id: &str, message: &str) {
        self.log(LogLevel::Info, trace_id, message, None, None);
    }

    pub fn warn(&self, trace_id: &str, message: &str) {
        self.log(LogLevel::Warn, trace_id, message, None, None);
    }

    pub fn error(&self, trace_id: &str, message: &str) {
        self.log(LogLevel::Error, trace_id, message, None, None);
    }

    pub fn log_with_details<T: Serialize>(
        &self,
        level: LogLevel,
        trace_id: &str,
        message: &str,
        details: &T,
    ) {
        let details_value = serde_json::to_value(details).ok();
        self.log(level, trace_id, message, None, details_value);
    }

    pub fn log_with_client_ip<T: Serialize>(
        &self,
        level: LogLevel,
        trace_id: &str,
        message: &str,
        client_ip: Option<&str>,
        details: &T,
    ) {
        let details_value = serde_json::to_value(details).ok();
        self.log(level, trace_id, message, client_ip, details_value);
    }

    pub fn log_security_event(&self, event: &SecurityEvent, client_ip: Option<&str>) {
        let entry = LogEntry {
            level: LogLevel::Warn.as_str().to_string(),
            timestamp_ms: event.timestamp_ms,
            service: SERVICE_NAME.to_string(),
            version: SERVICE_VERSION.to_string(),
            environment: get_environment(),
            trace_id: event.trace_id.clone(),
            message: event.code.description().to_string(),
            component: Some(self.component.clone()),
            client_ip: client_ip.map(|s| s.to_string()),
            event_code: Some(event.code.as_str().to_string()),
            details: serde_json::to_value(&event.details).ok(),
        };

        self.emit_log(LogLevel::Warn, &entry);
    }

    fn log(
        &self,
        level: LogLevel,
        trace_id: &str,
        message: &str,
        client_ip: Option<&str>,
        details: Option<serde_json::Value>,
    ) {
        let entry = LogEntry {
            level: level.as_str().to_string(),
            timestamp_ms: current_timestamp_ms(),
            service: SERVICE_NAME.to_string(),
            version: SERVICE_VERSION.to_string(),
            environment: get_environment(),
            trace_id: trace_id.to_string(),
            message: message.to_string(),
            component: Some(self.component.clone()),
            client_ip: client_ip.map(|s| s.to_string()),
            event_code: None,
            details,
        };

        self.emit_log(level, &entry);
    }

    fn emit_log(&self, level: LogLevel, entry: &LogEntry) {
        if let Ok(json) = serde_json::to_string(entry) {
            let _ = hostcalls::log(level.to_proxy_level(), &json);
        }
    }
}

pub fn log_request_start(trace_id: &str, method: &str, path: &str, client_ip: Option<&str>) {
    let logger = Logger::new("request");
    let msg = format!("Request started: {} {}", method, path);
    logger.log(LogLevel::Info, trace_id, &msg, client_ip, None);
}

pub fn log_request_end(trace_id: &str, status: u32, duration_ms: u64, client_ip: Option<&str>) {
    let logger = Logger::new("request");
    let details = serde_json::json!({
        "status": status,
        "duration_ms": duration_ms,
    });
    logger.log(
        LogLevel::Info,
        trace_id,
        &format!(
            "Request completed: status={} duration={}ms",
            status, duration_ms
        ),
        client_ip,
        Some(details),
    );
}

pub fn log_filter_decision(trace_id: &str, filter_name: &str, allowed: bool, reason: Option<&str>) {
    let logger = Logger::new(filter_name);
    let message = if allowed {
        format!("Filter passed: {}", filter_name)
    } else {
        format!(
            "Filter blocked: {} - {}",
            filter_name,
            reason.unwrap_or("No reason provided")
        )
    };

    if allowed {
        logger.debug(trace_id, &message);
    } else {
        logger.warn(trace_id, &message);
    }
}

fn current_timestamp_ms() -> u64 {
    match hostcalls::get_current_time() {
        Ok(time) => time
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64,
        Err(_) => 0,
    }
}
