use edge_ingress_common::{
    constants::{tls::*, TLS_HANDSHAKE_TIMEOUT},
    EdgeError, Result,
};
use rustls::{
    server::{ClientHello, ResolvesServerCert},
    sign::CertifiedKey,
    ServerConfig,
};
use serde::{Deserialize, Serialize};
use std::{
    collections::HashMap,
    path::PathBuf,
    sync::Arc,
    time::Duration,
};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TlsConfig {
    pub min_tls_version: String,
    pub preferred_tls_version: String,
    pub handshake_timeout: Duration,
    pub certificates: Vec<CertificateConfig>,
    pub enable_sni: bool,
    pub cert_reload_interval: Duration,
    /// Optional Cloudflare Authenticated Origin Pulls (mTLS) configuration.
    /// When None or `enabled = false`, edge-ingress accepts any TLS client
    /// (relying on Cloudflare DNS + origin firewall for upstream identity).
    /// When `enabled = true`, the rustls ServerConfig is built with a client
    /// certificate verifier that requires (or, in `optional` mode, accepts)
    /// a client cert signed by the CA bundle at `ca_path`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub client_auth: Option<ClientAuthConfig>,
}

impl Default for TlsConfig {
    fn default() -> Self {
        Self {
            min_tls_version: MIN_TLS_VERSION.to_string(),
            preferred_tls_version: PREFERRED_TLS_VERSION.to_string(),
            handshake_timeout: TLS_HANDSHAKE_TIMEOUT,
            certificates: Vec::new(),
            enable_sni: true,
            cert_reload_interval: Duration::from_secs(CERT_RELOAD_INTERVAL_SECS),
            client_auth: None,
        }
    }
}

/// Configuration for TLS client certificate authentication. Used to enforce
/// Cloudflare Authenticated Origin Pulls (AOP) so only TLS clients presenting
/// a cert signed by the configured CA bundle can terminate TLS on edge-ingress.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClientAuthConfig {
    /// Master switch. When false, this entire block is a no-op and the
    /// ServerConfig is built with `with_no_client_auth`.
    pub enabled: bool,

    /// Verification mode. One of:
    /// - "required": rustls rejects any client that does not present a
    ///   cert signed by `ca_path`.
    /// - "optional": rustls accepts both authenticated and unauthenticated
    ///   clients; used during AOP rollout before flipping to `required`.
    /// - "none": equivalent to `enabled: false`.
    #[serde(default = "ClientAuthConfig::default_mode")]
    pub mode: String,

    /// Path to a PEM-encoded CA bundle that signs valid client certs.
    /// For Cloudflare AOP this is
    /// /etc/edge-ingress/cloudflare/origin-pull-ca.pem mounted from the
    /// `cloudflare-aop-ca` Secret.
    pub ca_path: PathBuf,
}

impl ClientAuthConfig {
    fn default_mode() -> String {
        "required".to_string()
    }

    /// Whether the verifier should be built. False when the block is
    /// disabled or mode is explicitly "none".
    pub fn is_active(&self) -> bool {
        self.enabled && self.mode != "none"
    }

    /// Whether the verifier should reject unauthenticated clients.
    pub fn is_required(&self) -> bool {
        self.is_active() && self.mode == "required"
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CertificateConfig {
    pub hostname: String,
    pub cert_path: PathBuf,
    pub key_path: PathBuf,
    pub is_default: bool,
}

impl TlsConfig {
    pub fn validate(&self) -> Result<()> {
        if self.certificates.is_empty() {
            return Err(EdgeError::Configuration(
                "At least one certificate must be configured".to_string(),
            ));
        }

        let default_certs: Vec<_> = self
            .certificates
            .iter()
            .filter(|c| c.is_default)
            .collect();

        if default_certs.is_empty() {
            return Err(EdgeError::Configuration(
                "No default certificate configured".to_string(),
            ));
        }

        if default_certs.len() > 1 {
            return Err(EdgeError::Configuration(
                "Multiple default certificates configured".to_string(),
            ));
        }

        if !["1.2", "1.3"].contains(&self.min_tls_version.as_str()) {
            return Err(EdgeError::Configuration(format!(
                "Invalid min_tls_version: {}. Must be 1.2 or 1.3",
                self.min_tls_version
            )));
        }

        if !["1.2", "1.3"].contains(&self.preferred_tls_version.as_str()) {
            return Err(EdgeError::Configuration(format!(
                "Invalid preferred_tls_version: {}. Must be 1.2 or 1.3",
                self.preferred_tls_version
            )));
        }

        if self.handshake_timeout.as_secs() == 0 {
            return Err(EdgeError::Configuration(
                "handshake_timeout must be greater than 0".to_string(),
            ));
        }

        if self.handshake_timeout > Duration::from_secs(60) {
            return Err(EdgeError::Configuration(
                "handshake_timeout cannot exceed 60 seconds".to_string(),
            ));
        }

        if let Some(client_auth) = &self.client_auth {
            const VALID_MODES: &[&str] = &["required", "optional", "none"];
            if !VALID_MODES.contains(&client_auth.mode.as_str()) {
                return Err(EdgeError::Configuration(format!(
                    "Invalid client_auth.mode: {}. Must be one of: required, optional, none",
                    client_auth.mode
                )));
            }
            if client_auth.is_active() && client_auth.ca_path.as_os_str().is_empty() {
                return Err(EdgeError::Configuration(
                    "client_auth.ca_path must be set when mode is required or optional"
                        .to_string(),
                ));
            }
        }

        Ok(())
    }

    pub fn get_default_certificate(&self) -> Option<&CertificateConfig> {
        self.certificates.iter().find(|c| c.is_default)
    }

    pub fn get_certificate_for_hostname(&self, hostname: &str) -> Option<&CertificateConfig> {
        self.certificates
            .iter()
            .find(|c| c.hostname == hostname)
            .or_else(|| self.get_default_certificate())
    }
}

#[derive(Debug)]
pub struct CertResolver {
    certificates: HashMap<String, Arc<CertifiedKey>>,
    default_cert: Arc<CertifiedKey>,
}

impl CertResolver {
    pub fn new(
        certificates: HashMap<String, Arc<CertifiedKey>>,
        default_cert: Arc<CertifiedKey>,
    ) -> Self {
        Self {
            certificates,
            default_cert,
        }
    }
}

impl ResolvesServerCert for CertResolver {
    fn resolve(&self, client_hello: ClientHello) -> Option<Arc<CertifiedKey>> {
        if let Some(server_name) = client_hello.server_name() {
            if let Some(cert) = self.certificates.get(server_name) {
                return Some(Arc::clone(cert));
            }
        }
        Some(Arc::clone(&self.default_cert))
    }
}

pub fn build_server_config(
    cert_resolver: Arc<dyn ResolvesServerCert>,
    min_tls_version: &str,
    client_auth: &Option<ClientAuthConfig>,
) -> Result<Arc<ServerConfig>> {
    let builder = ServerConfig::builder();

    let mut config = match client_auth {
        Some(ca_cfg) if ca_cfg.is_active() => {
            let roots = load_client_auth_roots(&ca_cfg.ca_path)?;
            let verifier_builder =
                rustls::server::WebPkiClientVerifier::builder(Arc::new(roots));
            let verifier = if ca_cfg.is_required() {
                verifier_builder.build()
            } else {
                verifier_builder.allow_unauthenticated().build()
            }
            .map_err(|e| {
                EdgeError::Configuration(format!(
                    "Failed to build WebPkiClientVerifier: {}",
                    e
                ))
            })?;
            tracing::info!(
                mode = %ca_cfg.mode,
                ca_path = %ca_cfg.ca_path.display(),
                "client cert authentication (mTLS) enabled"
            );
            builder
                .with_client_cert_verifier(verifier)
                .with_cert_resolver(cert_resolver)
        }
        _ => {
            tracing::debug!("client cert authentication (mTLS) disabled");
            builder
                .with_no_client_auth()
                .with_cert_resolver(cert_resolver)
        }
    };

    match min_tls_version {
        "1.2" => {
            config.alpn_protocols = vec![b"h2".to_vec(), b"http/1.1".to_vec()];
        }
        "1.3" => {
            config.alpn_protocols = vec![b"h2".to_vec()];
        }
        _ => {
            return Err(EdgeError::Configuration(format!(
                "Unsupported TLS version: {}",
                min_tls_version
            )));
        }
    }

    Ok(Arc::new(config))
}

/// Load a PEM-encoded CA bundle into a RootCertStore for use as the
/// trust anchor in WebPkiClientVerifier. Used to enforce Cloudflare AOP
/// at the rustls layer.
fn load_client_auth_roots(path: &std::path::Path) -> Result<rustls::RootCertStore> {
    let file = std::fs::File::open(path).map_err(|e| {
        EdgeError::CertificateLoadFailed(format!(
            "Cannot open client_auth.ca_path {}: {}",
            path.display(),
            e
        ))
    })?;
    let mut reader = std::io::BufReader::new(file);
    let certs = rustls_pemfile::certs(&mut reader)
        .collect::<std::result::Result<Vec<_>, _>>()
        .map_err(|e| {
            EdgeError::CertificateLoadFailed(format!(
                "Invalid PEM in client_auth.ca_path {}: {}",
                path.display(),
                e
            ))
        })?;
    if certs.is_empty() {
        return Err(EdgeError::CertificateLoadFailed(format!(
            "client_auth.ca_path {} contained no certificates",
            path.display()
        )));
    }
    let mut roots = rustls::RootCertStore::empty();
    for cert in certs {
        roots.add(cert).map_err(|e| {
            EdgeError::CertificateLoadFailed(format!(
                "Failed to add CA cert to root store: {}",
                e
            ))
        })?;
    }
    Ok(roots)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_tls_config() {
        let config = TlsConfig::default();
        assert_eq!(config.min_tls_version, "1.2");
        assert_eq!(config.preferred_tls_version, "1.3");
        assert!(config.enable_sni);
    }

    #[test]
    fn test_validate_empty_certificates() {
        let config = TlsConfig::default();
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_validate_no_default_certificate() {
        let mut config = TlsConfig::default();
        config.certificates.push(CertificateConfig {
            hostname: "example.com".to_string(),
            cert_path: PathBuf::from("/path/to/cert.pem"),
            key_path: PathBuf::from("/path/to/key.pem"),
            is_default: false,
        });
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_validate_multiple_default_certificates() {
        let mut config = TlsConfig::default();
        config.certificates.push(CertificateConfig {
            hostname: "example.com".to_string(),
            cert_path: PathBuf::from("/path/to/cert1.pem"),
            key_path: PathBuf::from("/path/to/key1.pem"),
            is_default: true,
        });
        config.certificates.push(CertificateConfig {
            hostname: "example.org".to_string(),
            cert_path: PathBuf::from("/path/to/cert2.pem"),
            key_path: PathBuf::from("/path/to/key2.pem"),
            is_default: true,
        });
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_validate_invalid_tls_version() {
        let mut config = TlsConfig::default();
        config.min_tls_version = "1.1".to_string();
        config.certificates.push(CertificateConfig {
            hostname: "example.com".to_string(),
            cert_path: PathBuf::from("/path/to/cert.pem"),
            key_path: PathBuf::from("/path/to/key.pem"),
            is_default: true,
        });
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_validate_zero_handshake_timeout() {
        let mut config = TlsConfig::default();
        config.handshake_timeout = Duration::from_secs(0);
        config.certificates.push(CertificateConfig {
            hostname: "example.com".to_string(),
            cert_path: PathBuf::from("/path/to/cert.pem"),
            key_path: PathBuf::from("/path/to/key.pem"),
            is_default: true,
        });
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_validate_excessive_handshake_timeout() {
        let mut config = TlsConfig::default();
        config.handshake_timeout = Duration::from_secs(120);
        config.certificates.push(CertificateConfig {
            hostname: "example.com".to_string(),
            cert_path: PathBuf::from("/path/to/cert.pem"),
            key_path: PathBuf::from("/path/to/key.pem"),
            is_default: true,
        });
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_get_default_certificate() {
        let mut config = TlsConfig::default();
        config.certificates.push(CertificateConfig {
            hostname: "example.com".to_string(),
            cert_path: PathBuf::from("/path/to/cert.pem"),
            key_path: PathBuf::from("/path/to/key.pem"),
            is_default: true,
        });
        let default = config.get_default_certificate();
        assert!(default.is_some());
        assert_eq!(default.unwrap().hostname, "example.com");
    }

    #[test]
    fn test_get_certificate_for_hostname() {
        let mut config = TlsConfig::default();
        config.certificates.push(CertificateConfig {
            hostname: "example.com".to_string(),
            cert_path: PathBuf::from("/path/to/cert1.pem"),
            key_path: PathBuf::from("/path/to/key1.pem"),
            is_default: false,
        });
        config.certificates.push(CertificateConfig {
            hostname: "default.com".to_string(),
            cert_path: PathBuf::from("/path/to/cert2.pem"),
            key_path: PathBuf::from("/path/to/key2.pem"),
            is_default: true,
        });

        let cert = config.get_certificate_for_hostname("example.com");
        assert!(cert.is_some());
        assert_eq!(cert.unwrap().hostname, "example.com");

        let cert = config.get_certificate_for_hostname("unknown.com");
        assert!(cert.is_some());
        assert_eq!(cert.unwrap().hostname, "default.com");
    }
}
