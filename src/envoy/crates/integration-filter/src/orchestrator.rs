use crate::circuit_breaker::CircuitBreaker;
use crate::context::RequestContext;
use crate::filters::{
    HeaderFilterIntegration, RateLimitFilterIntegration, RequestFilterIntegration,
};
use etradie_envoy_common::{
    build_error_response, build_security_event_response, log_filter_decision,
    record_filter_execution, FilterDecision, Logger, MetricsCollector, LATENCY_BUDGET_MS,
};
use std::time::SystemTime;

pub struct FilterOrchestrator {
    rate_limiter: RateLimitFilterIntegration,
    header_validator: HeaderFilterIntegration,
    request_validator: RequestFilterIntegration,
    circuit_breaker: CircuitBreaker,
    logger: Logger,
    metrics: MetricsCollector,
}

impl FilterOrchestrator {
    pub fn new() -> Result<Self, String> {
        Ok(Self {
            rate_limiter: RateLimitFilterIntegration::with_defaults()?,
            header_validator: HeaderFilterIntegration::with_defaults()?,
            request_validator: RequestFilterIntegration::with_defaults(),
            circuit_breaker: CircuitBreaker::with_defaults(),
            logger: Logger::new("orchestrator"),
            metrics: MetricsCollector::new("orchestrator"),
        })
    }

    pub fn process_request(
        &mut self,
        context: &RequestContext,
        headers: &[(String, String)],
    ) -> OrchestratorResult {
        if self.is_health_check_path(context.path()) {
            self.logger.info(
                context.trace_id(),
                &format!("Health check request bypassing filters: {}", context.path()),
            );
            self.metrics.increment_counter("health_check_requests");
            return OrchestratorResult::Allowed;
        }

        let start_time = current_timestamp_ms();

        if !self
            .circuit_breaker
            .check_and_update_state(context.trace_id())
        {
            self.logger.error(
                context.trace_id(),
                "Circuit breaker is open, rejecting request",
            );
            self.metrics.increment_counter("circuit_breaker_rejections");
            return OrchestratorResult::CircuitBreakerOpen;
        }

        self.logger.info(
            context.trace_id(),
            &format!(
                "Processing request: {} {}",
                context.method(),
                context.path()
            ),
        );

        let result = self.execute_filter_chain(context, headers);

        let duration_ms = current_timestamp_ms().saturating_sub(start_time);
        self.check_latency_budget(context.trace_id(), duration_ms);
        self.record_metrics(&result, duration_ms);

        if matches!(result, OrchestratorResult::Denied(_)) {
            self.circuit_breaker.record_failure(context.trace_id());
        } else {
            self.circuit_breaker.record_success(context.trace_id());
        }

        result
    }

    fn is_health_check_path(&self, path: &str) -> bool {
        matches!(
            path,
            "/healthz" | "/health" | "/livez" | "/readyz" | "/ready" | "/alive"
        )
    }

    fn execute_filter_chain(
        &mut self,
        context: &RequestContext,
        headers: &[(String, String)],
    ) -> OrchestratorResult {
        let filter_start = current_timestamp_ms();
        let decision = self.rate_limiter.execute(context);
        let filter_duration = current_timestamp_ms().saturating_sub(filter_start);
        record_filter_execution("rate_limit", filter_duration, decision.allowed);
        log_filter_decision(
            context.trace_id(),
            "rate_limit",
            decision.allowed,
            decision.reason.as_deref(),
        );
        if !decision.allowed {
            return OrchestratorResult::Denied(decision);
        }

        let filter_start = current_timestamp_ms();
        let decision = self.header_validator.execute(context, headers);
        let filter_duration = current_timestamp_ms().saturating_sub(filter_start);
        record_filter_execution("header_validator", filter_duration, decision.allowed);
        log_filter_decision(
            context.trace_id(),
            "header_validator",
            decision.allowed,
            decision.reason.as_deref(),
        );
        if !decision.allowed {
            return OrchestratorResult::Denied(decision);
        }

        let filter_start = current_timestamp_ms();
        let decision = self.request_validator.execute(context, headers);
        let filter_duration = current_timestamp_ms().saturating_sub(filter_start);
        record_filter_execution("request_validator", filter_duration, decision.allowed);
        log_filter_decision(
            context.trace_id(),
            "request_validator",
            decision.allowed,
            decision.reason.as_deref(),
        );
        if !decision.allowed {
            return OrchestratorResult::Denied(decision);
        }

        self.logger
            .info(context.trace_id(), "Request passed all filters");
        OrchestratorResult::Allowed
    }

    fn check_latency_budget(&self, trace_id: &str, duration_ms: u64) {
        if duration_ms > LATENCY_BUDGET_MS {
            self.logger.warn(
                trace_id,
                &format!(
                    "Latency budget exceeded: {}ms (budget: {}ms)",
                    duration_ms, LATENCY_BUDGET_MS
                ),
            );
            self.metrics.record_latency_budget_exceeded();
        }
    }

    fn record_metrics(&self, result: &OrchestratorResult, duration_ms: u64) {
        self.metrics
            .record_histogram("request_duration_ms", duration_ms);
        self.metrics.increment_counter("requests_total");

        match result {
            OrchestratorResult::Allowed => {
                self.metrics.increment_counter("requests_allowed");
            }
            OrchestratorResult::Denied(_) => {
                self.metrics.increment_counter("requests_denied");
            }
            OrchestratorResult::CircuitBreakerOpen => {
                self.metrics
                    .increment_counter("requests_circuit_breaker_open");
            }
        }
    }
}

impl Default for FilterOrchestrator {
    fn default() -> Self {
        Self::new().expect("Failed to create FilterOrchestrator")
    }
}

#[derive(Debug)]
pub enum OrchestratorResult {
    Allowed,
    Denied(FilterDecision),
    CircuitBreakerOpen,
}

impl OrchestratorResult {
    pub fn is_allowed(&self) -> bool {
        matches!(self, OrchestratorResult::Allowed)
    }

    pub fn to_response(&self, trace_id: &str) -> (u32, Vec<(String, String)>, String) {
        match self {
            OrchestratorResult::Allowed => (200, vec![], String::new()),
            OrchestratorResult::Denied(decision) => {
                if let Some(event) = &decision.event {
                    let status = match event.code {
                        etradie_envoy_common::SecurityEventCode::RateLimitGlobal
                        | etradie_envoy_common::SecurityEventCode::RateLimitIp => 429,
                        etradie_envoy_common::SecurityEventCode::PayloadTooLarge => 413,
                        _ => 400,
                    };
                    build_security_event_response(event, status)
                } else {
                    let error = etradie_envoy_common::FilterError::InternalError {
                        message: decision
                            .reason
                            .clone()
                            .unwrap_or_else(|| "Request denied".to_string()),
                    };
                    build_error_response(&error, trace_id)
                }
            }
            OrchestratorResult::CircuitBreakerOpen => {
                let error = etradie_envoy_common::FilterError::CircuitBreakerOpen {
                    reason: "Service temporarily unavailable".to_string(),
                };
                build_error_response(&error, trace_id)
            }
        }
    }
}

fn current_timestamp_ms() -> u64 {
    use proxy_wasm::hostcalls;
    match hostcalls::get_current_time() {
        Ok(time) => time
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64,
        Err(_) => 0,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_orchestrator_creation() {
        let orchestrator = FilterOrchestrator::new();
        assert!(orchestrator.is_ok());
    }

    #[test]
    fn test_orchestrator_allows_valid_request() {
        let mut orchestrator = FilterOrchestrator::new().unwrap();

        let headers = vec![
            ("user-agent".to_string(), "test-agent".to_string()),
            ("content-type".to_string(), "application/json".to_string()),
            ("content-length".to_string(), "1024".to_string()),
        ];

        let context = crate::context::RequestContext::new(
            "POST".to_string(),
            "/api/v1/users".to_string(),
            &headers,
        );

        let result = orchestrator.process_request(&context, &headers);
        assert!(result.is_allowed());
    }

    #[test]
    fn test_orchestrator_denies_invalid_method() {
        let mut orchestrator = FilterOrchestrator::new().unwrap();

        let headers = vec![("user-agent".to_string(), "test-agent".to_string())];

        // TRACE is deliberately excluded from ALLOWED_HTTP_METHODS
        // (debug/proxy semantics not needed in front of the gateway).
        let context = crate::context::RequestContext::new(
            "TRACE".to_string(),
            "/api/v1/users".to_string(),
            &headers,
        );

        let result = orchestrator.process_request(&context, &headers);
        assert!(!result.is_allowed());
    }

    #[test]
    fn test_orchestrator_allows_health_check() {
        let mut orchestrator = FilterOrchestrator::new().unwrap();

        let headers = vec![];

        let context = crate::context::RequestContext::new(
            "GET".to_string(),
            "/healthz".to_string(),
            &headers,
        );

        let result = orchestrator.process_request(&context, &headers);
        assert!(result.is_allowed());
    }

    #[test]
    fn test_is_health_check_path() {
        let orchestrator = FilterOrchestrator::new().unwrap();

        assert!(orchestrator.is_health_check_path("/healthz"));
        assert!(orchestrator.is_health_check_path("/health"));
        assert!(orchestrator.is_health_check_path("/livez"));
        assert!(orchestrator.is_health_check_path("/readyz"));
        assert!(orchestrator.is_health_check_path("/ready"));
        assert!(orchestrator.is_health_check_path("/alive"));
        assert!(!orchestrator.is_health_check_path("/api/v1/users"));
    }

    #[test]
    fn test_orchestrator_result_to_response() {
        let result = OrchestratorResult::Allowed;
        let (status, _, _) = result.to_response("trace-123");
        assert_eq!(status, 200);
    }
}
