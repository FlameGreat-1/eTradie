use serde::{Deserialize, Serialize};
use std::fmt;
use std::net::{IpAddr, SocketAddr};
use std::time::{Duration, Instant};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Region {
    UsEast1,
    UsWest2,
    EuWest1,
    ApSoutheast1,
    Custom(u8),
}

impl Region {
    pub fn as_str(&self) -> &str {
        match self {
            Region::UsEast1 => "us-east-1",
            Region::UsWest2 => "us-west-2",
            Region::EuWest1 => "eu-west-1",
            Region::ApSoutheast1 => "ap-southeast-1",
            Region::Custom(_) => "custom",
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "us-east-1" => Some(Region::UsEast1),
            "us-west-2" => Some(Region::UsWest2),
            "eu-west-1" => Some(Region::EuWest1),
            "ap-southeast-1" => Some(Region::ApSoutheast1),
            _ => None,
        }
    }
}

impl fmt::Display for Region {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum UpstreamStatus {
    Healthy,
    Unhealthy,
    Unknown,
}

impl UpstreamStatus {
    pub fn is_healthy(&self) -> bool {
        matches!(self, UpstreamStatus::Healthy)
    }

    pub fn as_metric_value(&self) -> f64 {
        match self {
            UpstreamStatus::Healthy => 1.0,
            UpstreamStatus::Unhealthy => 0.0,
            UpstreamStatus::Unknown => -1.0,
        }
    }
}

#[derive(Debug, Clone)]
pub struct ConnectionInfo {
    pub client_addr: SocketAddr,
    pub client_ip: IpAddr,
    pub trace_id: String,
    pub established_at: Instant,
    pub tls_version: Option<TlsVersion>,
    pub sni_hostname: Option<String>,
}

impl ConnectionInfo {
    pub fn new(client_addr: SocketAddr, trace_id: String) -> Self {
        Self {
            client_addr,
            client_ip: client_addr.ip(),
            trace_id,
            established_at: Instant::now(),
            tls_version: None,
            sni_hostname: None,
        }
    }

    pub fn duration(&self) -> Duration {
        self.established_at.elapsed()
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TlsVersion {
    Tls12,
    Tls13,
}

impl TlsVersion {
    pub fn as_str(&self) -> &str {
        match self {
            TlsVersion::Tls12 => "1.2",
            TlsVersion::Tls13 => "1.3",
        }
    }
}

impl fmt::Display for TlsVersion {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "TLS {}", self.as_str())
    }
}

#[derive(Debug, Clone)]
pub struct UpstreamEndpoint {
    pub region: Region,
    pub address: SocketAddr,
    pub status: UpstreamStatus,
    pub last_health_check: Option<Instant>,
    pub consecutive_failures: u32,
    pub consecutive_successes: u32,
}

impl UpstreamEndpoint {
    pub fn new(region: Region, address: SocketAddr) -> Self {
        Self {
            region,
            address,
            status: UpstreamStatus::Unknown,
            last_health_check: None,
            consecutive_failures: 0,
            consecutive_successes: 0,
        }
    }

    pub fn mark_healthy(&mut self) {
        self.consecutive_successes += 1;
        self.consecutive_failures = 0;
        self.status = UpstreamStatus::Healthy;
        self.last_health_check = Some(Instant::now());
    }

    pub fn mark_unhealthy(&mut self) {
        self.consecutive_failures += 1;
        self.consecutive_successes = 0;
        self.status = UpstreamStatus::Unhealthy;
        self.last_health_check = Some(Instant::now());
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestMetadata {
    pub trace_id: String,
    pub client_ip: IpAddr,
    pub selected_region: Region,
    pub upstream_address: SocketAddr,
    pub tls_version: Option<TlsVersion>,
    pub bytes_received: u64,
    pub bytes_sent: u64,
    pub duration_ms: u64,
    pub status: RequestStatus,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RequestStatus {
    Success,
    UpstreamError,
    ClientError,
    Timeout,
    ConnectionFailed,
    // Generic catch-all for a connection that failed before it could be
    // classified into one of the specific variants above (e.g. it is the
    // initial value in handler.rs::handle_connection, recorded on the
    // connection-limit / TLS-handshake / routing early-return paths).
    Error,
}

impl RequestStatus {
    pub fn as_str(&self) -> &str {
        match self {
            RequestStatus::Success => "success",
            RequestStatus::UpstreamError => "upstream_error",
            RequestStatus::ClientError => "client_error",
            RequestStatus::Timeout => "timeout",
            RequestStatus::ConnectionFailed => "connection_failed",
            RequestStatus::Error => "error",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FallbackReason {
    PreferredUnavailable,
    SecondaryUnavailable,
    AllRegionsUnavailable,
}

impl FallbackReason {
    pub fn as_str(&self) -> &str {
        match self {
            FallbackReason::PreferredUnavailable => "preferred_unavailable",
            FallbackReason::SecondaryUnavailable => "secondary_unavailable",
            FallbackReason::AllRegionsUnavailable => "all_regions_unavailable",
        }
    }
}
