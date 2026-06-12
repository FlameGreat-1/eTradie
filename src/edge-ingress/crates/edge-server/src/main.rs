use edge_ingress_common::constants::{DEFAULT_OTEL_ENDPOINT, OTEL_EXPORTER_ENDPOINT_ENV, SERVICE_NAME, SERVICE_VERSION};
use edge_ingress_server::{EdgeServer, EdgeServerConfig};
use opentelemetry::global;
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::{
    trace::{self, Sampler},
    Resource,
};
use opentelemetry::KeyValue;
use std::env;
use std::process;
use tracing::{error, info};

fn init_otel_tracer() -> Option<opentelemetry_sdk::trace::Tracer> {
    let endpoint = env::var(OTEL_EXPORTER_ENDPOINT_ENV)
        .unwrap_or_else(|_| DEFAULT_OTEL_ENDPOINT.to_string());

    let environment = env::var(edge_ingress_common::constants::ENVIRONMENT_ENV)
        .unwrap_or_else(|_| "unknown".to_string());

    let tracer = opentelemetry_otlp::new_pipeline()
        .tracing()
        .with_exporter(
            opentelemetry_otlp::new_exporter()
                .tonic()
                .with_endpoint(&endpoint),
        )
        .with_trace_config(
            trace::config()
                .with_sampler(Sampler::AlwaysOn)
                .with_max_events_per_span(64)
                .with_max_attributes_per_span(16)
                .with_resource(Resource::new(vec![
                    KeyValue::new("service.name", SERVICE_NAME),
                    KeyValue::new("service.version", SERVICE_VERSION),
                    KeyValue::new("deployment.environment", environment),
                ])),
        )
        .install_batch(opentelemetry_sdk::runtime::Tokio);

    match tracer {
        Ok(tracer) => {
            info!(endpoint = %endpoint, "OpenTelemetry tracer initialized");
            Some(tracer)
        }
        Err(e) => {
            eprintln!("Failed to initialize OpenTelemetry tracer: {}. Continuing without trace export.", e);
            None
        }
    }
}

#[tokio::main]
async fn main() {
    let tracer = init_otel_tracer();
    edge_ingress_common::init_logging_with_otel(tracer);

    let config_path = env::var("CONFIG_PATH").unwrap_or_else(|_| {
        "/etc/edge-ingress/config.yaml".to_string()
    });

    info!(config_path = %config_path, "loading configuration");

    let config = match EdgeServerConfig::from_file(&config_path) {
        Ok(cfg) => cfg,
        Err(e) => {
            error!(error = %e, "failed to load configuration");
            process::exit(1);
        }
    };

    let server = EdgeServer::new(config);

    info!("starting edge-ingress server");

    if let Err(e) = server.run().await {
        error!(error = %e, "server error");
        global::shutdown_tracer_provider();
        process::exit(1);
    }

    global::shutdown_tracer_provider();
    info!("edge-ingress server stopped");
}
