use crate::config::RateLimitConfig;
use crate::storage::RateLimitStorage;
use etradie_envoy_common::{FilterDecision, MetricsCollector, SecurityEvent, SecurityEventCode};
use std::net::IpAddr;
use std::str::FromStr;

pub struct RateLimiter {
    storage: RateLimitStorage,
    config: RateLimitConfig,
    metrics: MetricsCollector,
}

impl RateLimiter {
    pub fn new(config: RateLimitConfig) -> Result<Self, String> {
        config.validate()?;

        Ok(Self {
            storage: RateLimitStorage::new(
                config.global_requests,
                config.global_refill_rate(),
                config.ip_requests,
                config.ip_refill_rate(),
            ),
            config,
            metrics: MetricsCollector::new("rate_limiter"),
        })
    }

    pub fn check_limits(&mut self, trace_id: &str, client_ip: Option<&str>) -> FilterDecision {
        let ip = client_ip.unwrap_or("unknown");

        if self.config.global_enabled {
            if let Err(_) = self.storage.check_global_limit() {
                let event = SecurityEvent::new(
                    SecurityEventCode::RateLimitGlobal,
                    trace_id.to_string(),
                    "Global rate limit exceeded".to_string(),
                );
                self.emit_token_metrics(ip);
                return FilterDecision::deny(
                    "Global rate limit exceeded".to_string(),
                    event,
                );
            }
        }

        if self.config.ip_enabled {
            if let Err(_) = self.storage.check_ip_limit(
                ip,
                self.config.ip_requests,
                self.config.ip_refill_rate(),
            ) {
                let event = SecurityEvent::new(
                    SecurityEventCode::RateLimitIp,
                    trace_id.to_string(),
                    format!("IP rate limit exceeded for {}", ip),
                );
                self.emit_token_metrics(ip);
                return FilterDecision::deny(
                    format!("IP rate limit exceeded for {}", ip),
                    event,
                );
            }
        }

        self.emit_token_metrics(ip);
        FilterDecision::allow()
    }

    fn emit_token_metrics(&self, ip: &str) {
        let global_remaining = self.storage.global_tokens_remaining();
        self.metrics.set_rate_limit_tokens_remaining("global", global_remaining);

        if let Some(ip_remaining) = self.storage.ip_tokens_remaining(ip) {
            self.metrics.set_rate_limit_tokens_remaining("ip", ip_remaining);
        }

        self.metrics.set_rate_limit_tracked_ips(self.storage.tracked_ip_count() as u64);
    }
}

pub fn extract_client_ip(headers: &[(String, String)]) -> Option<String> {
    for (key, value) in headers {
        if key.eq_ignore_ascii_case("x-forwarded-for") {
            if let Some(first_ip) = value.split(',').next() {
                let ip = first_ip.trim();
                if IpAddr::from_str(ip).is_ok() {
                    return Some(ip.to_string());
                }
            }
        }
    }

    for (key, value) in headers {
        if key.eq_ignore_ascii_case("x-real-ip") {
            let ip = value.trim();
            if IpAddr::from_str(ip).is_ok() {
                return Some(ip.to_string());
            }
        }
    }

    None
}
