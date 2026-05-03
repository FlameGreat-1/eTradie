use crate::config::TlsConfig;
use edge_ingress_common::{
    metrics::{record_tls_handshake_duration, record_tls_handshake_error, record_tls_version},
    types::TlsVersion,
    EdgeError, Result,
};
use std::time::Instant;
use tokio::io::{AsyncRead, AsyncWrite};
use tokio::time::{timeout, Duration};
use tracing::{debug, warn};

pub struct HandshakeManager {
    handshake_timeout: Duration,
}

impl HandshakeManager {
    pub fn new(config: &TlsConfig) -> Self {
        Self {
            handshake_timeout: config.handshake_timeout,
        }
    }

    pub async fn perform_handshake<S, T, F, Fut>(
        &self,
        stream: S,
        handshake_fn: F,
    ) -> Result<(T, TlsVersion, Duration)>
    where
        S: AsyncRead + AsyncWrite + Unpin,
        F: FnOnce(S) -> Fut,
        Fut: std::future::Future<Output = Result<T>>,
        T: HasTlsVersion,
    {
        let start = Instant::now();

        debug!(
            timeout_ms = self.handshake_timeout.as_millis(),
            "starting TLS handshake"
        );

        let result = timeout(self.handshake_timeout, handshake_fn(stream)).await;

        let handshake_result = match result {
            Ok(Ok(tls_stream)) => {
                let tls_version = tls_stream.get_tls_version()?;
                let duration = start.elapsed();

                record_tls_handshake_duration(duration.as_secs_f64(), tls_version);
                record_tls_version(tls_version);

                debug!(
                    tls_version = %tls_version,
                    duration_ms = duration.as_millis(),
                    "TLS handshake successful"
                );

                Ok((tls_stream, tls_version, duration))
            }
            Ok(Err(e)) => {
                let duration = start.elapsed();
                let error_type = classify_handshake_error(&e);

                record_tls_handshake_error(error_type);

                warn!(
                    error = %e,
                    error_type = error_type,
                    duration_ms = duration.as_millis(),
                    "TLS handshake failed"
                );

                Err(e)
            }
            Err(_) => {
                let duration = start.elapsed();
                record_tls_handshake_error("timeout");

                warn!(
                    timeout_ms = self.handshake_timeout.as_millis(),
                    duration_ms = duration.as_millis(),
                    "TLS handshake timeout"
                );

                Err(EdgeError::TlsHandshakeTimeout)
            }
        };

        handshake_result
    }
}

pub trait HasTlsVersion {
    fn get_tls_version(&self) -> Result<TlsVersion>;
}

fn classify_handshake_error(error: &EdgeError) -> &'static str {
    match error {
        EdgeError::TlsHandshakeTimeout => "timeout",
        EdgeError::Tls(msg) => {
            if msg.contains("certificate") {
                "certificate_error"
            } else if msg.contains("protocol") {
                "protocol_error"
            } else if msg.contains("cipher") {
                "cipher_error"
            } else {
                "unknown"
            }
        }
        _ => "internal_error",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_classify_handshake_error_timeout() {
        let error = EdgeError::TlsHandshakeTimeout;
        assert_eq!(classify_handshake_error(&error), "timeout");
    }

    #[test]
    fn test_classify_handshake_error_certificate() {
        let error = EdgeError::Tls("certificate verification failed".to_string());
        assert_eq!(classify_handshake_error(&error), "certificate_error");
    }

    #[test]
    fn test_classify_handshake_error_protocol() {
        let error = EdgeError::Tls("protocol version mismatch".to_string());
        assert_eq!(classify_handshake_error(&error), "protocol_error");
    }

    #[test]
    fn test_classify_handshake_error_cipher() {
        let error = EdgeError::Tls("no cipher suites in common".to_string());
        assert_eq!(classify_handshake_error(&error), "cipher_error");
    }

    #[test]
    fn test_classify_handshake_error_unknown() {
        let error = EdgeError::Tls("unknown error".to_string());
        assert_eq!(classify_handshake_error(&error), "unknown");
    }

    #[test]
    fn test_classify_handshake_error_internal() {
        let error = EdgeError::Internal("internal error".to_string());
        assert_eq!(classify_handshake_error(&error), "internal_error");
    }
}
