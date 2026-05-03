use crate::{
    config_loader::EdgeServerConfig,
    handler::ConnectionHandler,
    metrics_server::MetricsServer,
};
use edge_ingress_common::{
    log_server_started, log_server_shutdown, log_shutdown_draining,
    metrics::{
        init_metrics, set_shutdown_draining, update_upstream_healthy_count,
        update_upstream_pool_size, ACTIVE_CONNECTIONS,
    },
    types::{Region, UpstreamEndpoint},
};
use edge_ingress_geo_router::GeoRouter;
use edge_ingress_tls::TlsAcceptor;
use edge_ingress_upstream::UpstreamProxy;
use std::sync::Arc;
use tokio::net::TcpListener;
use tokio::signal;
use tokio::sync::broadcast;
use tokio::time::{sleep, Duration};
use tracing::{error, info};

pub struct EdgeServer {
    config: EdgeServerConfig,
    shutdown_tx: broadcast::Sender<()>,
}

impl EdgeServer {
    pub fn new(config: EdgeServerConfig) -> Self {
        let (shutdown_tx, _) = broadcast::channel(1);
        Self {
            config,
            shutdown_tx,
        }
    }

    pub async fn run(self) -> std::result::Result<(), Box<dyn std::error::Error + Send + Sync>> {
        init_metrics();

        let tls_acceptor = TlsAcceptor::new(self.config.tls.clone())?;
        let connection_limiter = self.config.build_connection_limiter();
        let geoip_lookup = self.config.build_geoip_lookup()?;
        let geo_router = GeoRouter::new(geoip_lookup);
        let upstream_proxy = self.config.build_upstream_proxy()?;

        self.initialize_upstream_endpoints(&upstream_proxy).await?;

        let handler = Arc::new(ConnectionHandler::new(
            tls_acceptor,
            geo_router,
            connection_limiter,
            upstream_proxy.clone(),
            self.config.clone(),
        ));

        let metrics_server = MetricsServer::new(self.config.server.metrics_bind_address);
        let metrics_handle = tokio::spawn(async move {
            if let Err(e) = metrics_server.run().await {
                error!(error = %e, "metrics server error");
            }
        });

        let health_checker_handle = self.spawn_health_checker(Arc::new(upstream_proxy.clone()));

        let tls_listener = TcpListener::bind(self.config.server.tls_bind_address).await?;

        log_server_started(
            self.config.server.tls_bind_address.port(),
            self.config.server.metrics_bind_address.port(),
        );

        let mut shutdown_rx = self.shutdown_tx.subscribe();

        loop {
            tokio::select! {
                accept_result = tls_listener.accept() => {
                    match accept_result {
                        Ok((stream, addr)) => {
                            let handler = Arc::clone(&handler);
                            tokio::spawn(async move {
                                handler.handle_connection(stream, addr).await;
                            });
                        }
                        Err(e) => {
                            error!(error = %e, "failed to accept TLS connection");
                        }
                    }
                }
                _ = shutdown_rx.recv() => {
                    info!("shutdown signal received");
                    break;
                }
                _ = signal::ctrl_c() => {
                    info!("SIGINT received, initiating shutdown");
                    let _ = self.shutdown_tx.send(());
                    break;
                }
            }
        }

        self.drain_connections().await;

        log_server_shutdown("graceful shutdown");

        metrics_handle.abort();
        health_checker_handle.abort();

        Ok(())
    }

    async fn drain_connections(&self) {
        let drain_timeout = Duration::from_secs(30);
        let check_interval = Duration::from_millis(500);
        let start = std::time::Instant::now();

        loop {
            let active = ACTIVE_CONNECTIONS.get();
            set_shutdown_draining(active);
            log_shutdown_draining(active);

            if active <= 0 {
                info!("all connections drained");
                break;
            }

            if start.elapsed() >= drain_timeout {
                info!(
                    remaining_connections = active,
                    "drain timeout reached, forcing shutdown"
                );
                break;
            }

            sleep(check_interval).await;
        }

        set_shutdown_draining(0);
    }

    async fn initialize_upstream_endpoints(
        &self,
        upstream_proxy: &UpstreamProxy,
    ) -> std::result::Result<(), Box<dyn std::error::Error + Send + Sync>> {
        for endpoint_config in &self.config.upstream.endpoints {
            let region = Region::from_str(&endpoint_config.region).ok_or_else(|| {
                format!("Invalid region: {}", endpoint_config.region)
            })?;

            let address = tokio::net::lookup_host(&endpoint_config.address)
                .await?
                .next()
                .ok_or_else(|| {
                    format!("Failed to resolve address: {}", endpoint_config.address)
                })?;

            let mut endpoint = UpstreamEndpoint::new(region, address);
            endpoint.mark_healthy();

            upstream_proxy.add_endpoint(endpoint).await;

            info!(
                region = %region,
                address = %address,
                "upstream endpoint initialized"
            );
        }

        Ok(())
    }

    fn spawn_health_checker(
        &self,
        upstream_proxy: Arc<UpstreamProxy>,
    ) -> tokio::task::JoinHandle<()> {
        let health_checker = upstream_proxy.get_health_checker();
        let check_interval = health_checker.check_interval();

        tokio::spawn(async move {
            let mut interval = tokio::time::interval(check_interval);

            loop {
                interval.tick().await;

                let pool = upstream_proxy.get_pool().await;
                let all_endpoints = pool.get_all_endpoints().await;

                for (region, endpoints) in &all_endpoints {
                    update_upstream_pool_size(*region, endpoints.len() as f64);

                    let healthy_count = endpoints.iter().filter(|e| e.status.is_healthy()).count();
                    update_upstream_healthy_count(*region, healthy_count as f64);

                    for endpoint in endpoints {
                        let is_healthy = health_checker.check_endpoint(endpoint.address).await;

                        pool.update_endpoint_health(*region, endpoint.address, is_healthy)
                            .await;

                        let updated_endpoints = pool.get_endpoints(*region).await;
                        if let Some(updated_endpoint) = updated_endpoints
                            .iter()
                            .find(|e| e.address == endpoint.address)
                        {
                            if health_checker.should_mark_healthy(updated_endpoint) {
                                health_checker.update_metrics(*region, updated_endpoint.status);
                            } else if health_checker.should_mark_unhealthy(updated_endpoint) {
                                health_checker.update_metrics(*region, updated_endpoint.status);
                            }
                        }
                    }
                }
            }
        })
    }

    pub fn shutdown(&self) {
        let _ = self.shutdown_tx.send(());
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new_server() {
        let config = EdgeServerConfig::default();
        let tls_addr = config.server.tls_bind_address;
        let metrics_addr = config.server.metrics_bind_address;

        let server = EdgeServer::new(config);
        assert_eq!(server.config.server.tls_bind_address, tls_addr);
        assert_eq!(server.config.server.metrics_bind_address, metrics_addr);
    }

    #[test]
    fn test_shutdown_signal() {
        let config = EdgeServerConfig::default();
        let server = EdgeServer::new(config);
        server.shutdown();
    }
}
