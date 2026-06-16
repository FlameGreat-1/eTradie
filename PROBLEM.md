softverse@Softverse:~/eTradie$ ^C
softverse@Softverse:~/eTradie$ ^C
softverse@Softverse:~/eTradie$ ADMIN_ARGO_PWD=$(kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d)
argocd login 127.0.0.1:8080 --username admin --password "$ADMIN_ARGO_PWD" --insecure
unset ADMIN_ARGO_PWD
argocd account list 2>&1 | head -3
'admin:login' logged in successfully
Context '127.0.0.1:8080' updated
NAME   ENABLED  CAPABILITIES
admin  true     login
softverse@Softverse:~/eTradie$ export KUBECONFIG=~/.kube/etradie-contabo.yaml

echo "=== G1. force ArgoCD to sync engine-staging ==="
kubectl -n argocd annotate application engine-staging argocd.argoproj.io/refresh=hard --overwrite
sleep 10
kubectl -n argocd get application engine-staging -o jsonpath='
  sync={.status.sync.status}{"\n"}
  revision={.status.sync.revision}{"\n"}
  health={.status.health.status}{"\n"}'

echo
echo "=== G2. wait for the Deployment template to flip to inject=disabled ==="
for i in 1 2 3 4 5 6; do
  INJ=$(kubectl -n etradie-system get deployment etradie-engine \
    -o jsonpath='{.spec.template.metadata.annotations.linkerd\.io/inject}')
  echo "  T+$((i*10))s: deployment template linkerd.io/inject = '$INJ'"
  [ "$INJ" = "disabled" ] && echo "  *** Deployment template updated ***" && break
  sleep 10
done

echo
echo "=== G3. find the new engine pod (should have NO linkerd-proxy container) ==="
sleep 15
ENG=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
echo "latest engine pod: $ENG"
echo
echo "--- containers in the new pod ---"
kubectl -n etradie-system get pod "$ENG" -o jsonpath='containers: {range .spec.containers[*]}{.name} {end}{"\n"}initContainers: {range .spec.initContainers[*]}{.name} {end}{"\n"}'
echo
echo "--- pod's inject annotation ---"
kubectl -n etradie-system get pod "$ENG" -o jsonpath='inject={.metadata.annotations.linkerd\.io/inject}{"\n"}'

echo
echo "=== G4. watch boot for up to 7 minutes (no mesh = clean startup) ==="
for i in $(seq 1 42); do
  STATUS=$(kubectl -n etradie-system get pod "$ENG" \
    -o jsonpath='READY={.status.containerStatuses[?(@.name=="engine")].ready} PHASE={.status.phase} RESTARTS={.status.containerStatuses[?(@.name=="engine")].restartCount}')
kubectl -n edge-ingress-system get pods 2>/dev/nulles.io/name in (etradie-gateway,etradie-execution,etradie-management,etradie-billing)'
=== G1. force ArgoCD to sync engine-staging ===
application.argoproj.io/engine-staging annotated

  sync=OutOfSync

  revision=b3240792c24db5cea370cef4da8f0ef70826272b

  health=Degraded

=== G2. wait for the Deployment template to flip to inject=disabled ===
  T+10s: deployment template linkerd.io/inject = 'disabled'
  *** Deployment template updated ***

=== G3. find the new engine pod (should have NO linkerd-proxy container) ===
latest engine pod: etradie-engine-6695956874-tnx75

--- containers in the new pod ---
containers: engine
initContainers: wait-for-deps migrate

--- pod's inject annotation ---
inject=disabled

=== G4. watch boot for up to 7 minutes (no mesh = clean startup) ===
  T+10s: READY=false PHASE=Running RESTARTS=16
  *** ENGINE CRASHED 16 TIMES — breaking ***

=== G5. final state + RAG bootstrap log ===
NAME                              READY   STATUS    RESTARTS       AGE   IP            NODE         NOMINATED NODE   READINESS GATES
etradie-engine-6695956874-tnx75   0/1     Running   16 (50s ago)   84m   10.42.0.217   vmi3362776   <none>           <none>

--- RAG bootstrap milestones ---
  File "/usr/local/lib/python3.12/site-packages/uvicorn/protocols/http/httptools_impl.py", line 409, in run_asgi
  File "/usr/local/lib/python3.12/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
  File "/usr/local/lib/python3.12/site-packages/uvicorn/protocols/http/httptools_impl.py", line 409, in run_asgi
  File "/usr/local/lib/python3.12/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
  File "/usr/local/lib/python3.12/site-packages/uvicorn/protocols/http/httptools_impl.py", line 409, in run_asgi
  File "/usr/local/lib/python3.12/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
  File "/usr/local/lib/python3.12/site-packages/uvicorn/protocols/http/httptools_impl.py", line 409, in run_asgi
  File "/usr/local/lib/python3.12/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
  File "/usr/local/lib/python3.12/site-packages/uvicorn/protocols/http/httptools_impl.py", line 409, in run_asgi
  File "/usr/local/lib/python3.12/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__

=== G6. cascade — downstream services ===
NAME                                 READY   STATUS                  RESTARTS          AGE
etradie-billing-6bd67b7b55-dqwmh     0/2     Init:CrashLoopBackOff   131 (73s ago)     15h
etradie-billing-75d844d7d8-w66s8     0/2     Init:CrashLoopBackOff   131 (86s ago)     15h
etradie-execution-6d89988995-7lnns   0/2     Init:CrashLoopBackOff   115 (110s ago)    15h
etradie-execution-8576bf499-dzblv    0/2     Init:0/2                116 (5m38s ago)   15h
etradie-gateway-785f4998f8-jb6pc     0/2     Init:CrashLoopBackOff   131 (2m17s ago)   15h
etradie-gateway-bfbc5fcf8-9p68r      0/2     Init:CrashLoopBackOff   131 (3m37s ago)   15h
etradie-management-f9d95547b-f88kp   0/2     Init:0/2                0                 34s
NAME                            READY   STATUS                  RESTARTS        AGE
cloudflared-fb8f66bf8-mwp7z     1/1     Running                 0               33h
edge-ingress-68489cd577-h9p8n   0/1     Init:CrashLoopBackOff   288 (24s ago)   24h
softverse@Softverse:~/eTradie$
softverse@Softverse:~/eTradie$
softverse@Softverse:~/eTradie$ export KUBECONFIG=~/.kube/etradie-contabo.yaml

ENG=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
echo "engine pod: $ENG"

echo
echo "=== H1. current pod state + restart count ==="
kubectl -n etradie-system get pod "$ENG"

echo
echo "=== H2. full engine log — last 100 lines, no grep, see the actual error ==="
kubectl -n etradie-system logs "$ENG" -c engine --tail=100

echo
echo "=== H3. previous container instance log — what made it restart? ==="
kubectl -n etradie-system logs "$ENG" -c engine --previous --tail=60 2>&1 | tail -60

echo
echo "=== H4. did RAG bootstrap actually complete? (search for the success marker) ==="
kubectl -n etradie-system logs "$ENG" -c engine --tail=2000 2>&1 \
  | grep -iE 'rag_bootstrap_completed|rag_bootstrap_starting|application_started|loaded_markdown|ingest|listening|uvicorn running|error|exception' | tail -30

echo
echo "=== H5. one gateway pod's init log — to understand why downstream is now Init:CrashLoopBackOff ==="
GW=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-gateway \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
echo "gateway pod: $GW"
kubectl -n etradie-system describe pod "$GW" 2>&1 | grep -A 10 'wait-for-deps\|Init:CrashLoopBackOff\|Reason:\|Message:' | head -40
kubectl -n etradie-system logs "$GW" -c wait-for-deps --previous --tail=30 2>/dev/null || \
kubectl -n etradie-system logs "$GW" -c wait-for-deps --tail=30 2>/dev/null
engine pod: etradie-engine-6695956874-tnx75

=== H1. current pod state + restart count ===
NAME                              READY   STATUS    RESTARTS         AGE
etradie-engine-6695956874-tnx75   0/1     Running   16 (3m30s ago)   87m

=== H2. full engine log — last 100 lines, no grep, see the actual error ===
    raise app_exc from app_exc.__cause__ or app_exc.__context__
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py", line 144, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "/usr/local/lib/python3.12/site-packages/engine/shared/body_limit.py", line 180, in __call__
    await self.app(scope, limited_receive, guarded_send)
  File "/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/asgi/__init__.py", line 687, in __call__
    span_name, additional_attributes = self.default_span_details(scope)
                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py", line 443, in _get_default_span_details
    route = _get_route_details(scope)
            ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py", line 427, in _get_route_details
    route = starlette_route.path
            ^^^^^^^^^^^^^^^^^^^^
AttributeError: '_IncludedRouter' object has no attribute 'path'
{"extra": {"phase": "periodic", "scanned": 0, "unhealthy": 0, "reprovisioned": 0, "failed": 0, "outcome": "ok"}, "event": "hosted_recovery_sweep_complete", "level": "INFO", "logger": "engine.ta.broker.mt5.hosted.recovery", "timestamp": "2026-06-16T16:45:48.512784Z"}
{"extra": {"operation": "GET /health", "error_type": "AttributeError", "error_message": "'_IncludedRouter' object has no attribute 'path'"}, "event": "panic_recovered", "level": "ERROR", "logger": "engine.shared.error_handler", "timestamp": "2026-06-16T16:45:53.397424Z", "exception": "Traceback (most recent call last):\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py\", line 164, in __call__\n    await self.app(scope, receive, _send)\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/cors.py\", line 88, in __call__\n    await self.app(scope, receive, send)\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 193, in __call__\n    response = await self.dispatch_func(request, call_next)\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/engine/shared/csrf.py\", line 230, in dispatch\n    return await call_next(request)\n           ^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 168, in call_next\n    raise app_exc from app_exc.__cause__ or app_exc.__context__\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 144, in coro\n    await self.app(scope, receive_or_disconnect, send_no_error)\n  File \"/usr/local/lib/python3.12/site-packages/engine/shared/body_limit.py\", line 180, in __call__\n    await self.app(scope, limited_receive, guarded_send)\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/asgi/__init__.py\", line 687, in __call__\n    span_name, additional_attributes = self.default_span_details(scope)\n                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py\", line 443, in _get_default_span_details\n    route = _get_route_details(scope)\n            ^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py\", line 427, in _get_route_details\n    route = starlette_route.path\n            ^^^^^^^^^^^^^^^^^^^^\nAttributeError: '_IncludedRouter' object has no attribute 'path'"}
INFO:     10.42.0.1:57378 - "GET /health HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/usr/local/lib/python3.12/site-packages/uvicorn/protocols/http/httptools_impl.py", line 409, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/fastapi/applications.py", line 1162, in __call__
    await super().__call__(scope, receive, send)
  File "/usr/local/lib/python3.12/site-packages/starlette/applications.py", line 90, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py", line 186, in __call__
    raise exc
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/cors.py", line 88, in __call__
    await self.app(scope, receive, send)
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py", line 193, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/engine/shared/csrf.py", line 230, in dispatch
    return await call_next(request)
           ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py", line 168, in call_next
    raise app_exc from app_exc.__cause__ or app_exc.__context__
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py", line 144, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "/usr/local/lib/python3.12/site-packages/engine/shared/body_limit.py", line 180, in __call__
    await self.app(scope, limited_receive, guarded_send)
  File "/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/asgi/__init__.py", line 687, in __call__
    span_name, additional_attributes = self.default_span_details(scope)
                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py", line 443, in _get_default_span_details
    route = _get_route_details(scope)
            ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py", line 427, in _get_route_details
    route = starlette_route.path
            ^^^^^^^^^^^^^^^^^^^^
AttributeError: '_IncludedRouter' object has no attribute 'path'
{"extra": {"operation": "GET /health", "error_type": "AttributeError", "error_message": "'_IncludedRouter' object has no attribute 'path'"}, "event": "panic_recovered", "level": "ERROR", "logger": "engine.shared.error_handler", "timestamp": "2026-06-16T16:45:58.398125Z", "exception": "Traceback (most recent call last):\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py\", line 164, in __call__\n    await self.app(scope, receive, _send)\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/cors.py\", line 88, in __call__\n    await self.app(scope, receive, send)\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 193, in __call__\n    response = await self.dispatch_func(request, call_next)\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/engine/shared/csrf.py\", line 230, in dispatch\n    return await call_next(request)\n           ^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 168, in call_next\n    raise app_exc from app_exc.__cause__ or app_exc.__context__\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 144, in coro\n    await self.app(scope, receive_or_disconnect, send_no_error)\n  File \"/usr/local/lib/python3.12/site-packages/engine/shared/body_limit.py\", line 180, in __call__\n    await self.app(scope, limited_receive, guarded_send)\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/asgi/__init__.py\", line 687, in __call__\n    span_name, additional_attributes = self.default_span_details(scope)\n                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py\", line 443, in _get_default_span_details\n    route = _get_route_details(scope)\n            ^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py\", line 427, in _get_route_details\n    route = starlette_route.path\n            ^^^^^^^^^^^^^^^^^^^^\nAttributeError: '_IncludedRouter' object has no attribute 'path'"}
INFO:     10.42.0.1:52564 - "GET /health HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/usr/local/lib/python3.12/site-packages/uvicorn/protocols/http/httptools_impl.py", line 409, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/fastapi/applications.py", line 1162, in __call__
    await super().__call__(scope, receive, send)
  File "/usr/local/lib/python3.12/site-packages/starlette/applications.py", line 90, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py", line 186, in __call__
    raise exc
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/cors.py", line 88, in __call__
    await self.app(scope, receive, send)
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py", line 193, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/engine/shared/csrf.py", line 230, in dispatch
    return await call_next(request)
           ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py", line 168, in call_next
    raise app_exc from app_exc.__cause__ or app_exc.__context__
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py", line 144, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "/usr/local/lib/python3.12/site-packages/engine/shared/body_limit.py", line 180, in __call__
    await self.app(scope, limited_receive, guarded_send)
  File "/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/asgi/__init__.py", line 687, in __call__
    span_name, additional_attributes = self.default_span_details(scope)
                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py", line 443, in _get_default_span_details
    route = _get_route_details(scope)
            ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py", line 427, in _get_route_details
    route = starlette_route.path
            ^^^^^^^^^^^^^^^^^^^^
AttributeError: '_IncludedRouter' object has no attribute 'path'

=== H3. previous container instance log — what made it restart? ===
    route = _get_route_details(scope)
            ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py", line 427, in _get_route_details
    route = starlette_route.path
            ^^^^^^^^^^^^^^^^^^^^
AttributeError: '_IncludedRouter' object has no attribute 'path'
{"extra": {"operation": "GET /health", "error_type": "AttributeError", "error_message": "'_IncludedRouter' object has no attribute 'path'"}, "event": "panic_recovered", "level": "ERROR", "logger": "engine.shared.error_handler", "timestamp": "2026-06-16T16:42:23.398677Z", "exception": "Traceback (most recent call last):\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py\", line 164, in __call__\n    await self.app(scope, receive, _send)\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/cors.py\", line 88, in __call__\n    await self.app(scope, receive, send)\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 193, in __call__\n    response = await self.dispatch_func(request, call_next)\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/engine/shared/csrf.py\", line 230, in dispatch\n    return await call_next(request)\n           ^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 168, in call_next\n    raise app_exc from app_exc.__cause__ or app_exc.__context__\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 144, in coro\n    await self.app(scope, receive_or_disconnect, send_no_error)\n  File \"/usr/local/lib/python3.12/site-packages/engine/shared/body_limit.py\", line 180, in __call__\n    await self.app(scope, limited_receive, guarded_send)\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/asgi/__init__.py\", line 687, in __call__\n    span_name, additional_attributes = self.default_span_details(scope)\n                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py\", line 443, in _get_default_span_details\n    route = _get_route_details(scope)\n            ^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py\", line 427, in _get_route_details\n    route = starlette_route.path\n            ^^^^^^^^^^^^^^^^^^^^\nAttributeError: '_IncludedRouter' object has no attribute 'path'"}
INFO:     10.42.0.1:43844 - "GET /health HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/usr/local/lib/python3.12/site-packages/uvicorn/protocols/http/httptools_impl.py", line 409, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/fastapi/applications.py", line 1162, in __call__
    await super().__call__(scope, receive, send)
  File "/usr/local/lib/python3.12/site-packages/starlette/applications.py", line 90, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py", line 186, in __call__
    raise exc
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/cors.py", line 88, in __call__
    await self.app(scope, receive, send)
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py", line 193, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/engine/shared/csrf.py", line 230, in dispatch
    return await call_next(request)
           ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py", line 168, in call_next
    raise app_exc from app_exc.__cause__ or app_exc.__context__
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py", line 144, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "/usr/local/lib/python3.12/site-packages/engine/shared/body_limit.py", line 180, in __call__
    await self.app(scope, limited_receive, guarded_send)
  File "/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/asgi/__init__.py", line 687, in __call__
    span_name, additional_attributes = self.default_span_details(scope)
                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py", line 443, in _get_default_span_details
    route = _get_route_details(scope)
            ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py", line 427, in _get_route_details
    route = starlette_route.path
            ^^^^^^^^^^^^^^^^^^^^
AttributeError: '_IncludedRouter' object has no attribute 'path'
INFO:     Shutting down
INFO:     Waiting for application shutdown.
{"event": "hosted_recovery_loop_cancelled", "level": "INFO", "logger": "engine.ta.broker.mt5.hosted.recovery", "timestamp": "2026-06-16T16:42:28.572973Z"}
{"extra": {"wait_for_jobs": false, "active_jobs": 0}, "event": "scheduler_shutting_down", "level": "INFO", "logger": "engine.shared.scheduler.apscheduler", "timestamp": "2026-06-16T16:42:28.573602Z"}
{"event": "scheduler_stopped", "level": "INFO", "logger": "engine.shared.scheduler.apscheduler", "timestamp": "2026-06-16T16:42:28.574085Z"}
{"event": "Scheduler has been shut down"}
{"event": "http_client_closed", "level": "INFO", "logger": "engine.shared.http.client", "timestamp": "2026-06-16T16:42:28.574718Z"}
{"event": "redis_cache_closed", "level": "INFO", "logger": "engine.shared.cache.redis_cache", "timestamp": "2026-06-16T16:42:28.575212Z"}
{"event": "database_manager_closed", "level": "INFO", "logger": "engine.shared.db.connection", "timestamp": "2026-06-16T16:42:28.586042Z"}
{"event": "application_stopped", "level": "INFO", "logger": "engine.main", "timestamp": "2026-06-16T16:42:28.586362Z"}
INFO:     Application shutdown complete.
INFO:     Finished server process [1]

=== H4. did RAG bootstrap actually complete? (search for the success marker) ===
    await self.app(scope, receive_or_disconnect, send_no_error)
AttributeError: '_IncludedRouter' object has no attribute 'path'
{"extra": {"operation": "GET /health", "error_type": "AttributeError", "error_message": "'_IncludedRouter' object has no attribute 'path'"}, "event": "panic_recovered", "level": "ERROR", "logger": "engine.shared.error_handler", "timestamp": "2026-06-16T16:45:48.397774Z", "exception": "Traceback (most recent call last):\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py\", line 164, in __call__\n    await self.app(scope, receive, _send)\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/cors.py\", line 88, in __call__\n    await self.app(scope, receive, send)\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 193, in __call__\n    response = await self.dispatch_func(request, call_next)\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/engine/shared/csrf.py\", line 230, in dispatch\n    return await call_next(request)\n           ^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 168, in call_next\n    raise app_exc from app_exc.__cause__ or app_exc.__context__\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 144, in coro\n    await self.app(scope, receive_or_disconnect, send_no_error)\n  File \"/usr/local/lib/python3.12/site-packages/engine/shared/body_limit.py\", line 180, in __call__\n    await self.app(scope, limited_receive, guarded_send)\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/asgi/__init__.py\", line 687, in __call__\n    span_name, additional_attributes = self.default_span_details(scope)\n                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py\", line 443, in _get_default_span_details\n    route = _get_route_details(scope)\n            ^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py\", line 427, in _get_route_details\n    route = starlette_route.path\n            ^^^^^^^^^^^^^^^^^^^^\nAttributeError: '_IncludedRouter' object has no attribute 'path'"}
INFO:     10.42.0.1:57366 - "GET /health HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py", line 186, in __call__
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive_or_disconnect, send_no_error)
AttributeError: '_IncludedRouter' object has no attribute 'path'
{"extra": {"operation": "GET /health", "error_type": "AttributeError", "error_message": "'_IncludedRouter' object has no attribute 'path'"}, "event": "panic_recovered", "level": "ERROR", "logger": "engine.shared.error_handler", "timestamp": "2026-06-16T16:45:53.397424Z", "exception": "Traceback (most recent call last):\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py\", line 164, in __call__\n    await self.app(scope, receive, _send)\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/cors.py\", line 88, in __call__\n    await self.app(scope, receive, send)\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 193, in __call__\n    response = await self.dispatch_func(request, call_next)\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/engine/shared/csrf.py\", line 230, in dispatch\n    return await call_next(request)\n           ^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 168, in call_next\n    raise app_exc from app_exc.__cause__ or app_exc.__context__\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 144, in coro\n    await self.app(scope, receive_or_disconnect, send_no_error)\n  File \"/usr/local/lib/python3.12/site-packages/engine/shared/body_limit.py\", line 180, in __call__\n    await self.app(scope, limited_receive, guarded_send)\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/asgi/__init__.py\", line 687, in __call__\n    span_name, additional_attributes = self.default_span_details(scope)\n                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py\", line 443, in _get_default_span_details\n    route = _get_route_details(scope)\n            ^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py\", line 427, in _get_route_details\n    route = starlette_route.path\n            ^^^^^^^^^^^^^^^^^^^^\nAttributeError: '_IncludedRouter' object has no attribute 'path'"}
INFO:     10.42.0.1:57378 - "GET /health HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py", line 186, in __call__
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive_or_disconnect, send_no_error)
AttributeError: '_IncludedRouter' object has no attribute 'path'
{"extra": {"operation": "GET /health", "error_type": "AttributeError", "error_message": "'_IncludedRouter' object has no attribute 'path'"}, "event": "panic_recovered", "level": "ERROR", "logger": "engine.shared.error_handler", "timestamp": "2026-06-16T16:45:58.398125Z", "exception": "Traceback (most recent call last):\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py\", line 164, in __call__\n    await self.app(scope, receive, _send)\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/cors.py\", line 88, in __call__\n    await self.app(scope, receive, send)\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 193, in __call__\n    response = await self.dispatch_func(request, call_next)\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/engine/shared/csrf.py\", line 230, in dispatch\n    return await call_next(request)\n           ^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 168, in call_next\n    raise app_exc from app_exc.__cause__ or app_exc.__context__\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 144, in coro\n    await self.app(scope, receive_or_disconnect, send_no_error)\n  File \"/usr/local/lib/python3.12/site-packages/engine/shared/body_limit.py\", line 180, in __call__\n    await self.app(scope, limited_receive, guarded_send)\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/asgi/__init__.py\", line 687, in __call__\n    span_name, additional_attributes = self.default_span_details(scope)\n                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py\", line 443, in _get_default_span_details\n    route = _get_route_details(scope)\n            ^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py\", line 427, in _get_route_details\n    route = starlette_route.path\n            ^^^^^^^^^^^^^^^^^^^^\nAttributeError: '_IncludedRouter' object has no attribute 'path'"}
INFO:     10.42.0.1:52564 - "GET /health HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py", line 186, in __call__
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive_or_disconnect, send_no_error)
AttributeError: '_IncludedRouter' object has no attribute 'path'
{"extra": {"operation": "GET /health", "error_type": "AttributeError", "error_message": "'_IncludedRouter' object has no attribute 'path'"}, "event": "panic_recovered", "level": "ERROR", "logger": "engine.shared.error_handler", "timestamp": "2026-06-16T16:46:03.398513Z", "exception": "Traceback (most recent call last):\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py\", line 164, in __call__\n    await self.app(scope, receive, _send)\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/cors.py\", line 88, in __call__\n    await self.app(scope, receive, send)\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 193, in __call__\n    response = await self.dispatch_func(request, call_next)\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/engine/shared/csrf.py\", line 230, in dispatch\n    return await call_next(request)\n           ^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 168, in call_next\n    raise app_exc from app_exc.__cause__ or app_exc.__context__\n  File \"/usr/local/lib/python3.12/site-packages/starlette/middleware/base.py\", line 144, in coro\n    await self.app(scope, receive_or_disconnect, send_no_error)\n  File \"/usr/local/lib/python3.12/site-packages/engine/shared/body_limit.py\", line 180, in __call__\n    await self.app(scope, limited_receive, guarded_send)\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/asgi/__init__.py\", line 687, in __call__\n    span_name, additional_attributes = self.default_span_details(scope)\n                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py\", line 443, in _get_default_span_details\n    route = _get_route_details(scope)\n            ^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/site-packages/opentelemetry/instrumentation/fastapi/__init__.py\", line 427, in _get_route_details\n    route = starlette_route.path\n            ^^^^^^^^^^^^^^^^^^^^\nAttributeError: '_IncludedRouter' object has no attribute 'path'"}
INFO:     10.42.0.1:52578 - "GET /health HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py", line 186, in __call__
  File "/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive_or_disconnect, send_no_error)
AttributeError: '_IncludedRouter' object has no attribute 'path'

=== H5. one gateway pod's init log — to understand why downstream is now Init:CrashLoopBackOff ===
gateway pod: etradie-gateway-bfbc5fcf8-9p68r
  wait-for-deps:
    Container ID:    containerd://47c3fc3f3762228f600ff374af20acff445d0d47771bdcbf225433a5f18fc33c
    Image:           busybox:1.36
    Image ID:        docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
    Port:            <none>
    Host Port:       <none>
    SeccompProfile:  RuntimeDefault
    Command:
      /bin/sh
      -c
      set -eu
--
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
      echo "[wait-for-deps] checking engine.etradie-system.svc.cluster.local:8000"
      while ! nc -z -w 2 "engine.etradie-system.svc.cluster.local" 8000; do
        if [ "$(date +%s)" -ge "${deadline}" ]; then
          echo "[wait-for-deps] FATAL: timed out waiting for engine.etradie-system.svc.cluster.local:8000"
          exit 1
        fi
        echo "[wait-for-deps] engine.etradie-system.svc.cluster.local:8000 not yet reachable; sleeping ${WAIT_FOR_DEPS_INTERVAL_SECS}s"
        sleep "${WAIT_FOR_DEPS_INTERVAL_SECS}"
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
softverse@Softverse:~/eTradie$
softverse@Softverse:~/eTradie$
softverse@Softverse:~/eTradie$ cd ~/eTradie
git fetch gitlab main
git log --oneline gitlab/main -1
# expect new commit at top: "helm/engine: disable OTel tracing in staging..."

git status
# if clean:
git pull --rebase gitlab main
# if it produces SHA divergence (probable from history):
git push --force-with-lease origin main
git log --oneline origin/main -3
remote: Enumerating objects: 9, done.
remote: Counting objects: 100% (9/9), done.
remote: Compressing objects: 100% (5/5), done.
remote: Total 5 (delta 4), reused 0 (delta 0), pack-reused 0 (from 0)
Unpacking objects: 100% (5/5), 1.98 KiB | 80.00 KiB/s, done.
From https://gitlab.com/exoper2/exoper
 * branch              main       -> FETCH_HEAD
   b3240792..24943c30  main       -> gitlab/main
24943c30 (gitlab/main) helm/engine: disable OTel tracing in staging to work around OTel/FastAPI _IncludedRouter crash (phase10.6 unblock)
On branch main
Your branch is up to date with 'origin/main'.

nothing to commit, working tree clean
From https://gitlab.com/exoper2/exoper
 * branch              main       -> FETCH_HEAD
Updating b3240792..24943c30
Fast-forward
 helm/engine/values-staging.yaml | 15 ++++++++++++---
 1 file changed, 12 insertions(+), 3 deletions(-)
Enumerating objects: 9, done.
Counting objects: 100% (9/9), done.
Delta compression using up to 4 threads
Compressing objects: 100% (5/5), done.
Writing objects: 100% (5/5), 2.00 KiB | 1.00 MiB/s, done.
Total 5 (delta 4), reused 0 (delta 0), pack-reused 0
remote: Resolving deltas: 100% (4/4), completed with 4 local objects.
To https://github.com/FlameGreat-1/eTradie.git
   b3240792..24943c30  main -> main
24943c30 (HEAD -> main, origin/main, gitlab/main) helm/engine: disable OTel tracing in staging to work around OTel/FastAPI _IncludedRouter crash (phase10.6 unblock)
b3240792 wip: local debug edits
6fc12230 helm/engine: temporarily disable mesh injection on engine pod (phase10.6 unblock)
softverse@Softverse:~/eTradie$ export KUBECONFIG=~/.kube/etradie-contabo.yaml

echo "=== K1. force ArgoCD sync ==="
kubectl -n argocd annotate application engine-staging argocd.argoproj.io/refresh=hard --overwrite
sleep 10

echo "=== K2. wait for deployment template to flip OTEL_EXPORTER_OTLP_ENDPOINT to empty ==="
for i in 1 2 3 4 5 6; do
  OTEL=$(kubectl -n etradie-system get configmap etradie-engine-config \
    -o jsonpath='{.data.OTEL_EXPORTER_OTLP_ENDPOINT}')
  echo "  T+$((i*10))s: OTEL_EXPORTER_OTLP_ENDPOINT = '$OTEL'"
  [ -z "$OTEL" ] && echo "  *** ConfigMap updated, value is empty ***" && break
  sleep 10
done

echo
echo "=== K3. find new engine pod (configmap checksum changes → deployment rolls) ==="
sleep 20
ENG=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
echo "engine pod: $ENG"
kubectl -n etradie-system get pod "$ENG"

echo
echo "=== K4. watch boot (no mesh + no OTel-FastAPI instrumentation = clean) ==="
for i in $(seq 1 30); do
  STATUS=$(kubectl -n etradie-system get pod "$ENG" \
    -o jsonpath='READY={.status.containerStatuses[?(@.name=="engine")].ready} PHASE={.status.phase} RESTARTS={.status.containerStatuses[?(@.name=="engine")].restartCount}')
  echo "  T+$((i*10))s: $STATUS"
  READY=$(kubectl -n etradie-system get pod "$ENG" \
    -o jsonpath='{.status.containerStatuses[?(@.name=="engine")].ready}')
  [ "$READY" = "true" ] && echo "  *** ENGINE READY ***" && break
  sleep 10
done

echo
echo "=== K5. log — should now show clean tracing_disabled + /health 200 ==="
kubectl -n etradie-system get pod "$ENG" -o wide
kubectl -n etradie-system logs "$ENG" -c engine --tail=80 2>&1 \
kubectl -n edge-ingress-system get pods 2>/dev/nulles.io/name in (etradie-gateway,etradie-execution,etradie-management,etradie-billing)'ror' | tail -30
=== K1. force ArgoCD sync ===
application.argoproj.io/engine-staging annotated
=== K2. wait for deployment template to flip OTEL_EXPORTER_OTLP_ENDPOINT to empty ===
  T+10s: OTEL_EXPORTER_OTLP_ENDPOINT = ''
  *** ConfigMap updated, value is empty ***

=== K3. find new engine pod (configmap checksum changes → deployment rolls) ===
engine pod: etradie-engine-55dbc59c78-7hgnx
NAME                              READY   STATUS    RESTARTS   AGE
etradie-engine-55dbc59c78-7hgnx   0/1     Running   0          33s

=== K4. watch boot (no mesh + no OTel-FastAPI instrumentation = clean) ===
  T+10s: READY=false PHASE=Running RESTARTS=0
  T+20s: READY=false PHASE=Running RESTARTS=0
  T+30s: READY=false PHASE=Running RESTARTS=0
  T+40s: READY=false PHASE=Running RESTARTS=0
  T+50s: READY=false PHASE=Running RESTARTS=0
  T+60s: READY=false PHASE=Running RESTARTS=0
  T+70s: READY=false PHASE=Running RESTARTS=0
  T+80s: READY=false PHASE=Running RESTARTS=0
  T+90s: READY=false PHASE=Running RESTARTS=0
  T+100s: READY=false PHASE=Running RESTARTS=0
  T+110s: READY=false PHASE=Running RESTARTS=0
  T+120s: READY=false PHASE=Running RESTARTS=0
  T+130s: READY=false PHASE=Running RESTARTS=0
  T+140s: READY=false PHASE=Running RESTARTS=0
  T+150s: READY=false PHASE=Running RESTARTS=0
  T+160s: READY=false PHASE=Running RESTARTS=0
  T+170s: READY=false PHASE=Running RESTARTS=0
  T+180s: READY=false PHASE=Running RESTARTS=0
  T+190s: READY=false PHASE=Running RESTARTS=0
  T+200s: READY=false PHASE=Running RESTARTS=0
  T+210s: READY=false PHASE=Running RESTARTS=0
  T+220s: READY=false PHASE=Running RESTARTS=0
  T+230s: READY=false PHASE=Running RESTARTS=0
  T+240s: READY=false PHASE=Running RESTARTS=0
  T+250s: READY=false PHASE=Running RESTARTS=0
  T+260s: READY=false PHASE=Running RESTARTS=0
  T+270s: READY=false PHASE=Running RESTARTS=0
  T+280s: READY=false PHASE=Running RESTARTS=0
  T+290s: READY=false PHASE=Running RESTARTS=0
  T+300s: READY=false PHASE=Running RESTARTS=0

=== K5. log — should now show clean tracing_disabled + /health 200 ===
NAME                              READY   STATUS    RESTARTS   AGE     IP           NODE         NOMINATED NODE   READINESS GATES
etradie-engine-55dbc59c78-7hgnx   0/1     Running   0          6m57s   10.42.0.34   vmi3362776   <none>           <none>
INFO:     10.42.0.1:48704 - "GET /health HTTP/1.1" 200 OK
INFO:     10.42.0.1:35508 - "GET /health HTTP/1.1" 200 OK
INFO:     10.42.0.1:43954 - "GET /health HTTP/1.1" 200 OK

=== K6. cascade — gateway/execution/management/billing/edge-ingress ===
NAME                                 READY   STATUS                  RESTARTS          AGE
etradie-billing-6bd67b7b55-dqwmh     0/2     Init:0/2                133 (7m ago)      15h
etradie-billing-75d844d7d8-w66s8     0/2     Init:Error              133 (7m22s ago)   15h
etradie-execution-6d89988995-7lnns   0/2     Init:0/2                117 (6m49s ago)   15h
etradie-execution-8576bf499-dzblv    0/2     Init:CrashLoopBackOff   117 (2m19s ago)   15h
etradie-gateway-785f4998f8-jb6pc     0/2     Init:CrashLoopBackOff   133 (56s ago)     15h
etradie-gateway-bfbc5fcf8-9p68r      0/2     Init:CrashLoopBackOff   133 (2m21s ago)   15h
etradie-management-f9d95547b-fb75p   0/2     Terminating             0                 2m21s
NAME                            READY   STATUS                  RESTARTS         AGE
cloudflared-fb8f66bf8-mwp7z     1/1     Running                 0                33h
edge-ingress-68489cd577-h9p8n   0/1     Init:CrashLoopBackOff   290 (3m3s ago)   24h
softverse@Softverse:~/eTradie$
softverse@Softverse:~/eTradie$
softverse@Softverse:~/eTradie$ export KUBECONFIG=~/.kube/etradie-contabo.yaml
ENG=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
echo "engine pod: $ENG"

echo
echo "=== D1. directly hit /readiness from inside the cluster (port-forward) ==="
kubectl -n etradie-system port-forward "$ENG" 18000:8000 >/tmp/pf.log 2>&1 &
PF=$!
sleep 3
curl -sS -o /tmp/readiness.body -w "HTTP=%{http_code} time=%{time_total}s\n" \
  http://127.0.0.1:18000/readiness
echo "--- /readiness response body ---"
cat /tmp/readiness.body
echo
kill $PF 2>/dev/null
wait $PF 2>/dev/null

echo
echo "=== D2. engine log — startup_health + readiness probe failures ==="
kubectl -n etradie-system logs "$ENG" -c engine --tail=600 2>&1 \
  | grep -iE 'startup_health|tracing_disabled|application_started|rag_bootstrap_completed|rag_health_startup|readiness|/readiness|503|db_health|cache_health|rag_startup|loaded_markdown' | tail -25

echo
echo "=== D3. one gateway pod's init log to see why it crashes ==="
GW=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-gateway \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
echo "gateway pod: $GW"
kubectl -n etradie-system get pod "$GW" -o jsonpath='{range .spec.initContainers[*]}{.name}{"\n"}{end}'
echo "--- last gateway init log ---"
kubectl -n etradie-system logs "$GW" -c wait-for-deps --previous --tail=20 2>/dev/null \
  || kubectl -n etradie-system logs "$GW" -c wait-for-deps --tail=20 2>/dev/null
engine pod: etradie-engine-55dbc59c78-7hgnx

=== D1. directly hit /readiness from inside the cluster (port-forward) ===
[1] 43944
HTTP=503 time=30.003990s
--- /readiness response body ---
{"status":"not_ready","db":true,"cache":true,"rag":{"enabled":true,"vectorstore_connected":true,"database_connected":true,"embedding_ready":false}}

=== D2. engine log — startup_health + readiness probe failures ===
INFO:     10.42.0.1:53514 - "GET /readiness HTTP/1.1" 503 Service Unavailable
{"event": "db_health_check_passed", "level": "DEBUG", "logger": "engine.shared.db.connection", "timestamp": "2026-06-16T17:02:52.432056Z"}
{"event": "cache_health_check_passed", "level": "DEBUG", "logger": "engine.shared.cache.redis_cache", "timestamp": "2026-06-16T17:02:52.434135Z"}
{"event": "db_health_check_passed", "level": "DEBUG", "logger": "engine.shared.db.connection", "timestamp": "2026-06-16T17:02:52.469983Z"}
{"event": "db_health_check_passed", "level": "DEBUG", "logger": "engine.shared.db.connection", "timestamp": "2026-06-16T17:02:57.441999Z"}
{"event": "cache_health_check_passed", "level": "DEBUG", "logger": "engine.shared.cache.redis_cache", "timestamp": "2026-06-16T17:02:57.444330Z"}
{"event": "db_health_check_passed", "level": "DEBUG", "logger": "engine.shared.db.connection", "timestamp": "2026-06-16T17:02:57.507007Z"}
{"extra": {"db": true, "cache": true, "rag": false}, "event": "readiness_probe_unhealthy", "level": "WARNING", "logger": "engine.routers.health", "timestamp": "2026-06-16T17:02:57.574105Z"}
{"event": "db_health_check_passed", "level": "DEBUG", "logger": "engine.shared.db.connection", "timestamp": "2026-06-16T17:03:01.199470Z"}
{"event": "cache_health_check_passed", "level": "DEBUG", "logger": "engine.shared.cache.redis_cache", "timestamp": "2026-06-16T17:03:01.200486Z"}
{"event": "db_health_check_passed", "level": "DEBUG", "logger": "engine.shared.db.connection", "timestamp": "2026-06-16T17:03:01.238551Z"}
{"extra": {"db": true, "cache": true, "rag": false}, "event": "readiness_probe_unhealthy", "level": "WARNING", "logger": "engine.routers.health", "timestamp": "2026-06-16T17:03:04.674947Z"}
{"event": "db_health_check_passed", "level": "DEBUG", "logger": "engine.shared.db.connection", "timestamp": "2026-06-16T17:03:05.535837Z"}
{"event": "cache_health_check_passed", "level": "DEBUG", "logger": "engine.shared.cache.redis_cache", "timestamp": "2026-06-16T17:03:05.537164Z"}
{"event": "db_health_check_passed", "level": "DEBUG", "logger": "engine.shared.db.connection", "timestamp": "2026-06-16T17:03:05.568966Z"}
{"extra": {"db": true, "cache": true, "rag": false}, "event": "readiness_probe_unhealthy", "level": "WARNING", "logger": "engine.routers.health", "timestamp": "2026-06-16T17:03:13.762954Z"}
{"event": "db_health_check_passed", "level": "DEBUG", "logger": "engine.shared.db.connection", "timestamp": "2026-06-16T17:03:15.536547Z"}
{"event": "cache_health_check_passed", "level": "DEBUG", "logger": "engine.shared.cache.redis_cache", "timestamp": "2026-06-16T17:03:15.538487Z"}
{"event": "db_health_check_passed", "level": "DEBUG", "logger": "engine.shared.db.connection", "timestamp": "2026-06-16T17:03:15.576256Z"}
{"extra": {"db": true, "cache": true, "rag": false}, "event": "readiness_probe_unhealthy", "level": "WARNING", "logger": "engine.routers.health", "timestamp": "2026-06-16T17:03:23.747681Z"}
{"event": "db_health_check_passed", "level": "DEBUG", "logger": "engine.shared.db.connection", "timestamp": "2026-06-16T17:03:25.534954Z"}
{"event": "cache_health_check_passed", "level": "DEBUG", "logger": "engine.shared.cache.redis_cache", "timestamp": "2026-06-16T17:03:25.536233Z"}
{"event": "db_health_check_passed", "level": "DEBUG", "logger": "engine.shared.db.connection", "timestamp": "2026-06-16T17:03:25.579058Z"}
{"extra": {"db": true, "cache": true, "rag": false}, "event": "readiness_probe_unhealthy", "level": "WARNING", "logger": "engine.routers.health", "timestamp": "2026-06-16T17:03:30.658771Z"}
INFO:     127.0.0.1:58000 - "GET /readiness HTTP/1.1" 503 Service Unavailable

=== D3. one gateway pod's init log to see why it crashes ===
gateway pod: etradie-gateway-bfbc5fcf8-9p68r
wait-for-deps
linkerd-init
--- last gateway init log ---
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
softverse@Softverse:~/eTradie$
softverse@Softverse:~/eTradie$