use crate::constants::{ENVIRONMENT_ENV, SERVICE_NAME, SERVICE_VERSION};
use crate::types::{ConnectionInfo, Region, RequestMetadata, TlsVersion};
use std::env;
use std::net::IpAddr;
use tracing::{error, info, warn};

pub fn init_logging() {
    use tracing_subscriber::{fmt, EnvFilter, layer::SubscriberExt, util::SubscriberInitExt};

    let environment = env::var(ENVIRONMENT_ENV).unwrap_or_else(|_| "unknown".to_string());

    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info"));

    let fmt_layer = fmt::layer()
        .json()
        .with_target(false)
        .with_current_span(true)
        .with_span_list(false);

    tracing_subscriber::registry()
        .with(filter)
        .with(fmt_layer)
        .init();

    info!(
        service = SERVICE_NAME,
        version = SERVICE_VERSION,
        environment = %environment,
        "logging initialized"
    );
}

/// Initialise structured JSON logging with an OpenTelemetry tracing layer.
///
/// `tracer` is the concrete SDK tracer produced by
/// `opentelemetry_otlp ...install_batch()` in `init_otel_tracer`. It is
/// passed in (rather than fetched via `global::tracer`, which returns a
/// type-erased `BoxedTracer` that does not implement `PreSampledTracer`)
/// so `OpenTelemetryLayer::new` accepts it. When `None` (the exporter
/// failed to initialise) the OTel layer is omitted and only the JSON
/// stdout subscriber is installed, so logging still works without trace
/// export.
pub fn init_logging_with_otel(tracer: Option<opentelemetry_sdk::trace::Tracer>) {
    use tracing_subscriber::{fmt, EnvFilter, layer::SubscriberExt, util::SubscriberInitExt};
    use tracing_opentelemetry::OpenTelemetryLayer;

    let environment = env::var(ENVIRONMENT_ENV).unwrap_or_else(|_| "unknown".to_string());

    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info"));

    let fmt_layer = fmt::layer()
        .json()
        .with_target(false)
        .with_current_span(true)
        .with_span_list(false);

    match tracer {
        Some(tracer) => {
            let otel_layer = OpenTelemetryLayer::new(tracer);
            tracing_subscriber::registry()
                .with(filter)
                .with(fmt_layer)
                .with(otel_layer)
                .init();
            info!(
                service = SERVICE_NAME,
                version = SERVICE_VERSION,
                environment = %environment,
                "logging initialized with OpenTelemetry"
            );
        }
        None => {
            tracing_subscriber::registry()
                .with(filter)
                .with(fmt_layer)
                .init();
            info!(
                service = SERVICE_NAME,
                version = SERVICE_VERSION,
                environment = %environment,
                "logging initialized (OpenTelemetry export unavailable)"
            );
        }
    }
}

pub fn log_connection_accepted(conn_info: &ConnectionInfo) {
    info!(
        trace_id = %conn_info.trace_id,
        client_ip = %conn_info.client_ip,
        client_addr = %conn_info.client_addr,
        service = SERVICE_NAME,
        "connection_accepted"
    );
}

pub fn log_connection_closed(conn_info: &ConnectionInfo, bytes_received: u64, bytes_sent: u64) {
    let duration_ms = conn_info.duration().as_millis() as u64;

    info!(
        trace_id = %conn_info.trace_id,
        client_ip = %conn_info.client_ip,
        duration_ms = duration_ms,
        bytes_received = bytes_received,
        bytes_sent = bytes_sent,
        service = SERVICE_NAME,
        "connection_closed"
    );
}

pub fn log_tls_handshake_success(
    conn_info: &ConnectionInfo,
    tls_version: TlsVersion,
    sni_hostname: Option<&str>,
    duration_ms: u64,
) {
    info!(
        trace_id = %conn_info.trace_id,
        client_ip = %conn_info.client_ip,
        tls_version = %tls_version,
        sni_hostname = sni_hostname,
        duration_ms = duration_ms,
        service = SERVICE_NAME,
        "tls_handshake_success"
    );
}

pub fn log_tls_handshake_failed(
    client_ip: IpAddr,
    trace_id: &str,
    error: &str,
    duration_ms: u64,
) {
    warn!(
        trace_id = trace_id,
        client_ip = %client_ip,
        error = error,
        duration_ms = duration_ms,
        service = SERVICE_NAME,
        "tls_handshake_failed"
    );
}

pub fn log_region_selected(
    trace_id: &str,
    client_ip: IpAddr,
    selected_region: Region,
    is_fallback: bool,
) {
    info!(
        trace_id = trace_id,
        client_ip = %client_ip,
        selected_region = %selected_region,
        is_fallback = is_fallback,
        service = SERVICE_NAME,
        "region_selected"
    );
}

pub fn log_upstream_connection_success(
    trace_id: &str,
    region: Region,
    upstream_addr: &str,
    duration_ms: u64,
) {
    info!(
        trace_id = trace_id,
        region = %region,
        upstream_addr = upstream_addr,
        duration_ms = duration_ms,
        service = SERVICE_NAME,
        "upstream_connection_success"
    );
}

pub fn log_upstream_connection_failed(
    trace_id: &str,
    region: Region,
    upstream_addr: &str,
    error: &str,
    duration_ms: u64,
) {
    warn!(
        trace_id = trace_id,
        region = %region,
        upstream_addr = upstream_addr,
        error = error,
        duration_ms = duration_ms,
        service = SERVICE_NAME,
        "upstream_connection_failed"
    );
}

pub fn log_request_completed(metadata: &RequestMetadata) {
    info!(
        trace_id = %metadata.trace_id,
        client_ip = %metadata.client_ip,
        selected_region = %metadata.selected_region,
        upstream_address = %metadata.upstream_address,
        tls_version = ?metadata.tls_version,
        bytes_received = metadata.bytes_received,
        bytes_sent = metadata.bytes_sent,
        duration_ms = metadata.duration_ms,
        status = metadata.status.as_str(),
        service = SERVICE_NAME,
        "request_completed"
    );
}

pub fn log_connection_limit_exceeded(client_ip: IpAddr, limit: usize, is_per_ip: bool) {
    warn!(
        client_ip = %client_ip,
        limit = limit,
        limit_type = if is_per_ip { "per_ip" } else { "global" },
        service = SERVICE_NAME,
        "connection_limit_exceeded"
    );
}

pub fn log_upstream_health_check(region: Region, is_healthy: bool, consecutive_count: u32) {
    info!(
        region = %region,
        is_healthy = is_healthy,
        consecutive_count = consecutive_count,
        service = SERVICE_NAME,
        "upstream_health_check"
    );
}

pub fn log_retry_attempt(trace_id: &str, region: Region, attempt: u8, max_attempts: u8) {
    info!(
        trace_id = trace_id,
        region = %region,
        attempt = attempt,
        max_attempts = max_attempts,
        service = SERVICE_NAME,
        "retry_attempt"
    );
}

pub fn log_all_upstreams_unavailable(trace_id: &str, client_ip: IpAddr) {
    error!(
        trace_id = trace_id,
        client_ip = %client_ip,
        service = SERVICE_NAME,
        "all_upstreams_unavailable"
    );
}

pub fn log_invalid_request(trace_id: &str, client_ip: IpAddr, reason: &str) {
    warn!(
        trace_id = trace_id,
        client_ip = %client_ip,
        reason = reason,
        service = SERVICE_NAME,
        "invalid_request"
    );
}

pub fn log_internal_error(trace_id: &str, error: &str) {
    error!(
        trace_id = trace_id,
        error = error,
        service = SERVICE_NAME,
        "internal_error"
    );
}

pub fn log_server_started(tls_port: u16, metrics_port: u16) {
    info!(
        tls_port = tls_port,
        metrics_port = metrics_port,
        service = SERVICE_NAME,
        version = SERVICE_VERSION,
        "server_started"
    );
}

pub fn log_server_shutdown(reason: &str) {
    info!(
        reason = reason,
        service = SERVICE_NAME,
        "server_shutdown"
    );
}

pub fn log_configuration_loaded(config_path: &str) {
    info!(
        config_path = config_path,
        service = SERVICE_NAME,
        "configuration_loaded"
    );
}

pub fn log_certificate_loaded(hostname: &str, expires_at: &str) {
    info!(
        hostname = hostname,
        expires_at = expires_at,
        service = SERVICE_NAME,
        "certificate_loaded"
    );
}

pub fn log_geoip_database_loaded(path: &str, database_type: &str) {
    info!(
        path = path,
        database_type = database_type,
        service = SERVICE_NAME,
        "geoip_database_loaded"
    );
}

pub fn log_shutdown_draining(active_connections: i64) {
    info!(
        active_connections = active_connections,
        service = SERVICE_NAME,
        "shutdown_draining_connections"
    );
}
