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
        }
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
) -> Result<Arc<ServerConfig>> {
    let mut config = ServerConfig::builder()
        .with_no_client_auth()
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
