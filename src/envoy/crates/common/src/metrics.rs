use crate::constants::{METRIC_PREFIX, SERVICE_VERSION};
use crate::types::SecurityEventCode;
use proxy_wasm::hostcalls;
use proxy_wasm::types::MetricType;
use std::collections::HashMap;

static mut METRIC_CACHE: Option<HashMap<String, u32>> = None;

fn get_metric_cache() -> &'static mut HashMap<String, u32> {
    unsafe {
        if METRIC_CACHE.is_none() {
            METRIC_CACHE = Some(HashMap::new());
        }
        METRIC_CACHE.as_mut().unwrap()
    }
}

fn get_or_define_metric(name: &str, metric_type: MetricType) -> Option<u32> {
    let cache = get_metric_cache();

    if let Some(&metric_id) = cache.get(name) {
        return Some(metric_id);
    }

    match hostcalls::define_metric(metric_type, name) {
        Ok(metric_id) => {
            cache.insert(name.to_string(), metric_id);
            Some(metric_id)
        }
        Err(_) => None,
    }
}

pub struct MetricsCollector {
    prefix: String,
}

impl MetricsCollector {
    pub fn new(component: &str) -> Self {
        Self {
            prefix: format!("{}_{}", METRIC_PREFIX, component),
        }
    }

    pub fn increment_counter(&self, name: &str) {
        self.increment_counter_by(name, 1);
    }

    pub fn increment_counter_by(&self, name: &str, value: u64) {
        let metric_name = format!("{}_{}", self.prefix, name);
        if let Some(metric_id) = get_or_define_metric(&metric_name, MetricType::Counter) {
            let _ = hostcalls::increment_metric(metric_id, value as i64);
        }
    }

    pub fn record_histogram(&self, name: &str, value: u64) {
        let metric_name = format!("{}_{}", self.prefix, name);
        if let Some(metric_id) = get_or_define_metric(&metric_name, MetricType::Histogram) {
            let _ = hostcalls::record_metric(metric_id, value);
        }
    }

    pub fn set_gauge(&self, name: &str, value: u64) {
        let metric_name = format!("{}_{}", self.prefix, name);
        if let Some(metric_id) = get_or_define_metric(&metric_name, MetricType::Gauge) {
            let _ = hostcalls::record_metric(metric_id, value);
        }
    }

    pub fn record_request(&self, status: u32, duration_ms: u64) {
        self.increment_counter("requests_total");

        if status >= 400 && status < 500 {
            self.increment_counter("requests_4xx");
        } else if status >= 500 {
            self.increment_counter("requests_5xx");
        } else if status >= 200 && status < 300 {
            self.increment_counter("requests_2xx");
        }

        self.record_histogram("request_duration_ms", duration_ms);
    }

    pub fn record_blocked_request(&self, reason: &str) {
        self.increment_counter("requests_blocked");
        let metric_name = format!("blocked_{}", sanitize_metric_name(reason));
        self.increment_counter(&metric_name);
    }

    pub fn record_security_event(&self, event_code: SecurityEventCode) {
        self.increment_counter("security_events");
        let metric_name = format!("security_{}", event_code.as_str());
        self.increment_counter(&metric_name);
    }

    pub fn record_rate_limit(&self, limit_type: &str) {
        self.increment_counter("rate_limits");
        let metric_name = format!("rate_limit_{}", sanitize_metric_name(limit_type));
        self.increment_counter(&metric_name);
    }

    pub fn record_circuit_breaker_state(&self, open: bool) {
        let value = if open { 1 } else { 0 };
        self.set_gauge("circuit_breaker_open", value);
    }

    pub fn record_latency_budget_exceeded(&self) {
        self.increment_counter("latency_budget_exceeded");
    }

    pub fn record_request_body_size(&self, size_bytes: u64) {
        self.record_histogram("request_body_size_bytes", size_bytes);
    }

    pub fn set_rate_limit_tokens_remaining(&self, limit_type: &str, tokens: u64) {
        let metric_name = format!("rate_limit_tokens_remaining_{}", sanitize_metric_name(limit_type));
        self.set_gauge(&metric_name, tokens);
    }

    pub fn set_rate_limit_tracked_ips(&self, count: u64) {
        self.set_gauge("rate_limit_tracked_ips", count);
    }
}

fn sanitize_metric_name(name: &str) -> String {
    name.chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || c == '_' {
                c.to_ascii_lowercase()
            } else {
                '_'
            }
        })
        .collect()
}

pub fn record_filter_execution(filter_name: &str, duration_ms: u64, allowed: bool) {
    let collector = MetricsCollector::new("filter");

    let metric_name = format!("{}_duration_ms", sanitize_metric_name(filter_name));
    collector.record_histogram(&metric_name, duration_ms);

    if allowed {
        let metric_name = format!("{}_passed", sanitize_metric_name(filter_name));
        collector.increment_counter(&metric_name);
    } else {
        let metric_name = format!("{}_blocked", sanitize_metric_name(filter_name));
        collector.increment_counter(&metric_name);
    }
}

pub fn init_service_info(environment: &str) {
    let info_metric_name = format!("{}_info", METRIC_PREFIX);
    if let Some(metric_id) = get_or_define_metric(&info_metric_name, MetricType::Gauge) {
        let _ = hostcalls::record_metric(metric_id, 1);
    }

    let version_metric_name = format!("{}_version_info", METRIC_PREFIX);
    if let Some(metric_id) = get_or_define_metric(&version_metric_name, MetricType::Gauge) {
        let _ = hostcalls::record_metric(metric_id, 1);
    }
}
