use etradie_envoy_common::{Logger, LogLevel, MetricsCollector, CIRCUIT_BREAKER_FAILURE_THRESHOLD, CIRCUIT_BREAKER_RESET_TIMEOUT_SECS};
use serde::Serialize;
use std::time::SystemTime;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum CircuitState {
    Closed,
    Open,
    HalfOpen,
}

impl CircuitState {
    fn as_str(&self) -> &'static str {
        match self {
            Self::Closed => "closed",
            Self::Open => "open",
            Self::HalfOpen => "half_open",
        }
    }
}

#[derive(Serialize)]
struct StateTransition {
    from_state: String,
    to_state: String,
    failure_count: u32,
    threshold: u32,
}

pub struct CircuitBreaker {
    state: CircuitState,
    failure_count: u32,
    failure_threshold: u32,
    last_failure_time_ms: u64,
    reset_timeout_ms: u64,
    logger: Logger,
    metrics: MetricsCollector,
}

impl CircuitBreaker {
    pub fn new(failure_threshold: u32, reset_timeout_secs: u64) -> Self {
        Self {
            state: CircuitState::Closed,
            failure_count: 0,
            failure_threshold,
            last_failure_time_ms: 0,
            reset_timeout_ms: reset_timeout_secs * 1000,
            logger: Logger::new("circuit_breaker"),
            metrics: MetricsCollector::new("circuit_breaker"),
        }
    }

    pub fn with_defaults() -> Self {
        Self::new(
            CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            CIRCUIT_BREAKER_RESET_TIMEOUT_SECS,
        )
    }

    pub fn record_success(&mut self, trace_id: &str) {
        match self.state {
            CircuitState::HalfOpen => {
                let transition = StateTransition {
                    from_state: CircuitState::HalfOpen.as_str().to_string(),
                    to_state: CircuitState::Closed.as_str().to_string(),
                    failure_count: self.failure_count,
                    threshold: self.failure_threshold,
                };
                self.logger.log_with_details(
                    LogLevel::Info,
                    trace_id,
                    "Circuit breaker state transition",
                    &transition,
                );
                self.state = CircuitState::Closed;
                self.failure_count = 0;
                self.metrics.record_circuit_breaker_state(false);
            }
            CircuitState::Closed => {
                if self.failure_count > 0 {
                    self.failure_count = self.failure_count.saturating_sub(1);
                }
            }
            CircuitState::Open => {}
        }
    }

    pub fn record_failure(&mut self, trace_id: &str) {
        self.failure_count += 1;
        self.last_failure_time_ms = current_timestamp_ms();

        if self.failure_count >= self.failure_threshold && self.state == CircuitState::Closed {
            let transition = StateTransition {
                from_state: CircuitState::Closed.as_str().to_string(),
                to_state: CircuitState::Open.as_str().to_string(),
                failure_count: self.failure_count,
                threshold: self.failure_threshold,
            };
            self.logger.log_with_details(
                LogLevel::Warn,
                trace_id,
                "Circuit breaker state transition",
                &transition,
            );
            self.state = CircuitState::Open;
            self.metrics.record_circuit_breaker_state(true);
            self.metrics.increment_counter("circuit_breaker_opened");
        }
    }

    pub fn check_and_update_state(&mut self, trace_id: &str) -> bool {
        match self.state {
            CircuitState::Closed => true,
            CircuitState::Open => {
                let elapsed_ms = current_timestamp_ms().saturating_sub(self.last_failure_time_ms);

                if elapsed_ms >= self.reset_timeout_ms {
                    let transition = StateTransition {
                        from_state: CircuitState::Open.as_str().to_string(),
                        to_state: CircuitState::HalfOpen.as_str().to_string(),
                        failure_count: self.failure_count,
                        threshold: self.failure_threshold,
                    };
                    self.logger.log_with_details(
                        LogLevel::Info,
                        trace_id,
                        "Circuit breaker state transition",
                        &transition,
                    );
                    self.state = CircuitState::HalfOpen;
                    self.failure_count = 0;
                    true
                } else {
                    false
                }
            }
            CircuitState::HalfOpen => true,
        }
    }

    pub fn reset(&mut self, trace_id: &str) {
        let transition = StateTransition {
            from_state: self.state.as_str().to_string(),
            to_state: CircuitState::Closed.as_str().to_string(),
            failure_count: self.failure_count,
            threshold: self.failure_threshold,
        };
        self.logger.log_with_details(
            LogLevel::Info,
            trace_id,
            "Circuit breaker manual reset",
            &transition,
        );
        self.state = CircuitState::Closed;
        self.failure_count = 0;
        self.metrics.record_circuit_breaker_state(false);
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
    fn test_circuit_breaker_creation() {
        let _cb = CircuitBreaker::with_defaults();
    }

    #[test]
    fn test_circuit_breaker_opens_after_threshold() {
        let mut cb = CircuitBreaker::new(3, 30);
        assert!(cb.check_and_update_state("trace-0"));
        cb.record_failure("trace-1");
        assert!(cb.check_and_update_state("trace-1"));
        cb.record_failure("trace-2");
        assert!(cb.check_and_update_state("trace-2"));
        cb.record_failure("trace-3");
        assert!(!cb.check_and_update_state("trace-3"));
    }

    #[test]
    fn test_circuit_breaker_blocks_when_open() {
        let mut cb = CircuitBreaker::new(2, 30);
        cb.record_failure("trace-1");
        cb.record_failure("trace-2");
        assert!(!cb.check_and_update_state("trace-3"));
    }

    #[test]
    fn test_circuit_breaker_success_reduces_failures() {
        let mut cb = CircuitBreaker::new(5, 30);
        cb.record_failure("trace-1");
        cb.record_failure("trace-2");
        cb.record_success("trace-3");
        assert!(cb.check_and_update_state("trace-4"));
    }

    #[test]
    fn test_circuit_breaker_reset() {
        let mut cb = CircuitBreaker::new(2, 30);
        cb.record_failure("trace-1");
        cb.record_failure("trace-2");
        assert!(!cb.check_and_update_state("trace-3"));
        cb.reset("trace-reset");
        assert!(cb.check_and_update_state("trace-4"));
    }

    #[test]
    fn test_half_open_to_closed_on_success() {
        let mut cb = CircuitBreaker::new(2, 30);
        cb.record_failure("trace-1");
        cb.record_failure("trace-2");
        cb.state = CircuitState::HalfOpen;
        cb.record_success("trace-3");
        assert!(cb.check_and_update_state("trace-4"));
    }
}
