use std::io;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum EdgeError {
    #[error("TLS error: {0}")]
    Tls(String),

    #[error("TLS handshake timeout")]
    TlsHandshakeTimeout,

    #[error("Connection limit exceeded: {limit}")]
    ConnectionLimitExceeded { limit: usize },

    #[error("Per-IP connection limit exceeded for {ip}: {limit}")]
    PerIpConnectionLimitExceeded { ip: String, limit: usize },

    #[error("Upstream connection failed: {0}")]
    UpstreamConnectionFailed(String),

    #[error("Upstream timeout: {0}")]
    UpstreamTimeout(String),

    #[error("Upstream unavailable: {region}")]
    UpstreamUnavailable { region: String },

    #[error("All upstreams unavailable")]
    AllUpstreamsUnavailable,

    #[error("Region selection failed: {0}")]
    RegionSelectionFailed(String),

    #[error("GeoIP lookup failed: {0}")]
    GeoIpLookupFailed(String),

    #[error("Invalid request: {0}")]
    InvalidRequest(String),

    #[error("Request too large: {size} bytes (max: {max})")]
    RequestTooLarge { size: usize, max: usize },

    #[error("Header too large: {size} bytes (max: {max})")]
    HeaderTooLarge { size: usize, max: usize },

    #[error("Configuration error: {0}")]
    Configuration(String),

    #[error("Certificate loading failed: {0}")]
    CertificateLoadFailed(String),

    #[error("IO error: {0}")]
    Io(#[from] io::Error),

    #[error("Internal error: {0}")]
    Internal(String),
}

impl EdgeError {
    pub fn error_code(&self) -> &'static str {
        use crate::constants::error_codes::*;
        
        match self {
            EdgeError::Tls(_) | EdgeError::TlsHandshakeTimeout => TLS_HANDSHAKE_FAILED,
            EdgeError::ConnectionLimitExceeded { .. } 
            | EdgeError::PerIpConnectionLimitExceeded { .. } => CONNECTION_LIMIT_EXCEEDED,
            EdgeError::UpstreamConnectionFailed(_) 
            | EdgeError::UpstreamUnavailable { .. }
            | EdgeError::AllUpstreamsUnavailable => UPSTREAM_UNAVAILABLE,
            EdgeError::UpstreamTimeout(_) => UPSTREAM_TIMEOUT,
            EdgeError::InvalidRequest(_) 
            | EdgeError::RequestTooLarge { .. }
            | EdgeError::HeaderTooLarge { .. } => INVALID_REQUEST,
            EdgeError::RegionSelectionFailed(_) 
            | EdgeError::GeoIpLookupFailed(_) => REGION_SELECTION_FAILED,
            _ => INTERNAL_ERROR,
        }
    }

    pub fn is_retryable(&self) -> bool {
        matches!(
            self,
            EdgeError::UpstreamConnectionFailed(_) 
            | EdgeError::UpstreamTimeout(_)
            | EdgeError::UpstreamUnavailable { .. }
        )
    }

    pub fn is_client_error(&self) -> bool {
        matches!(
            self,
            EdgeError::InvalidRequest(_)
            | EdgeError::RequestTooLarge { .. }
            | EdgeError::HeaderTooLarge { .. }
            | EdgeError::ConnectionLimitExceeded { .. }
            | EdgeError::PerIpConnectionLimitExceeded { .. }
        )
    }
}

pub type Result<T> = std::result::Result<T, EdgeError>;
