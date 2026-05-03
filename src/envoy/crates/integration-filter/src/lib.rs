mod circuit_breaker;
mod context;
mod filters;
mod orchestrator;

use context::RequestContext;
use etradie_envoy_common::{
    build_traceparent, init_service_info, log_request_end, log_request_start,
    set_environment, MetricsCollector,
};
use orchestrator::FilterOrchestrator;
use proxy_wasm::traits::{Context, HttpContext, RootContext};
use proxy_wasm::types::{Action, LogLevel};
use std::cell::RefCell;

thread_local! {
    static ORCHESTRATOR: RefCell<Option<FilterOrchestrator>> = RefCell::new(None);
}

#[no_mangle]
pub fn _start() {
    proxy_wasm::set_log_level(LogLevel::Info);
    proxy_wasm::set_root_context(|_| -> Box<dyn RootContext> {
        Box::new(ETradieRootContext)
    });
}

struct ETradieRootContext;

impl Context for ETradieRootContext {}

impl RootContext for ETradieRootContext {
    fn on_vm_start(&mut self, _vm_configuration_size: usize) -> bool {
        let environment = self
            .get_vm_configuration()
            .and_then(|bytes| String::from_utf8(bytes).ok())
            .unwrap_or_else(|| "production".to_string());

        set_environment(&environment);
        init_service_info(&environment);

        match FilterOrchestrator::new() {
            Ok(orchestrator) => {
                ORCHESTRATOR.with(|o| {
                    *o.borrow_mut() = Some(orchestrator);
                });
                proxy_wasm::hostcalls::log(LogLevel::Info, "eTradie integration filter initialized").ok();
                true
            }
            Err(e) => {
                proxy_wasm::hostcalls::log(
                    LogLevel::Error,
                    &format!("Failed to initialize orchestrator: {}", e),
                ).ok();
                false
            }
        }
    }

    fn create_http_context(&self, _context_id: u32) -> Option<Box<dyn HttpContext>> {
        Some(Box::new(ETradieHttpContext {
            context: None,
            response_status: 0,
        }))
    }

    fn get_type(&self) -> Option<proxy_wasm::types::ContextType> {
        Some(proxy_wasm::types::ContextType::HttpContext)
    }
}

struct ETradieHttpContext {
    context: Option<RequestContext>,
    response_status: u32,
}

impl Context for ETradieHttpContext {}

impl HttpContext for ETradieHttpContext {
    fn on_http_request_headers(&mut self, _num_headers: usize, _end_of_stream: bool) -> Action {
        let method = self.get_http_request_header(":method").unwrap_or_else(|| "GET".to_string());
        let path = self.get_http_request_header(":path").unwrap_or_else(|| "/".to_string());

        let headers = self.get_http_request_headers();

        let context = RequestContext::new(method.clone(), path.clone(), &headers);

        log_request_start(context.trace_id(), &method, &path, context.client_ip());

        if let Some(content_length) = self.get_http_request_header("content-length") {
            if let Ok(size) = content_length.parse::<u64>() {
                let metrics = MetricsCollector::new("request");
                metrics.record_request_body_size(size);
            }
        }

        let result = ORCHESTRATOR.with(|o| {
            if let Some(orchestrator) = o.borrow_mut().as_mut() {
                orchestrator.process_request(&context, &headers)
            } else {
                proxy_wasm::hostcalls::log(
                    LogLevel::Error,
                    "Orchestrator not initialized",
                ).ok();
                orchestrator::OrchestratorResult::CircuitBreakerOpen
            }
        });

        if result.is_allowed() {
            self.add_http_request_header("x-trace-id", context.trace_id());
            self.add_http_request_header("x-request-id", context.request_id());

            let traceparent = build_traceparent(context.trace_id(), context.span_id());
            self.add_http_request_header("traceparent", &traceparent);

            self.context = Some(context);
            Action::Continue
        } else {
            let (status, headers, body) = result.to_response(context.trace_id());
            self.response_status = status;
            let header_refs: Vec<(&str, &str)> = headers.iter()
                .map(|(k, v)| (k.as_str(), v.as_str()))
                .collect();
            self.send_http_response(status, header_refs, Some(body.as_bytes()));
            Action::Pause
        }
    }

    fn on_http_response_headers(&mut self, _num_headers: usize, _end_of_stream: bool) -> Action {
        if let Some(status_str) = self.get_http_response_header(":status") {
            if let Ok(status) = status_str.parse::<u32>() {
                self.response_status = status;
            }
        }

        if let Some(ref ctx) = self.context {
            let duration_ms = ctx.elapsed_ms();
            let metrics = MetricsCollector::new("orchestrator");
            metrics.record_request(self.response_status, duration_ms);
        }

        Action::Continue
    }

    fn on_log(&mut self) {
        if let Some(ref ctx) = self.context {
            let duration_ms = ctx.elapsed_ms();
            log_request_end(
                ctx.trace_id(),
                self.response_status,
                duration_ms,
                ctx.client_ip(),
            );
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_root_context_creation() {
        let root = ETradieRootContext;
        assert!(root.get_type().is_some());
    }

    #[test]
    fn test_http_context_creation() {
        let root = ETradieRootContext;
        let http_context = root.create_http_context(1);
        assert!(http_context.is_some());
    }
}
