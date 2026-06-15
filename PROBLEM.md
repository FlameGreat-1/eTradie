
softverse@Softverse:~/eTradie$
softverse@Softverse:~/eTradie$ # 1. The init-container failure on the engine new pod (this drives the cascade)
kubectl -n etradie-system describe pod etradie-engine-d7bd6444d-2lwp8 | sed -n '/Init Containers:/,/Containers:/p'
echo "---"
kubectl -n etradie-system logs etradie-engine-d7bd6444d-2lwp8 -c wait-for-deps --tail=80 2>&1
echo "---"
# If "wait-for-deps" is the wrong name, this catches whichever init container is actually there
kubectl -n etradie-system get pod etradie-engine-d7bd6444d-2lwp8 \
  -o jsonpath='{range .spec.initContainers[*]}{.name}{"\n"}{end}'

# 2. Same for the new gateway pod (different chart, different init shape)
kubectl -n etradie-system get pod etradie-gateway-bfbc5fcf8-k2lm9 \
  -o jsonpath='{range .spec.initContainers[*]}{.name}{"\n"}{end}'
kubectl -n etradie-system logs etradie-gateway-bfbc5fcf8-k2lm9 --all-containers --tail=40 2>&1

# 3. Envoy main-container failure
kubectl -n envoy-system logs etradie-envoy-57cffb98b-wjv7n -c envoy --tail=80 2>&1
echo "---"
kubectl -n envoy-system logs etradie-envoy-57cffb98b-wjv7n -c envoy --previous --tail=80 2>&1
echo "---"
kubectl -n envoy-system describe pod etradie-envoy-57cffb98b-wjv7n | sed -n '/Containers:/,/Conditions:/p' | head -80

# 4. Quick sanity — are the old (broken) replicasets still hanging around because
#    the ReplicaSet controller can't scale them down? List them.
kubectl -n etradie-system get rs -o wide 2>&1 | grep -E 'engine|gateway'

# 5. Confirm Linkerd injector + identity are healthy (a dead injector would
#    explain why new pods can't get their proxy sidecar working, blocking the
#    init container's network reachability)
kubectl -n linkerd get pods
Init Containers:
  wait-for-deps:
    Container ID:    containerd://4130cbc550d72986ead891daa63421027feb8928abbdb66de1832fd18006f534
    Image:           busybox:1.36
    Image ID:        docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
    Port:            <none>
    Host Port:       <none>
    SeccompProfile:  RuntimeDefault
    Command:
      /bin/sh
      -c
      set -eu
      deadline=$(( $(date +%s) + ${WAIT_FOR_DEPS_TIMEOUT_SECS} ))
      echo "[wait-for-deps] checking postgres.etradie-system.svc.cluster.local:5432"
      while ! nc -z -w 2 "postgres.etradie-system.svc.cluster.local" 5432; do
        if [ "$(date +%s)" -ge "${deadline}" ]; then
          echo "[wait-for-deps] FATAL: timed out waiting for postgres.etradie-system.svc.cluster.local:5432"
          exit 1
        fi
        echo "[wait-for-deps] postgres.etradie-system.svc.cluster.local:5432 not yet reachable; sleeping ${WAIT_FOR_DEPS_INTERVAL_SECS}s"
        sleep "${WAIT_FOR_DEPS_INTERVAL_SECS}"
      done
      echo "[wait-for-deps] postgres.etradie-system.svc.cluster.local:5432 reachable"
      echo "[wait-for-deps] checking redis.etradie-system.svc.cluster.local:6379"
      while ! nc -z -w 2 "redis.etradie-system.svc.cluster.local" 6379; do
        if [ "$(date +%s)" -ge "${deadline}" ]; then
          echo "[wait-for-deps] FATAL: timed out waiting for redis.etradie-system.svc.cluster.local:6379"
          exit 1
        fi
        echo "[wait-for-deps] redis.etradie-system.svc.cluster.local:6379 not yet reachable; sleeping ${WAIT_FOR_DEPS_INTERVAL_SECS}s"
        sleep "${WAIT_FOR_DEPS_INTERVAL_SECS}"
      done
      echo "[wait-for-deps] redis.etradie-system.svc.cluster.local:6379 reachable"
      echo "[wait-for-deps] checking chromadb.etradie-system.svc.cluster.local:8000"
      while ! nc -z -w 2 "chromadb.etradie-system.svc.cluster.local" 8000; do
        if [ "$(date +%s)" -ge "${deadline}" ]; then
          echo "[wait-for-deps] FATAL: timed out waiting for chromadb.etradie-system.svc.cluster.local:8000"
          exit 1
        fi
        echo "[wait-for-deps] chromadb.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping ${WAIT_FOR_DEPS_INTERVAL_SECS}s"
        sleep "${WAIT_FOR_DEPS_INTERVAL_SECS}"
      done
      echo "[wait-for-deps] chromadb.etradie-system.svc.cluster.local:8000 reachable"
      echo "[wait-for-deps] all dependencies reachable"

    State:          Terminated
      Reason:       Completed
      Exit Code:    0
      Started:      Mon, 15 Jun 2026 09:38:42 +0100
      Finished:     Mon, 15 Jun 2026 09:38:42 +0100
    Ready:          True
    Restart Count:  9
    Limits:
      cpu:     100m
      memory:  128Mi
    Requests:
      cpu:     50m
      memory:  64Mi
    Environment:
      WAIT_FOR_DEPS_TIMEOUT_SECS:   180
      WAIT_FOR_DEPS_INTERVAL_SECS:  2
    Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from kube-api-access-fnnp8 (ro)
  migrate:
    Container ID:    containerd://1d63237f737256eb9817db42d72ba59db90609c7b5b0ad8c51a089157b59e926
    Image:           ghcr.io/flamegreat-1/etradie/engine:0.1.0
    Image ID:        ghcr.io/flamegreat-1/etradie/engine@sha256:401e2afaec9ffc96a374c6c0eed5e848846fed4a3e31158f341fca79a44e7ed2
    Port:            <none>
    Host Port:       <none>
    SeccompProfile:  RuntimeDefault
    Command:
      /bin/sh
      -c
      set -eu
      echo "[migrate] running alembic upgrade head"
      alembic upgrade head
      echo "[migrate] migration complete"

    State:          Waiting
      Reason:       CrashLoopBackOff
    Last State:     Terminated
      Reason:       Error
      Exit Code:    1
      Started:      Mon, 15 Jun 2026 09:40:10 +0100
      Finished:     Mon, 15 Jun 2026 09:40:13 +0100
    Ready:          False
    Restart Count:  3
    Limits:
      cpu:     500m
      memory:  512Mi
    Requests:
      cpu:     50m
      memory:  128Mi
    Environment Variables from:
      etradie-engine-config   ConfigMap  Optional: false
      etradie-engine-secrets  Secret     Optional: false
    Environment:
      PYTHONUNBUFFERED:  1
      HOME:              /home/etradie
    Mounts:
      /home/etradie/.cache from model-cache (rw)
      /tmp from tmp (rw)
      /var/run/secrets/kubernetes.io/serviceaccount from kube-api-access-fnnp8 (ro)
  linkerd-init:
    Container ID:
    Image:           cr.l5d.io/linkerd/proxy-init:v2.2.3
    Image ID:
    Port:            <none>
    Host Port:       <none>
    SeccompProfile:  RuntimeDefault
    Args:
      --incoming-proxy-port
      4143
      --outgoing-proxy-port
      4140
      --proxy-uid
      2102
      --inbound-ports-to-ignore
      4190,4191,4567,4568
      --outbound-ports-to-ignore
      4317
    State:          Waiting
      Reason:       PodInitializing
    Ready:          False
    Restart Count:  0
    Limits:
      cpu:     100m
      memory:  64Mi
    Requests:
      cpu:        50m
      memory:     64Mi
    Environment:  <none>
    Mounts:
      /run from linkerd-proxy-init-xtables-lock (rw)
      /var/run/secrets/kubernetes.io/serviceaccount from kube-api-access-fnnp8 (ro)
Containers:
---
[wait-for-deps] checking postgres.etradie-system.svc.cluster.local:5432
[wait-for-deps] postgres.etradie-system.svc.cluster.local:5432 reachable
[wait-for-deps] checking redis.etradie-system.svc.cluster.local:6379
[wait-for-deps] redis.etradie-system.svc.cluster.local:6379 reachable
[wait-for-deps] checking chromadb.etradie-system.svc.cluster.local:8000
[wait-for-deps] chromadb.etradie-system.svc.cluster.local:8000 reachable
[wait-for-deps] all dependencies reachable
---
wait-for-deps
migrate
linkerd-init
wait-for-deps
linkerd-init
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping 2s
[wait-for-deps] FATAL: timed out waiting for engine.etradie-system.svc.cluster.local:8000
Error from server (BadRequest): container "linkerd-init" in pod "etradie-gateway-bfbc5fcf8-k2lm9" is waiting to start: PodInitializing
[2026-06-15 08:39:02.674][1][info][main] [source/server/server.cc:413] initializing epoch 0 (base id=0, hot restart version=11.104)
[2026-06-15 08:39:02.674][1][info][main] [source/server/server.cc:415] statically linked extensions:
[2026-06-15 08:39:02.676][1][info][main] [source/server/server.cc:417]   envoy.http.cache: envoy.extensions.http.cache.file_system_http_cache, envoy.extensions.http.cache.simple
[2026-06-15 08:39:02.676][1][info][main] [source/server/server.cc:417]   envoy.http.original_ip_detection: envoy.http.original_ip_detection.custom_header, envoy.http.original_ip_detection.xff
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.health_check.event_sinks: envoy.health_check.event_sink.file
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.matching.network.input: envoy.matching.inputs.application_protocol, envoy.matching.inputs.destination_ip, envoy.matching.inputs.destination_port, envoy.matching.inputs.direct_source_ip, envoy.matching.inputs.dns_san, envoy.matching.inputs.filter_state, envoy.matching.inputs.server_name, envoy.matching.inputs.source_ip, envoy.matching.inputs.source_port, envoy.matching.inputs.source_type, envoy.matching.inputs.subject, envoy.matching.inputs.transport_protocol, envoy.matching.inputs.uri_san
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.resource_monitors: envoy.resource_monitors.fixed_heap, envoy.resource_monitors.injected_resource
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.formatter: envoy.formatter.cel, envoy.formatter.metadata, envoy.formatter.req_without_query
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.grpc_credentials: envoy.grpc_credentials.aws_iam, envoy.grpc_credentials.default, envoy.grpc_credentials.file_based_metadata
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.matching.http.custom_matchers: envoy.matching.custom_matchers.trie_matcher
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.upstream.local_address_selector: envoy.upstream.local_address_selector.default_local_address_selector
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.transport_sockets.upstream: envoy.transport_sockets.alts, envoy.transport_sockets.http_11_proxy, envoy.transport_sockets.internal_upstream, envoy.transport_sockets.quic, envoy.transport_sockets.raw_buffer, envoy.transport_sockets.starttls, envoy.transport_sockets.tap, envoy.transport_sockets.tcp_stats, envoy.transport_sockets.tls, envoy.transport_sockets.upstream_proxy_protocol, raw_buffer, starttls, tls
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.compression.compressor: envoy.compression.brotli.compressor, envoy.compression.gzip.compressor, envoy.compression.zstd.compressor
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.geoip_providers: envoy.geoip_providers.maxmind
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.regex_engines: envoy.regex_engines.google_re2
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.quic.server_preferred_address: quic.server_preferred_address.fixed
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.filters.udp.session: envoy.filters.udp.session.dynamic_forward_proxy, envoy.filters.udp.session.http_capsule
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.network.dns_resolver: envoy.network.dns_resolver.cares, envoy.network.dns_resolver.getaddrinfo
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.path.match: envoy.path.match.uri_template.uri_template_matcher
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.access_loggers.extension_filters: envoy.access_loggers.extension_filters.cel
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.filters.listener: envoy.filters.listener.http_inspector, envoy.filters.listener.local_ratelimit, envoy.filters.listener.original_dst, envoy.filters.listener.original_src, envoy.filters.listener.proxy_protocol, envoy.filters.listener.tls_inspector, envoy.listener.http_inspector, envoy.listener.original_dst, envoy.listener.original_src, envoy.listener.proxy_protocol, envoy.listener.tls_inspector
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.health_checkers: envoy.health_checkers.grpc, envoy.health_checkers.http, envoy.health_checkers.redis, envoy.health_checkers.tcp, envoy.health_checkers.thrift
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.clusters: envoy.cluster.eds, envoy.cluster.logical_dns, envoy.cluster.original_dst, envoy.cluster.static, envoy.cluster.strict_dns, envoy.clusters.aggregate, envoy.clusters.dynamic_forward_proxy, envoy.clusters.redis
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.rbac.matchers: envoy.rbac.matchers.upstream_ip_port
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.http.header_validators: envoy.http.header_validators.envoy_default
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.dubbo_proxy.filters: envoy.filters.dubbo.router
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.bootstrap: envoy.bootstrap.internal_listener, envoy.bootstrap.wasm, envoy.extensions.network.socket_interface.default_socket_interface
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.quic.proof_source: envoy.quic.proof_source.filter_chain
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.filters.network: envoy.echo, envoy.ext_authz, envoy.filters.network.connection_limit, envoy.filters.network.direct_response, envoy.filters.network.dubbo_proxy, envoy.filters.network.echo, envoy.filters.network.ext_authz, envoy.filters.network.http_connection_manager, envoy.filters.network.local_ratelimit, envoy.filters.network.mongo_proxy, envoy.filters.network.ratelimit, envoy.filters.network.rbac, envoy.filters.network.redis_proxy, envoy.filters.network.set_filter_state, envoy.filters.network.sni_cluster, envoy.filters.network.sni_dynamic_forward_proxy, envoy.filters.network.tcp_proxy, envoy.filters.network.thrift_proxy, envoy.filters.network.wasm, envoy.filters.network.zookeeper_proxy, envoy.http_connection_manager, envoy.mongo_proxy, envoy.ratelimit, envoy.redis_proxy, envoy.tcp_proxy
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.config_mux: envoy.config_mux.delta_grpc_mux_factory, envoy.config_mux.grpc_mux_factory, envoy.config_mux.new_grpc_mux_factory, envoy.config_mux.sotw_grpc_mux_factory
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.matching.common_inputs: envoy.matching.common_inputs.environment_variable
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.filters.http: envoy.bandwidth_limit, envoy.buffer, envoy.cors, envoy.csrf, envoy.ext_authz, envoy.ext_proc, envoy.fault, envoy.filters.http.adaptive_concurrency, envoy.filters.http.admission_control, envoy.filters.http.alternate_protocols_cache, envoy.filters.http.aws_lambda, envoy.filters.http.aws_request_signing, envoy.filters.http.bandwidth_limit, envoy.filters.http.buffer, envoy.filters.http.cache, envoy.filters.http.cdn_loop, envoy.filters.http.composite, envoy.filters.http.compressor, envoy.filters.http.connect_grpc_bridge, envoy.filters.http.cors, envoy.filters.http.csrf, envoy.filters.http.custom_response, envoy.filters.http.decompressor, envoy.filters.http.dynamic_forward_proxy, envoy.filters.http.ext_authz, envoy.filters.http.ext_proc, envoy.filters.http.fault, envoy.filters.http.file_system_buffer, envoy.filters.http.gcp_authn, envoy.filters.http.geoip, envoy.filters.http.grpc_field_extraction, envoy.filters.http.grpc_http1_bridge, envoy.filters.http.grpc_http1_reverse_bridge, envoy.filters.http.grpc_json_transcoder, envoy.filters.http.grpc_stats, envoy.filters.http.grpc_web, envoy.filters.http.header_mutation, envoy.filters.http.header_to_metadata, envoy.filters.http.health_check, envoy.filters.http.ip_tagging, envoy.filters.http.json_to_metadata, envoy.filters.http.jwt_authn, envoy.filters.http.local_ratelimit, envoy.filters.http.lua, envoy.filters.http.match_delegate, envoy.filters.http.oauth2, envoy.filters.http.on_demand, envoy.filters.http.original_src, envoy.filters.http.rate_limit_quota, envoy.filters.http.ratelimit, envoy.filters.http.rbac, envoy.filters.http.router, envoy.filters.http.set_filter_state, envoy.filters.http.set_metadata, envoy.filters.http.stateful_session, envoy.filters.http.tap, envoy.filters.http.wasm, envoy.geoip, envoy.grpc_http1_bridge, envoy.grpc_json_transcoder, envoy.grpc_web, envoy.health_check, envoy.ip_tagging, envoy.local_rate_limit, envoy.lua, envoy.rate_limit, envoy.router
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.common.key_value: envoy.key_value.file_based
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.connection_handler: envoy.connection_handler.default
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.matching.network.custom_matchers: envoy.matching.custom_matchers.trie_matcher
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.http.custom_response: envoy.extensions.http.custom_response.local_response_policy, envoy.extensions.http.custom_response.redirect_policy
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.quic.server.crypto_stream: envoy.quic.crypto_stream.server.quiche
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.route.early_data_policy: envoy.route.early_data_policy.default
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.listener_manager_impl: envoy.listener_manager_impl.default, envoy.listener_manager_impl.validation
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.thrift_proxy.protocols: auto, binary, binary/non-strict, compact, twitter
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.internal_redirect_predicates: envoy.internal_redirect_predicates.allow_listed_routes, envoy.internal_redirect_predicates.previous_routes, envoy.internal_redirect_predicates.safe_cross_scheme
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.matching.action: envoy.matching.actions.format_string, filter-chain-name
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.thrift_proxy.transports: auto, framed, header, unframed
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.rate_limit_descriptors: envoy.rate_limit_descriptors.expr
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.thrift_proxy.filters: envoy.filters.thrift.header_to_metadata, envoy.filters.thrift.payload_to_metadata, envoy.filters.thrift.rate_limit, envoy.filters.thrift.router
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.dubbo_proxy.serializers: dubbo.hessian2
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   filter_state.object: envoy.filters.listener.original_dst.local_ip, envoy.filters.listener.original_dst.remote_ip, envoy.network.application_protocols, envoy.network.transport_socket.original_dst_address, envoy.network.upstream_server_name, envoy.network.upstream_subject_alt_names, envoy.tcp_proxy.cluster, envoy.tcp_proxy.disable_tunneling, envoy.upstream.dynamic_host, envoy.upstream.dynamic_port
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.tracers: envoy.dynamic.ot, envoy.tracers.datadog, envoy.tracers.dynamic_ot, envoy.tracers.opencensus, envoy.tracers.opentelemetry, envoy.tracers.skywalking, envoy.tracers.xray, envoy.tracers.zipkin, envoy.zipkin
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.upstream_options: envoy.extensions.upstreams.http.v3.HttpProtocolOptions, envoy.extensions.upstreams.tcp.v3.TcpProtocolOptions, envoy.upstreams.http.http_protocol_options, envoy.upstreams.tcp.tcp_protocol_options
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.path.rewrite: envoy.path.rewrite.uri_template.uri_template_rewriter
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.quic.connection_id_generator: envoy.quic.deterministic_connection_id_generator
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.config.validators: envoy.config.validators.minimum_clusters, envoy.config.validators.minimum_clusters_validator
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.wasm.runtime: envoy.wasm.runtime.null, envoy.wasm.runtime.v8
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.http.early_header_mutation: envoy.http.early_header_mutation.header_mutation
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.stats_sinks: envoy.dog_statsd, envoy.graphite_statsd, envoy.metrics_service, envoy.open_telemetry_stat_sink, envoy.stat_sinks.dog_statsd, envoy.stat_sinks.graphite_statsd, envoy.stat_sinks.hystrix, envoy.stat_sinks.metrics_service, envoy.stat_sinks.open_telemetry, envoy.stat_sinks.statsd, envoy.stat_sinks.wasm, envoy.statsd
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.matching.http.input: envoy.matching.inputs.cel_data_input, envoy.matching.inputs.destination_ip, envoy.matching.inputs.destination_port, envoy.matching.inputs.direct_source_ip, envoy.matching.inputs.dns_san, envoy.matching.inputs.request_headers, envoy.matching.inputs.request_trailers, envoy.matching.inputs.response_headers, envoy.matching.inputs.response_trailers, envoy.matching.inputs.server_name, envoy.matching.inputs.source_ip, envoy.matching.inputs.source_port, envoy.matching.inputs.source_type, envoy.matching.inputs.status_code_class_input, envoy.matching.inputs.status_code_input, envoy.matching.inputs.subject, envoy.matching.inputs.uri_san, query_params
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.http.stateful_header_formatters: envoy.http.stateful_header_formatters.preserve_case, preserve_case
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.resolvers: envoy.ip
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.retry_priorities: envoy.retry_priorities.previous_priorities
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.guarddog_actions: envoy.watchdog.abort_action, envoy.watchdog.profile_action
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.request_id: envoy.request_id.uuid
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   quic.http_server_connection: quic.http_server_connection.default
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.compression.decompressor: envoy.compression.brotli.decompressor, envoy.compression.gzip.decompressor, envoy.compression.zstd.decompressor
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   network.connection.client: default, envoy_internal
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.config_subscription: envoy.config_subscription.ads, envoy.config_subscription.ads_collection, envoy.config_subscription.aggregated_grpc_collection, envoy.config_subscription.delta_grpc, envoy.config_subscription.delta_grpc_collection, envoy.config_subscription.filesystem, envoy.config_subscription.filesystem_collection, envoy.config_subscription.grpc, envoy.config_subscription.rest
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.udp_packet_writer: envoy.udp_packet_writer.default, envoy.udp_packet_writer.gso
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.load_balancing_policies: envoy.load_balancing_policies.cluster_provided, envoy.load_balancing_policies.least_request, envoy.load_balancing_policies.maglev, envoy.load_balancing_policies.random, envoy.load_balancing_policies.ring_hash, envoy.load_balancing_policies.round_robin, envoy.load_balancing_policies.subset
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.filters.udp_listener: envoy.filters.udp.dns_filter, envoy.filters.udp_listener.udp_proxy
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.transport_sockets.downstream: envoy.transport_sockets.alts, envoy.transport_sockets.quic, envoy.transport_sockets.raw_buffer, envoy.transport_sockets.starttls, envoy.transport_sockets.tap, envoy.transport_sockets.tcp_stats, envoy.transport_sockets.tls, raw_buffer, starttls, tls
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.http.stateful_session: envoy.http.stateful_session.cookie, envoy.http.stateful_session.header
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.retry_host_predicates: envoy.retry_host_predicates.omit_canary_hosts, envoy.retry_host_predicates.omit_host_metadata, envoy.retry_host_predicates.previous_hosts
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.tls.cert_validator: envoy.tls.cert_validator.default, envoy.tls.cert_validator.spiffe
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.access_loggers: envoy.access_loggers.file, envoy.access_loggers.http_grpc, envoy.access_loggers.open_telemetry, envoy.access_loggers.stderr, envoy.access_loggers.stdout, envoy.access_loggers.tcp_grpc, envoy.access_loggers.wasm, envoy.file_access_log, envoy.http_grpc_access_log, envoy.open_telemetry_access_log, envoy.stderr_access_log, envoy.stdout_access_log, envoy.tcp_grpc_access_log, envoy.wasm_access_log
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.upstreams: envoy.filters.connection_pools.tcp.generic
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.filters.http.upstream: envoy.buffer, envoy.filters.http.admission_control, envoy.filters.http.buffer, envoy.filters.http.header_mutation, envoy.filters.http.upstream_codec
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.dubbo_proxy.protocols: dubbo
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.matching.input_matchers: envoy.matching.matchers.cel_matcher, envoy.matching.matchers.consistent_hashing, envoy.matching.matchers.ip, envoy.matching.matchers.runtime_fraction
[2026-06-15 08:39:02.685][1][critical][main] [source/server/server.cc:133] error initializing config '  /etc/envoy/envoy.yaml': Unable to parse JSON as proto (INVALID_ARGUMENT: invalid JSON in  envoy.config.bootstrap.v3.Bootstrap @ overload_manager.resource_monitors[0].typed_config.<any>.max_heap_size_bytes: uint64, near 1:418 (offset   417): non-number characters in quoted  number): {"overload_manager":{"actions":[{"name":"envoy.overload_actions.shrink_heap","triggers":[{"threshold":{"value":"0.95"},"name":"envoy.resource_monitors.fixed_heap"}]},{"triggers":[{"name":"envoy.resource_monitors.fixed_heap","threshold":{"value":"0.98"}}],"name":"envoy.overload_actions.stop_accepting_requests"}],"resource_monitors":[{"name":"envoy.resource_monitors.fixed_heap","typed_config":{"max_heap_size_bytes":"2.147483648e+09","@type":"type.googleapis.com/envoy.extensions.resource_monitors.fixed_heap.v3.FixedHeapConfig"}}],"refresh_interval":"0.25s"},"static_resources":{"clusters":[{"health_checks":[{"http_health_check":{"path":"/readiness","expected_statuses":[{"start":200,"end":299}]},"interval":"10s","timeout":"1s","unhealthy_threshold":3,"healthy_threshold":2}],"outlier_detection":{"max_ejection_percent":50,"enforcing_consecutive_5xx":100,"base_ejection_time":"30s","consecutive_5xx":5,"interval":"10s"},"dns_lookup_family":"V4_ONLY","load_assignment":{"endpoints":[{"lb_endpoints":[{"endpoint":{"address":{"socket_address":{"port_value":8080,"address":"gateway-headless.etradie-system.svc.cluster.local"}}}}]}],"cluster_name":"gateway_cluster"},"type":"STRICT_DNS","connect_timeout":"5s","lb_policy":"ROUND_ROBIN","circuit_breakers":{"thresholds":[{"priority":"DEFAULT","max_pending_requests":1024,"max_retries":3,"max_connections":1024,"max_requests":1024}]},"name":"gateway_cluster"},{"connect_timeout":"5s","health_checks":[{"timeout":"1s","interval":"10s","healthy_threshold":2,"unhealthy_threshold":3,"http_health_check":{"path":"/readiness","expected_statuses":[{"start":200,"end":299}]}}],"lb_policy":"ROUND_ROBIN","outlier_detection":{"interval":"10s","consecutive_5xx":5,"max_ejection_percent":50,"enforcing_consecutive_5xx":100,"base_ejection_time":"30s"},"load_assignment":{"endpoints":[{"lb_endpoints":[{"endpoint":{"address":{"socket_address":{"port_value":8082,"address":"billing-service.etradie-system.svc.cluster.local"}}}}]}],"cluster_name":"billing_cluster"},"dns_lookup_family":"V4_ONLY","circuit_breakers":{"thresholds":[{"max_pending_requests":256,"priority":"DEFAULT","max_connections":256,"max_retries":0,"max_requests":256}]},"name":"billing_cluster","type":"STRICT_DNS"},{"typed_extension_protocol_options":{"envoy.extensions.upstreams.http.v3.HttpProtocolOptions":{"explicit_http_config":{"http2_protocol_options":{}},"@type":"type.googleapis.com/envoy.extensions.upstreams.http.v3.HttpProtocolOptions"}},"type":"STRICT_DNS","name":"otel_collector_cluster","load_assignment":{"endpoints":[{"lb_endpoints":[{"endpoint":{"address":{"socket_address":{"address":"otel-collector.etradie-observability.svc.cluster.local","port_value":4317}}}}]}],"cluster_name":"otel_collector_cluster"},"connect_timeout":"5s","lb_policy":"ROUND_ROBIN","dns_lookup_family":"V4_ONLY"}],"listeners":[{"filter_chains":[{"filters":[{"name":"envoy.filters.network.http_connection_manager","typed_config":{"tracing":{"random_sampling":{"value":100},"provider":{"name":"envoy.tracers.opentelemetry","typed_config":{"@type":"type.googleapis.com/envoy.config.trace.v3.OpenTelemetryConfig","grpc_service":{"envoy_grpc":{"cluster_name":"otel_collector_cluster"},"timeout":"0.250s"},"service_name":"etradie-envoy"}}},"stat_prefix":"ingress_http","@type":"type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager","max_request_headers_kb":64,"http_filters":[{"name":"envoy.filters.http.wasm","typed_config":{"config":{"name":"etradie_integration_filter","root_id":"etradie_root","vm_config":{"allow_precompiled":true,"runtime":"envoy.wasm.runtime.v8","code":{"local":{"filename":"/etc/envoy/wasm/integration-filter.wasm"}}}},"@type":"type.googleapis.com/envoy.extensions.filters.http.wasm.v3.Wasm"}},{"name":"envoy.filters.http.buffer","typed_config":{"@type":"type.googleapis.com/envoy.extensions.filters.http.buffer.v3.Buffer","max_request_bytes":"1.048576e+07"}},{"typed_config":{"status":{"code":429},"@type":"type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit","filter_enforced":{"default_value":{"numerator":0,"denominator":"HUNDRED"},"runtime_key":"local_rate_limit_enforced"},"stat_prefix":"http_local_rate_limiter","token_bucket":{"fill_interval":"1s","max_tokens":500,"tokens_per_fill":500},"response_headers_to_add":[{"header":{"key":"Retry-After","value":"1"},"append_action":"OVERWRITE_IF_EXISTS_OR_ADD"}],"filter_enabled":{"default_value":{"numerator":100,"denominator":"HUNDRED"},"runtime_key":"local_rate_limit_enabled"}},"name":"envoy.filters.http.local_ratelimit"},{"name":"envoy.filters.http.router","typed_config":{"@type":"type.googleapis.com/envoy.extensions.filters.http.router.v3.Router"}}],"route_config":{"name":"local_route","virtual_hosts":[{"routes":[{"match":{"prefix":"/webhooks/paddle"},"route":{"idle_timeout":"30s","timeout":"20s","retry_policy":{"num_retries":0,"retry_on":"","per_try_timeout":"15s"},"cluster":"billing_cluster"},"typed_per_filter_config":{"envoy.filters.http.local_ratelimit":{"filter_enabled":{"default_value":{"denominator":"HUNDRED","numerator":0}},"@type":"type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit","filter_enforced":{"default_value":{"numerator":0,"denominator":"HUNDRED"}},"stat_prefix":"http_local_rate_limiter_webhook","token_bucket":{"tokens_per_fill":500,"fill_interval":"1s","max_tokens":500}},"envoy.filters.http.buffer":{"buffer":{"max_request_bytes":262144},"@type":"type.googleapis.com/envoy.extensions.filters.http.buffer.v3.BufferPerRoute"}}},{"route":{"cluster":"billing_cluster","idle_timeout":"30s","retry_policy":{"num_retries":0,"retry_on":"","per_try_timeout":"15s"},"timeout":"20s"},"match":{"prefix":"/webhooks/lemonsqueezy"},"typed_per_filter_config":{"envoy.filters.http.buffer":{"buffer":{"max_request_bytes":262144},"@type":"type.googleapis.com/envoy.extensions.filters.http.buffer.v3.BufferPerRoute"},"envoy.filters.http.local_ratelimit":{"token_bucket":{"max_tokens":500,"fill_interval":"1s","tokens_per_fill":500},"filter_enforced":{"default_value":{"denominator":"HUNDRED","numerator":0}},"@type":"type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit","filter_enabled":{"default_value":{"numerator":0,"denominator":"HUNDRED"}},"stat_prefix":"http_local_rate_limiter_webhook"}}},{"match":{"prefix":"/"},"typed_per_filter_config":{"envoy.filters.http.buffer":{"buffer":{"max_request_bytes":"1.048576e+07"},"@type":"type.googleapis.com/envoy.extensions.filters.http.buffer.v3.BufferPerRoute"}},"route":{"retry_policy":{"retry_on":"connect-failure,refused-stream,unavailable,cancelled,retriable-status-codes","per_try_timeout":"10s","retriable_status_codes":[503],"num_retries":2},"timeout":"30s","cluster":"gateway_cluster","idle_timeout":"60s"}}],"name":"backend","domains":["*"],"response_headers_to_add":[{"header":{"value":"default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'","key":"Content-Security-Policy"},"append_action":"OVERWRITE_IF_EXISTS_OR_ADD"},{"append_action":"OVERWRITE_IF_EXISTS_OR_ADD","header":{"key":"X-Frame-Options","value":"DENY"}},{"header":{"key":"X-Content-Type-Options","value":"nosniff"},"append_action":"OVERWRITE_IF_EXISTS_OR_ADD"},{"header":{"key":"Referrer-Policy","value":"no-referrer"},"append_action":"OVERWRITE_IF_EXISTS_OR_ADD"}]}]},"use_remote_address":true,"access_log":[{"typed_config":{"path":"/dev/stdout","log_format":{"json_format":{"bytes_sent":"%BYTES_SENT%","timestamp":"%START_TIME%","response_code":"%RESPONSE_CODE%","response_flags":"%RESPONSE_FLAGS%","method":"%REQ(:METHOD)%","trace_id":"%REQ(X-TRACE-ID)%","user_agent":"%REQ(USER-AGENT)%","request_id":"%REQ(X-REQUEST-ID)%","authority":"%REQ(:AUTHORITY)%","upstream_cluster":"%UPSTREAM_CLUSTER%","upstream_service_time":"%RESP(X-ENVOY-UPSTREAM-SERVICE-TIME)%","bytes_received":"%BYTES_RECEIVED%","x_forwarded_for":"%REQ(X-FORWARDED-FOR)%","protocol":"%PROTOCOL%","upstream_host":"%UPSTREAM_HOST%","duration_ms":"%DURATION%","path":"%REQ(X-ENVOY-ORIGINAL-PATH?:PATH)%"}},"@type":"type.googleapis.com/envoy.extensions.access_loggers.file.v3.FileAccessLog"},"name":"envoy.access_loggers.file"}],"codec_type":"AUTO","xff_num_trusted_hops":1}}]}],"name":"http_listener","address":{"socket_address":{"port_value":8080,"address":"0.0.0.0"}}}]},"admin":{"address":{"socket_address":{"port_value":9901,"address":"0.0.0.0"}}},"layered_runtime":{"layers":[{"static_layer":{"overload":{"global_downstream_max_connections":50000}},"name":"static_layer"}]}}
[2026-06-15 08:39:02.685][1][info][main] [source/server/server.cc:997] exiting
Unable to parse JSON as proto (INVALID_ARGUMENT: invalid JSON in  envoy.config.bootstrap.v3.Bootstrap @ overload_manager.resource_monitors[0].typed_config.<any>.max_heap_size_bytes: uint64, near 1:418 (offset   417): non-number characters in quoted  number): {"overload_manager":{"actions":[{"name":"envoy.overload_actions.shrink_heap","triggers":[{"threshold":{"value":"0.95"},"name":"envoy.resource_monitors.fixed_heap"}]},{"triggers":[{"name":"envoy.resource_monitors.fixed_heap","threshold":{"value":"0.98"}}],"name":"envoy.overload_actions.stop_accepting_requests"}],"resource_monitors":[{"name":"envoy.resource_monitors.fixed_heap","typed_config":{"max_heap_size_bytes":"2.147483648e+09","@type":"type.googleapis.com/envoy.extensions.resource_monitors.fixed_heap.v3.FixedHeapConfig"}}],"refresh_interval":"0.25s"},"static_resources":{"clusters":[{"health_checks":[{"http_health_check":{"path":"/readiness","expected_statuses":[{"start":200,"end":299}]},"interval":"10s","timeout":"1s","unhealthy_threshold":3,"healthy_threshold":2}],"outlier_detection":{"max_ejection_percent":50,"enforcing_consecutive_5xx":100,"base_ejection_time":"30s","consecutive_5xx":5,"interval":"10s"},"dns_lookup_family":"V4_ONLY","load_assignment":{"endpoints":[{"lb_endpoints":[{"endpoint":{"address":{"socket_address":{"port_value":8080,"address":"gateway-headless.etradie-system.svc.cluster.local"}}}}]}],"cluster_name":"gateway_cluster"},"type":"STRICT_DNS","connect_timeout":"5s","lb_policy":"ROUND_ROBIN","circuit_breakers":{"thresholds":[{"priority":"DEFAULT","max_pending_requests":1024,"max_retries":3,"max_connections":1024,"max_requests":1024}]},"name":"gateway_cluster"},{"connect_timeout":"5s","health_checks":[{"timeout":"1s","interval":"10s","healthy_threshold":2,"unhealthy_threshold":3,"http_health_check":{"path":"/readiness","expected_statuses":[{"start":200,"end":299}]}}],"lb_policy":"ROUND_ROBIN","outlier_detection":{"interval":"10s","consecutive_5xx":5,"max_ejection_percent":50,"enforcing_consecutive_5xx":100,"base_ejection_time":"30s"},"load_assignment":{"endpoints":[{"lb_endpoints":[{"endpoint":{"address":{"socket_address":{"port_value":8082,"address":"billing-service.etradie-system.svc.cluster.local"}}}}]}],"cluster_name":"billing_cluster"},"dns_lookup_family":"V4_ONLY","circuit_breakers":{"thresholds":[{"max_pending_requests":256,"priority":"DEFAULT","max_connections":256,"max_retries":0,"max_requests":256}]},"name":"billing_cluster","type":"STRICT_DNS"},{"typed_extension_protocol_options":{"envoy.extensions.upstreams.http.v3.HttpProtocolOptions":{"explicit_http_config":{"http2_protocol_options":{}},"@type":"type.googleapis.com/envoy.extensions.upstreams.http.v3.HttpProtocolOptions"}},"type":"STRICT_DNS","name":"otel_collector_cluster","load_assignment":{"endpoints":[{"lb_endpoints":[{"endpoint":{"address":{"socket_address":{"address":"otel-collector.etradie-observability.svc.cluster.local","port_value":4317}}}}]}],"cluster_name":"otel_collector_cluster"},"connect_timeout":"5s","lb_policy":"ROUND_ROBIN","dns_lookup_family":"V4_ONLY"}],"listeners":[{"filter_chains":[{"filters":[{"name":"envoy.filters.network.http_connection_manager","typed_config":{"tracing":{"random_sampling":{"value":100},"provider":{"name":"envoy.tracers.opentelemetry","typed_config":{"@type":"type.googleapis.com/envoy.config.trace.v3.OpenTelemetryConfig","grpc_service":{"envoy_grpc":{"cluster_name":"otel_collector_cluster"},"timeout":"0.250s"},"service_name":"etradie-envoy"}}},"stat_prefix":"ingress_http","@type":"type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager","max_request_headers_kb":64,"http_filters":[{"name":"envoy.filters.http.wasm","typed_config":{"config":{"name":"etradie_integration_filter","root_id":"etradie_root","vm_config":{"allow_precompiled":true,"runtime":"envoy.wasm.runtime.v8","code":{"local":{"filename":"/etc/envoy/wasm/integration-filter.wasm"}}}},"@type":"type.googleapis.com/envoy.extensions.filters.http.wasm.v3.Wasm"}},{"name":"envoy.filters.http.buffer","typed_config":{"@type":"type.googleapis.com/envoy.extensions.filters.http.buffer.v3.Buffer","max_request_bytes":"1.048576e+07"}},{"typed_config":{"status":{"code":429},"@type":"type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit","filter_enforced":{"default_value":{"numerator":0,"denominator":"HUNDRED"},"runtime_key":"local_rate_limit_enforced"},"stat_prefix":"http_local_rate_limiter","token_bucket":{"fill_interval":"1s","max_tokens":500,"tokens_per_fill":500},"response_headers_to_add":[{"header":{"key":"Retry-After","value":"1"},"append_action":"OVERWRITE_IF_EXISTS_OR_ADD"}],"filter_enabled":{"default_value":{"numerator":100,"denominator":"HUNDRED"},"runtime_key":"local_rate_limit_enabled"}},"name":"envoy.filters.http.local_ratelimit"},{"name":"envoy.filters.http.router","typed_config":{"@type":"type.googleapis.com/envoy.extensions.filters.http.router.v3.Router"}}],"route_config":{"name":"local_route","virtual_hosts":[{"routes":[{"match":{"prefix":"/webhooks/paddle"},"route":{"idle_timeout":"30s","timeout":"20s","retry_policy":{"num_retries":0,"retry_on":"","per_try_timeout":"15s"},"cluster":"billing_cluster"},"typed_per_filter_config":{"envoy.filters.http.local_ratelimit":{"filter_enabled":{"default_value":{"denominator":"HUNDRED","numerator":0}},"@type":"type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit","filter_enforced":{"default_value":{"numerator":0,"denominator":"HUNDRED"}},"stat_prefix":"http_local_rate_limiter_webhook","token_bucket":{"tokens_per_fill":500,"fill_interval":"1s","max_tokens":500}},"envoy.filters.http.buffer":{"buffer":{"max_request_bytes":262144},"@type":"type.googleapis.com/envoy.extensions.filters.http.buffer.v3.BufferPerRoute"}}},{"route":{"cluster":"billing_cluster","idle_timeout":"30s","retry_policy":{"num_retries":0,"retry_on":"","per_try_timeout":"15s"},"timeout":"20s"},"match":{"prefix":"/webhooks/lemonsqueezy"},"typed_per_filter_config":{"envoy.filters.http.buffer":{"buffer":{"max_request_bytes":262144},"@type":"type.googleapis.com/envoy.extensions.filters.http.buffer.v3.BufferPerRoute"},"envoy.filters.http.local_ratelimit":{"token_bucket":{"max_tokens":500,"fill_interval":"1s","tokens_per_fill":500},"filter_enforced":{"default_value":{"denominator":"HUNDRED","numerator":0}},"@type":"type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit","filter_enabled":{"default_value":{"numerator":0,"denominator":"HUNDRED"}},"stat_prefix":"http_local_rate_limiter_webhook"}}},{"match":{"prefix":"/"},"typed_per_filter_config":{"envoy.filters.http.buffer":{"buffer":{"max_request_bytes":"1.048576e+07"},"@type":"type.googleapis.com/envoy.extensions.filters.http.buffer.v3.BufferPerRoute"}},"route":{"retry_policy":{"retry_on":"connect-failure,refused-stream,unavailable,cancelled,retriable-status-codes","per_try_timeout":"10s","retriable_status_codes":[503],"num_retries":2},"timeout":"30s","cluster":"gateway_cluster","idle_timeout":"60s"}}],"name":"backend","domains":["*"],"response_headers_to_add":[{"header":{"value":"default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'","key":"Content-Security-Policy"},"append_action":"OVERWRITE_IF_EXISTS_OR_ADD"},{"append_action":"OVERWRITE_IF_EXISTS_OR_ADD","header":{"key":"X-Frame-Options","value":"DENY"}},{"header":{"key":"X-Content-Type-Options","value":"nosniff"},"append_action":"OVERWRITE_IF_EXISTS_OR_ADD"},{"header":{"key":"Referrer-Policy","value":"no-referrer"},"append_action":"OVERWRITE_IF_EXISTS_OR_ADD"}]}]},"use_remote_address":true,"access_log":[{"typed_config":{"path":"/dev/stdout","log_format":{"json_format":{"bytes_sent":"%BYTES_SENT%","timestamp":"%START_TIME%","response_code":"%RESPONSE_CODE%","response_flags":"%RESPONSE_FLAGS%","method":"%REQ(:METHOD)%","trace_id":"%REQ(X-TRACE-ID)%","user_agent":"%REQ(USER-AGENT)%","request_id":"%REQ(X-REQUEST-ID)%","authority":"%REQ(:AUTHORITY)%","upstream_cluster":"%UPSTREAM_CLUSTER%","upstream_service_time":"%RESP(X-ENVOY-UPSTREAM-SERVICE-TIME)%","bytes_received":"%BYTES_RECEIVED%","x_forwarded_for":"%REQ(X-FORWARDED-FOR)%","protocol":"%PROTOCOL%","upstream_host":"%UPSTREAM_HOST%","duration_ms":"%DURATION%","path":"%REQ(X-ENVOY-ORIGINAL-PATH?:PATH)%"}},"@type":"type.googleapis.com/envoy.extensions.access_loggers.file.v3.FileAccessLog"},"name":"envoy.access_loggers.file"}],"codec_type":"AUTO","xff_num_trusted_hops":1}}]}],"name":"http_listener","address":{"socket_address":{"port_value":8080,"address":"0.0.0.0"}}}]},"admin":{"address":{"socket_address":{"port_value":9901,"address":"0.0.0.0"}}},"layered_runtime":{"layers":[{"static_layer":{"overload":{"global_downstream_max_connections":50000}},"name":"static_layer"}]}}
---
[2026-06-15 08:39:02.674][1][info][main] [source/server/server.cc:413] initializing epoch 0 (base id=0, hot restart version=11.104)
[2026-06-15 08:39:02.674][1][info][main] [source/server/server.cc:415] statically linked extensions:
[2026-06-15 08:39:02.676][1][info][main] [source/server/server.cc:417]   envoy.http.cache: envoy.extensions.http.cache.file_system_http_cache, envoy.extensions.http.cache.simple
[2026-06-15 08:39:02.676][1][info][main] [source/server/server.cc:417]   envoy.http.original_ip_detection: envoy.http.original_ip_detection.custom_header, envoy.http.original_ip_detection.xff
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.health_check.event_sinks: envoy.health_check.event_sink.file
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.matching.network.input: envoy.matching.inputs.application_protocol, envoy.matching.inputs.destination_ip, envoy.matching.inputs.destination_port, envoy.matching.inputs.direct_source_ip, envoy.matching.inputs.dns_san, envoy.matching.inputs.filter_state, envoy.matching.inputs.server_name, envoy.matching.inputs.source_ip, envoy.matching.inputs.source_port, envoy.matching.inputs.source_type, envoy.matching.inputs.subject, envoy.matching.inputs.transport_protocol, envoy.matching.inputs.uri_san
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.resource_monitors: envoy.resource_monitors.fixed_heap, envoy.resource_monitors.injected_resource
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.formatter: envoy.formatter.cel, envoy.formatter.metadata, envoy.formatter.req_without_query
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.grpc_credentials: envoy.grpc_credentials.aws_iam, envoy.grpc_credentials.default, envoy.grpc_credentials.file_based_metadata
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.matching.http.custom_matchers: envoy.matching.custom_matchers.trie_matcher
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.upstream.local_address_selector: envoy.upstream.local_address_selector.default_local_address_selector
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.transport_sockets.upstream: envoy.transport_sockets.alts, envoy.transport_sockets.http_11_proxy, envoy.transport_sockets.internal_upstream, envoy.transport_sockets.quic, envoy.transport_sockets.raw_buffer, envoy.transport_sockets.starttls, envoy.transport_sockets.tap, envoy.transport_sockets.tcp_stats, envoy.transport_sockets.tls, envoy.transport_sockets.upstream_proxy_protocol, raw_buffer, starttls, tls
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.compression.compressor: envoy.compression.brotli.compressor, envoy.compression.gzip.compressor, envoy.compression.zstd.compressor
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.geoip_providers: envoy.geoip_providers.maxmind
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.regex_engines: envoy.regex_engines.google_re2
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.quic.server_preferred_address: quic.server_preferred_address.fixed
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.filters.udp.session: envoy.filters.udp.session.dynamic_forward_proxy, envoy.filters.udp.session.http_capsule
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.network.dns_resolver: envoy.network.dns_resolver.cares, envoy.network.dns_resolver.getaddrinfo
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.path.match: envoy.path.match.uri_template.uri_template_matcher
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.access_loggers.extension_filters: envoy.access_loggers.extension_filters.cel
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.filters.listener: envoy.filters.listener.http_inspector, envoy.filters.listener.local_ratelimit, envoy.filters.listener.original_dst, envoy.filters.listener.original_src, envoy.filters.listener.proxy_protocol, envoy.filters.listener.tls_inspector, envoy.listener.http_inspector, envoy.listener.original_dst, envoy.listener.original_src, envoy.listener.proxy_protocol, envoy.listener.tls_inspector
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.health_checkers: envoy.health_checkers.grpc, envoy.health_checkers.http, envoy.health_checkers.redis, envoy.health_checkers.tcp, envoy.health_checkers.thrift
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.clusters: envoy.cluster.eds, envoy.cluster.logical_dns, envoy.cluster.original_dst, envoy.cluster.static, envoy.cluster.strict_dns, envoy.clusters.aggregate, envoy.clusters.dynamic_forward_proxy, envoy.clusters.redis
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.rbac.matchers: envoy.rbac.matchers.upstream_ip_port
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.http.header_validators: envoy.http.header_validators.envoy_default
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.dubbo_proxy.filters: envoy.filters.dubbo.router
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.bootstrap: envoy.bootstrap.internal_listener, envoy.bootstrap.wasm, envoy.extensions.network.socket_interface.default_socket_interface
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.quic.proof_source: envoy.quic.proof_source.filter_chain
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.filters.network: envoy.echo, envoy.ext_authz, envoy.filters.network.connection_limit, envoy.filters.network.direct_response, envoy.filters.network.dubbo_proxy, envoy.filters.network.echo, envoy.filters.network.ext_authz, envoy.filters.network.http_connection_manager, envoy.filters.network.local_ratelimit, envoy.filters.network.mongo_proxy, envoy.filters.network.ratelimit, envoy.filters.network.rbac, envoy.filters.network.redis_proxy, envoy.filters.network.set_filter_state, envoy.filters.network.sni_cluster, envoy.filters.network.sni_dynamic_forward_proxy, envoy.filters.network.tcp_proxy, envoy.filters.network.thrift_proxy, envoy.filters.network.wasm, envoy.filters.network.zookeeper_proxy, envoy.http_connection_manager, envoy.mongo_proxy, envoy.ratelimit, envoy.redis_proxy, envoy.tcp_proxy
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.config_mux: envoy.config_mux.delta_grpc_mux_factory, envoy.config_mux.grpc_mux_factory, envoy.config_mux.new_grpc_mux_factory, envoy.config_mux.sotw_grpc_mux_factory
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.matching.common_inputs: envoy.matching.common_inputs.environment_variable
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.filters.http: envoy.bandwidth_limit, envoy.buffer, envoy.cors, envoy.csrf, envoy.ext_authz, envoy.ext_proc, envoy.fault, envoy.filters.http.adaptive_concurrency, envoy.filters.http.admission_control, envoy.filters.http.alternate_protocols_cache, envoy.filters.http.aws_lambda, envoy.filters.http.aws_request_signing, envoy.filters.http.bandwidth_limit, envoy.filters.http.buffer, envoy.filters.http.cache, envoy.filters.http.cdn_loop, envoy.filters.http.composite, envoy.filters.http.compressor, envoy.filters.http.connect_grpc_bridge, envoy.filters.http.cors, envoy.filters.http.csrf, envoy.filters.http.custom_response, envoy.filters.http.decompressor, envoy.filters.http.dynamic_forward_proxy, envoy.filters.http.ext_authz, envoy.filters.http.ext_proc, envoy.filters.http.fault, envoy.filters.http.file_system_buffer, envoy.filters.http.gcp_authn, envoy.filters.http.geoip, envoy.filters.http.grpc_field_extraction, envoy.filters.http.grpc_http1_bridge, envoy.filters.http.grpc_http1_reverse_bridge, envoy.filters.http.grpc_json_transcoder, envoy.filters.http.grpc_stats, envoy.filters.http.grpc_web, envoy.filters.http.header_mutation, envoy.filters.http.header_to_metadata, envoy.filters.http.health_check, envoy.filters.http.ip_tagging, envoy.filters.http.json_to_metadata, envoy.filters.http.jwt_authn, envoy.filters.http.local_ratelimit, envoy.filters.http.lua, envoy.filters.http.match_delegate, envoy.filters.http.oauth2, envoy.filters.http.on_demand, envoy.filters.http.original_src, envoy.filters.http.rate_limit_quota, envoy.filters.http.ratelimit, envoy.filters.http.rbac, envoy.filters.http.router, envoy.filters.http.set_filter_state, envoy.filters.http.set_metadata, envoy.filters.http.stateful_session, envoy.filters.http.tap, envoy.filters.http.wasm, envoy.geoip, envoy.grpc_http1_bridge, envoy.grpc_json_transcoder, envoy.grpc_web, envoy.health_check, envoy.ip_tagging, envoy.local_rate_limit, envoy.lua, envoy.rate_limit, envoy.router
[2026-06-15 08:39:02.677][1][info][main] [source/server/server.cc:417]   envoy.common.key_value: envoy.key_value.file_based
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.connection_handler: envoy.connection_handler.default
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.matching.network.custom_matchers: envoy.matching.custom_matchers.trie_matcher
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.http.custom_response: envoy.extensions.http.custom_response.local_response_policy, envoy.extensions.http.custom_response.redirect_policy
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.quic.server.crypto_stream: envoy.quic.crypto_stream.server.quiche
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.route.early_data_policy: envoy.route.early_data_policy.default
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.listener_manager_impl: envoy.listener_manager_impl.default, envoy.listener_manager_impl.validation
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.thrift_proxy.protocols: auto, binary, binary/non-strict, compact, twitter
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.internal_redirect_predicates: envoy.internal_redirect_predicates.allow_listed_routes, envoy.internal_redirect_predicates.previous_routes, envoy.internal_redirect_predicates.safe_cross_scheme
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.matching.action: envoy.matching.actions.format_string, filter-chain-name
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.thrift_proxy.transports: auto, framed, header, unframed
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.rate_limit_descriptors: envoy.rate_limit_descriptors.expr
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.thrift_proxy.filters: envoy.filters.thrift.header_to_metadata, envoy.filters.thrift.payload_to_metadata, envoy.filters.thrift.rate_limit, envoy.filters.thrift.router
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.dubbo_proxy.serializers: dubbo.hessian2
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   filter_state.object: envoy.filters.listener.original_dst.local_ip, envoy.filters.listener.original_dst.remote_ip, envoy.network.application_protocols, envoy.network.transport_socket.original_dst_address, envoy.network.upstream_server_name, envoy.network.upstream_subject_alt_names, envoy.tcp_proxy.cluster, envoy.tcp_proxy.disable_tunneling, envoy.upstream.dynamic_host, envoy.upstream.dynamic_port
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.tracers: envoy.dynamic.ot, envoy.tracers.datadog, envoy.tracers.dynamic_ot, envoy.tracers.opencensus, envoy.tracers.opentelemetry, envoy.tracers.skywalking, envoy.tracers.xray, envoy.tracers.zipkin, envoy.zipkin
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.upstream_options: envoy.extensions.upstreams.http.v3.HttpProtocolOptions, envoy.extensions.upstreams.tcp.v3.TcpProtocolOptions, envoy.upstreams.http.http_protocol_options, envoy.upstreams.tcp.tcp_protocol_options
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.path.rewrite: envoy.path.rewrite.uri_template.uri_template_rewriter
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.quic.connection_id_generator: envoy.quic.deterministic_connection_id_generator
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.config.validators: envoy.config.validators.minimum_clusters, envoy.config.validators.minimum_clusters_validator
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.wasm.runtime: envoy.wasm.runtime.null, envoy.wasm.runtime.v8
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.http.early_header_mutation: envoy.http.early_header_mutation.header_mutation
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.stats_sinks: envoy.dog_statsd, envoy.graphite_statsd, envoy.metrics_service, envoy.open_telemetry_stat_sink, envoy.stat_sinks.dog_statsd, envoy.stat_sinks.graphite_statsd, envoy.stat_sinks.hystrix, envoy.stat_sinks.metrics_service, envoy.stat_sinks.open_telemetry, envoy.stat_sinks.statsd, envoy.stat_sinks.wasm, envoy.statsd
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.matching.http.input: envoy.matching.inputs.cel_data_input, envoy.matching.inputs.destination_ip, envoy.matching.inputs.destination_port, envoy.matching.inputs.direct_source_ip, envoy.matching.inputs.dns_san, envoy.matching.inputs.request_headers, envoy.matching.inputs.request_trailers, envoy.matching.inputs.response_headers, envoy.matching.inputs.response_trailers, envoy.matching.inputs.server_name, envoy.matching.inputs.source_ip, envoy.matching.inputs.source_port, envoy.matching.inputs.source_type, envoy.matching.inputs.status_code_class_input, envoy.matching.inputs.status_code_input, envoy.matching.inputs.subject, envoy.matching.inputs.uri_san, query_params
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.http.stateful_header_formatters: envoy.http.stateful_header_formatters.preserve_case, preserve_case
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.resolvers: envoy.ip
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.retry_priorities: envoy.retry_priorities.previous_priorities
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.guarddog_actions: envoy.watchdog.abort_action, envoy.watchdog.profile_action
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.request_id: envoy.request_id.uuid
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   quic.http_server_connection: quic.http_server_connection.default
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.compression.decompressor: envoy.compression.brotli.decompressor, envoy.compression.gzip.decompressor, envoy.compression.zstd.decompressor
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   network.connection.client: default, envoy_internal
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.config_subscription: envoy.config_subscription.ads, envoy.config_subscription.ads_collection, envoy.config_subscription.aggregated_grpc_collection, envoy.config_subscription.delta_grpc, envoy.config_subscription.delta_grpc_collection, envoy.config_subscription.filesystem, envoy.config_subscription.filesystem_collection, envoy.config_subscription.grpc, envoy.config_subscription.rest
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.udp_packet_writer: envoy.udp_packet_writer.default, envoy.udp_packet_writer.gso
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.load_balancing_policies: envoy.load_balancing_policies.cluster_provided, envoy.load_balancing_policies.least_request, envoy.load_balancing_policies.maglev, envoy.load_balancing_policies.random, envoy.load_balancing_policies.ring_hash, envoy.load_balancing_policies.round_robin, envoy.load_balancing_policies.subset
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.filters.udp_listener: envoy.filters.udp.dns_filter, envoy.filters.udp_listener.udp_proxy
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.transport_sockets.downstream: envoy.transport_sockets.alts, envoy.transport_sockets.quic, envoy.transport_sockets.raw_buffer, envoy.transport_sockets.starttls, envoy.transport_sockets.tap, envoy.transport_sockets.tcp_stats, envoy.transport_sockets.tls, raw_buffer, starttls, tls
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.http.stateful_session: envoy.http.stateful_session.cookie, envoy.http.stateful_session.header
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.retry_host_predicates: envoy.retry_host_predicates.omit_canary_hosts, envoy.retry_host_predicates.omit_host_metadata, envoy.retry_host_predicates.previous_hosts
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.tls.cert_validator: envoy.tls.cert_validator.default, envoy.tls.cert_validator.spiffe
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.access_loggers: envoy.access_loggers.file, envoy.access_loggers.http_grpc, envoy.access_loggers.open_telemetry, envoy.access_loggers.stderr, envoy.access_loggers.stdout, envoy.access_loggers.tcp_grpc, envoy.access_loggers.wasm, envoy.file_access_log, envoy.http_grpc_access_log, envoy.open_telemetry_access_log, envoy.stderr_access_log, envoy.stdout_access_log, envoy.tcp_grpc_access_log, envoy.wasm_access_log
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.upstreams: envoy.filters.connection_pools.tcp.generic
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.filters.http.upstream: envoy.buffer, envoy.filters.http.admission_control, envoy.filters.http.buffer, envoy.filters.http.header_mutation, envoy.filters.http.upstream_codec
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.dubbo_proxy.protocols: dubbo
[2026-06-15 08:39:02.678][1][info][main] [source/server/server.cc:417]   envoy.matching.input_matchers: envoy.matching.matchers.cel_matcher, envoy.matching.matchers.consistent_hashing, envoy.matching.matchers.ip, envoy.matching.matchers.runtime_fraction
[2026-06-15 08:39:02.685][1][critical][main] [source/server/server.cc:133] error initializing config '  /etc/envoy/envoy.yaml': Unable to parse JSON as proto (INVALID_ARGUMENT: invalid JSON in  envoy.config.bootstrap.v3.Bootstrap @ overload_manager.resource_monitors[0].typed_config.<any>.max_heap_size_bytes: uint64, near 1:418 (offset   417): non-number characters in quoted  number): {"overload_manager":{"actions":[{"name":"envoy.overload_actions.shrink_heap","triggers":[{"threshold":{"value":"0.95"},"name":"envoy.resource_monitors.fixed_heap"}]},{"triggers":[{"name":"envoy.resource_monitors.fixed_heap","threshold":{"value":"0.98"}}],"name":"envoy.overload_actions.stop_accepting_requests"}],"resource_monitors":[{"name":"envoy.resource_monitors.fixed_heap","typed_config":{"max_heap_size_bytes":"2.147483648e+09","@type":"type.googleapis.com/envoy.extensions.resource_monitors.fixed_heap.v3.FixedHeapConfig"}}],"refresh_interval":"0.25s"},"static_resources":{"clusters":[{"health_checks":[{"http_health_check":{"path":"/readiness","expected_statuses":[{"start":200,"end":299}]},"interval":"10s","timeout":"1s","unhealthy_threshold":3,"healthy_threshold":2}],"outlier_detection":{"max_ejection_percent":50,"enforcing_consecutive_5xx":100,"base_ejection_time":"30s","consecutive_5xx":5,"interval":"10s"},"dns_lookup_family":"V4_ONLY","load_assignment":{"endpoints":[{"lb_endpoints":[{"endpoint":{"address":{"socket_address":{"port_value":8080,"address":"gateway-headless.etradie-system.svc.cluster.local"}}}}]}],"cluster_name":"gateway_cluster"},"type":"STRICT_DNS","connect_timeout":"5s","lb_policy":"ROUND_ROBIN","circuit_breakers":{"thresholds":[{"priority":"DEFAULT","max_pending_requests":1024,"max_retries":3,"max_connections":1024,"max_requests":1024}]},"name":"gateway_cluster"},{"connect_timeout":"5s","health_checks":[{"timeout":"1s","interval":"10s","healthy_threshold":2,"unhealthy_threshold":3,"http_health_check":{"path":"/readiness","expected_statuses":[{"start":200,"end":299}]}}],"lb_policy":"ROUND_ROBIN","outlier_detection":{"interval":"10s","consecutive_5xx":5,"max_ejection_percent":50,"enforcing_consecutive_5xx":100,"base_ejection_time":"30s"},"load_assignment":{"endpoints":[{"lb_endpoints":[{"endpoint":{"address":{"socket_address":{"port_value":8082,"address":"billing-service.etradie-system.svc.cluster.local"}}}}]}],"cluster_name":"billing_cluster"},"dns_lookup_family":"V4_ONLY","circuit_breakers":{"thresholds":[{"max_pending_requests":256,"priority":"DEFAULT","max_connections":256,"max_retries":0,"max_requests":256}]},"name":"billing_cluster","type":"STRICT_DNS"},{"typed_extension_protocol_options":{"envoy.extensions.upstreams.http.v3.HttpProtocolOptions":{"explicit_http_config":{"http2_protocol_options":{}},"@type":"type.googleapis.com/envoy.extensions.upstreams.http.v3.HttpProtocolOptions"}},"type":"STRICT_DNS","name":"otel_collector_cluster","load_assignment":{"endpoints":[{"lb_endpoints":[{"endpoint":{"address":{"socket_address":{"address":"otel-collector.etradie-observability.svc.cluster.local","port_value":4317}}}}]}],"cluster_name":"otel_collector_cluster"},"connect_timeout":"5s","lb_policy":"ROUND_ROBIN","dns_lookup_family":"V4_ONLY"}],"listeners":[{"filter_chains":[{"filters":[{"name":"envoy.filters.network.http_connection_manager","typed_config":{"tracing":{"random_sampling":{"value":100},"provider":{"name":"envoy.tracers.opentelemetry","typed_config":{"@type":"type.googleapis.com/envoy.config.trace.v3.OpenTelemetryConfig","grpc_service":{"envoy_grpc":{"cluster_name":"otel_collector_cluster"},"timeout":"0.250s"},"service_name":"etradie-envoy"}}},"stat_prefix":"ingress_http","@type":"type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager","max_request_headers_kb":64,"http_filters":[{"name":"envoy.filters.http.wasm","typed_config":{"config":{"name":"etradie_integration_filter","root_id":"etradie_root","vm_config":{"allow_precompiled":true,"runtime":"envoy.wasm.runtime.v8","code":{"local":{"filename":"/etc/envoy/wasm/integration-filter.wasm"}}}},"@type":"type.googleapis.com/envoy.extensions.filters.http.wasm.v3.Wasm"}},{"name":"envoy.filters.http.buffer","typed_config":{"@type":"type.googleapis.com/envoy.extensions.filters.http.buffer.v3.Buffer","max_request_bytes":"1.048576e+07"}},{"typed_config":{"status":{"code":429},"@type":"type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit","filter_enforced":{"default_value":{"numerator":0,"denominator":"HUNDRED"},"runtime_key":"local_rate_limit_enforced"},"stat_prefix":"http_local_rate_limiter","token_bucket":{"fill_interval":"1s","max_tokens":500,"tokens_per_fill":500},"response_headers_to_add":[{"header":{"key":"Retry-After","value":"1"},"append_action":"OVERWRITE_IF_EXISTS_OR_ADD"}],"filter_enabled":{"default_value":{"numerator":100,"denominator":"HUNDRED"},"runtime_key":"local_rate_limit_enabled"}},"name":"envoy.filters.http.local_ratelimit"},{"name":"envoy.filters.http.router","typed_config":{"@type":"type.googleapis.com/envoy.extensions.filters.http.router.v3.Router"}}],"route_config":{"name":"local_route","virtual_hosts":[{"routes":[{"match":{"prefix":"/webhooks/paddle"},"route":{"idle_timeout":"30s","timeout":"20s","retry_policy":{"num_retries":0,"retry_on":"","per_try_timeout":"15s"},"cluster":"billing_cluster"},"typed_per_filter_config":{"envoy.filters.http.local_ratelimit":{"filter_enabled":{"default_value":{"denominator":"HUNDRED","numerator":0}},"@type":"type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit","filter_enforced":{"default_value":{"numerator":0,"denominator":"HUNDRED"}},"stat_prefix":"http_local_rate_limiter_webhook","token_bucket":{"tokens_per_fill":500,"fill_interval":"1s","max_tokens":500}},"envoy.filters.http.buffer":{"buffer":{"max_request_bytes":262144},"@type":"type.googleapis.com/envoy.extensions.filters.http.buffer.v3.BufferPerRoute"}}},{"route":{"cluster":"billing_cluster","idle_timeout":"30s","retry_policy":{"num_retries":0,"retry_on":"","per_try_timeout":"15s"},"timeout":"20s"},"match":{"prefix":"/webhooks/lemonsqueezy"},"typed_per_filter_config":{"envoy.filters.http.buffer":{"buffer":{"max_request_bytes":262144},"@type":"type.googleapis.com/envoy.extensions.filters.http.buffer.v3.BufferPerRoute"},"envoy.filters.http.local_ratelimit":{"token_bucket":{"max_tokens":500,"fill_interval":"1s","tokens_per_fill":500},"filter_enforced":{"default_value":{"denominator":"HUNDRED","numerator":0}},"@type":"type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit","filter_enabled":{"default_value":{"numerator":0,"denominator":"HUNDRED"}},"stat_prefix":"http_local_rate_limiter_webhook"}}},{"match":{"prefix":"/"},"typed_per_filter_config":{"envoy.filters.http.buffer":{"buffer":{"max_request_bytes":"1.048576e+07"},"@type":"type.googleapis.com/envoy.extensions.filters.http.buffer.v3.BufferPerRoute"}},"route":{"retry_policy":{"retry_on":"connect-failure,refused-stream,unavailable,cancelled,retriable-status-codes","per_try_timeout":"10s","retriable_status_codes":[503],"num_retries":2},"timeout":"30s","cluster":"gateway_cluster","idle_timeout":"60s"}}],"name":"backend","domains":["*"],"response_headers_to_add":[{"header":{"value":"default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'","key":"Content-Security-Policy"},"append_action":"OVERWRITE_IF_EXISTS_OR_ADD"},{"append_action":"OVERWRITE_IF_EXISTS_OR_ADD","header":{"key":"X-Frame-Options","value":"DENY"}},{"header":{"key":"X-Content-Type-Options","value":"nosniff"},"append_action":"OVERWRITE_IF_EXISTS_OR_ADD"},{"header":{"key":"Referrer-Policy","value":"no-referrer"},"append_action":"OVERWRITE_IF_EXISTS_OR_ADD"}]}]},"use_remote_address":true,"access_log":[{"typed_config":{"path":"/dev/stdout","log_format":{"json_format":{"bytes_sent":"%BYTES_SENT%","timestamp":"%START_TIME%","response_code":"%RESPONSE_CODE%","response_flags":"%RESPONSE_FLAGS%","method":"%REQ(:METHOD)%","trace_id":"%REQ(X-TRACE-ID)%","user_agent":"%REQ(USER-AGENT)%","request_id":"%REQ(X-REQUEST-ID)%","authority":"%REQ(:AUTHORITY)%","upstream_cluster":"%UPSTREAM_CLUSTER%","upstream_service_time":"%RESP(X-ENVOY-UPSTREAM-SERVICE-TIME)%","bytes_received":"%BYTES_RECEIVED%","x_forwarded_for":"%REQ(X-FORWARDED-FOR)%","protocol":"%PROTOCOL%","upstream_host":"%UPSTREAM_HOST%","duration_ms":"%DURATION%","path":"%REQ(X-ENVOY-ORIGINAL-PATH?:PATH)%"}},"@type":"type.googleapis.com/envoy.extensions.access_loggers.file.v3.FileAccessLog"},"name":"envoy.access_loggers.file"}],"codec_type":"AUTO","xff_num_trusted_hops":1}}]}],"name":"http_listener","address":{"socket_address":{"port_value":8080,"address":"0.0.0.0"}}}]},"admin":{"address":{"socket_address":{"port_value":9901,"address":"0.0.0.0"}}},"layered_runtime":{"layers":[{"static_layer":{"overload":{"global_downstream_max_connections":50000}},"name":"static_layer"}]}}
[2026-06-15 08:39:02.685][1][info][main] [source/server/server.cc:997] exiting
Unable to parse JSON as proto (INVALID_ARGUMENT: invalid JSON in  envoy.config.bootstrap.v3.Bootstrap @ overload_manager.resource_monitors[0].typed_config.<any>.max_heap_size_bytes: uint64, near 1:418 (offset   417): non-number characters in quoted  number): {"overload_manager":{"actions":[{"name":"envoy.overload_actions.shrink_heap","triggers":[{"threshold":{"value":"0.95"},"name":"envoy.resource_monitors.fixed_heap"}]},{"triggers":[{"name":"envoy.resource_monitors.fixed_heap","threshold":{"value":"0.98"}}],"name":"envoy.overload_actions.stop_accepting_requests"}],"resource_monitors":[{"name":"envoy.resource_monitors.fixed_heap","typed_config":{"max_heap_size_bytes":"2.147483648e+09","@type":"type.googleapis.com/envoy.extensions.resource_monitors.fixed_heap.v3.FixedHeapConfig"}}],"refresh_interval":"0.25s"},"static_resources":{"clusters":[{"health_checks":[{"http_health_check":{"path":"/readiness","expected_statuses":[{"start":200,"end":299}]},"interval":"10s","timeout":"1s","unhealthy_threshold":3,"healthy_threshold":2}],"outlier_detection":{"max_ejection_percent":50,"enforcing_consecutive_5xx":100,"base_ejection_time":"30s","consecutive_5xx":5,"interval":"10s"},"dns_lookup_family":"V4_ONLY","load_assignment":{"endpoints":[{"lb_endpoints":[{"endpoint":{"address":{"socket_address":{"port_value":8080,"address":"gateway-headless.etradie-system.svc.cluster.local"}}}}]}],"cluster_name":"gateway_cluster"},"type":"STRICT_DNS","connect_timeout":"5s","lb_policy":"ROUND_ROBIN","circuit_breakers":{"thresholds":[{"priority":"DEFAULT","max_pending_requests":1024,"max_retries":3,"max_connections":1024,"max_requests":1024}]},"name":"gateway_cluster"},{"connect_timeout":"5s","health_checks":[{"timeout":"1s","interval":"10s","healthy_threshold":2,"unhealthy_threshold":3,"http_health_check":{"path":"/readiness","expected_statuses":[{"start":200,"end":299}]}}],"lb_policy":"ROUND_ROBIN","outlier_detection":{"interval":"10s","consecutive_5xx":5,"max_ejection_percent":50,"enforcing_consecutive_5xx":100,"base_ejection_time":"30s"},"load_assignment":{"endpoints":[{"lb_endpoints":[{"endpoint":{"address":{"socket_address":{"port_value":8082,"address":"billing-service.etradie-system.svc.cluster.local"}}}}]}],"cluster_name":"billing_cluster"},"dns_lookup_family":"V4_ONLY","circuit_breakers":{"thresholds":[{"max_pending_requests":256,"priority":"DEFAULT","max_connections":256,"max_retries":0,"max_requests":256}]},"name":"billing_cluster","type":"STRICT_DNS"},{"typed_extension_protocol_options":{"envoy.extensions.upstreams.http.v3.HttpProtocolOptions":{"explicit_http_config":{"http2_protocol_options":{}},"@type":"type.googleapis.com/envoy.extensions.upstreams.http.v3.HttpProtocolOptions"}},"type":"STRICT_DNS","name":"otel_collector_cluster","load_assignment":{"endpoints":[{"lb_endpoints":[{"endpoint":{"address":{"socket_address":{"address":"otel-collector.etradie-observability.svc.cluster.local","port_value":4317}}}}]}],"cluster_name":"otel_collector_cluster"},"connect_timeout":"5s","lb_policy":"ROUND_ROBIN","dns_lookup_family":"V4_ONLY"}],"listeners":[{"filter_chains":[{"filters":[{"name":"envoy.filters.network.http_connection_manager","typed_config":{"tracing":{"random_sampling":{"value":100},"provider":{"name":"envoy.tracers.opentelemetry","typed_config":{"@type":"type.googleapis.com/envoy.config.trace.v3.OpenTelemetryConfig","grpc_service":{"envoy_grpc":{"cluster_name":"otel_collector_cluster"},"timeout":"0.250s"},"service_name":"etradie-envoy"}}},"stat_prefix":"ingress_http","@type":"type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager","max_request_headers_kb":64,"http_filters":[{"name":"envoy.filters.http.wasm","typed_config":{"config":{"name":"etradie_integration_filter","root_id":"etradie_root","vm_config":{"allow_precompiled":true,"runtime":"envoy.wasm.runtime.v8","code":{"local":{"filename":"/etc/envoy/wasm/integration-filter.wasm"}}}},"@type":"type.googleapis.com/envoy.extensions.filters.http.wasm.v3.Wasm"}},{"name":"envoy.filters.http.buffer","typed_config":{"@type":"type.googleapis.com/envoy.extensions.filters.http.buffer.v3.Buffer","max_request_bytes":"1.048576e+07"}},{"typed_config":{"status":{"code":429},"@type":"type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit","filter_enforced":{"default_value":{"numerator":0,"denominator":"HUNDRED"},"runtime_key":"local_rate_limit_enforced"},"stat_prefix":"http_local_rate_limiter","token_bucket":{"fill_interval":"1s","max_tokens":500,"tokens_per_fill":500},"response_headers_to_add":[{"header":{"key":"Retry-After","value":"1"},"append_action":"OVERWRITE_IF_EXISTS_OR_ADD"}],"filter_enabled":{"default_value":{"numerator":100,"denominator":"HUNDRED"},"runtime_key":"local_rate_limit_enabled"}},"name":"envoy.filters.http.local_ratelimit"},{"name":"envoy.filters.http.router","typed_config":{"@type":"type.googleapis.com/envoy.extensions.filters.http.router.v3.Router"}}],"route_config":{"name":"local_route","virtual_hosts":[{"routes":[{"match":{"prefix":"/webhooks/paddle"},"route":{"idle_timeout":"30s","timeout":"20s","retry_policy":{"num_retries":0,"retry_on":"","per_try_timeout":"15s"},"cluster":"billing_cluster"},"typed_per_filter_config":{"envoy.filters.http.local_ratelimit":{"filter_enabled":{"default_value":{"denominator":"HUNDRED","numerator":0}},"@type":"type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit","filter_enforced":{"default_value":{"numerator":0,"denominator":"HUNDRED"}},"stat_prefix":"http_local_rate_limiter_webhook","token_bucket":{"tokens_per_fill":500,"fill_interval":"1s","max_tokens":500}},"envoy.filters.http.buffer":{"buffer":{"max_request_bytes":262144},"@type":"type.googleapis.com/envoy.extensions.filters.http.buffer.v3.BufferPerRoute"}}},{"route":{"cluster":"billing_cluster","idle_timeout":"30s","retry_policy":{"num_retries":0,"retry_on":"","per_try_timeout":"15s"},"timeout":"20s"},"match":{"prefix":"/webhooks/lemonsqueezy"},"typed_per_filter_config":{"envoy.filters.http.buffer":{"buffer":{"max_request_bytes":262144},"@type":"type.googleapis.com/envoy.extensions.filters.http.buffer.v3.BufferPerRoute"},"envoy.filters.http.local_ratelimit":{"token_bucket":{"max_tokens":500,"fill_interval":"1s","tokens_per_fill":500},"filter_enforced":{"default_value":{"denominator":"HUNDRED","numerator":0}},"@type":"type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit","filter_enabled":{"default_value":{"numerator":0,"denominator":"HUNDRED"}},"stat_prefix":"http_local_rate_limiter_webhook"}}},{"match":{"prefix":"/"},"typed_per_filter_config":{"envoy.filters.http.buffer":{"buffer":{"max_request_bytes":"1.048576e+07"},"@type":"type.googleapis.com/envoy.extensions.filters.http.buffer.v3.BufferPerRoute"}},"route":{"retry_policy":{"retry_on":"connect-failure,refused-stream,unavailable,cancelled,retriable-status-codes","per_try_timeout":"10s","retriable_status_codes":[503],"num_retries":2},"timeout":"30s","cluster":"gateway_cluster","idle_timeout":"60s"}}],"name":"backend","domains":["*"],"response_headers_to_add":[{"header":{"value":"default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'","key":"Content-Security-Policy"},"append_action":"OVERWRITE_IF_EXISTS_OR_ADD"},{"append_action":"OVERWRITE_IF_EXISTS_OR_ADD","header":{"key":"X-Frame-Options","value":"DENY"}},{"header":{"key":"X-Content-Type-Options","value":"nosniff"},"append_action":"OVERWRITE_IF_EXISTS_OR_ADD"},{"header":{"key":"Referrer-Policy","value":"no-referrer"},"append_action":"OVERWRITE_IF_EXISTS_OR_ADD"}]}]},"use_remote_address":true,"access_log":[{"typed_config":{"path":"/dev/stdout","log_format":{"json_format":{"bytes_sent":"%BYTES_SENT%","timestamp":"%START_TIME%","response_code":"%RESPONSE_CODE%","response_flags":"%RESPONSE_FLAGS%","method":"%REQ(:METHOD)%","trace_id":"%REQ(X-TRACE-ID)%","user_agent":"%REQ(USER-AGENT)%","request_id":"%REQ(X-REQUEST-ID)%","authority":"%REQ(:AUTHORITY)%","upstream_cluster":"%UPSTREAM_CLUSTER%","upstream_service_time":"%RESP(X-ENVOY-UPSTREAM-SERVICE-TIME)%","bytes_received":"%BYTES_RECEIVED%","x_forwarded_for":"%REQ(X-FORWARDED-FOR)%","protocol":"%PROTOCOL%","upstream_host":"%UPSTREAM_HOST%","duration_ms":"%DURATION%","path":"%REQ(X-ENVOY-ORIGINAL-PATH?:PATH)%"}},"@type":"type.googleapis.com/envoy.extensions.access_loggers.file.v3.FileAccessLog"},"name":"envoy.access_loggers.file"}],"codec_type":"AUTO","xff_num_trusted_hops":1}}]}],"name":"http_listener","address":{"socket_address":{"port_value":8080,"address":"0.0.0.0"}}}]},"admin":{"address":{"socket_address":{"port_value":9901,"address":"0.0.0.0"}}},"layered_runtime":{"layers":[{"static_layer":{"overload":{"global_downstream_max_connections":50000}},"name":"static_layer"}]}}
---
Init Containers:
  linkerd-init:
    Container ID:    containerd://7ce5a74bb26a486539e36f4b6c8dd69b117610882e9ce9e762cd13fafda375c5
    Image:           cr.l5d.io/linkerd/proxy-init:v2.2.3
    Image ID:        cr.l5d.io/linkerd/proxy-init@sha256:1075bc22a4a8f0852311dc84c9db0552f1245d07fe4fdebd4bc6cf4566bcbc76
    Port:            <none>
    Host Port:       <none>
    SeccompProfile:  RuntimeDefault
    Args:
      --incoming-proxy-port
      4143
      --outgoing-proxy-port
      4140
      --proxy-uid
      2102
      --inbound-ports-to-ignore
      4190,4191,4567,4568
      --outbound-ports-to-ignore
      4567,4568
    State:          Terminated
      Reason:       Completed
      Exit Code:    0
      Started:      Mon, 15 Jun 2026 08:57:18 +0100
      Finished:     Mon, 15 Jun 2026 08:57:18 +0100
    Ready:          True
    Restart Count:  0
    Limits:
      cpu:     100m
      memory:  64Mi
    Requests:
      cpu:        50m
      memory:     64Mi
    Environment:  <none>
    Mounts:
      /run from linkerd-proxy-init-xtables-lock (rw)
Containers:
  linkerd-proxy:
    Container ID:    containerd://1e921389ead9fc6951d12767d46485a7a25d7dc883429c74b797aadd2979d26f
    Image:           cr.l5d.io/linkerd/proxy:stable-2.14.10
    Image ID:        cr.l5d.io/linkerd/proxy@sha256:7876cee0717575ebc39d2b7cfd701e0df28a809bcb2cf4974716a0bce1ce32cb
    Ports:           4143/TCP, 4191/TCP
    Host Ports:      0/TCP, 0/TCP
    SeccompProfile:  RuntimeDefault
    State:           Running
      Started:       Mon, 15 Jun 2026 08:57:19 +0100
    Ready:           True
    Restart Count:   0
    Limits:
      cpu:     200m
      memory:  256Mi
    Requests:
      cpu:      50m
      memory:   64Mi
    Liveness:   http-get http://:4191/live delay=10s timeout=1s period=10s #success=1 #failure=3
    Readiness:  http-get http://:4191/ready delay=2s timeout=1s period=10s #success=1 #failure=3
    Environment:
      _pod_name:                                                etradie-envoy-57cffb98b-wjv7n (v1:metadata.name)
      _pod_ns:                                                  envoy-system (v1:metadata.namespace)
      _pod_nodeName:                                             (v1:spec.nodeName)
      LINKERD2_PROXY_LOG:                                       warn,linkerd=info
      LINKERD2_PROXY_LOG_FORMAT:                                plain
      LINKERD2_PROXY_DESTINATION_SVC_ADDR:                      linkerd-dst-headless.linkerd.svc.cluster.local.:8086
      LINKERD2_PROXY_DESTINATION_PROFILE_NETWORKS:              10.0.0.0/8,100.64.0.0/10,172.16.0.0/12,192.168.0.0/16
      LINKERD2_PROXY_POLICY_SVC_ADDR:                           linkerd-policy.linkerd.svc.cluster.local.:8090
      LINKERD2_PROXY_POLICY_WORKLOAD:                           $(_pod_ns):$(_pod_name)
      LINKERD2_PROXY_INBOUND_DEFAULT_POLICY:                    all-unauthenticated
      LINKERD2_PROXY_POLICY_CLUSTER_NETWORKS:                   10.0.0.0/8,100.64.0.0/10,172.16.0.0/12,192.168.0.0/16
      LINKERD2_PROXY_INBOUND_CONNECT_TIMEOUT:                   100ms
      LINKERD2_PROXY_OUTBOUND_CONNECT_TIMEOUT:                  1000ms
      LINKERD2_PROXY_OUTBOUND_DISCOVERY_IDLE_TIMEOUT:           5s
      LINKERD2_PROXY_INBOUND_DISCOVERY_IDLE_TIMEOUT:            90s
      LINKERD2_PROXY_CONTROL_LISTEN_ADDR:                       0.0.0.0:4190
      LINKERD2_PROXY_ADMIN_LISTEN_ADDR:                         0.0.0.0:4191
      LINKERD2_PROXY_OUTBOUND_LISTEN_ADDR:                      127.0.0.1:4140
      LINKERD2_PROXY_INBOUND_LISTEN_ADDR:                       0.0.0.0:4143
      LINKERD2_PROXY_INBOUND_IPS:                                (v1:status.podIPs)
      LINKERD2_PROXY_INBOUND_PORTS:                             8080,9901
      LINKERD2_PROXY_DESTINATION_PROFILE_SUFFIXES:              svc.cluster.local.
      LINKERD2_PROXY_INBOUND_ACCEPT_KEEPALIVE:                  10000ms
      LINKERD2_PROXY_OUTBOUND_CONNECT_KEEPALIVE:                10000ms
etradie-engine-5cd9b9d777       1         1         0       81m   engine       ghcr.io/flamegreat-1/etradie/engine:0.1.0            app.kubernetes.io/instance=etradie-engine,app.kubernetes.io/name=etradie-engine,pod-template-hash=5cd9b9d777
etradie-engine-d7bd6444d        1         1         0       49m   engine       ghcr.io/flamegreat-1/etradie/engine:0.1.0            app.kubernetes.io/instance=etradie-engine,app.kubernetes.io/name=etradie-engine,pod-template-hash=d7bd6444d
etradie-gateway-7bd667b5d7      1         1         0       82m   gateway      ghcr.io/flamegreat-1/etradie/gateway:staging-0.1.0   app.kubernetes.io/instance=etradie-gateway,app.kubernetes.io/name=etradie-gateway,pod-template-hash=7bd667b5d7
etradie-gateway-bfbc5fcf8       1         1         0       49m   gateway      ghcr.io/flamegreat-1/etradie/gateway:staging-0.1.0   app.kubernetes.io/instance=etradie-gateway,app.kubernetes.io/name=etradie-gateway,pod-template-hash=bfbc5fcf8
NAME                                      READY   STATUS    RESTARTS   AGE
linkerd-destination-7c965848b9-4wxbj      4/4     Running   0          67s
linkerd-identity-759f6d955-jssdj          2/2     Running   0          3h42m
linkerd-proxy-injector-84886f7f5d-tls8d   2/2     Running   0          67s
softverse@Softverse:~/eTradie$
