use crate::config::{CertResolver, CertificateConfig, TlsConfig};
use edge_ingress_common::{
    metrics::record_certificate_expiry,
    EdgeError, Result,
};
use rustls::{pki_types::PrivateKeyDer, sign::CertifiedKey};
use rustls_pemfile::{certs, private_key};
use std::{
    collections::HashMap,
    fs::File,
    io::BufReader,
    path::Path,
    sync::Arc,
};
use tracing::{info, warn};
use x509_parser::prelude::*;

const CERT_EXPIRY_WARNING_DAYS: i64 = 30;

pub struct CertificateLoader {
    config: TlsConfig,
}

impl CertificateLoader {
    pub fn new(config: TlsConfig) -> Result<Self> {
        config.validate()?;
        Ok(Self { config })
    }

    pub fn load_all_certificates(&self) -> Result<Arc<CertResolver>> {
        let mut certificates = HashMap::new();
        let mut default_cert = None;

        for cert_config in &self.config.certificates {
            let certified_key = self.load_certificate(cert_config)?;

            if cert_config.is_default {
                if default_cert.is_some() {
                    return Err(EdgeError::CertificateLoadFailed(
                        "Multiple default certificates configured".to_string()
                    ));
                }
                default_cert = Some(Arc::new(certified_key.clone()));
            }

            certificates.insert(cert_config.hostname.clone(), Arc::new(certified_key));

            info!(
                hostname = %cert_config.hostname,
                is_default = cert_config.is_default,
                "certificate loaded successfully"
            );
        }

        let default = default_cert.ok_or_else(|| {
            EdgeError::CertificateLoadFailed("No default certificate configured".to_string())
        })?;

        Ok(Arc::new(CertResolver::new(certificates, default)))
    }

    fn load_certificate(&self, cert_config: &CertificateConfig) -> Result<CertifiedKey> {
        let cert_chain = self.load_cert_chain(&cert_config.cert_path)?;
        let private_key = self.load_private_key(&cert_config.key_path)?;

        self.validate_certificate_chain(&cert_chain, &cert_config.hostname)?;

        let signing_key = rustls::crypto::ring::sign::any_supported_type(&private_key)
            .map_err(|e| {
                EdgeError::CertificateLoadFailed(format!(
                    "Invalid private key for {}: {}",
                    cert_config.hostname, e
                ))
            })?;

        Ok(CertifiedKey::new(cert_chain, signing_key))
    }

    fn load_cert_chain(&self, path: &Path) -> Result<Vec<rustls::pki_types::CertificateDer<'static>>> {
        let file = File::open(path).map_err(|e| {
            EdgeError::CertificateLoadFailed(format!(
                "Cannot open certificate file {}: {}",
                path.display(),
                e
            ))
        })?;

        let mut reader = BufReader::new(file);
        let cert_chain = certs(&mut reader)
            .collect::<std::result::Result<Vec<_>, _>>()
            .map_err(|e| {
                EdgeError::CertificateLoadFailed(format!(
                    "Invalid certificate format in {}: {}",
                    path.display(),
                    e
                ))
            })?;

        if cert_chain.is_empty() {
            return Err(EdgeError::CertificateLoadFailed(format!(
                "No valid certificates found in {}",
                path.display()
            )));
        }

        Ok(cert_chain)
    }

    fn load_private_key(&self, path: &Path) -> Result<PrivateKeyDer<'static>> {
        let file = File::open(path).map_err(|e| {
            EdgeError::CertificateLoadFailed(format!(
                "Cannot open private key file {}: {}",
                path.display(),
                e
            ))
        })?;

        let mut reader = BufReader::new(file);
        private_key(&mut reader)
            .map_err(|e| {
                EdgeError::CertificateLoadFailed(format!(
                    "Invalid private key format in {}: {}",
                    path.display(),
                    e
                ))
            })?
            .ok_or_else(|| {
                EdgeError::CertificateLoadFailed(format!(
                    "No valid private key found in {}",
                    path.display()
                ))
            })
    }

    fn validate_certificate_chain(
        &self,
        cert_chain: &[rustls::pki_types::CertificateDer<'static>],
        expected_hostname: &str,
    ) -> Result<()> {
        if cert_chain.is_empty() {
            return Err(EdgeError::CertificateLoadFailed(
                "Certificate chain is empty".to_string(),
            ));
        }

        let leaf_cert = &cert_chain[0];
        let (_, parsed_cert) = X509Certificate::from_der(leaf_cert.as_ref()).map_err(|e| {
            EdgeError::CertificateLoadFailed(format!("Invalid X.509 certificate: {}", e))
        })?;

        self.validate_certificate_expiry(&parsed_cert, expected_hostname)?;
        self.validate_certificate_hostname(&parsed_cert, expected_hostname)?;

        Ok(())
    }

    fn validate_certificate_expiry(&self, cert: &X509Certificate, hostname: &str) -> Result<()> {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|e| EdgeError::CertificateLoadFailed(format!("System time error: {}", e)))?
            .as_secs() as i64;

        let not_before = cert.validity().not_before.timestamp();
        let not_after = cert.validity().not_after.timestamp();

        if now < not_before {
            return Err(EdgeError::CertificateLoadFailed(format!(
                "Certificate not yet valid (valid from: {})",
                cert.validity().not_before
            )));
        }

        if now > not_after {
            return Err(EdgeError::CertificateLoadFailed(format!(
                "Certificate expired on {}",
                cert.validity().not_after
            )));
        }

        let seconds_until_expiry = not_after - now;
        let days_until_expiry = seconds_until_expiry / 86400;

        record_certificate_expiry(hostname, seconds_until_expiry as f64);

        if days_until_expiry < CERT_EXPIRY_WARNING_DAYS {
            warn!(
                hostname = hostname,
                days_remaining = days_until_expiry,
                expires_at = %cert.validity().not_after,
                "certificate expiring soon"
            );
        }

        Ok(())
    }

    fn validate_certificate_hostname(
        &self,
        cert: &X509Certificate,
        expected_hostname: &str,
    ) -> Result<()> {
        let subject = cert.subject();
        let common_name = subject
            .iter_common_name()
            .next()
            .and_then(|cn| cn.as_str().ok());

        let mut valid_hostnames = Vec::new();
        if let Some(cn) = common_name {
            valid_hostnames.push(cn.to_string());
        }

        if let Ok(Some(san_ext)) = cert.subject_alternative_name() {
            for name in &san_ext.value.general_names {
                if let GeneralName::DNSName(dns_name) = name {
                    valid_hostnames.push(dns_name.to_string());
                }
            }
        }

        let hostname_matches = valid_hostnames.iter().any(|h| {
            h == expected_hostname || self.matches_wildcard(h, expected_hostname)
        });

        if !hostname_matches {
            warn!(
                expected = expected_hostname,
                found = ?valid_hostnames,
                "certificate hostname mismatch (proceeding with caution)"
            );
        }

        Ok(())
    }

    fn matches_wildcard(&self, pattern: &str, hostname: &str) -> bool {
        if !pattern.starts_with("*.") {
            return pattern == hostname;
        }
        let domain_suffix = &pattern[2..];
        if let Some(dot_pos) = hostname.find('.') {
            let hostname_suffix = &hostname[dot_pos + 1..];
            hostname_suffix == domain_suffix
        } else {
            false
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_matches_wildcard() {
        let loader = CertificateLoader {
            config: TlsConfig::default(),
        };

        assert!(loader.matches_wildcard("*.example.com", "www.example.com"));
        assert!(loader.matches_wildcard("*.example.com", "api.example.com"));
        assert!(!loader.matches_wildcard("*.example.com", "sub.api.example.com"));
        assert!(!loader.matches_wildcard("*.example.com", "example.com"));
        assert!(!loader.matches_wildcard("example.com", "www.example.com"));
        assert!(loader.matches_wildcard("example.com", "example.com"));
    }

    #[test]
    fn test_matches_wildcard_edge_cases() {
        let loader = CertificateLoader {
            config: TlsConfig::default(),
        };

        assert!(!loader.matches_wildcard("*.example.com", ""));
        assert!(!loader.matches_wildcard("*.example.com", "com"));
        assert!(!loader.matches_wildcard("*", "anything.com"));
        assert!(loader.matches_wildcard("*.co.uk", "example.co.uk"));
    }
}
