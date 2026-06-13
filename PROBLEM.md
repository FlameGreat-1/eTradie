


SECTION 1:




OTAL                                                                       24862  14079   6260    360    38%

=========================== short test summary info ============================
FAILED tests/chaos/test_hosted_recovery_service.py::test_start_background_loop_idempotent - AssertionError: assert 0 == 1
 +  where 0 = <MagicMock name='mock.create_task' id='140614840236704'>.call_count
 +    where <MagicMock name='mock.create_task' id='140614840236704'> = <MagicMock id='140614850875024'>.create_task
FAILED tests/chaos/test_outbound_limiter_and_pool.py::test_limiter_blocks_until_refill_and_raises_on_deadline - assert False is True
FAILED tests/chaos/test_prometheusrule_renders.py::test_mt_node_chart_renders_memory_leak_rule - AssertionError: helm template mt-node failed: Error: execution error at (mt-node/templates/statefulset.yaml:107:20): helm/mt-node: .Values.image.repository is REQUIRED. Set it in helm/mt-node/values-{staging,production}.yaml to the pinned mt-node image registry path, e.g. ghcr.io/<your-org>/etradie-mt-node.
  
  Use --debug flag to render out invalid YAML
  
assert 1 == 0
 +  where 1 = CompletedProcess(args=['helm', 'template', 'release', '/home/runner/work/eTradie/eTradie/helm/mt-node', '--namespace', 'etradie-system', '--set', 'mtConnection.enabled=true', '--set', 'mtConnection.connectionId=test-1234567890', '--set', 'mtConnection.userId=u-1', '--set', 'mtConnection.server=Exness-MT5Trial9', '--set', 'mtConnection.sealedSecretName=test-secret'], returncode=1, stdout='', stderr='Error: execution error at (mt-node/templates/statefulset.yaml:107:20): helm/mt-node: .Values.image.repository is REQUIRED. Set it in helm/mt-node/values-{staging,production}.yaml to the pinned mt-node image registry path, e.g. ghcr.io/<your-org>/etradie-mt-node.\n\nUse --debug flag to render out invalid YAML\n').returncode
FAILED tests/integration/test_broker_endpoints.py::TestAccountInfo::test_returns_balance_fields - assert 401 == 200
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestPositions::test_returns_position_list - assert 401 == 200
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestPendingOrders::test_returns_order_list - assert 401 == 200
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestSymbolInfo::test_returns_instrument_metadata - assert 401 == 200
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestSymbolInfo::test_missing_symbol_returns_400 - assert 401 == 400
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestTickPrice::test_returns_bid_ask - assert 401 == 200
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestTickPrice::test_missing_symbol_returns_400 - assert 401 == 400
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestPosition::test_returns_position_by_ticket - assert 401 == 200
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestPosition::test_missing_ticket_returns_400 - assert 401 == 400
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestPlaceOrder::test_market_order - assert 401 == 200
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestPlaceOrder::test_limit_order - assert 401 == 200
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestPlaceOrder::test_missing_symbol_returns_400 - assert 401 == 400
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestCancelOrder::test_cancel_success - assert 401 == 200
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestModifyPosition::test_modify_success - assert 401 == 200
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestModifyPosition::test_missing_ticket_returns_400 - assert 401 == 400
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestClosePartial::test_partial_close_success - assert 401 == 200
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestClosePartial::test_zero_volume_returns_400 - assert 401 == 400
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestClosePosition::test_close_success - assert 401 == 200
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_broker_endpoints.py::TestClosePosition::test_missing_ticket_returns_400 - assert 401 == 400
 +  where 401 = <Response [401 Unauthorized]>.status_code
FAILED tests/integration/test_ta_repositories.py::TestSnapshotRepository::test_create_and_get_by_id - engine.shared.exceptions.DatabaseOperationalError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "technical_snapshots" does not exist
[SQL: SELECT max(technical_snapshots.version) AS max_1 
FROM technical_snapshots 
WHERE technical_snapshots.user_id = $1::VARCHAR AND technical_snapshots.symbol = $2::VARCHAR AND technical_snapshots.timeframe = $3::VARCHAR]
[parameters: ('test_user_id_123', 'EURUSD_b3d129', 'H4')]
(Background on this error at: https://sqlalche.me/e/20/f405)
FAILED tests/integration/test_ta_repositories.py::TestSnapshotRepository::test_get_latest_snapshot - engine.shared.exceptions.DatabaseOperationalError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "technical_snapshots" does not exist
[SQL: SELECT max(technical_snapshots.version) AS max_1 
FROM technical_snapshots 
WHERE technical_snapshots.user_id = $1::VARCHAR AND technical_snapshots.symbol = $2::VARCHAR AND technical_snapshots.timeframe = $3::VARCHAR]
[parameters: ('test_user_id_123', 'GBPUSD_cf5db4', 'D1')]
(Background on this error at: https://sqlalche.me/e/20/f405)
FAILED tests/integration/test_ta_repositories.py::TestSnapshotRepository::test_version_auto_increments - engine.shared.exceptions.DatabaseOperationalError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "technical_snapshots" does not exist
[SQL: SELECT max(technical_snapshots.version) AS max_1 
FROM technical_snapshots 
WHERE technical_snapshots.user_id = $1::VARCHAR AND technical_snapshots.symbol = $2::VARCHAR AND technical_snapshots.timeframe = $3::VARCHAR]
[parameters: ('test_user_id_123', 'USDJPY_a1a628', 'H1')]
(Background on this error at: https://sqlalche.me/e/20/f405)
FAILED tests/integration/test_ta_repositories.py::TestSnapshotRepository::test_get_snapshot_count - engine.shared.exceptions.DatabaseOperationalError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "technical_snapshots" does not exist
[SQL: SELECT max(technical_snapshots.version) AS max_1 
FROM technical_snapshots 
WHERE technical_snapshots.user_id = $1::VARCHAR AND technical_snapshots.symbol = $2::VARCHAR AND technical_snapshots.timeframe = $3::VARCHAR]
[parameters: ('test_user_id_123', 'TEST5EE023', 'M15')]
(Background on this error at: https://sqlalche.me/e/20/f405)
FAILED tests/integration/test_ta_repositories.py::TestSnapshotRepository::test_delete_by_id - engine.shared.exceptions.DatabaseOperationalError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "technical_snapshots" does not exist
[SQL: SELECT max(technical_snapshots.version) AS max_1 
FROM technical_snapshots 
WHERE technical_snapshots.user_id = $1::VARCHAR AND technical_snapshots.symbol = $2::VARCHAR AND technical_snapshots.timeframe = $3::VARCHAR]
[parameters: ('test_user_id_123', 'XAUUSD', 'W1')]
(Background on this error at: https://sqlalche.me/e/20/f405)
FAILED tests/shared/http/client.py::test_get_success - engine.shared.exceptions.HttpClientError: Unexpected error during test request: ClientResponse.__init__() missing 1 required keyword-only argument: 'stream_writer'
FAILED tests/shared/http/client.py::test_post_success - engine.shared.exceptions.HttpClientError: Unexpected error during test request: ClientResponse.__init__() missing 1 required keyword-only argument: 'stream_writer'
FAILED tests/shared/http/client.py::test_rate_limit_handling - engine.shared.exceptions.HttpClientError: Unexpected error during unknown request: ClientResponse.__init__() missing 1 required keyword-only argument: 'stream_writer'
FAILED tests/shared/http/client.py::test_non_retryable_error - engine.shared.exceptions.HttpClientError: Unexpected error during unknown request: ClientResponse.__init__() missing 1 required keyword-only argument: 'stream_writer'
FAILED tests/shared/http/client.py::test_server_error_retry - engine.shared.exceptions.HttpClientError: Unexpected error during unknown request: ClientResponse.__init__() missing 1 required keyword-only argument: 'stream_writer'
FAILED tests/shared/http/client.py::test_circuit_breaker_trip - engine.shared.exceptions.HttpClientError: Unexpected error during test request: ClientResponse.__init__() missing 1 required keyword-only argument: 'stream_writer'
ERROR tests/api/test_dashboard_api.py::TestHealthEndpoints::test_health_endpoint - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestHealthEndpoints::test_health_rag - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisLatest::test_analysis_latest - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisLatest::test_analysis_latest_filter_by_pair - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisLatest::test_analysis_latest_limit - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisHistory::test_analysis_history - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisHistory::test_analysis_history_filter_status - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisHistory::test_analysis_history_filter_grade - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisHistory::test_analysis_history_filter_provider - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisHistory::test_analysis_history_pagination - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisStats::test_analysis_stats - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisStats::test_analysis_stats_filter_pair - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisDetail::test_analysis_detail - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisDetail::test_analysis_detail_not_found - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisRerun::test_analysis_rerun_ta_unavailable - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisRerun::test_analysis_rerun_empty_symbol - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestAnalysisRerun::test_analysis_rerun_no_auth - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestProcessorConfig::test_processor_models - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestProcessorConfig::test_processor_config_get - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]

RROR tests/api/test_dashboard_api.py::TestProcessorConfig::test_processor_config_update_temperature - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestProcessorConfig::test_processor_config_update_invalid_provider - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestProcessorConfig::test_regular_user_rejected_from_processor_models - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestProcessorConfig::test_regular_user_rejected_from_processor_config_get - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestProcessorConfig::test_regular_user_rejected_from_processor_config_put - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
ERROR tests/api/test_dashboard_api.py::TestProcessorConfig::test_no_auth_returns_401 - pydantic_core._pydantic_core.ValidationError: 1 validation error for MT5Config
  Value error, MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi [type=value_error, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.9/v/value_error
======= 33 failed, 466 passed, 23 skipped, 25 errors in 61.25s (0:01:01) =======



SECTION 2:  



13s
Run docker/build-push-action@v6
GitHub Actions runtime token ACs
Docker info
Proxy configuration
Buildx version
Builder info
/usr/bin/docker buildx build --cache-from type=gha,scope=billing --file src/billing/Dockerfile --iidfile /home/runner/work/_temp/docker-actions-toolkit-qwroSc/build-iidfile-97ef29d72e.txt --tag etradie/billing:scan --load --metadata-file /home/runner/work/_temp/docker-actions-toolkit-qwroSc/build-metadata-006cb78b30.json .
#0 building with "builder-b5e6ed2d-9c4c-4d72-9a11-b25830b69700" instance using docker-container driver

#1 [internal] load build definition from Dockerfile
#1 transferring dockerfile: 1.28kB done
#1 DONE 0.0s

#2 [auth] library/golang:pull token for registry-1.docker.io
#2 DONE 0.0s

#3 [auth] library/alpine:pull token for registry-1.docker.io
#3 DONE 0.0s

#4 [internal] load metadata for docker.io/library/golang:1.25-alpine
#4 ...

#5 [internal] load metadata for docker.io/library/alpine:3.20
#5 DONE 0.6s

#4 [internal] load metadata for docker.io/library/golang:1.25-alpine
#4 DONE 0.6s

#6 [internal] load .dockerignore
#6 transferring context: 638B done
#6 DONE 0.0s

#7 importing cache manifest from gha:14055370830121197203
#7 DONE 0.0s

#8 [runtime 1/4] FROM docker.io/library/alpine:3.20@sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc
#8 resolve docker.io/library/alpine:3.20@sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc done
#8 sha256:25f1d6b1951ac8eb3740558fe94cb83d377bdadf95fd9f98b50d2e1b96130471 3.63MB / 3.63MB 0.1s done
#8 DONE 0.1s

#9 [builder 1/7] FROM docker.io/library/golang:1.25-alpine@sha256:8d95af53d0d58e1759ddb4028285d9b1239067e4fbf4f544618cad0f60fbc354
#9 resolve docker.io/library/golang:1.25-alpine@sha256:8d95af53d0d58e1759ddb4028285d9b1239067e4fbf4f544618cad0f60fbc354 done
#9 sha256:4f4fb700ef54461cfa02571ae0db9a0dc1e0cdb5577484a6d75e68dc38e8acc1 32B / 32B done
#9 sha256:1c222edac8107d5a3691e31c4d7c3420e5e0ea0c26e110125aa79a4f09a1c1d6 125B / 125B 0.0s done
#9 sha256:54a5de338fb4d7451a8806e26d415c6f24cebed06386053e5874af301ed71727 290.24kB / 290.24kB 0.1s done
#9 sha256:9b70e313681f44d32991ec943f89228bc91d7431d4a84feafc269a76e3f96a63 3.87MB / 3.87MB 0.1s done
#9 extracting sha256:9b70e313681f44d32991ec943f89228bc91d7431d4a84feafc269a76e3f96a63
#9 sha256:05c934f997ad58295f8830de88f3ab19fa41578d69bb3a3fd4d4960be4ce8df9 23.07MB / 60.23MB 0.2s
#9 sha256:05c934f997ad58295f8830de88f3ab19fa41578d69bb3a3fd4d4960be4ce8df9 60.23MB / 60.23MB 0.4s done
#9 ...

#8 [runtime 1/4] FROM docker.io/library/alpine:3.20@sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc
#8 extracting sha256:25f1d6b1951ac8eb3740558fe94cb83d377bdadf95fd9f98b50d2e1b96130471 0.5s done
#8 DONE 0.6s

#9 [builder 1/7] FROM docker.io/library/golang:1.25-alpine@sha256:8d95af53d0d58e1759ddb4028285d9b1239067e4fbf4f544618cad0f60fbc354
#9 extracting sha256:9b70e313681f44d32991ec943f89228bc91d7431d4a84feafc269a76e3f96a63 0.4s done
#9 extracting sha256:54a5de338fb4d7451a8806e26d415c6f24cebed06386053e5874af301ed71727
#9 extracting sha256:54a5de338fb4d7451a8806e26d415c6f24cebed06386053e5874af301ed71727 0.2s done
#9 extracting sha256:05c934f997ad58295f8830de88f3ab19fa41578d69bb3a3fd4d4960be4ce8df9
#9 ...

#10 [internal] load build context
#10 transferring context: 24.06MB 1.3s done
#10 DONE 1.3s

#11 [runtime 2/4] RUN apk --no-cache add ca-certificates tzdata     && rm -rf /var/cache/apk/*
#11 0.123 fetch https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64/APKINDEX.tar.gz
#11 0.625 fetch https://dl-cdn.alpinelinux.org/alpine/v3.20/community/x86_64/APKINDEX.tar.gz
#11 1.120 (1/2) Installing ca-certificates (20260413-r0)
#11 1.153 (2/2) Installing tzdata (2026b-r0)
#11 1.233 Executing busybox-1.36.1-r31.trigger
#11 1.245 Executing ca-certificates-20260413-r0.trigger
#11 1.309 OK: 10 MiB in 16 packages
#11 DONE 2.0s

#9 [builder 1/7] FROM docker.io/library/golang:1.25-alpine@sha256:8d95af53d0d58e1759ddb4028285d9b1239067e4fbf4f544618cad0f60fbc354
#9 ...

#12 [runtime 3/4] WORKDIR /app
#12 DONE 0.1s

#9 [builder 1/7] FROM docker.io/library/golang:1.25-alpine@sha256:8d95af53d0d58e1759ddb4028285d9b1239067e4fbf4f544618cad0f60fbc354
#9 extracting sha256:05c934f997ad58295f8830de88f3ab19fa41578d69bb3a3fd4d4960be4ce8df9 4.2s done
#9 DONE 5.0s

#9 [builder 1/7] FROM docker.io/library/golang:1.25-alpine@sha256:8d95af53d0d58e1759ddb4028285d9b1239067e4fbf4f544618cad0f60fbc354
#9 extracting sha256:1c222edac8107d5a3691e31c4d7c3420e5e0ea0c26e110125aa79a4f09a1c1d6 done
#9 extracting sha256:4f4fb700ef54461cfa02571ae0db9a0dc1e0cdb5577484a6d75e68dc38e8acc1 done
#9 DONE 5.0s

#13 [builder 2/7] WORKDIR /src
#13 DONE 0.4s

#14 [builder 3/7] RUN apk add --no-cache git ca-certificates tzdata make
#14 5.062 WARNING: fetching https://dl-cdn.alpinelinux.org/alpine/v3.24/main/x86_64/APKINDEX.tar.gz: DNS: transient error (try again later)
#14 5.378 ERROR: unable to select packages:
#14 5.378   git (no such package):
#14 5.378     required by: world[git]
#14 5.378   make (no such package):
#14 5.378     required by: world[make]
#14 5.378   tzdata (no such package):
#14 5.378     required by: world[tzdata]
#14 ERROR: process "/bin/sh -c apk add --no-cache git ca-certificates tzdata make" did not complete successfully: exit code: 3
------
 > [builder 3/7] RUN apk add --no-cache git ca-certificates tzdata make:
5.062 WARNING: fetching https://dl-cdn.alpinelinux.org/alpine/v3.24/main/x86_64/APKINDEX.tar.gz: DNS: transient error (try again later)
5.378 ERROR: unable to select packages:
5.378   git (no such package):
5.378     required by: world[git]
5.378   make (no such package):
5.378     required by: world[make]
5.378   tzdata (no such package):
5.378     required by: world[tzdata]
------
Dockerfile:6
--------------------
   4 |     WORKDIR /src
   5 |     
   6 | >>> RUN apk add --no-cache git ca-certificates tzdata make
   7 |     
   8 |     COPY go.mod go.sum* ./
--------------------
ERROR: failed to build: failed to solve: process "/bin/sh -c apk add --no-cache git ca-certificates tzdata make" did not complete successfully: exit code: 3
Reference
Check build summary support
Error: buildx failed with: ERROR: failed to build: failed to solve: process "/bin/sh -c apk add --no-cac


SECTION 3:


stBuild_MacroFlags_DXYPresent
--- PASS: TestBuild_MacroFlags_DXYPresent (0.00s)
=== RUN   TestBuild_MacroFlags_QEQTPresent
--- PASS: TestBuild_MacroFlags_QEQTPresent (0.00s)
=== RUN   TestBuild_AllFrameworksAlwaysIncludesWyckoff
--- PASS: TestBuild_AllFrameworksAlwaysIncludesWyckoff (0.00s)
=== RUN   TestBuild_SymbolPassthrough
--- PASS: TestBuild_SymbolPassthrough (0.00s)
PASS
ok  	github.com/flamegreat-1/etradie/src/gateway/internal/querybuilder	0.007s
=== RUN   TestCheckHighImpactEventProximity_NoCalendar
--- PASS: TestCheckHighImpactEventProximity_NoCalendar (0.00s)
=== RUN   TestCheckHighImpactEventProximity_NoHighImpactEvents
--- PASS: TestCheckHighImpactEventProximity_NoHighImpactEvents (0.00s)
=== RUN   TestCheckHighImpactEventProximity_HighImpactWithinLockout
--- PASS: TestCheckHighImpactEventProximity_HighImpactWithinLockout (0.00s)
=== RUN   TestCheckHighImpactEventProximity_HighImpactOutsideLockout
--- PASS: TestCheckHighImpactEventProximity_HighImpactOutsideLockout (0.00s)
=== RUN   TestCheckCounterTrend_NoTrade
--- PASS: TestCheckCounterTrend_NoTrade (0.00s)
=== RUN   TestCheckCounterTrend_AlignedTrade
--- PASS: TestCheckCounterTrend_AlignedTrade (0.00s)
=== RUN   TestCheckCounterTrend_CounterWithoutChoch_Reject
--- PASS: TestCheckCounterTrend_CounterWithoutChoch_Reject (0.00s)
=== RUN   TestCheckCounterTrend_CounterWithChoch_Warn
--- PASS: TestCheckCounterTrend_CounterWithChoch_Warn (0.00s)
=== RUN   TestCheckCounterTrend_BearishTrendLongDirection_Reject
--- PASS: TestCheckCounterTrend_BearishTrendLongDirection_Reject (0.00s)
=== RUN   TestCheckWeekendGapRisk_Weekday
--- PASS: TestCheckWeekendGapRisk_Weekday (0.00s)
=== RUN   TestCheckLowLiquidityHours
--- PASS: TestCheckLowLiquidityHours (0.00s)
=== RUN   TestGuardEvaluator_AllPassOnAlignedTrade
--- PASS: TestGuardEvaluator_AllPassOnAlignedTrade (0.00s)
=== RUN   TestGuardEvaluator_CounterTrendRejectsWithoutChoch
--- PASS: TestGuardEvaluator_CounterTrendRejectsWithoutChoch (0.00s)
=== RUN   TestEvaluatePreLLM_ContainsOnlyDeterministicChecks
--- PASS: TestEvaluatePreLLM_ContainsOnlyDeterministicChecks (0.00s)
=== RUN   TestEvaluatePostLLM_ContainsOnlyCounterTrend
--- PASS: TestEvaluatePostLLM_ContainsOnlyCounterTrend (0.00s)
=== RUN   TestMergeResults_PreservesCanonicalOrder
--- PASS: TestMergeResults_PreservesCanonicalOrder (0.00s)
=== RUN   TestMergeResults_PreLLMRejectStillRejectsAfterMerge
--- PASS: TestMergeResults_PreLLMRejectStillRejectsAfterMerge (0.00s)
=== RUN   TestRouter_NoSetup_ProcessorRejects
--- PASS: TestRouter_NoSetup_ProcessorRejects (0.00s)
=== RUN   TestRouter_GuardRejection_NoExecution
--- PASS: TestRouter_GuardRejection_NoExecution (0.00s)
=== RUN   TestRouter_TradeApproved_ExecutionCalled
--- PASS: TestRouter_TradeApproved_ExecutionCalled (0.00s)
=== RUN   TestRouter_NilExecutionPort_Graceful
--- PASS: TestRouter_NilExecutionPort_Graceful (0.00s)
=== RUN   TestRouter_ExecutionError_ReturnsError
--- PASS: TestRouter_ExecutionError_ReturnsError (0.00s)
=== RUN   TestRoutePreLLM_PassesThroughOnAllPass
--- PASS: TestRoutePreLLM_PassesThroughOnAllPass (0.00s)
=== RUN   TestRoutePreLLM_RejectsOnAsianSessionForXAUUSD
--- PASS: TestRoutePreLLM_RejectsOnAsianSessionForXAUUSD (0.00s)
PASS
ok  	github.com/flamegreat-1/etradie/src/gateway/internal/routing	0.015s
=== RUN   TestReverseProxy_PathRewrite
=== RUN   TestReverseProxy_PathRewrite/execution_state
=== RUN   TestReverseProxy_PathRewrite/execution_account
=== RUN   TestReverseProxy_PathRewrite/execution_settings
=== RUN   TestReverseProxy_PathRewrite/execution_orders_cancel
=== RUN   TestReverseProxy_PathRewrite/management_trades
=== RUN   TestReverseProxy_PathRewrite/management_pnl
=== RUN   TestReverseProxy_PathRewrite/engine_broker
=== RUN   TestReverseProxy_PathRewrite/engine_analysis
=== RUN   TestReverseProxy_PathRewrite/engine_llm
=== RUN   TestReverseProxy_PathRewrite/engine_usage
=== RUN   TestReverseProxy_PathRewrite/engine_processor
--- PASS: TestReverseProxy_PathRewrite (0.01s)
    --- PASS: TestReverseProxy_PathRewrite/execution_state (0.00s)
    --- PASS: TestReverseProxy_PathRewrite/execution_account (0.00s)
    --- PASS: TestReverseProxy_PathRewrite/execution_settings (0.00s)
    --- PASS: TestReverseProxy_PathRewrite/execution_orders_cancel (0.00s)
    --- PASS: TestReverseProxy_PathRewrite/management_trades (0.00s)
    --- PASS: TestReverseProxy_PathRewrite/management_pnl (0.00s)
    --- PASS: TestReverseProxy_PathRewrite/engine_broker (0.00s)
    --- PASS: TestReverseProxy_PathRewrite/engine_analysis (0.00s)
    --- PASS: TestReverseProxy_PathRewrite/engine_llm (0.00s)
    --- PASS: TestReverseProxy_PathRewrite/engine_usage (0.00s)
    --- PASS: TestReverseProxy_PathRewrite/engine_processor (0.00s)
=== RUN   TestReverseProxy_RewriteWithQueryString
--- PASS: TestReverseProxy_RewriteWithQueryString (0.00s)
=== RUN   TestReverseProxy_ForwardsCookieAndCSRF
--- PASS: TestReverseProxy_ForwardsCookieAndCSRF (0.00s)
=== RUN   TestReverseProxy_StatusAndBodyPassthrough
=== RUN   TestReverseProxy_StatusAndBodyPassthrough/tier_required_403
=== RUN   TestReverseProxy_StatusAndBodyPassthrough/llm_quota_429
--- PASS: TestReverseProxy_StatusAndBodyPassthrough (0.00s)
    --- PASS: TestReverseProxy_StatusAndBodyPassthrough/tier_required_403 (0.00s)
    --- PASS: TestReverseProxy_StatusAndBodyPassthrough/llm_quota_429 (0.00s)
=== RUN   TestReverseProxy_UnreachableUpstreamReturns502
--- PASS: TestReverseProxy_UnreachableUpstreamReturns502 (0.00s)
=== RUN   TestNewReverseProxyHandler_RejectsBadUpstream
--- PASS: TestNewReverseProxyHandler_RejectsBadUpstream (0.00s)
PASS
ok  	github.com/flamegreat-1/etradie/src/gateway/internal/server	0.026s
=== RUN   TestLoad_EmptyRedis_ReturnsDefaults
--- PASS: TestLoad_EmptyRedis_ReturnsDefaults (0.00s)
=== RUN   TestSave_Load_RoundTrip
--- PASS: TestSave_Load_RoundTrip (0.00s)
=== RUN   TestSetCycleInterval_GetCycleInterval
--- PASS: TestSetCycleInterval_GetCycleInterval (0.00s)
=== RUN   TestSetCycleInterval_OverwritesPrevious
--- PASS: TestSetCycleInterval_OverwritesPrevious (0.00s)
=== RUN   TestGetCycleInterval_NoOverride_ReturnsZero
--- PASS: TestGetCycleInterval_NoOverride_ReturnsZero (0.00s)
=== RUN   TestSave_OverwritesCompletely
--- PASS: TestSave_OverwritesCompletely (0.00s)
PASS
ok  	github.com/flamegreat-1/etradie/src/gateway/internal/settingsstore	0.023s
=== RUN   TestGetActiveSymbols_ReturnsDefaults_WhenEmpty
--- PASS: TestGetActiveSymbols_ReturnsDefaults_WhenEmpty (0.00s)
=== RUN   TestGetActiveSymbols_DefaultsAreCopy
--- PASS: TestGetActiveSymbols_DefaultsAreCopy (0.00s)
=== RUN   TestSetActiveSymbols_RoundTrip
--- PASS: TestSetActiveSymbols_RoundTrip (0.00s)
=== RUN   TestSetActiveSymbols_NormalizesToUppercase
--- PASS: TestSetActiveSymbols_NormalizesToUppercase (0.00s)
=== RUN   TestSetActiveSymbols_TrimsWhitespace
--- PASS: TestSetActiveSymbols_TrimsWhitespace (0.00s)
=== RUN   TestSetActiveSymbols_EmptyList_ReturnsFalse
--- PASS: TestSetActiveSymbols_EmptyList_ReturnsFalse (0.00s)
=== RUN   TestSetActiveSymbols_AllWhitespace_ReturnsFalse
--- PASS: TestSetActiveSymbols_AllWhitespace_ReturnsFalse (0.00s)
=== RUN   TestSetActiveSymbols_OverwritesPrevious
--- PASS: TestSetActiveSymbols_OverwritesPrevious (0.00s)
=== RUN   TestResetToDefaults_ClearsSelection
--- PASS: TestResetToDefaults_ClearsSelection (0.00s)
=== RUN   TestResetToDefaults_WhenAlreadyEmpty
--- PASS: TestResetToDefaults_WhenAlreadyEmpty (0.00s)
PASS
ok  	github.com/flamegreat-1/etradie/src/gateway/internal/symbolstore	0.022s
?   	github.com/flamegreat-1/etradie/src/gateway/internal/tradingplanadapter	[no test files]
FAIL
Error: Process completed with exit code 1.