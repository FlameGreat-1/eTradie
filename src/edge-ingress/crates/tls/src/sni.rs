use edge_ingress_common::{types::TlsVersion, EdgeError, Result};
use rustls::ServerConnection;
use std::sync::Arc;
use tokio::io::{AsyncRead, AsyncWrite};
use tokio_rustls::TlsAcceptor;
use tracing::debug;

pub struct SniHandler {
    acceptor: TlsAcceptor,
}

impl SniHandler {
    pub fn new(server_config: Arc<rustls::ServerConfig>) -> Self {
        Self {
            acceptor: TlsAcceptor::from(server_config),
        }
    }

    pub async fn accept<S>(&self, stream: S) -> Result<(TlsStream<S>, SniInfo)>
    where
        S: AsyncRead + AsyncWrite + Unpin,
    {
        let tls_stream = self
            .acceptor
            .accept(stream)
            .await
            .map_err(|e| EdgeError::Tls(format!("TLS accept failed: {}", e)))?;

        let sni_info = self.extract_sni_info(&tls_stream)?;

        Ok((tls_stream, sni_info))
    }

    fn extract_sni_info<S>(&self, stream: &tokio_rustls::server::TlsStream<S>) -> Result<SniInfo>
    where
        S: AsyncRead + AsyncWrite + Unpin,
    {
        let (_, server_conn) = stream.get_ref();
        
        let sni_hostname = server_conn
            .server_name()
            .map(|s| s.to_string());

        let tls_version = self.extract_tls_version(server_conn)?;

        let cipher_suite = server_conn
            .negotiated_cipher_suite()
            .map(|cs| cs.suite().as_str().unwrap_or("unknown").to_string());

        debug!(
            sni_hostname = ?sni_hostname,
            tls_version = %tls_version,
            cipher_suite = ?cipher_suite,
            "SNI information extracted"
        );

        Ok(SniInfo {
            hostname: sni_hostname,
            tls_version,
            cipher_suite,
        })
    }

    fn extract_tls_version(&self, conn: &ServerConnection) -> Result<TlsVersion> {
        let protocol_version = conn
            .protocol_version()
            .ok_or_else(|| EdgeError::Tls("No TLS version negotiated".to_string()))?;

        match protocol_version {
            rustls::ProtocolVersion::TLSv1_2 => Ok(TlsVersion::Tls12),
            rustls::ProtocolVersion::TLSv1_3 => Ok(TlsVersion::Tls13),
            _ => Err(EdgeError::Tls(format!(
                "Unsupported TLS version: {:?}",
                protocol_version
            ))),
        }
    }
}

pub type TlsStream<S> = tokio_rustls::server::TlsStream<S>;

#[derive(Debug, Clone)]
pub struct SniInfo {
    pub hostname: Option<String>,
    pub tls_version: TlsVersion,
    pub cipher_suite: Option<String>,
}

impl SniInfo {
    pub fn hostname(&self) -> Option<&str> {
        self.hostname.as_deref()
    }

    pub fn tls_version(&self) -> TlsVersion {
        self.tls_version
    }

    pub fn cipher_suite(&self) -> Option<&str> {
        self.cipher_suite.as_deref()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sni_info_accessors() {
        let info = SniInfo {
            hostname: Some("example.com".to_string()),
            tls_version: TlsVersion::Tls13,
            cipher_suite: Some("TLS_AES_256_GCM_SHA384".to_string()),
        };

        assert_eq!(info.hostname(), Some("example.com"));
        assert_eq!(info.tls_version(), TlsVersion::Tls13);
        assert_eq!(info.cipher_suite(), Some("TLS_AES_256_GCM_SHA384"));
    }

    #[test]
    fn test_sni_info_no_hostname() {
        let info = SniInfo {
            hostname: None,
            tls_version: TlsVersion::Tls12,
            cipher_suite: None,
        };

        assert_eq!(info.hostname(), None);
        assert_eq!(info.tls_version(), TlsVersion::Tls12);
        assert_eq!(info.cipher_suite(), None);
    }
}
