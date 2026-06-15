ants.py::TestSession::test_overlap_within_london_and_ny PASSED [ 99%]
tests/ta/test_orchestrator.py::test_fetch_sequence_success_primary_broker PASSED [ 99%]
tests/ta/test_orchestrator.py::test_fetch_sequence_fails_over_to_fallback PASSED [ 99%]
tests/ta/test_orchestrator.py::test_fetch_sequence_both_brokers_fail PASSED [100%]

=================================== FAILURES ===================================
________ TestEndpointPaths.test_internal_pipeline_endpoints_registered _________
tests/api/endpoints.py:61: in test_internal_pipeline_endpoints_registered
    assert path in registered_paths
E   AssertionError: assert '/internal/ta/analyze' in {'', '/docs', '/docs/oauth2-redirect', '/metrics', '/openapi.json'}
__________ TestEndpointPaths.test_broker_bridge_endpoints_registered ___________
tests/api/endpoints.py:77: in test_broker_bridge_endpoints_registered
    assert path in registered_paths
E   AssertionError: assert '/internal/broker/account_info' in {'', '/docs', '/docs/oauth2-redirect', '/metrics', '/openapi.json'}
______________ TestEndpointPaths.test_health_endpoint_registered _______________
tests/api/endpoints.py:84: in test_health_endpoint_registered
    assert "/health" in registered_paths
E   AssertionError: assert '/health' in {'', '/docs', '/docs/oauth2-redirect', '/metrics', '/openapi.json'}
____________ TestEndpointPaths.test_dashboard_endpoints_registered _____________
tests/api/endpoints.py:93: in test_dashboard_endpoints_registered
    assert path in registered_paths
E   AssertionError: assert '/api/analysis/latest' in {'', '/docs', '/docs/oauth2-redirect', '/metrics', '/openapi.json'}

---------- coverage: platform linux, python 3.12.13-final-0 ----------
Name                                                                        Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------------------------------------------------------------
src/engine/__init__.py                                                          0      0      0      0   100%
src/engine/admin/__init__.py           

6, 236-248, 258-267, 271-284, 296-319
src/engine/ta/storage/repositories/snapshot.py                                 51      8      4      1    80%   132-145, 180-198, 226
src/engine/ta/storage/schemas/__init__.py                                       5      0      0      0   100%
src/engine/ta/storage/schemas/broker_symbol.py                                 17      0      0      0   100%
src/engine/ta/storage/schemas/candidate.py                                     81      0      0      0   100%
src/engine/ta/storage/schemas/candle.py                                        25      0      0      0   100%
src/engine/ta/storage/schemas/snapshot.py                                      38      0      0      0   100%
src/engine/ta/storage/uow.py                                                  117     74     20      0    31%   35-41, 45-47, 51-53, 57-59, 63-65, 68-77, 80-89, 107-113, 117-119, 123-125, 129-131, 135-137, 140-149, 152-161, 172, 181
src/engine/verify_chroma.py                                                    23     23     10      0     0%   1-38
-----------------------------------------------------------------------------------------------------------------------
TOTAL                                                                       24877  12982   6266    476    42%

=========================== short test summary info ============================
FAILED tests/api/endpoints.py::TestEndpointPaths::test_internal_pipeline_endpoints_registered - AssertionError: assert '/internal/ta/analyze' in {'', '/docs', '/docs/oauth2-redirect', '/metrics', '/openapi.json'}
FAILED tests/api/endpoints.py::TestEndpointPaths::test_broker_bridge_endpoints_registered - AssertionError: assert '/internal/broker/account_info' in {'', '/docs', '/docs/oauth2-redirect', '/metrics', '/openapi.json'}
FAILED tests/api/endpoints.py::TestEndpointPaths::test_health_endpoint_registered - AssertionError: assert '/health' in {'', '/docs', '/docs/oauth2-redirect', '/metrics', '/openapi.json'}
FAILED tests/api/endpoints.py::TestEndpointPaths::test_dashboard_endpoints_registered - AssertionError: assert '/api/analysis/latest' in {'', '/docs', '/docs/oauth2-redirect', '/metrics', '/openapi.json'}
================== 4 failed, 520 passed, 23 skipped in 55.93s ==================
Error: Process completed with exit code 1.
