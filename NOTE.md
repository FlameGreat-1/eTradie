


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


















YOU HAVE FULL AND COMPLETE READ AND WRITE ACCESS TO THE REPO FROM MY OTHER ACCOUNT BECAUSE I HAVE ADDED YOU AS A GROUP MEMEBER WITH A DEVELOPER ROLE:

https://gitlab.com/cotradee3/cotradeecode

SO IT MEANS YOU CAN EXAMINE FILES, MODIFY, CREATE AND IMPLEMENT, COMMIT AND CREATE MERGE REQUEST ETC

CRITICAL: EVERYTHING IS ON THE MAIN BRANCH. 

DO NOT FOOLSIHLY START LISTING WHAT IS ON THE MASTER BRANCH

HERE IS EXACTLY WHAT I WANT YOU TO DO:


THERE ARE MANY THINGS WE NEED TO ADDRESS FOR PROPER AND HIGH PERFORMANCE IN THE FRONTEND:

1.  ALL OF THESE SHOULD BE UPDATING DYNAMICALLY AND AUTOMATICALLY IN REAL-TIME WITHOUT ANY SINGLEDELAY: Chart Sync, Open & Closed Trades, P&L, Win Rate & Journal, Header (balance, equity etc)


I MEAN ANY SINGLE ACTION OR ANYTHING THAT HAPPENS IN THE BACKEND SHOULD SYNC AND UPDATE DYNAMICALLY.

CURRENTLY SOME OF THOSE THINGS DOESN'T SHOW SUCH AS ACTIVE MANAGED TRADE, JOURNAL ETC.

THE TP, SL, ENTERY ETC SHOWING ON THE CHART ARE NOT FUNCTIONING PROPERLY AT ALL. IN FACT, WHEN A TRADE CLOSES IN THE BROKER IT DOESN'T CLOSE ON THE CHART AT ALL, PROFIT AND LOSS DOESN'T SHOW AT ALL ON THE CHART AS TRADES ARE MOVING AND MANY OTHER ISSUES

2. EVERYTHING IN THE FRONTEND SHOULD BE ULTRA-FAST AND SHOULD WORK AT A BLAZING SPEED..

3. SOMETIMES THE CHART LAGS WHEN I CHANGE INSTRUMENT OR OR TIMEFRAME.

ITS' NOT TOO OBVIOUS BUT WHAT I NEED IS A BLAZING SPEED WITH UNNOTICEABLE DELAY OR ANYTHING AT ALL



4. THE THEMING IN THE WHOLE DASHBOARD IS NOT WORKING AT ALL. WHEN I SWITCH TO LIGHT MODE EVERYTHING DISAPPEARS. I MEAN I LITERALLY SEE NOTHING.

THAT IS NOT HOW AN ENTERPRISE APPLICATION SHOULD FUNCTION.


5. THE ENTIRE DASHBOARD IS NOT RESPONSIVE.

ACCORDING TO BEST PRACTICES AND ENTERPRISE GRADE, IT SHOULD WORK SEEMLY ACROSS ALL DEVICES (MOBILE SCREENS, TABLETS, DESKTOPS ETC) WITHOUT ANY ISSUES OR HINDERANCES AT ALL.


6. THE STYLING OF THE ENTIRE UI HAS TO BE IMPROVED AND ELAVTED TO BEST PRACTICES, ENTERPRISE GRADE AND INDUSTRY STANDARD

SO HAVE YOU SEE WE HAVE A LOT OF ISSUES TO ADDRESS NOW?


SO I WANT YOU TO EXAMINE THE CODEBASE DEEPLY AND THOROUGHLY TO ADDRESS ALL THESE ISSUES.

AVOID GUESSING

AVOID ASSUMPTIONS

YOU HAVE TO BE 100% CERTAIN AND SURE OF EVERYTHING.

AS A SENIOR ENGINEER YOU MUST MAKE SURE EVERYTHING FOLLOWS BEST PRACTICES, ENTERPRISE GRADE AND INDUSTRY STANDARD FOR A PERFECT UI, HIGH PERFORMANCE, RESPONSIVENESS, BLAZING SPEED, DYNAMIC UPDATES


YOU SHOULD EXAMINE THE PRACTICE.md ALSO THOROUGHLY FROM THE BEGINNING TO THE END SO THAT YOU WILL SEE ALL THE ENTERPRISE FRONTEND BEST PRACTICES YOU  MUST STRICTLY FOLLOW GIVEN THAT THIS IS TRADING ALGORITHM DASHBOARD THAT REQUIRES CAREFUL DESIGN.



PLEAS NOTE: SINCE THIS IS VERY BIG YOU HAVE TO EXECUTE IT IN MULTIPLE COMMITS INSTEAD OF RUSHING EVERYTHING AT ONCE AND END UP DOING RUBBISH.

YOU SHOULD NOT COMMIT MANY HEAVY FILES ONCE BECAUSE YOU WILL HIT LIMIT AND IT WILL FAIL


LASTLY, YOU SHOULD COMMIT DIRECTLY TO THE MAIN BRANCH USING THE DIRECT URL

DO YOU UNDERSTAND EVERYTHING I HAVE INSTRUCTED ?


























base_repository] extra={'repository': 'rag_citation_log', 'operation': 'add', 'duration_ms': 2.72, 'row_count': 1, 'trace_id': None}
etradie-engine  | 2026-04-27T06:29:20.453203Z [DEBUG    ] db_transaction_committed       [engine.shared.db.connection] extra={'trace_id': None, 'duration_ms': 1728.0}
etradie-engine  | 2026-04-27T06:29:20.454032Z [INFO     ] citations_logged               [engine.rag.services.audit] count=31 retrieval_log_id=29d0abaf-28b6-4df1-851e-f6a972b0288f
etradie-engine  | 2026-04-27T06:29:20.454703Z [INFO     ] rag_retrieval_completed        [engine.rag.orchestrator] chunks=31 chunks_from_gap_fill=0 chunks_from_primary=31 citations=31 coverage=partial elapsed_ms=9892.9 mandatory_doc_types=9 scenarios=0 strategy=scenario_first trace_id=031068d8681d0cf502453f94996e76ca
etradie-engine  | INFO:     172.24.0.5:43056 - "POST /internal/rag/retrieve HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:20.501598Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'rag_citation_log', 'operation': 'add', 'duration_ms': 98.68, 'row_count': 1, 'trace_id': None}
etradie-engine  | 2026-04-27T06:29:20.615249Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'rag_citation_log', 'operation': 'add', 'duration_ms': 113.03, 'row_count': 1, 'trace_id': None}
etradie-engine  | 2026-04-27T06:29:20.617395Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'rag_citation_log', 'operation': 'add', 'duration_ms': 1.71, 'row_count': 1, 'trace_id': None}
etradie-engine  | 2026-04-27T06:29:20.625970Z [INFO     ] loaded_active_llm_connection_from_db [engine.dependencies] extra={'provider': 'gemini', 'model': 'gemini-2.5-pro', 'connection_id': '7883e657-1010-4c4a-953f-b5fcf4076640'}
etradie-engine  | 2026-04-27T06:29:26.513450Z [INFO     ] llm_client_created             [engine.processor.llm.factory] extra={'provider': 'gemini', 'model': 'gemini-2.5-pro', 'temperature': 0.0, 'max_output_tokens': 16384, 'timeout_seconds': 180}
etradie-engine  | 2026-04-27T06:29:26.514032Z [INFO     ] user_processor_cached          [engine.dependencies] extra={'user_id': 'f4d8853ca258f665b3d000b0097c2225', 'provider': 'gemini', 'model': 'gemini-2.5-pro'}
etradie-engine  | 2026-04-27T06:29:26.514619Z [INFO     ] processor_started              [engine.processor.service] extra={'symbol': 'Crash 1000 Index', 'ta_keys': ['alignment', 'htf_timeframes', 'ltf_timeframes', 'overall_trend', 'smc_candidates', 'snapshots', 'snd_candidates', 'status', 'symbol'], 'macro_keys': [], 'rag_keys': ['citations', 'conflict_details', 'conflict_result', 'coverage_gaps', 'coverage_result', 'created_at', 'id', 'matched_scenarios', 'retrieved_chunks', 'strategy_used', 'total_chunks_considered', 'total_chunks_returned'], 'trace_id': '031068d8681d0cf502453f94996e76ca'}
etradie-engine  | 2026-04-27T06:29:26.544061Z [DEBUG    ] processor_prompt_built         [engine.processor.service] extra={'symbol': 'Crash 1000 Index', 'user_message_length': 681023, 'prompt_hash': '6cc54e1cc461c85cd98cd376c3f0e202', 'trace_id': '031068d8681d0cf502453f94996e76ca'}
etradie-engine  | 2026-04-27T06:29:26.553595Z [DEBUG    ] db_transaction_committed       [engine.shared.db.connection] extra={'trace_id': None, 'duration_ms': 7981.0}
etradie-engine  | Looking for jobs to run
etradie-engine  | Next wakeup is due at 2026-04-27 06:39:23.563139+00:00 (in 596.996216 seconds)
etradie-engine  | Running job "SchedulerManager._create_job_wrapper.<locals>._wrapper (trigger: interval[0:10:00], next run at: 2026-04-27 06:39:23 UTC)" (scheduled at 2026-04-27 06:29:23.563139+00:00)
etradie-engine  | 2026-04-27T06:29:26.574985Z [INFO     ] scheduler_job_started          [engine.shared.scheduler.apscheduler] extra={'job_id': 'collect_central_bank', 'trace_id': 'af55ea8c97664ee199130d1b7bb0ea14'} trace_id=af55ea8c97664ee199130d1b7bb0ea14
etradie-engine  | INFO:     127.0.0.1:57630 - "GET /health HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:26.580225Z [INFO     ] citations_logged               [engine.rag.services.audit] count=31 retrieval_log_id=1d254d9b-1081-46aa-ba66-eb48c3e4ed73
etradie-engine  | 2026-04-27T06:29:26.580828Z [INFO     ] rag_retrieval_completed        [engine.rag.orchestrator] chunks=31 chunks_from_gap_fill=0 chunks_from_primary=31 citations=31 coverage=partial elapsed_ms=10066.9 mandatory_doc_types=9 scenarios=0 strategy=scenario_first trace_id=031068d8681d0cf502453f94996e76ca
etradie-engine  | INFO:     172.24.0.5:33202 - "POST /internal/rag/retrieve HTTP/1.1" 200 OK
etradie-engine  | AFC is enabled with max remote calls: 10.
etradie-engine  | INFO:     172.24.0.11:38730 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:26.690486Z [INFO     ] processor_started              [engine.processor.service] extra={'symbol': 'XAUUSD', 'ta_keys': ['alignment', 'htf_timeframes', 'ltf_timeframes', 'overall_trend', 'smc_candidates', 'snapshots', 'snd_candidates', 'status', 'symbol'], 'macro_keys': ['calendar', 'central_bank', 'collection_errors', 'cot', 'datasets_available', 'dxy', 'economic', 'intermarket', 'news', 'sentiment'], 'rag_keys': ['citations', 'conflict_details', 'conflict_result', 'coverage_gaps', 'coverage_result', 'created_at', 'id', 'matched_scenarios', 'retrieved_chunks', 'strategy_used', 'total_chunks_considered', 'total_chunks_returned'], 'trace_id': '031068d8681d0cf502453f94996e76ca'}
etradie-engine  | 2026-04-27T06:29:26.703553Z [DEBUG    ] processor_prompt_built         [engine.processor.service] extra={'symbol': 'XAUUSD', 'user_message_length': 496026, 'prompt_hash': 'edfa10cbc80630ba70df3e03229b74c9', 'trace_id': '031068d8681d0cf502453f94996e76ca'}
etradie-engine  | AFC is enabled with max remote calls: 10.
etradie-engine  | INFO:     172.24.0.11:53492 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:26.864647Z [INFO     ] zmq_positions_fetched          [engine.ta.broker.mt5.zmq.client] extra={'count': 0}
etradie-engine  | INFO:     172.24.0.11:38730 - "GET /internal/broker/positions HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:26.916463Z [INFO     ] zmq_pending_orders_fetched     [engine.ta.broker.mt5.zmq.client] extra={'count': 3}
etradie-engine  | INFO:     172.24.0.11:38730 - "GET /internal/broker/pending_orders HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:27.468932Z [DEBUG    ] http_request_success           [engine.shared.http.client] extra={'provider': 'fed_rss', 'category': 'CENTRAL_BANK', 'method': 'GET', 'url': 'https://www.federalreserve.gov/feeds/press_all.xml', 'status': 200, 'duration_ms': 892.04, 'attempt': 1, 'trace_id': None} trace_id=af55ea8c97664ee199130d1b7bb0ea14
etradie-engine  | 2026-04-27T06:29:27.509223Z [INFO     ] rss_fetched                    [engine.shared.rss.parser] new_entries=0 total_entries=20 trace_id=af55ea8c97664ee199130d1b7bb0ea14 url=https://www.federalreserve.gov/feeds/press_all.xml
etradie-engine  | INFO:     172.24.0.6:48694 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
etradie-engine  | INFO:     172.24.0.6:48694 - "GET /metrics/ HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:29.758196Z [DEBUG    ] http_request_success           [engine.shared.http.client] extra={'provider': 'ecb_rss', 'category': 'CENTRAL_BANK', 'method': 'GET', 'url': 'https://www.ecb.europa.eu/rss/press.html', 'status': 200, 'duration_ms': 2248.17, 'attempt': 1, 'trace_id': None} trace_id=af55ea8c97664ee199130d1b7bb0ea14
etradie-engine  | 2026-04-27T06:29:29.777947Z [INFO     ] rss_fetched                    [engine.shared.rss.parser] new_entries=0 total_entries=15 trace_id=af55ea8c97664ee199130d1b7bb0ea14 url=https://www.ecb.europa.eu/rss/press.html
etradie-engine  | INFO:     172.24.0.11:38730 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:30.127460Z [INFO     ] zmq_positions_fetched          [engine.ta.broker.mt5.zmq.client] extra={'count': 0}
etradie-engine  | INFO:     172.24.0.11:38730 - "GET /internal/broker/positions HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:30.166945Z [INFO     ] zmq_pending_orders_fetched     [engine.ta.broker.mt5.zmq.client] extra={'count': 3}
etradie-engine  | INFO:     172.24.0.11:38730 - "GET /internal/broker/pending_orders HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:38730 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:38730 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:33.432328Z [INFO     ] zmq_positions_fetched          [engine.ta.broker.mt5.zmq.client] extra={'count': 0}
etradie-engine  | INFO:     172.24.0.11:38730 - "GET /internal/broker/positions HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:33.481539Z [INFO     ] zmq_pending_orders_fetched     [engine.ta.broker.mt5.zmq.client] extra={'count': 3}
etradie-engine  | INFO:     172.24.0.11:38730 - "GET /internal/broker/pending_orders HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:35.048898Z [ERROR    ] http_non_retryable_error       [engine.shared.http.client] extra={'provider': 'boe_rss', 'url': 'https://www.bankofengland.co.uk/rss/news', 'status': 403, 'body_preview': '<HTML><HEAD>\n<TITLE>Access Denied</TITLE>\n</HEAD><BODY>\n<H1>Access Denied</H1>\n \nYou don\'t have permission to access "http&#58;&#47;&#47;www&#46;bankofengland&#46;co&#46;uk&#47;rss&#47;news" on this server.<P>\nReference&#32;&#35;18&#46;deb00f17&#46;1777271373&#46;a94320a2\n<P>https&#58;&#47;&#47;errors&#46;edgesuite&#46;net&#47;18&#46;deb00f17&#46;1777271373&#46;a94320a2</P>\n</BODY>\n</HTML>\n', 'trace_id': None} trace_id=af55ea8c97664ee199130d1b7bb0ea14
etradie-engine  | 2026-04-27T06:29:35.049468Z [ERROR    ] cb_provider_fetch_failed       [engine.macro.providers.central_bank.base] error=boe_rss returned 403 provider=boe_rss trace_id=af55ea8c97664ee199130d1b7bb0ea14
etradie-engine  | 2026-04-27T06:29:35.050096Z [WARNING  ] cb_provider_skipped            [engine.macro.collectors.central_bank.collector] provider=boe_rss trace_id=af55ea8c97664ee199130d1b7bb0ea14
etradie-engine  | INFO:     172.24.0.11:38730 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:36.752225Z [INFO     ] zmq_positions_fetched          [engine.ta.broker.mt5.zmq.client] extra={'count': 0}
etradie-engine  | INFO:     172.24.0.11:38730 - "GET /internal/broker/positions HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:36.863532Z [INFO     ] zmq_pending_orders_fetched     [engine.ta.broker.mt5.zmq.client] extra={'count': 3}
etradie-engine  | INFO:     172.24.0.11:38730 - "GET /internal/broker/pending_orders HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:38730 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:38.556701Z [INFO     ] tick_stream_disconnected       [engine.main] extra={'user_id': 'f4d8853ca258f665b3d000b0097c2225', 'symbol': 'Crash 1000 Index'}
etradie-engine  | INFO:     connection closed
etradie-engine  | 2026-04-27T06:29:41.728852Z [DEBUG    ] http_request_success           [engine.shared.http.client] extra={'provider': 'boj_rss', 'category': 'CENTRAL_BANK', 'method': 'GET', 'url': 'https://www.boj.or.jp/en/rss/whatsnew.xml', 'status': 200, 'duration_ms': 6664.42, 'attempt': 1, 'trace_id': None} trace_id=af55ea8c97664ee199130d1b7bb0ea14
etradie-engine  | 2026-04-27T06:29:41.754764Z [INFO     ] rss_fetched                    [engine.shared.rss.parser] new_entries=0 total_entries=49 trace_id=af55ea8c97664ee199130d1b7bb0ea14 url=https://www.boj.or.jp/en/rss/whatsnew.xml
etradie-engine  | INFO:     127.0.0.1:35186 - "GET /health HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:37468 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.6:38950 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
etradie-engine  | INFO:     172.24.0.6:38950 - "GET /metrics/ HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:37468 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:43.189698Z [INFO     ] zmq_positions_fetched          [engine.ta.broker.mt5.zmq.client] extra={'count': 0}
etradie-engine  | INFO:     172.24.0.11:37468 - "GET /internal/broker/positions HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:43.245263Z [INFO     ] zmq_pending_orders_fetched     [engine.ta.broker.mt5.zmq.client] extra={'count': 3}
etradie-engine  | INFO:     172.24.0.11:37468 - "GET /internal/broker/pending_orders HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:43.749647Z [DEBUG    ] http_request_success           [engine.shared.http.client] extra={'provider': 'rba_rss', 'category': 'CENTRAL_BANK', 'method': 'GET', 'url': 'https://www.rba.gov.au/rss/rss-cb-media-releases.xml', 'status': 200, 'duration_ms': 1993.98, 'attempt': 1, 'trace_id': None} trace_id=af55ea8c97664ee199130d1b7bb0ea14
etradie-engine  | 2026-04-27T06:29:43.755205Z [INFO     ] rss_fetched                    [engine.shared.rss.parser] new_entries=0 total_entries=1 trace_id=af55ea8c97664ee199130d1b7bb0ea14 url=https://www.rba.gov.au/rss/rss-cb-media-releases.xml
etradie-engine  | INFO:     172.24.0.11:37468 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:46.504373Z [INFO     ] zmq_positions_fetched          [engine.ta.broker.mt5.zmq.client] extra={'count': 0}
etradie-engine  | INFO:     172.24.0.11:37468 - "GET /internal/broker/positions HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:46.544266Z [INFO     ] zmq_pending_orders_fetched     [engine.ta.broker.mt5.zmq.client] extra={'count': 3}
etradie-engine  | INFO:     172.24.0.11:37468 - "GET /internal/broker/pending_orders HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:46.786446Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_output', 'operation': 'execute_query', 'duration_ms': 82.57, 'row_count': 50, 'trace_id': None}
etradie-engine  | INFO:     172.24.0.1:43518 - "GET /api/analysis/latest?limit=50 HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:47.876480Z [DEBUG    ] http_request_success           [engine.shared.http.client] extra={'provider': 'boc_rss', 'category': 'CENTRAL_BANK', 'method': 'GET', 'url': 'https://www.bankofcanada.ca/content_type/press-releases/feed/', 'status': 200, 'duration_ms': 4120.58, 'attempt': 1, 'trace_id': None} trace_id=af55ea8c97664ee199130d1b7bb0ea14
etradie-engine  | 2026-04-27T06:29:47.891706Z [INFO     ] rss_fetched                    [engine.shared.rss.parser] new_entries=0 total_entries=10 trace_id=af55ea8c97664ee199130d1b7bb0ea14 url=https://www.bankofcanada.ca/content_type/press-releases/feed/
etradie-engine  | INFO:     172.24.0.11:37468 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:49.469577Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_output', 'operation': 'execute_query', 'duration_ms': 7.15, 'row_count': 1, 'trace_id': None}
etradie-engine  | INFO:     172.24.0.1:43518 - "GET /api/analysis/latest?limit=1 HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:37468 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:49.888697Z [INFO     ] zmq_positions_fetched          [engine.ta.broker.mt5.zmq.client] extra={'count': 0}
etradie-engine  | INFO:     172.24.0.11:37468 - "GET /internal/broker/positions HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:49.939626Z [INFO     ] zmq_pending_orders_fetched     [engine.ta.broker.mt5.zmq.client] extra={'count': 3}
etradie-engine  | INFO:     172.24.0.11:37468 - "GET /internal/broker/pending_orders HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:50.735061Z [ERROR    ] http_non_retryable_error       [engine.shared.http.client] extra={'provider': 'rbnz_rss', 'url': 'https://www.rbnz.govt.nz/rss/news', 'status': 403, 'body_preview': '<!DOCTYPE html>\r\n<html lang="en">\r\n<head>\r\n<title>Website unavailable - Reserve Bank of New Zealand - Te Pūtea Matua</title>\r\n<meta charset="utf-8">\r\n<meta name="viewport" content="width=device-width, initial-scale=1">\r\n<meta http-equiv="X-UA-Compatible" content="IE=edge">\r\n<style>*{box-sizing:border-box}body{font-family:Arial,sans-serif;font-size:16px}.header,body{background-color:#343434;color:#fff}.header{padding:15px;text-align:center;font-size:1.5em}a{text-decoration:underline;color:#fff}a:', 'trace_id': None} trace_id=af55ea8c97664ee199130d1b7bb0ea14
etradie-engine  | 2026-04-27T06:29:50.735518Z [ERROR    ] cb_provider_fetch_failed       [engine.macro.providers.central_bank.base] error=rbnz_rss returned 403 provider=rbnz_rss trace_id=af55ea8c97664ee199130d1b7bb0ea14
etradie-engine  | 2026-04-27T06:29:50.735862Z [WARNING  ] cb_provider_skipped            [engine.macro.collectors.central_bank.collector] provider=rbnz_rss trace_id=af55ea8c97664ee199130d1b7bb0ea14
etradie-engine  | 2026-04-27T06:29:51.676386Z [ERROR    ] http_non_retryable_error       [engine.shared.http.client] extra={'provider': 'snb_rss', 'url': 'https://www.snb.ch/en/mmr/reference/rss_en/source/rss_en.rss', 'status': 404, 'body_preview': '<!DOCTYPE html>\n<html lang="en" data-g-name="Page" class="c-page" data-setup=\'{ "authorMode": false, "gdpr": { "version": "2023-09-27T10:35:00.000+02:00", "categories": [ "essential", "analytics", "marketing" ], "tracking": "analytics" } }\'\n>\n\t<head>\n\t\t<meta charset="utf-8">\n\n\t<meta name="version" content="2.50.0">\n\t<meta name="environment" content="P1">\n\t<meta name="timestamp" content="2026-04-27T06:19:37.849550Z">\n\n<meta name="viewport" content="width=device-width, initial-scale=1">\n\n\n\n<title>', 'trace_id': None} trace_id=af55ea8c97664ee199130d1b7bb0ea14
etradie-engine  | 2026-04-27T06:29:51.676880Z [ERROR    ] cb_provider_fetch_failed       [engine.macro.providers.central_bank.base] error=snb_rss returned 404 provider=snb_rss trace_id=af55ea8c97664ee199130d1b7bb0ea14
etradie-engine  | 2026-04-27T06:29:51.677389Z [WARNING  ] cb_provider_skipped            [engine.macro.collectors.central_bank.collector] provider=snb_rss trace_id=af55ea8c97664ee199130d1b7bb0ea14
etradie-engine  | 2026-04-27T06:29:51.678979Z [DEBUG    ] db_transaction_committed       [engine.shared.db.connection] extra={'trace_id': None, 'duration_ms': 1.0} trace_id=af55ea8c97664ee199130d1b7bb0ea14
etradie-engine  | 2026-04-27T06:29:51.682263Z [DEBUG    ] cache_set_success              [engine.shared.cache.redis_cache] extra={'namespace': 'cb', 'key': 'latest', 'size_bytes': 280, 'ttl_seconds': 600, 'trace_id': None} trace_id=af55ea8c97664ee199130d1b7bb0ea14
etradie-engine  | Job "SchedulerManager._create_job_wrapper.<locals>._wrapper (trigger: interval[0:10:00], next run at: 2026-04-27 06:39:23 UTC)" executed successfully
etradie-engine  | 2026-04-27T06:29:51.684699Z [DEBUG    ] scheduler_job_completed        [engine.shared.scheduler.apscheduler] extra={'job_id': 'collect_central_bank', 'duration_seconds': 26.44}
etradie-engine  | INFO:     172.24.0.11:37468 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:52.507014Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_output', 'operation': 'execute_query', 'duration_ms': 56.04, 'row_count': 68, 'trace_id': None}
etradie-engine  | INFO:     172.24.0.1:43518 - "GET /api/analysis/latest?limit=200 HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:29:55.213309Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_output', 'operation': 'execute_query', 'duration_ms': 5.26, 'row_count': 1, 'trace_id': None}
etradie-engine  | 2026-04-27T06:29:55.224136Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_audit_log', 'operation': 'execute_query', 'duration_ms': 9.71, 'row_count': 2, 'trace_id': None}
etradie-engine  | INFO:     172.24.0.1:43518 - "GET /api/analysis/analysis_Crash_1000_Index_20260427_0448_a8b3 HTTP/1.1" 200 OK
etradie-engine  | INFO:     127.0.0.1:52890 - "GET /health HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.6:41124 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
etradie-engine  | INFO:     172.24.0.6:41124 - "GET /metrics/ HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:36376 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:35074 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:35074 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:30:03.446112Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_output', 'operation': 'execute_query', 'duration_ms': 43.43, 'row_count': 50, 'trace_id': None}
etradie-engine  | 2026-04-27T06:30:03.447886Z [INFO     ] zmq_positions_fetched          [engine.ta.broker.mt5.zmq.client] extra={'count': 0}
etradie-engine  | INFO:     172.24.0.11:35074 - "GET /internal/broker/positions HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.1:41616 - "GET /api/analysis/latest?limit=50 HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:30:03.516271Z [INFO     ] zmq_pending_orders_fetched     [engine.ta.broker.mt5.zmq.client] extra={'count': 3}
etradie-engine  | INFO:     172.24.0.11:35074 - "GET /internal/broker/pending_orders HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:35074 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:30:06.786311Z [INFO     ] zmq_positions_fetched          [engine.ta.broker.mt5.zmq.client] extra={'count': 0}
etradie-engine  | INFO:     172.24.0.11:35074 - "GET /internal/broker/positions HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:30:06.834972Z [INFO     ] zmq_pending_orders_fetched     [engine.ta.broker.mt5.zmq.client] extra={'count': 3}
etradie-engine  | INFO:     172.24.0.11:35074 - "GET /internal/broker/pending_orders HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:35074 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.6:46046 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
etradie-engine  | INFO:     172.24.0.6:46046 - "GET /metrics/ HTTP/1.1" 200 OK
etradie-engine  | INFO:     127.0.0.1:33476 - "GET /health HTTP/1.1" 200 OK
etradie-engine  | INFO:     ('172.24.0.1', 56148) - "WebSocket /api/broker/stream-ticks" [accepted]
etradie-engine  | INFO:     connection open
etradie-engine  | 2026-04-27T06:30:16.648526Z [INFO     ] tick_stream_connected          [engine.main] extra={'user_id': 'f4d8853ca258f665b3d000b0097c2225', 'symbol': 'Crash 1000 Index'}
etradie-engine  | 2026-04-27T06:30:16.691990Z [INFO     ] tick_stream_disconnected       [engine.main] extra={'user_id': 'f4d8853ca258f665b3d000b0097c2225', 'symbol': 'Crash 1000 Index'}
etradie-engine  | INFO:     connection closed
etradie-engine  | INFO:     ('172.24.0.1', 56158) - "WebSocket /api/broker/stream-ticks" [accepted]
etradie-engine  | INFO:     connection open
etradie-engine  | 2026-04-27T06:30:19.085331Z [INFO     ] tick_stream_connected          [engine.main] extra={'user_id': 'f4d8853ca258f665b3d000b0097c2225', 'symbol': 'Crash 1000 Index'}
etradie-engine  | INFO:     172.24.0.6:59830 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
etradie-engine  | INFO:     172.24.0.6:59830 - "GET /metrics/ HTTP/1.1" 200 OK
etradie-engine  | INFO:     127.0.0.1:40924 - "GET /health HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:30:28.065844Z [INFO     ] zmq_candles_fetched            [engine.ta.broker.mt5.zmq.client] extra={'symbol': 'Crash 1000 Index', 'timeframe': <Timeframe.H1: 'H1'>, 'count': 500, 'duration_seconds': 0.9527776979994087}
etradie-engine  | INFO:     172.24.0.1:50490 - "GET /api/broker/candles?symbol=Crash+1000+Index&timeframe=H1&count=500 HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:35296 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:55596 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:55612 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.6:58904 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
etradie-engine  | INFO:     172.24.0.6:58904 - "GET /metrics/ HTTP/1.1" 200 OK
etradie-engine  | INFO:     127.0.0.1:33408 - "GET /health HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:30:42.910750Z [INFO     ] llm_response_parsed            [engine.processor.parsing.response_parser] extra={'analysis_id': 'analysis_xauusd_20260427_0628_a4b1', 'pair': 'XAUUSD', 'direction': 'NO SETUP', 'grade': 'REJECT', 'score': 3.0, 'warnings_count': 0, 'trace_id': '031068d8681d0cf502453f94996e76ca'}
etradie-engine  | 2026-04-27T06:30:42.921472Z [INFO     ] stream_subscriber_stopped      [engine.main] extra={'user_id': 'f4d8853ca258f665b3d000b0097c2225', 'channel': 'etradie:stream:user:f4d8853ca258f665b3d000b0097c2225'}
etradie-engine  | 2026-04-27T06:30:42.975549Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_output', 'operation': 'execute_query', 'duration_ms': 21.83, 'row_count': 1, 'trace_id': None}
etradie-engine  | INFO:     172.24.0.1:59674 - "GET /api/analysis/latest?limit=1 HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:30:43.025530Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_output', 'operation': 'upsert', 'duration_ms': 107.33, 'row_count': 1, 'trace_id': None}
etradie-engine  | 2026-04-27T06:30:43.026001Z [DEBUG    ] repository_upsert_executed     [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_output', 'index_elements': ['analysis_id'], 'update_fields': ['direction', 'setup_grade', 'confluence_score', 'confidence', 'proceed_to_module_b', 'status', 'error_message', 'duration_ms', 'raw_output'], 'idempotency_key': None, 'trace_id': None}
etradie-engine  | 2026-04-27T06:30:43.040805Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_output', 'operation': 'execute_query', 'duration_ms': 60.96, 'row_count': 50, 'trace_id': None}
etradie-engine  | INFO:     172.24.0.1:60976 - "GET /api/analysis/latest?limit=50 HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:30:43.058323Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_audit_log', 'operation': 'add', 'duration_ms': 24.7, 'row_count': 1, 'trace_id': None}
etradie-engine  | 2026-04-27T06:30:43.063416Z [DEBUG    ] db_transaction_committed       [engine.shared.db.connection] extra={'trace_id': None, 'duration_ms': 146.0}
etradie-engine  | 2026-04-27T06:30:43.064995Z [INFO     ] processor_completed            [engine.processor.service] extra={'symbol': 'XAUUSD', 'analysis_id': 'analysis_xauusd_20260427_0628_a4b1', 'direction': 'NO SETUP', 'grade': 'REJECT', 'score': 3.0, 'confidence': 'NO SETUP', 'proceed': 'NO', 'rr_ratio': None, 'duration_ms': 78992.5, 'input_tokens': 200072, 'output_tokens': 2942, 'warnings': [], 'trace_id': '031068d8681d0cf502453f94996e76ca'}
etradie-engine  | INFO:     172.24.0.5:33202 - "POST /internal/processor/process HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:30:43.138558Z [INFO     ] debug_output_saved             [engine.main] extra={'symbol': 'XAUUSD', 'subdirectory': 'runcycle', 'directory': '/output/runcycle/XAUUSD_20260427T063043Z', 'files': ['ta_snapshots', 'ta_smc_candidates', 'ta_snd_candidates', 'ta_metadata', 'macro_analysis', 'rag_knowledge', 'processor_result', 'execution_request']}
etradie-engine  | INFO:     172.24.0.5:33202 - "POST /internal/debug/runcycle HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:49606 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | INFO:     ('172.24.0.1', 60980) - "WebSocket /api/broker/stream-ticks" [accepted]
etradie-engine  | INFO:     connection open
etradie-engine  | 2026-04-27T06:30:47.639343Z [INFO     ] tick_stream_connected          [engine.main] extra={'user_id': 'f4d8853ca258f665b3d000b0097c2225', 'symbol': 'Crash 1000 Index'}
etradie-engine  | INFO:     172.24.0.11:49608 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:42628 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.6:60566 - "GET /metrics HTTP/1.1" 307 Temporary Redirect
etradie-engine  | INFO:     172.24.0.6:60566 - "GET /metrics/ HTTP/1.1" 200 OK
etradie-engine  | INFO:     127.0.0.1:39588 - "GET /health HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:30:58.010118Z [INFO     ] llm_response_parsed            [engine.processor.parsing.response_parser] extra={'analysis_id': 'analysis_Crash_1000_Index_20260427_0628_a4b1', 'pair': 'Crash 1000 Index', 'direction': 'SHORT', 'grade': 'B', 'score': 6.0, 'warnings_count': 0, 'trace_id': '031068d8681d0cf502453f94996e76ca'}
etradie-engine  | 2026-04-27T06:30:58.027765Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_output', 'operation': 'upsert', 'duration_ms': 16.17, 'row_count': 1, 'trace_id': None}
etradie-engine  | 2026-04-27T06:30:58.028313Z [DEBUG    ] repository_upsert_executed     [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_output', 'index_elements': ['analysis_id'], 'update_fields': ['direction', 'setup_grade', 'confluence_score', 'confidence', 'proceed_to_module_b', 'status', 'error_message', 'duration_ms', 'raw_output'], 'idempotency_key': None, 'trace_id': None}
etradie-engine  | 2026-04-27T06:30:58.036927Z [DEBUG    ] repository_query_executed      [engine.shared.db.repositories.base_repository] extra={'repository': 'analysis_audit_log', 'operation': 'add', 'duration_ms': 6.37, 'row_count': 1, 'trace_id': None}
etradie-engine  | 2026-04-27T06:30:58.044706Z [DEBUG    ] db_transaction_committed       [engine.shared.db.connection] extra={'trace_id': None, 'duration_ms': 33.0}
etradie-engine  | 2026-04-27T06:30:58.045653Z [INFO     ] processor_completed            [engine.processor.service] extra={'symbol': 'Crash 1000 Index', 'analysis_id': 'analysis_Crash_1000_Index_20260427_0628_a4b1', 'direction': 'SHORT', 'grade': 'B', 'score': 6.0, 'confidence': 'MEDIUM', 'proceed': 'YES', 'rr_ratio': 4.15, 'duration_ms': 95637.6, 'input_tokens': 279118, 'output_tokens': 4321, 'warnings': [], 'trace_id': '031068d8681d0cf502453f94996e76ca'}
etradie-engine  | INFO:     172.24.0.5:43056 - "POST /internal/processor/process HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:30:58.129068Z [INFO     ] debug_output_saved             [engine.main] extra={'symbol': 'Crash 1000 Index', 'subdirectory': 'runcycle', 'directory': '/output/runcycle/Crash 1000 Index_20260427T063058Z', 'files': ['ta_snapshots', 'ta_smc_candidates', 'ta_snd_candidates', 'ta_metadata', 'macro_analysis', 'rag_knowledge', 'processor_result', 'execution_request']}
etradie-engine  | INFO:     172.24.0.5:43056 - "POST /internal/debug/runcycle HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:42628 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:30:58.193000Z [INFO     ] zmq_positions_fetched          [engine.ta.broker.mt5.zmq.client] extra={'count': 0}
etradie-engine  | INFO:     172.24.0.11:42628 - "GET /internal/broker/positions HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:30:58.254663Z [INFO     ] zmq_pending_orders_fetched     [engine.ta.broker.mt5.zmq.client] extra={'count': 3}
etradie-engine  | INFO:     172.24.0.11:42628 - "GET /internal/broker/pending_orders HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:42628 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:31:02.835459Z [INFO     ] zmq_positions_fetched          [engine.ta.broker.mt5.zmq.client] extra={'count': 0}
etradie-engine  | INFO:     172.24.0.11:42628 - "GET /internal/broker/positions HTTP/1.1" 200 OK
etradie-engine  | 2026-04-27T06:31:02.886096Z [INFO     ] zmq_pending_orders_fetched     [engine.ta.broker.mt5.zmq.client] extra={'count': 3}
etradie-engine  | INFO:     172.24.0.11:42628 - "GET /internal/broker/pending_orders HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.11:42628 - "GET /internal/broker/account_info HTTP/1.1" 200 OK
etradie-engine  | INFO:     172.24.0.6:42784 - "GET /metrics HTTP/1.1" 307 Temporary Redirect