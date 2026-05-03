use crate::config_loader::EdgeServerConfig;
use edge_ingress_common::{
    create_connection_info, extract_or_generate_trace_id,
    log_connection_closed, log_region_selected,
    metrics::{
        record_bytes_received, record_bytes_sent, record_connection_accepted,
        record_connection_duration, record_request_completed, record_tls_handshake_error,
    },
    types::{Region, RequestMetadata, RequestStatus},
    EdgeError, Result,
};
use edge_ingress_connection_limiter::{ConnectionGuard, ConnectionLimiter};
use edge_ingress_geo_router::GeoRouter;
use edge_ingress_tls::{AcceptedConnection, TlsAcceptor};
use edge_ingress_upstream::UpstreamProxy;
use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;
use std::time::Instant;
use tokio::io::{copy_bidirectional, AsyncRead, AsyncWrite};
use tokio::net::TcpStream;
use tokio::time::timeout;
use tracing::error;

pub struct ConnectionHandler {
    tls_acceptor: Arc<TlsAcceptor>,
    geo_router: Arc<GeoRouter>,
    connection_limiter: Arc<ConnectionLimiter>,
    upstream_proxy: Arc<UpstreamProxy>,
    config: Arc<EdgeServerConfig>,
}

impl ConnectionHandler {
    pub fn new(
        tls_acceptor: TlsAcceptor,
        geo_router: GeoRouter,
        connection_limiter: ConnectionLimiter,
        upstream_proxy: UpstreamProxy,
        config: EdgeServerConfig,
    ) -> Self {
        Self {
            tls_acceptor: Arc::new(tls_acceptor),
            geo_router: Arc::new(geo_router),
            connection_limiter: Arc::new(connection_limiter),
            upstream_proxy: Arc::new(upstream_proxy),
            config: Arc::new(config),
        }
    }

    pub async fn handle_connection(&self, client_stream: TcpStream, client_addr: SocketAddr) {
        let start_time = Instant::now();
        let mut final_region = Region::UsEast1;
        let mut final_status = RequestStatus::Error;

        let _connection_guard = match self.acquire_connection_limits(client_addr) {
            Ok(guard) => guard,
            Err(e) => {
                error!(
                    client_addr = %client_addr,
                    error = %e,
                    "connection limit exceeded"
                );
                record_connection_duration(final_region, final_status, start_time.elapsed().as_secs_f64());
                return;
            }
        };

        record_connection_accepted();

        let trace_id = extract_or_generate_trace_id(None);
        let mut conn_info = create_connection_info(client_addr, Some(&trace_id));

        let tls_result = self.perform_tls_handshake(client_stream).await;

        let accepted_conn = match tls_result {
            Ok(conn) => {
                conn_info.tls_version = Some(conn.tls_version());
                conn_info.sni_hostname = conn.hostname().map(|s| s.to_string());
                conn
            }
            Err(e) => {
                record_tls_handshake_error("handshake_failed");
                error!(
                    client_ip = %client_addr.ip(),
                    error = %e,
                    "TLS handshake failed"
                );
                record_connection_duration(final_region, final_status, start_time.elapsed().as_secs_f64());
                return;
            }
        };

        let routing_result = self.route_to_upstream(&conn_info).await;

        let (selected_region, upstream_stream) = match routing_result {
            Ok((region, stream)) => {
                final_region = region;
                (region, stream)
            }
            Err(e) => {
                error!(
                    trace_id = %trace_id,
                    error = %e,
                    "routing failed"
                );
                log_connection_closed(&conn_info, 0, 0);
                record_connection_duration(final_region, final_status, start_time.elapsed().as_secs_f64());
                return;
            }
        };

        let proxy_result = self
            .proxy_traffic(
                accepted_conn.into_stream(),
                upstream_stream,
                &conn_info,
                selected_region,
                start_time,
            )
            .await;

        match proxy_result {
            Ok(metadata) => {
                final_status = RequestStatus::Success;
                log_connection_closed(&conn_info, metadata.bytes_received, metadata.bytes_sent);
            }
            Err(e) => {
                error!(
                    trace_id = %trace_id,
                    error = %e,
                    "proxy error"
                );
                log_connection_closed(&conn_info, 0, 0);
            }
        }

        record_connection_duration(final_region, final_status, start_time.elapsed().as_secs_f64());
    }

    fn acquire_connection_limits(
        &self,
        client_addr: SocketAddr,
    ) -> Result<ConnectionGuard<'_>> {
        self.connection_limiter.acquire(client_addr.ip())
    }

    async fn perform_tls_handshake<S>(
        &self,
        stream: S,
    ) -> Result<AcceptedConnection<S>>
    where
        S: AsyncRead + AsyncWrite + Unpin + Send + 'static,
    {
        self.tls_acceptor.accept(stream).await
    }

    async fn route_to_upstream(
        &self,
        conn_info: &edge_ingress_common::types::ConnectionInfo,
    ) -> Result<(Region, TcpStream)> {
        let upstream_health = self.get_upstream_health().await;

        let (selected_region, fallback_reason) = self
            .geo_router
            .route(conn_info.client_ip, &upstream_health)?;

        log_region_selected(
            &conn_info.trace_id,
            conn_info.client_ip,
            selected_region,
            fallback_reason.is_some(),
        );

        let upstream_stream = self.upstream_proxy.connect(selected_region).await?;

        Ok((selected_region, upstream_stream))
    }

    async fn proxy_traffic<S>(
        &self,
        mut client_stream: S,
        mut upstream_stream: TcpStream,
        conn_info: &edge_ingress_common::types::ConnectionInfo,
        selected_region: Region,
        start_time: Instant,
    ) -> Result<RequestMetadata>
    where
        S: AsyncRead + AsyncWrite + Unpin,
    {
        let idle_timeout = self.config.idle_timeout();

        let copy_result = timeout(
            idle_timeout,
            copy_bidirectional(&mut client_stream, &mut upstream_stream),
        )
        .await;

        let (bytes_to_upstream, bytes_to_client) = match copy_result {
            Ok(Ok((to_upstream, to_client))) => (to_upstream, to_client),
            Ok(Err(e)) => {
                error!(
                    trace_id = %conn_info.trace_id,
                    error = %e,
                    "bidirectional copy error"
                );
                return Err(EdgeError::Internal(format!("Copy error: {}", e)));
            }
            Err(_) => {
                error!(
                    trace_id = %conn_info.trace_id,
                    timeout_secs = idle_timeout.as_secs(),
                    "idle timeout"
                );
                return Err(EdgeError::Internal("Idle timeout".to_string()));
            }
        };

        let duration = start_time.elapsed();

        record_bytes_received(selected_region, bytes_to_upstream);
        record_bytes_sent(selected_region, bytes_to_client);
        record_request_completed(RequestStatus::Success, selected_region, duration.as_secs_f64());

        let metadata = RequestMetadata {
            trace_id: conn_info.trace_id.clone(),
            client_ip: conn_info.client_ip,
            selected_region,
            upstream_address: upstream_stream.peer_addr().unwrap_or_else(|_| "0.0.0.0:0".parse().unwrap()),
            tls_version: conn_info.tls_version,
            bytes_received: bytes_to_upstream,
            bytes_sent: bytes_to_client,
            duration_ms: duration.as_millis() as u64,
            status: RequestStatus::Success,
        };

        Ok(metadata)
    }

    async fn get_upstream_health(&self) -> HashMap<Region, edge_ingress_common::types::UpstreamStatus> {
        let pool = self.upstream_proxy.get_pool().await;
        let all_endpoints = pool.get_all_endpoints().await;

        let mut health_map = HashMap::new();

        for (region, endpoints) in all_endpoints {
            let has_healthy = endpoints.iter().any(|e| e.status.is_healthy());
            let status = if has_healthy {
                edge_ingress_common::types::UpstreamStatus::Healthy
            } else {
                edge_ingress_common::types::UpstreamStatus::Unhealthy
            };
            health_map.insert(region, status);
        }

        health_map
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use edge_ingress_geo_router::GeoIpLookup;
    use edge_ingress_tls::TlsConfig;
    use edge_ingress_upstream::{HealthChecker, UpstreamPool};

    fn create_test_config() -> EdgeServerConfig {
        EdgeServerConfig::default()
    }

    fn create_test_handler() -> Result<ConnectionHandler> {
        let config = create_test_config();

        let mut tls_config = TlsConfig::default();
        tls_config.certificates.push(edge_ingress_tls::CertificateConfig {
            hostname: "test.example.com".to_string(),
            cert_path: std::path::PathBuf::from("/tmp/cert.pem"),
            key_path: std::path::PathBuf::from("/tmp/key.pem"),
            is_default: true,
        });

        let connection_limiter = ConnectionLimiter::with_default_limits();

        let geoip_lookup = GeoIpLookup::from_default_path()?;
        let geo_router = GeoRouter::new(geoip_lookup);

        let pool = UpstreamPool::new();
        let health_checker = HealthChecker::new();
        let upstream_proxy = UpstreamProxy::new(pool, health_checker);

        Ok(ConnectionHandler {
            tls_acceptor: Arc::new(TlsAcceptor::new(tls_config)?),
            geo_router: Arc::new(geo_router),
            connection_limiter: Arc::new(connection_limiter),
            upstream_proxy: Arc::new(upstream_proxy),
            config: Arc::new(config),
        })
    }

    #[tokio::test]
    async fn test_get_upstream_health_empty() {
        if let Ok(handler) = create_test_handler() {
            let health = handler.get_upstream_health().await;
            assert!(health.is_empty());
        }
    }
}
