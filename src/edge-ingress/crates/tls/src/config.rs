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
            // error rather than silently disabling mTLS. `required: true`
            // matches the chart base default and the direct-origin AOP
            // design; tunnel deployments override both in their overlay.
            client_auth: ClientAuthConfig {
                ca_path: PathBuf::new(),
                required: true,
            },
        }
    }
}

/// TLS client certificate authentication.
///
/// Two modes, selected by `required`:
///
/// * `required: true`  (chart base default): every TLS handshake MUST
///   present a client cert signed by the CA bundle at `ca_path`. Fits
///   direct-internet deployments where Cloudflare's edge dials the
///   origin and presents its AOP client cert (the canonical Authenticated
///   Origin Pulls posture).
///
/// * `required: false`: the CA bundle is loaded and any presented client
///   cert is verified against it, but handshakes that do NOT present a
///   client cert are also accepted. Fits Cloudflare Tunnel deployments
///   where cloudflared cannot present an AOP client cert (no such field
///   exists in its originRequest schema). The trust boundary in tunnel
///   mode is the tunnel JWT + ufw + downstream Linkerd mesh.
///
/// In both modes the bundle at `ca_path` must be a parseable PEM with
/// at least one cert; an empty / missing / malformed `ca_path` is a
/// startup failure when `required` is true, and is permitted (with the
/// verifier configured for allow-unauthenticated) when `required` is
/// false but a non-empty path is configured. When `required` is false
/// AND `ca_path` is empty, no client-cert verifier is wired at all and
/// every handshake is accepted at the rustls layer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClientAuthConfig {
    /// Path to a PEM-encoded CA bundle that signs valid client certs.
    /// For Cloudflare AOP this is
    /// /etc/edge-ingress/cloudflare/origin-pull-ca.pem mounted from the
    /// `cloudflare-aop-ca` Secret.
    pub ca_path: PathBuf,

    /// When true, every TLS handshake must present a valid client cert
    /// or it fails at ServerHello. When false, client certs are
    /// optional. Default is `true`: any config that omits the field
    /// (legacy configs, missing chart values) gets the strict posture.
    #[serde(default = "default_client_auth_required")]
    pub required: bool,
}

/// Serde default for `ClientAuthConfig::required`. Strict-by-default so
/// a config that omits the field (older configs, mistakenly-deleted
/// chart value) does not silently disable mTLS.
fn default_client_auth_required() -> bool {
    true
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

        // ca_path is required only when the deployment enforces mTLS.
        // For tunnel deployments (client_auth.required = false), an
        // empty ca_path is permitted: no client-cert verifier is wired
        // at the rustls layer (see build_server_config below).
        if self.client_auth.required && self.client_auth.ca_path.as_os_str().is_empty() {
            return Err(EdgeError::Configuration(
                "tls.client_auth.ca_path must be set when tls.client_auth.required = true"
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
    // Three rustls server configurations are possible:
    //
    //   required=true, ca_path set:    .with_client_cert_verifier(builder.build())
    //                                  -> handshake fails without a valid client cert.
    //   required=false, ca_path set:   .with_client_cert_verifier(builder.allow_unauthenticated().build())
    //                                  -> handshake accepts no cert OR a cert that
    //                                     verifies against ca_path. Invalid cert still fails.
    //   required=false, ca_path empty: .with_no_client_auth()
    //                                  -> handshake accepts every client; no
    //                                     verifier is wired at all.
    //
    // The required=true + ca_path empty case is rejected by validate()
    // before this function is reached.

    let mut config_builder = ServerConfig::builder();

    let mut config = if client_auth.ca_path.as_os_str().is_empty() {
        // required=false implied (required=true would have failed
        // validate). No verifier; every client accepted.
        tracing::warn!(
            "client cert authentication DISABLED (tls.client_auth.ca_path empty); \
             every TLS handshake will be accepted. Use only for tunnel topologies \
             where the trust boundary is upstream (e.g. Cloudflare Tunnel JWT)."
        );
        config_builder
            .with_no_client_auth()
            .with_cert_resolver(cert_resolver)
    } else {
        let roots = load_client_auth_roots(&client_auth.ca_path)?;
        let verifier_builder = rustls::server::WebPkiClientVerifier::builder(Arc::new(roots));

        let verifier = if client_auth.required {
            verifier_builder.build().map_err(|e| {
                EdgeError::Configuration(format!(
                    "Failed to build WebPkiClientVerifier from {}: {}",
                    client_auth.ca_path.display(),
                    e
                ))
            })?
        } else {
            verifier_builder.allow_unauthenticated().build().map_err(|e| {
                EdgeError::Configuration(format!(
                    "Failed to build WebPkiClientVerifier (allow_unauthenticated) from {}: {}",
                    client_auth.ca_path.display(),
                    e
                ))
            })?
        };

        if client_auth.required {
            tracing::info!(
                ca_path = %client_auth.ca_path.display(),
                "client cert authentication (mTLS) ENFORCED"
            );
        } else {
            tracing::info!(
                ca_path = %client_auth.ca_path.display(),
                "client cert authentication (mTLS) OPTIONAL; accepts handshakes \
                 without a client cert. Used in Cloudflare Tunnel topology."
            );
        }

        config_builder
            .with_client_cert_verifier(verifier)
            .with_cert_resolver(cert_resolver)
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

    /// Build a TlsConfig that satisfies validate(): one default cert and
    /// a non-empty ca_path. Used by every test that expects validate() to
    /// succeed. Default `required` stays true (strict mTLS).
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

    /// Build a TlsConfig for the tunnel-mode case: required=false. Both
    /// the empty-ca_path variant and the non-empty-ca_path variant must
    /// validate cleanly.
    fn tls_config_tunnel_mode(with_ca_path: bool) -> TlsConfig {
        let mut cfg = TlsConfig::default();
        cfg.certificates.push(CertificateConfig {
            hostname: "example.com".to_string(),
            cert_path: PathBuf::from("/path/to/cert.pem"),
            key_path: PathBuf::from("/path/to/key.pem"),
            is_default: true,
        });
        cfg.client_auth.required = false;
        if with_ca_path {
            cfg.client_auth.ca_path =
                PathBuf::from("/etc/edge-ingress/cloudflare/origin-pull-ca.pem");
        }
        cfg
    }

    #[test]
    fn test_default_tls_config_is_invalid() {
        // Default must be invalid: no certs and no ca_path. Default
        // `required` is true (strict-by-default), so the empty ca_path
        // is a startup failure.
        let config = TlsConfig::default();
        assert_eq!(config.min_tls_version, "1.2");
        assert_eq!(config.preferred_tls_version, "1.3");
        assert!(config.enable_sni);
        assert!(config.client_auth.ca_path.as_os_str().is_empty());
        assert!(config.client_auth.required, "required must default to true");
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_validate_tunnel_mode_with_ca_path_ok() {
        // required=false + non-empty ca_path: optional mTLS. Should pass
        // validate().
        let cfg = tls_config_tunnel_mode(true);
        assert!(cfg.validate().is_ok(),
            "tunnel-mode config with ca_path should validate");
    }

    #[test]
    fn test_validate_tunnel_mode_without_ca_path_ok() {
        // required=false + empty ca_path: no client-cert verifier at all.
        // Should pass validate() because the rustls path uses
        // .with_no_client_auth() for this case.
        let cfg = tls_config_tunnel_mode(false);
        assert!(cfg.validate().is_ok(),
            "tunnel-mode config without ca_path should validate");
    }

    #[test]
    fn test_validate_required_true_empty_ca_path_rejects() {
        // required=true + empty ca_path: explicit operator error.
        let mut cfg = TlsConfig::default();
        cfg.certificates.push(CertificateConfig {
            hostname: "example.com".to_string(),
            cert_path: PathBuf::from("/path/to/cert.pem"),
            key_path: PathBuf::from("/path/to/key.pem"),
            is_default: true,
        });
        // ca_path stays empty; required stays true (default).
        let err = cfg.validate().unwrap_err();
        let msg = format!("{}", err);
        assert!(
            msg.contains("ca_path") && msg.contains("required = true"),
            "expected ca_path-with-required-true error, got: {}",
            msg
        );
    }

    #[test]
    fn test_client_auth_required_default_is_true_when_field_missing() {
        // Deserialise a TlsConfig YAML that OMITS the required field.
        // Serde must apply default_client_auth_required() = true.
        let yaml = r#"
min_tls_version: "1.2"
preferred_tls_version: "1.3"
handshake_timeout:
  secs: 10
  nanos: 0
enable_sni: true
cert_reload_interval:
  secs: 3600
  nanos: 0
certificates:
  - hostname: example.com
    cert_path: /path/to/cert.pem
    key_path: /path/to/key.pem
    is_default: true
client_auth:
  ca_path: /etc/edge-ingress/cloudflare/origin-pull-ca.pem
"#;
        let cfg: TlsConfig = serde_yaml::from_str(yaml).expect("valid YAML");
        assert!(
            cfg.client_auth.required,
            "omitted `required` must deserialize to true (strict-by-default)"
        );
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
