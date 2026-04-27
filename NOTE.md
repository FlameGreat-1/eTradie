


g_orders HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.2:47304 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | 2026-04-25T20:47:56.096095Z [INFO     ] zmq_positions_fetched          [engine.ta.broker.mt5.zmq.client] extra={'count': 0}
etradie-engine  | INFO:     172.24.0.2:47304 - "GET /internal/broker/positions HTTP/1.1" 200 OK
etradie-engine  | 2026-04-25T20:47:56.144020Z [INFO     ] zmq_pending_orders_fetched     [engine.ta.broker.mt5.zmq.client] extra={'count': 1}
etradie-engine  | INFO:     172.24.0.2:47304 - "GET /internal/broker/pending_orders HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.2:47304 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | INFO:     127.0.0.1:53288 - "GET /health HTTP/1.1" 200 OK
etradie-engine  | 2026-04-25T20:48:04.870641Z [INFO     ] llm_response_parsed            [engine.processor.parsing.response_parser] extra={'analysis_id': 'analysis_Boom_1000_Index_20260425_2048_a4b1', 'pair': 'Boom 1000 Index', 'direction': 'SHORT', 'grade': 'A', 'score': 7.0, 'warnings_count': 0, 'trace_id': '4b1e86cd9bd1e9532cf10ad196a460c9'}
etradie-engine  | 2026-04-25T20:48:04.879090Z [INFO     ] stream_subscriber_stopped      [engine.main] extra={'user_id': 'f4d8853ca258f665b3d000b0097c2225', 'channel': 'etradie:stream:user:f4d8853ca258f665b3d000b0097c2225'}
etradie-engine  | 2026-04-25T20:48:04.910731Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_output', 'operation': 'execute_query', 'duration_ms': 7.19, 'row_count': 1, 'trace_id': None}
etradie-engine  | INFO:     172.24.0.1:46322 - "GET /api/analysis/latest?limit=1 HTTP/1.1" 200 OK
etradie-engine  | 2026-04-25T20:48:04.939995Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_output', 'operation': 'execute_query', 'duration_ms': 19.28, 'row_count': 50, 'trace_id': None}
etradie-engine  | INFO:     172.24.0.1:47734 - "GET /api/analysis/latest?limit=50 HTTP/1.1" 200 OK
etradie-engine  | 2026-04-25T20:48:04.951506Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_output', 'operation': 'upsert', 'duration_ms': 77.97, 'row_count': 1, 'trace_id': None}
etradie-engine  | 2026-04-25T20:48:04.952003Z [DEBUG    ] repository_upsert_executed     [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_output', 'index_elements': ['analysis_id'], 'update_fields': ['direction', 'setup_grade', 'confluence_score', 'confidence', 'proceed_to_module_b', 'status', 'error_message', 'duration_ms', 'raw_output'], 'idempotency_key': None, 'trace_id': None}
etradie-engine  | 2026-04-25T20:48:04.970004Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_audit_log', 'operation': 'add', 'duration_ms': 16.35, 'row_count': 1, 'trace_id': None}
etradie-engine  | 2026-04-25T20:48:04.993518Z [DEBUG    ] db_transaction_committed       [engine.shared.db.connection] extra={'trace_id': None, 'duration_ms': 121.0}
etradie-engine  | 2026-04-25T20:48:04.994316Z [INFO     ] processor_completed            [engine.processor.service] extra={'symbol': 'Boom 1000 Index', 'analysis_id': 'analysis_Boom_1000_Index_20260425_2048_a4b1', 'direction': 'SHORT', 'grade': 'A', 'score': 7.0, 'confidence': 'HIGH', 'proceed': 'YES', 'rr_ratio': 31.89, 'duration_ms': 135909.1, 'input_tokens': 267352, 'output_tokens': 4379, 'warnings': [], 'trace_id': '4b1e86cd9bd1e9532cf10ad196a460c9'}
etradie-engine  | INFO:     172.24.0.9:37544 - "POST /internal/processor/process HTTP/1.1" 200 OK
etradie-engine  | 2026-04-25T20:48:05.793026Z [INFO     ] debug_output_saved             [engine.main] extra={'symbol': 'Boom 1000 Index', 'subdirectory': 'runcycle', 'directory': '/output/runcycle/Boom 1000 Index_20260425T204805Z', 'files': ['ta_snapshots', 'ta_smc_candidates', 'ta_snd_candidates', 'ta_metadata', 'macro_analysis', 'rag_knowledge', 'processor_result', 'execution_request']}
etradie-engine  | INFO:     172.24.0.9:37544 - "POST /internal/debug/runcycle HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.3:41770 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
etradie-engine  | INFO:     172.24.0.3:41770 - "GET /metrics/ HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.2:43928 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | 2026-04-25T20:48:13.220420Z [INFO     ] zmq_positions_fetched          [engine.ta.broker.mt5.zmq.client] extra={'count': 0}
etradie-engine  | INFO:     172.24.0.2:43928 - "GET /internal/broker/positions HTTP/1.1" 200 OK
etradie-engine  | 2026-04-25T20:48:13.332702Z [INFO     ] zmq_pending_orders_fetched     [engine.ta.broker.mt5.zmq.client] extra={'count': 1}
etradie-engine  | INFO:     172.24.0.2:43928 - "GET /internal/broker/pending_orders HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.2:43928 - "GET /internal/broker/symbol_info?symbol=Boom+1000+Index HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.2:43928 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.2:43928 - "GET /internal/broker/symbol_info?symbol=Boom+1000+Index HTTP/1.1" 200 OK
etradie-engine  | 2026-04-25T20:48:13.636749Z [ERROR    ] broker_place_order_failed      [engine.main] extra={'symbol': 'Boom 1000 Index', 'direction': 'SELL', 'error': 'ZMQ EA error: OrderSend failed: 10031 - Request rejected due to absence of network connection', 'user_id': 'f4d8853ca258f665b3d000b0097c2225'}
etradie-engine  | INFO:     172.24.0.2:43928 - "POST /internal/broker/place_order HTTP/1.1" 502 Bad Gateway
etradie-engine  | INFO:     127.0.0.1:44470 - "GET /health HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.3:44254 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
etradie-engine  | INFO:     172.24.0.3:44254 - "GET /metrics/ HTTP/1.1" 200 OK
etradie-engine  | INFO:     127.0.0.1:44454 - "GET /health HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.3:57926 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
etradie-engine  | INFO:     172.24.0.3:57926 - "GET /metrics/ HTTP/1.1" 200 OK






nt":"scheduler","user_id":"f4d8853ca258f665b3d000b0097c2225","username":"flamegreat","symbols":["Boom 1000 Index"],"timestamp":1777149073116,"event":"user_cycle_completed"}
etradie-gateway  | {"level":"info","service":"etradie-gateway","component":"api_handler","symbols":["Boom 1000 Index"],"trace_id":"","timestamp":1777149907786,"event":"dashboard_run_cycle_triggered"}
etradie-gateway  | {"level":"info","service":"etradie-gateway","component":"orchestrator","trace_id":"4b1e86cd9bd1e9532cf10ad196a460c9","cycle_id":"4da9a0df5d15363064e69d402cce3de1","symbols":["Boom 1000 Index"],"attempt":1,"timestamp":1777149907786,"event":"cycle_started"}
etradie-gateway  | {"level":"info","service":"etradie-gateway","component":"ta_collector","symbols_requested":["Boom 1000 Index"],"symbols_total":1,"symbols_success":1,"duration_ms":37982,"trace_id":"4b1e86cd9bd1e9532cf10ad196a460c9","timestamp":1777149944813,"event":"ta_collection_completed"}
etradie-gateway  | {"level":"info","service":"etradie-gateway","component":"macro_collector","datasets_available":["central_bank","economic","news","calendar","dxy","intermarket","sentiment"],"datasets_failed":["cot"],"duration_ms":40771,"trace_id":"4b1e86cd9bd1e9532cf10ad196a460c9","timestamp":1777149947602,"event":"macro_collection_completed"}
etradie-gateway  | {"level":"info","service":"etradie-gateway","component":"guard_evaluator","overall_verdict":"PASS","blocking_rules":[],"checks_total":5,"duration_ms":0.0135,"trace_id":"4b1e86cd9bd1e9532cf10ad196a460c9","timestamp":1777150085051,"event":"guard_evaluation_completed"}
etradie-gateway  | {"level":"info","service":"etradie-gateway","component":"execution_grpc_adapter","symbol":"Boom 1000 Index","direction":"SHORT","grade":"A","analysis_id":"BOOM 1000 INDEX_SH_BMS_RTO_BEARISH_BEARISH_14464.993_c2de5b09","timestamp":1777150085056,"event":"calling_execution_service"}
etradie-gateway  | {"level":"info","service":"etradie-gateway","component":"execution_grpc_adapter","symbol":"Boom 1000 Index","accepted":false,"status":"REJECTED","order_id":"","timestamp":1777150093660,"event":"execution_response_received"}
etradie-gateway  | {"level":"info","service":"etradie-gateway","component":"decision_router","symbol":"Boom 1000 Index","direction":"SHORT","confidence":0.85,"grade":"A","guard_verdict":"PASS","trace_id":"4b1e86cd9bd1e9532cf10ad196a460c9","timestamp":1777150093660,"event":"route_trade_approved"}
etradie-gateway  | {"level":"info","service":"etradie-gateway","component":"orchestrator","trace_id":"4b1e86cd9bd1e9532cf10ad196a460c9","cycle_id":"4da9a0df5d15363064e69d402cce3de1","status":"COMPLETED","outcome":"TRADE_APPROVED","duration_ms":187738,"outputs_count":1,"attempt":1,"will_retry":false,"timestamp":1777150093662,"event":"cycle_finished"}
