use std::time::Duration;

pub const SERVICE_NAME: &str = "edge-ingress";
pub const SERVICE_VERSION: &str = env!("CARGO_PKG_VERSION");

pub const TLS_PORT: u16 = 443;
pub const METRICS_PORT: u16 = 9902;

pub const MAX_GLOBAL_CONNECTIONS: usize = 100_000;
pub const MAX_CONNECTIONS_PER_IP: usize = 1_000;

pub const TLS_HANDSHAKE_TIMEOUT: Duration = Duration::from_secs(10);
pub const UPSTREAM_CONNECT_TIMEOUT: Duration = Duration::from_secs(5);
pub const IDLE_TIMEOUT: Duration = Duration::from_secs(300);
pub const UPSTREAM_REQUEST_TIMEOUT: Duration = Duration::from_secs(60);

// NOTE: HTTP request-byte and header-size limits are intentionally NOT
// defined here. edge-ingress is a Layer-4 TLS-terminating TCP proxy
// (handler.rs: TLS handshake -> geo-route -> copy_bidirectional); it
// never parses HTTP and therefore cannot enforce an HTTP byte/header
// cap. Those limits live at the HTTP-aware layer (Envoy:
// max_request_bytes per route + max_request_headers_kb on the HTTP
// connection manager, see helm/envoy/templates/configmap.yaml) and at
// the Go services' auth.MaxJSONBodyBytes. The previously-declared
// MAX_REQUEST_SIZE / MAX_HEADER_SIZE constants were never read on the
// L4 path and were removed (TIER4 finding E5) because they implied a
// protection this proxy does not provide.

pub const MAX_RETRY_ATTEMPTS: u8 = 1;
pub const RETRY_BACKOFF_MS: u64 = 100;

pub const HEALTH_CHECK_INTERVAL: Duration = Duration::from_secs(10);
pub const HEALTH_CHECK_TIMEOUT: Duration = Duration::from_secs(3);
pub const HEALTH_CHECK_UNHEALTHY_THRESHOLD: u32 = 3;
pub const HEALTH_CHECK_HEALTHY_THRESHOLD: u32 = 2;

pub const TRACE_ID_LENGTH: usize = 32;
pub const TRACE_ID_HEADER: &str = "X-Request-ID";
pub const W3C_TRACEPARENT_HEADER: &str = "traceparent";
pub const W3C_TRACEPARENT_VERSION: &str = "00";
pub const W3C_TRACE_FLAGS_SAMPLED: &str = "01";

pub const DEFAULT_ENVOY_SERVICE: &str = "envoy.etradie-system.svc.cluster.local";
pub const DEFAULT_ENVOY_PORT: u16 = 8080;

pub const GEOIP_DATABASE_PATH: &str = "/data/geoip/GeoLite2-City.mmdb";

pub const METRICS_HISTOGRAM_BUCKETS: &[f64] = &[
    0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
];

pub const LOG_LEVEL_ENV: &str = "EDGE_INGRESS_LOG_LEVEL";
pub const CONFIG_PATH_ENV: &str = "EDGE_INGRESS_CONFIG_PATH";
pub const ENVIRONMENT_ENV: &str = "EDGE_INGRESS_ENVIRONMENT";
pub const OTEL_EXPORTER_ENDPOINT_ENV: &str = "OTEL_EXPORTER_OTLP_ENDPOINT";
pub const DEFAULT_OTEL_ENDPOINT: &str = "http://otel-collector.monitoring.svc.cluster.local:4317";

pub mod tls {
    pub const MIN_TLS_VERSION: &str = "1.2";
    pub const PREFERRED_TLS_VERSION: &str = "1.3";
    pub const CIPHER_SUITES: &[&str] = &[
        "TLS_AES_256_GCM_SHA384",
        "TLS_AES_128_GCM_SHA256",
        "TLS_CHACHA20_POLY1305_SHA256",
    ];
    pub const CERT_RELOAD_INTERVAL_SECS: u64 = 3600;
}

pub mod regions {
    pub const DEFAULT_REGION: &str = "us-east-1";
    pub const FALLBACK_REGIONS: &[&str] = &["us-west-2", "eu-west-1", "ap-southeast-1"];
}

pub mod error_codes {
    pub const TLS_HANDSHAKE_FAILED: &str = "TLS_HANDSHAKE_FAILED";
    pub const CONNECTION_LIMIT_EXCEEDED: &str = "CONNECTION_LIMIT_EXCEEDED";
    pub const UPSTREAM_UNAVAILABLE: &str = "UPSTREAM_UNAVAILABLE";
    pub const UPSTREAM_TIMEOUT: &str = "UPSTREAM_TIMEOUT";
    pub const INVALID_REQUEST: &str = "INVALID_REQUEST";
    pub const INTERNAL_ERROR: &str = "INTERNAL_ERROR";
    pub const REGION_SELECTION_FAILED: &str = "REGION_SELECTION_FAILED";
}
