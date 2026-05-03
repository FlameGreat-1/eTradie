use edge_ingress_common::{
    constants::{SERVICE_NAME, SERVICE_VERSION},
    metrics::gather_metrics,
};
use http_body_util::Full;
use hyper::{
    body::{Bytes, Incoming},
    service::service_fn,
    Method, Request, Response, StatusCode,
};
use hyper_util::rt::TokioIo;
use std::convert::Infallible;
use std::net::SocketAddr;
use tokio::net::TcpListener;
use tracing::{error, info};

pub struct MetricsServer {
    bind_address: SocketAddr,
}

impl MetricsServer {
    pub fn new(bind_address: SocketAddr) -> Self {
        Self { bind_address }
    }

    pub async fn run(self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let listener = TcpListener::bind(self.bind_address).await?;

        info!(
            bind_address = %self.bind_address,
            "metrics server started"
        );

        loop {
            let (stream, remote_addr) = match listener.accept().await {
                Ok(conn) => conn,
                Err(e) => {
                    error!(error = %e, "failed to accept metrics connection");
                    continue;
                }
            };

            tokio::spawn(async move {
                let io = TokioIo::new(stream);

                if let Err(e) = hyper::server::conn::http1::Builder::new()
                    .serve_connection(io, service_fn(handle_request))
                    .await
                {
                    error!(
                        remote_addr = %remote_addr,
                        error = %e,
                        "metrics server connection error"
                    );
                }
            });
        }
    }
}

async fn handle_request(
    req: Request<Incoming>,
) -> Result<Response<Full<Bytes>>, Infallible> {
    let path = req.uri().path();
    let method = req.method();

    match (method, path) {
        (&Method::GET, "/healthz") => Ok(healthz_handler()),
        (&Method::GET, "/readyz") => Ok(readyz_handler()),
        (&Method::GET, "/metrics") => Ok(metrics_handler()),
        (&Method::GET, "/version") => Ok(version_handler()),
        _ => Ok(not_found_handler()),
    }
}

fn healthz_handler() -> Response<Full<Bytes>> {
    Response::builder()
        .status(StatusCode::OK)
        .header("Content-Type", "text/plain")
        .body(Full::new(Bytes::from("OK")))
        .unwrap()
}

fn readyz_handler() -> Response<Full<Bytes>> {
    Response::builder()
        .status(StatusCode::OK)
        .header("Content-Type", "text/plain")
        .body(Full::new(Bytes::from("OK")))
        .unwrap()
}

fn metrics_handler() -> Response<Full<Bytes>> {
    match gather_metrics() {
        Ok(metrics) => Response::builder()
            .status(StatusCode::OK)
            .header("Content-Type", "text/plain; version=0.0.4")
            .body(Full::new(Bytes::from(metrics)))
            .unwrap(),
        Err(e) => {
            error!(error = %e, "failed to gather metrics");
            Response::builder()
                .status(StatusCode::INTERNAL_SERVER_ERROR)
                .header("Content-Type", "text/plain")
                .body(Full::new(Bytes::from(format!("Error: {}", e))))
                .unwrap()
        }
    }
}

fn version_handler() -> Response<Full<Bytes>> {
    let version_info = serde_json::json!({
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "build_date": option_env!("BUILD_DATE").unwrap_or("unknown"),
        "git_commit": option_env!("GIT_COMMIT").unwrap_or("unknown"),
    });

    Response::builder()
        .status(StatusCode::OK)
        .header("Content-Type", "application/json")
        .body(Full::new(Bytes::from(version_info.to_string())))
        .unwrap()
}

fn not_found_handler() -> Response<Full<Bytes>> {
    Response::builder()
        .status(StatusCode::NOT_FOUND)
        .header("Content-Type", "text/plain")
        .body(Full::new(Bytes::from("Not Found")))
        .unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_healthz_handler() {
        let response = healthz_handler();
        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_readyz_handler() {
        let response = readyz_handler();
        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_metrics_handler() {
        let response = metrics_handler();
        assert_eq!(response.status(), StatusCode::OK);
        assert_eq!(
            response.headers().get("Content-Type").unwrap(),
            "text/plain; version=0.0.4"
        );
    }

    #[tokio::test]
    async fn test_version_handler() {
        let response = version_handler();
        assert_eq!(response.status(), StatusCode::OK);
        assert_eq!(
            response.headers().get("Content-Type").unwrap(),
            "application/json"
        );
    }

    #[tokio::test]
    async fn test_not_found_handler() {
        let response = not_found_handler();
        assert_eq!(response.status(), StatusCode::NOT_FOUND);
    }
}
