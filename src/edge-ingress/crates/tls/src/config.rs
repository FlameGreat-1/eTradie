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
    /// Cloudflare Authenticated Origin Pulls (mTLS) configuration.
    /// edge-ingress always requires a client certificate signed by the
    /// CA bundle at `client_auth.ca_path` on every TLS handshake. There
    /// is no opt-out: a deployment without a valid CA bundle fails
    /// startup at config validation time.
    pub client_auth: ClientAuthConfig,
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
            // Default has an empty ca_path on purpose: any production-bound
            // config that forgets to set it fails validate() with a clear
            // error rather than silently disabling mTLS.
            client_auth: ClientAuthConfig {
                ca_path: PathBuf::new(),
            },
        }
    }
}

/// TLS client certificate authentication. The presence of this struct
/// in TlsConfig is mandatory; the only knob is which CA bundle signs
/// valid client certs.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClientAuthConfig {
    /// Path to a PEM-encoded CA bundle that signs valid client certs.
    /// For Cloudflare AOP this is
    /// /etc/edge-ingress/cloudflare/origin-pull-ca.pem mounted from the
    /// `cloudflare-aop-ca` Secret.
    pub ca_path: PathBuf,
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

        if self.client_auth.ca_path.as_os_str().is_empty() {
            return Err(EdgeError::Configuration(
                "tls.client_auth.ca_path must be set; mTLS is mandatory"
                    .to_string(),
            ));
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
    client_auth: &ClientAuthConfig,
) -> Result<Arc<ServerConfig>> {
    let roots = load_client_auth_roots(&client_auth.ca_path)?;
    let verifier = rustls::server::WebPkiClientVerifier::builder(Arc::new(roots))
        .build()
        .map_err(|e| {
            EdgeError::Configuration(format!(
                "Failed to build WebPkiClientVerifier from {}: {}",
                client_auth.ca_path.display(),
                e
            ))
        })?;

    tracing::info!(
        ca_path = %client_auth.ca_path.display(),
        "client cert authentication (mTLS) enforced"
    );

    let mut config = ServerConfig::builder()
        .with_client_cert_verifier(verifier)
        .with_cert_resolver(cert_resolver);

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

    /// Build a TlsConfig that satisfies validate(): one default cert and
    /// a non-empty ca_path. Used by every test that expects validate() to
    /// succeed.
    fn tls_config_with_aop() -> TlsConfig {
        let mut cfg = TlsConfig::default();
        cfg.certificates.push(CertificateConfig {
            hostname: "example.com".to_string(),
            cert_path: PathBuf::from("/path/to/cert.pem"),
            key_path: PathBuf::from("/path/to/key.pem"),
            is_default: true,
        });
        cfg.client_auth.ca_path = PathBuf::from("/etc/edge-ingress/cloudflare/origin-pull-ca.pem");
        cfg
    }

    #[test]
    fn test_default_tls_config_is_invalid() {
        // Default must be invalid: no certs and no ca_path.
        let config = TlsConfig::default();
        assert_eq!(config.min_tls_version, "1.2");
        assert_eq!(config.preferred_tls_version, "1.3");
        assert!(config.enable_sni);
        assert!(config.client_auth.ca_path.as_os_str().is_empty());
        assert!(config.validate().is_err());
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
        config.client_auth.ca_path = PathBuf::from("/some/ca.pem");
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
        config.client_auth.ca_path = PathBuf::from("/some/ca.pem");
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_validate_invalid_tls_version() {
        let mut config = tls_config_with_aop();
        config.min_tls_version = "1.1".to_string();
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_validate_zero_handshake_timeout() {
        let mut config = tls_config_with_aop();
        config.handshake_timeout = Duration::from_secs(0);
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_validate_excessive_handshake_timeout() {
        let mut config = tls_config_with_aop();
        config.handshake_timeout = Duration::from_secs(120);
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_validate_missing_ca_path() {
        // Has certs but no ca_path -> mTLS missing -> reject.
        let mut config = TlsConfig::default();
        config.certificates.push(CertificateConfig {
            hostname: "example.com".to_string(),
            cert_path: PathBuf::from("/path/to/cert.pem"),
            key_path: PathBuf::from("/path/to/key.pem"),
            is_default: true,
        });
        // ca_path is intentionally left empty by Default.
        let err = config.validate().unwrap_err();
        assert!(
            format!("{}", err).contains("client_auth.ca_path"),
            "expected ca_path error, got: {}",
            err
        );
    }

    #[test]
    fn test_validate_complete_config_passes() {
        let config = tls_config_with_aop();
        assert!(config.validate().is_ok(), "full AOP config should validate");
    }

    #[test]
    fn test_get_default_certificate() {
        let config = tls_config_with_aop();
        let default = config.get_default_certificate();
        assert!(default.is_some());
        assert_eq!(default.unwrap().hostname, "example.com");
    }

    #[test]
    fn test_get_certificate_for_hostname() {
        let mut config = tls_config_with_aop();
        config.certificates.push(CertificateConfig {
            hostname: "other.com".to_string(),
            cert_path: PathBuf::from("/path/to/cert2.pem"),
            key_path: PathBuf::from("/path/to/key2.pem"),
            is_default: false,
        });
        let cert = config.get_certificate_for_hostname("other.com");
        assert!(cert.is_some());
        assert_eq!(cert.unwrap().hostname, "other.com");

        // Falls back to the default for an unknown hostname.
        let cert = config.get_certificate_for_hostname("unknown.com");
        assert!(cert.is_some());
        assert_eq!(cert.unwrap().hostname, "example.com");
    }
}
