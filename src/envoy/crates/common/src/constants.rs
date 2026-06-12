pub const MAX_REQUEST_BODY_SIZE: usize = 10 * 1024 * 1024;
pub const MAX_HEADER_SIZE: usize = 8 * 1024;
pub const MAX_HEADER_COUNT: usize = 100;
pub const MAX_QUERY_STRING_SIZE: usize = 4 * 1024;
pub const MAX_USER_AGENT_SIZE: usize = 500;

pub const TRACE_ID_LENGTH: usize = 32;
pub const TRACE_ID_CHARSET: &[u8] = b"0123456789abcdef";

pub const GLOBAL_RATE_LIMIT_REQUESTS: u64 = 10_000;
pub const GLOBAL_RATE_LIMIT_PERIOD_SECS: u64 = 1;

pub const IP_RATE_LIMIT_REQUESTS: u64 = 100;
pub const IP_RATE_LIMIT_PERIOD_SECS: u64 = 1;

pub const CIRCUIT_BREAKER_FAILURE_THRESHOLD: u32 = 5;
pub const CIRCUIT_BREAKER_RESET_TIMEOUT_SECS: u64 = 30;

pub const LATENCY_BUDGET_MS: u64 = 1;

pub const HEADER_X_REQUEST_ID: &str = "x-request-id";
pub const HEADER_X_TRACE_ID: &str = "x-trace-id";
pub const HEADER_TRACEPARENT: &str = "traceparent";
pub const HEADER_USER_AGENT: &str = "user-agent";
pub const HEADER_CONTENT_TYPE: &str = "content-type";
pub const HEADER_CONTENT_LENGTH: &str = "content-length";
pub const HEADER_RETRY_AFTER: &str = "retry-after";

// Browser security headers. The Envoy route_config sets these on proxied
// responses; ResponseBuilder seeds the same values on filter-generated
// local replies so blocked requests carry them too. Kept byte-identical
// to the route_config block so the two paths never drift. HSTS is set at
// the Cloudflare TLS edge, not here.
pub const HEADER_X_CONTENT_TYPE_OPTIONS: &str = "x-content-type-options";
pub const HEADER_X_FRAME_OPTIONS: &str = "x-frame-options";
pub const HEADER_REFERRER_POLICY: &str = "referrer-policy";
pub const HEADER_CONTENT_SECURITY_POLICY: &str = "content-security-policy";

pub const VALUE_X_CONTENT_TYPE_OPTIONS: &str = "nosniff";
pub const VALUE_X_FRAME_OPTIONS: &str = "DENY";
pub const VALUE_REFERRER_POLICY: &str = "strict-origin-when-cross-origin";
pub const VALUE_CONTENT_SECURITY_POLICY: &str = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: blob:; connect-src 'self' https: wss:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'";

// Cloudflare-set headers honoured by the trust-chain resolver. Envoy
// itself does NOT validate these; trust enforcement lives in the gateway
// auth/clientip resolver, which gates them on the immediate peer being
// in the configured trusted-proxy CIDR list.
pub const HEADER_CF_CONNECTING_IP: &str = "cf-connecting-ip";
pub const HEADER_X_FORWARDED_FOR: &str = "x-forwarded-for";
pub const HEADER_X_REAL_IP: &str = "x-real-ip";

pub const W3C_TRACEPARENT_VERSION: &str = "00";
pub const W3C_TRACE_FLAGS_SAMPLED: &str = "01";

pub const ALLOWED_CONTENT_TYPES: &[&str] = &[
    "application/json",
    "text/event-stream",
    "application/x-www-form-urlencoded",
    "multipart/form-data",
    "text/plain",
];

// Full HTTP method set the gateway exposes. The previous {GET,POST}
// default rejected PUT (password change, admin user actions),
// DELETE (planned admin endpoints), PATCH (partial updates), and
// OPTIONS (CORS preflight from dashboard). HEAD is included for
// uptime probes that prefer header-only responses.
pub const ALLOWED_HTTP_METHODS: &[&str] =
    &["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"];

pub const HTTP_STATUS_BAD_REQUEST: u32 = 400;
pub const HTTP_STATUS_PAYLOAD_TOO_LARGE: u32 = 413;
pub const HTTP_STATUS_TOO_MANY_REQUESTS: u32 = 429;
pub const HTTP_STATUS_INTERNAL_SERVER_ERROR: u32 = 500;
pub const HTTP_STATUS_SERVICE_UNAVAILABLE: u32 = 503;

pub const METRIC_PREFIX: &str = "etradie_envoy";
pub const METRIC_REQUESTS_TOTAL: &str = "requests_total";
pub const METRIC_REQUESTS_BLOCKED: &str = "requests_blocked";
pub const METRIC_LATENCY_MS: &str = "latency_ms";
pub const METRIC_CIRCUIT_BREAKER_OPEN: &str = "circuit_breaker_open";

pub const SERVICE_NAME: &str = "etradie-envoy";
pub const SERVICE_VERSION: &str = "1.0.0";
pub const ENVIRONMENT_KEY: &str = "environment";
pub const DEFAULT_ENVIRONMENT: &str = "unknown";
