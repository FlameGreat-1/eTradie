use crate::{
    cert_loader::CertificateLoader,
    config::{build_server_config, TlsConfig},
    handshake::{HandshakeManager, HasTlsVersion},
    sni::{SniHandler, SniInfo, TlsStream},
};
use edge_ingress_common::{types::TlsVersion, Result};
use std::sync::Arc;
use tokio::io::{AsyncRead, AsyncWrite};
use tracing::info;

pub struct TlsAcceptor {
    sni_handler: Arc<SniHandler>,
    handshake_manager: HandshakeManager,
}

impl TlsAcceptor {
    pub fn new(config: TlsConfig) -> Result<Self> {
        config.validate()?;

        let cert_loader = CertificateLoader::new(config.clone())?;
        let cert_resolver = cert_loader.load_all_certificates()?;

        // mTLS is mandatory; client_auth is a required field on TlsConfig.
        let server_config = build_server_config(
            cert_resolver,
            &config.min_tls_version,
            &config.client_auth,
        )?;

        let sni_handler = Arc::new(SniHandler::new(server_config));
        let handshake_manager = HandshakeManager::new(&config);

        info!(
            min_tls_version = %config.min_tls_version,
            certificate_count = config.certificates.len(),
            "TLS acceptor initialized"
        );

        Ok(Self {
            sni_handler,
            handshake_manager,
        })
    }

    pub async fn accept<S>(&self, stream: S) -> Result<AcceptedConnection<S>>
    where
        S: AsyncRead + AsyncWrite + Unpin + Send + 'static,
    {
        let sni_handler = Arc::clone(&self.sni_handler);

        let (tls_stream, tls_version, handshake_duration) = self
            .handshake_manager
            .perform_handshake(stream, move |s| async move {
                let (stream, sni_info) = sni_handler.accept(s).await?;
                Ok(TlsStreamWithInfo { stream, sni_info })
            })
            .await?;

        Ok(AcceptedConnection {
            stream: tls_stream.stream,
            sni_info: tls_stream.sni_info,
            tls_version,
            handshake_duration,
        })
    }
}

struct TlsStreamWithInfo<S>
where
    S: AsyncRead + AsyncWrite + Unpin,
{
    stream: TlsStream<S>,
    sni_info: SniInfo,
}

impl<S> HasTlsVersion for TlsStreamWithInfo<S>
where
    S: AsyncRead + AsyncWrite + Unpin,
{
    fn get_tls_version(&self) -> Result<TlsVersion> {
        Ok(self.sni_info.tls_version())
    }
}

pub struct AcceptedConnection<S>
where
    S: AsyncRead + AsyncWrite + Unpin,
{
    pub stream: TlsStream<S>,
    pub sni_info: SniInfo,
    pub tls_version: TlsVersion,
    pub handshake_duration: std::time::Duration,
}

impl<S> AcceptedConnection<S>
where
    S: AsyncRead + AsyncWrite + Unpin,
{
    pub fn hostname(&self) -> Option<&str> {
        self.sni_info.hostname()
    }

    pub fn tls_version(&self) -> TlsVersion {
        self.tls_version
    }

    pub fn cipher_suite(&self) -> Option<&str> {
        self.sni_info.cipher_suite()
    }

    pub fn handshake_duration(&self) -> std::time::Duration {
        self.handshake_duration
    }

    pub fn into_stream(self) -> TlsStream<S> {
        self.stream
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn test_tls_config_validation() {
        let mut config = TlsConfig::default();
        config.certificates.push(crate::config::CertificateConfig {
            hostname: "example.com".to_string(),
            cert_path: PathBuf::from("/path/to/cert.pem"),
            key_path: PathBuf::from("/path/to/key.pem"),
            is_default: true,
        });
        config.client_auth.ca_path = PathBuf::from("/etc/edge-ingress/cloudflare/origin-pull-ca.pem");

        assert!(config.validate().is_ok());
    }
}
