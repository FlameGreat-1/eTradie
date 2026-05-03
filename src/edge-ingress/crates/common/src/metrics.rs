use crate::constants::{METRICS_HISTOGRAM_BUCKETS, SERVICE_NAME, SERVICE_VERSION};
use crate::types::{FallbackReason, Region, RequestStatus, TlsVersion, UpstreamStatus};
use lazy_static::lazy_static;
use prometheus::{
    register_counter_vec, register_gauge, register_gauge_vec, register_histogram_vec,
    register_int_counter_vec, register_int_gauge, CounterVec, Encoder, GaugeVec, HistogramVec,
    IntCounterVec, IntGauge, Gauge, TextEncoder,
};
use std::env;

lazy_static! {
    pub static ref ACTIVE_CONNECTIONS: IntGauge = register_int_gauge!(
        "edge_ingress_active_connections",
        "Current number of active connections"
    )
    .unwrap();
    pub static ref TOTAL_CONNECTIONS: IntCounterVec = register_int_counter_vec!(
        "edge_ingress_total_connections",
        "Total number of connections accepted",
        &["status"]
    )
    .unwrap();
    pub static ref CONNECTION_ERRORS: IntCounterVec = register_int_counter_vec!(
        "edge_ingress_connection_errors_total",
        "Total connection errors by type",
        &["error_type"]
    )
    .unwrap();
    pub static ref TLS_HANDSHAKE_DURATION: HistogramVec = register_histogram_vec!(
        "edge_ingress_tls_handshake_duration_seconds",
        "TLS handshake duration in seconds",
        &["tls_version"],
        METRICS_HISTOGRAM_BUCKETS.to_vec()
    )
    .unwrap();
    pub static ref TLS_HANDSHAKE_ERRORS: IntCounterVec = register_int_counter_vec!(
        "edge_ingress_tls_handshake_errors_total",
        "Total TLS handshake errors by type",
        &["error_type"]
    )
    .unwrap();
    pub static ref TLS_VERSION_GAUGE: GaugeVec = register_gauge_vec!(
        "edge_ingress_tls_version",
        "TLS version distribution",
        &["version"]
    )
    .unwrap();
    pub static ref REQUESTS_TOTAL: IntCounterVec = register_int_counter_vec!(
        "edge_ingress_requests_total",
        "Total requests by status",
        &["status"]
    )
    .unwrap();
    pub static ref REQUEST_DURATION: HistogramVec = register_histogram_vec!(
        "edge_ingress_request_duration_seconds",
        "Request duration in seconds",
        &["region", "status"],
        METRICS_HISTOGRAM_BUCKETS.to_vec()
    )
    .unwrap();
    pub static ref BYTES_RECEIVED: CounterVec = register_counter_vec!(
        "edge_ingress_bytes_received_total",
        "Total bytes received from clients",
        &["region"]
    )
    .unwrap();
    pub static ref BYTES_SENT: CounterVec = register_counter_vec!(
        "edge_ingress_bytes_sent_total",
        "Total bytes sent to clients",
        &["region"]
    )
    .unwrap();
    pub static ref UPSTREAM_HEALTH: GaugeVec = register_gauge_vec!(
        "edge_ingress_upstream_health",
        "Upstream health status (1=healthy, 0=unhealthy, -1=unknown)",
        &["region"]
    )
    .unwrap();
    pub static ref REGION_SELECTIONS: IntCounterVec = register_int_counter_vec!(
        "edge_ingress_region_selections_total",
        "Total region selections",
        &["region"]
    )
    .unwrap();
    pub static ref FALLBACK_SELECTIONS: IntCounterVec = register_int_counter_vec!(
        "edge_ingress_fallback_selections_total",
        "Total fallback selections by reason",
        &["reason"]
    )
    .unwrap();
    pub static ref UPSTREAM_CONNECT_DURATION: HistogramVec = register_histogram_vec!(
        "edge_ingress_upstream_connect_duration_seconds",
        "Upstream connection duration in seconds",
        &["region"],
        METRICS_HISTOGRAM_BUCKETS.to_vec()
    )
    .unwrap();
    pub static ref UPSTREAM_CONNECT_ERRORS: IntCounterVec = register_int_counter_vec!(
        "edge_ingress_upstream_connect_errors_total",
        "Total upstream connection errors",
        &["region", "error_type"]
    )
    .unwrap();
    pub static ref CERTIFICATE_EXPIRY_SECONDS: GaugeVec = register_gauge_vec!(
        "edge_ingress_certificate_expiry_seconds",
        "Seconds until certificate expiry",
        &["hostname"]
    )
    .unwrap();
    pub static ref GEOIP_LOOKUPS_TOTAL: IntCounterVec = register_int_counter_vec!(
        "edge_ingress_geoip_lookups_total",
        "Total GeoIP lookups by status",
        &["status"]
    )
    .unwrap();
    pub static ref GEOIP_LOOKUP_DURATION: HistogramVec = register_histogram_vec!(
        "edge_ingress_geoip_lookup_duration_seconds",
        "GeoIP lookup duration in seconds",
        &[],
        METRICS_HISTOGRAM_BUCKETS.to_vec()
    )
    .unwrap();
    pub static ref CONNECTION_DURATION: HistogramVec = register_histogram_vec!(
        "edge_ingress_connection_duration_seconds",
        "Total connection lifetime from accept to close",
        &["region", "status"],
        vec![0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
    )
    .unwrap();
    pub static ref UPSTREAM_POOL_SIZE: GaugeVec = register_gauge_vec!(
        "edge_ingress_upstream_pool_size",
        "Total upstream endpoints per region",
        &["region"]
    )
    .unwrap();
    pub static ref UPSTREAM_HEALTHY_COUNT: GaugeVec = register_gauge_vec!(
        "edge_ingress_upstream_healthy_count",
        "Healthy upstream endpoints per region",
        &["region"]
    )
    .unwrap();
    pub static ref SERVICE_INFO: GaugeVec = register_gauge_vec!(
        "edge_ingress_info",
        "Service metadata",
        &["version", "environment", "rust_version"]
    )
    .unwrap();
    pub static ref RETRY_ATTEMPTS_TOTAL: IntCounterVec = register_int_counter_vec!(
        "edge_ingress_retry_attempts_total",
        "Total retry attempts by outcome",
        &["status"]
    )
    .unwrap();
    pub static ref SHUTDOWN_CONNECTIONS_DRAINING: IntGauge = register_int_gauge!(
        "edge_ingress_shutdown_connections_draining",
        "Connections being drained during shutdown"
    )
    .unwrap();
}

pub fn init_metrics() {
    let environment = env::var(crate::constants::ENVIRONMENT_ENV)
        .unwrap_or_else(|_| "unknown".to_string());
    let rust_version = env!("CARGO_PKG_RUST_VERSION");

    SERVICE_INFO
        .with_label_values(&[SERVICE_VERSION, &environment, rust_version])
        .set(1.0);
}

pub fn increment_active_connections() {
    ACTIVE_CONNECTIONS.inc();
}

pub fn decrement_active_connections() {
    ACTIVE_CONNECTIONS.dec();
}

pub fn record_connection_accepted() {
    TOTAL_CONNECTIONS.with_label_values(&["accepted"]).inc();
}

pub fn record_connection_rejected(reason: &str) {
    TOTAL_CONNECTIONS.with_label_values(&["rejected"]).inc();
    CONNECTION_ERRORS.with_label_values(&[reason]).inc();
}

pub fn record_tls_handshake_duration(duration_secs: f64, tls_version: TlsVersion) {
    TLS_HANDSHAKE_DURATION
        .with_label_values(&[tls_version.as_str()])
        .observe(duration_secs);
}

pub fn record_tls_handshake_error(error_type: &str) {
    TLS_HANDSHAKE_ERRORS.with_label_values(&[error_type]).inc();
}

pub fn record_tls_version(tls_version: TlsVersion) {
    TLS_VERSION_GAUGE
        .with_label_values(&[tls_version.as_str()])
        .inc();
}

pub fn record_request_completed(status: RequestStatus, region: Region, duration_secs: f64) {
    REQUESTS_TOTAL.with_label_values(&[status.as_str()]).inc();
    REQUEST_DURATION
        .with_label_values(&[region.as_str(), status.as_str()])
        .observe(duration_secs);
}

pub fn record_bytes_received(region: Region, bytes: u64) {
    BYTES_RECEIVED
        .with_label_values(&[region.as_str()])
        .inc_by(bytes as f64);
}

pub fn record_bytes_sent(region: Region, bytes: u64) {
    BYTES_SENT
        .with_label_values(&[region.as_str()])
        .inc_by(bytes as f64);
}

pub fn update_upstream_health(region: Region, status: UpstreamStatus) {
    UPSTREAM_HEALTH
        .with_label_values(&[region.as_str()])
        .set(status.as_metric_value());
}

pub fn record_region_selection(region: Region) {
    REGION_SELECTIONS.with_label_values(&[region.as_str()]).inc();
}

pub fn record_fallback_selection(reason: FallbackReason) {
    FALLBACK_SELECTIONS
        .with_label_values(&[reason.as_str()])
        .inc();
}

pub fn record_upstream_connect_duration(region: Region, duration_secs: f64) {
    UPSTREAM_CONNECT_DURATION
        .with_label_values(&[region.as_str()])
        .observe(duration_secs);
}

pub fn record_upstream_connect_error(region: Region, error_type: &str) {
    UPSTREAM_CONNECT_ERRORS
        .with_label_values(&[region.as_str(), error_type])
        .inc();
}

pub fn record_certificate_expiry(hostname: &str, seconds_until_expiry: f64) {
    CERTIFICATE_EXPIRY_SECONDS
        .with_label_values(&[hostname])
        .set(seconds_until_expiry);
}

pub fn record_geoip_lookup(status: &str) {
    GEOIP_LOOKUPS_TOTAL.with_label_values(&[status]).inc();
}

pub fn record_geoip_lookup_duration(duration_secs: f64) {
    GEOIP_LOOKUP_DURATION
        .with_label_values(&[])
        .observe(duration_secs);
}

pub fn record_connection_duration(region: Region, status: RequestStatus, duration_secs: f64) {
    CONNECTION_DURATION
        .with_label_values(&[region.as_str(), status.as_str()])
        .observe(duration_secs);
}

pub fn update_upstream_pool_size(region: Region, size: f64) {
    UPSTREAM_POOL_SIZE
        .with_label_values(&[region.as_str()])
        .set(size);
}

pub fn update_upstream_healthy_count(region: Region, count: f64) {
    UPSTREAM_HEALTHY_COUNT
        .with_label_values(&[region.as_str()])
        .set(count);
}

pub fn record_retry_attempt(status: &str) {
    RETRY_ATTEMPTS_TOTAL.with_label_values(&[status]).inc();
}

pub fn set_shutdown_draining(count: i64) {
    SHUTDOWN_CONNECTIONS_DRAINING.set(count);
}

pub fn gather_metrics() -> Result<String, Box<dyn std::error::Error>> {
    let encoder = TextEncoder::new();
    let metric_families = prometheus::gather();
    let mut buffer = Vec::new();
    encoder.encode(&metric_families, &mut buffer)?;
    Ok(String::from_utf8(buffer)?)
}
