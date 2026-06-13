 downloading github.com/cenkalti/backoff/v5 v5.0.3
go: downloading github.com/grpc-ecosystem/grpc-gateway/v2 v2.28.0
go: downloading google.golang.org/genproto/googleapis/api v0.0.0-20260401024825-9d38bb4040a9
?   	github.com/flamegreat-1/etradie/src/gateway/cmd/gateway	[no test files]
=== RUN   TestFullPipeline_MultiSymbol_OnlyOneHasCandidates
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551661,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551662,"message":"redis_subscriber_started"}
    advanced_test.go:53: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/advanced_test.go:53
        	Error:      	Not equal: 
        	            	expected: 1
        	            	actual  : 0
        	Test:       	TestFullPipeline_MultiSymbol_OnlyOneHasCandidates
        	Messages:   	Processor should be called once (only for EURUSD)
    advanced_test.go:66: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/advanced_test.go:66
        	Error:      	Expected value not to be nil.
        	Test:       	TestFullPipeline_MultiSymbol_OnlyOneHasCandidates
{"level":"info","service":"alert","component":"redis_transport","time":1781341551667,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551667,"message":"alert_hub_closed"}
redis: 2026/06/13 09:05:51 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:44506->[::1]:6379: use of closed network connection
--- FAIL: TestFullPipeline_MultiSymbol_OnlyOneHasCandidates (0.01s)
=== RUN   TestFullPipeline_ExecutionPortError
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551667,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551668,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551669,"message":"redis_subscriber_started"}
    advanced_test.go:100: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/advanced_test.go:100
        	Error:      	Not equal: 
        	            	expected: 1
        	            	actual  : 0
        	Test:       	TestFullPipeline_ExecutionPortError
    advanced_test.go:111: INFO: Time-based guards rejected (blocking_rules=[MR-REJECT-008]). Execution error capture assertions skipped. Expected on weekends/off-hours.
{"level":"info","service":"alert","component":"redis_transport","time":1781341551673,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551673,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551673,"message":"redis_subscriber_stopped"}
--- FAIL: TestFullPipeline_ExecutionPortError (0.01s)
=== RUN   TestFullPipeline_PartialMacroData
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551673,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551675,"message":"redis_subscriber_started"}
    advanced_test.go:146: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/advanced_test.go:146
        	Error:      	Not equal: 
        	            	expected: 1
        	            	actual  : 0
        	Test:       	TestFullPipeline_PartialMacroData
{"level":"info","service":"alert","component":"redis_transport","time":1781341551678,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551678,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551678,"message":"redis_subscriber_stopped"}
--- FAIL: TestFullPipeline_PartialMacroData (0.01s)
=== RUN   TestFullPipeline_EmptyRAGChunks
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551679,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551680,"message":"redis_subscriber_started"}
    advanced_test.go:180: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/advanced_test.go:180
        	Error:      	Not equal: 
        	            	expected: 1
        	            	actual  : 0
        	Test:       	TestFullPipeline_EmptyRAGChunks
    advanced_test.go:194: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/advanced_test.go:194
        	Error:      	Expected value not to be nil.
        	Test:       	TestFullPipeline_EmptyRAGChunks
{"level":"info","service":"alert","component":"redis_transport","time":1781341551684,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551684,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551684,"message":"redis_subscriber_stopped"}
redis: 2026/06/13 09:05:51 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:44572->[::1]:6379: use of closed network connection
--- FAIL: TestFullPipeline_EmptyRAGChunks (0.01s)
=== RUN   TestFullPipeline_EmptySymbolList
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551685,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551686,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551687,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551687,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551687,"message":"redis_subscriber_stopped"}
--- PASS: TestFullPipeline_EmptySymbolList (0.00s)
=== RUN   TestConfirmationPulse_LTFConfirmed
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551688,"message":"redis_transport_started"}
    confirmation_dataflow_test.go:37: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/confirmation_dataflow_test.go:37
        	Error:      	Not equal: 
        	            	expected: 1
        	            	actual  : 0
        	Test:       	TestConfirmationPulse_LTFConfirmed
        	Messages:   	TA should be called once for confirmation pulse
    confirmation_dataflow_test.go:42: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/confirmation_dataflow_test.go:42
        	Error:      	"[]" should have 1 item(s), but has 0
        	Test:       	TestConfirmationPulse_LTFConfirmed
{"level":"info","service":"alert","component":"redis_transport","time":1781341551688,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551688,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551689,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551689,"message":"redis_subscriber_stopped"}
--- FAIL: TestConfirmationPulse_LTFConfirmed (0.00s)
=== RUN   TestConfirmationPulse_LTFNotConfirmed
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551689,"message":"redis_transport_started"}
    confirmation_dataflow_test.go:94: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/confirmation_dataflow_test.go:94
        	Error:      	Not equal: 
        	            	expected: "SMC LTF confirmation not yet met"
        	            	actual  : "News lockout: Economic-calendar data unavailable; failing closed to avoid trading blind into news"
        	            	
        	            	Diff:
        	            	--- Expected
        	            	+++ Actual
        	            	@@ -1 +1 @@
        	            	-SMC LTF confirmation not yet met
        	            	+News lockout: Economic-calendar data unavailable; failing closed to avoid trading blind into news
        	Test:       	TestConfirmationPulse_LTFNotConfirmed
{"level":"info","service":"alert","component":"redis_transport","time":1781341551690,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551690,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551690,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551690,"message":"redis_subscriber_stopped"}
--- FAIL: TestConfirmationPulse_LTFNotConfirmed (0.00s)
=== RUN   TestConfirmationPulse_CandidateNotFound
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551690,"message":"redis_transport_started"}
    confirmation_dataflow_test.go:115: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/confirmation_dataflow_test.go:115
        	Error:      	"News lockout: Economic-calendar data unavailable; failing closed to avoid trading blind into news" does not contain "not found in TA results"
        	Test:       	TestConfirmationPulse_CandidateNotFound
    confirmation_dataflow_test.go:116: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/confirmation_dataflow_test.go:116
        	Error:      	"News lockout: Economic-calendar data unavailable; failing closed to avoid trading blind into news" does not contain "NONEXISTENT-ANALYSIS-ID"
        	Test:       	TestConfirmationPulse_CandidateNotFound
{"level":"info","service":"alert","component":"redis_transport","time":1781341551691,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551691,"message":"alert_hub_closed"}
--- FAIL: TestConfirmationPulse_CandidateNotFound (0.00s)
=== RUN   TestConfirmationPulse_TAFailure
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551691,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551691,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551691,"message":"redis_transport_started"}
    confirmation_dataflow_test.go:138: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/confirmation_dataflow_test.go:138
        	Error:      	"News lockout: Economic-calendar data unavailable; failing closed to avoid trading blind into news" does not contain "TA collection failed"
        	Test:       	TestConfirmationPulse_TAFailure
{"level":"info","service":"alert","component":"redis_transport","time":1781341551692,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551692,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551692,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551692,"message":"redis_subscriber_stopped"}
--- FAIL: TestConfirmationPulse_TAFailure (0.00s)
=== RUN   TestConfirmationPulse_NoCandidates
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551693,"message":"redis_transport_started"}
    confirmation_dataflow_test.go:158: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/confirmation_dataflow_test.go:158
        	Error:      	Not equal: 

       	expected: "TA returned no candidates for symbol"
        	            	actual  : "News lockout: Economic-calendar data unavailable; failing closed to avoid trading blind into news"
        	            	
        	            	Diff:
        	            	--- Expected
        	            	+++ Actual
        	            	@@ -1 +1 @@
        	            	-TA returned no candidates for symbol
        	            	+News lockout: Economic-calendar data unavailable; failing closed to avoid trading blind into news
        	Test:       	TestConfirmationPulse_NoCandidates
{"level":"info","service":"alert","component":"redis_transport","time":1781341551693,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551693,"message":"alert_hub_closed"}
--- FAIL: TestConfirmationPulse_NoCandidates (0.00s)
=== RUN   TestDataFlow_RAGReceivesCorrectQueryParams
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551694,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551694,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551694,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551695,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551699,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551699,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551699,"message":"redis_subscriber_stopped"}
--- PASS: TestDataFlow_RAGReceivesCorrectQueryParams (0.01s)
=== RUN   TestDataFlow_ProcessorReceivesAssembledContext
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551700,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551702,"message":"redis_subscriber_started"}
    confirmation_dataflow_test.go:391: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/confirmation_dataflow_test.go:391
        	Error:      	"[]" should have 1 item(s), but has 0
        	Test:       	TestDataFlow_ProcessorReceivesAssembledContext
        	Messages:   	Processor should be called once
{"level":"info","service":"alert","component":"redis_transport","time":1781341551706,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551706,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551706,"message":"redis_subscriber_stopped"}
--- FAIL: TestDataFlow_ProcessorReceivesAssembledContext (0.01s)
=== RUN   TestFullPipeline_NewsProximityGuardRejects
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551707,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551708,"message":"redis_subscriber_started"}
    edge_cases_test.go:38: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/edge_cases_test.go:38
        	Error:      	Not equal: 
        	            	expected: 1
        	            	actual  : 0
        	Test:       	TestFullPipeline_NewsProximityGuardRejects
{"level":"info","service":"alert","component":"redis_transport","time":1781341551712,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551712,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551712,"message":"redis_subscriber_stopped"}
--- FAIL: TestFullPipeline_NewsProximityGuardRejects (0.01s)
=== RUN   TestFullPipeline_NilExecutionPort
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551712,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551713,"message":"redis_subscriber_started"}
    edge_cases_test.go:111: INFO: Time-based guards rejected (blocking_rules=[MR-REJECT-008]). Nil execution port assertions skipped. Expected on weekends/off-hours.
{"level":"info","service":"alert","component":"redis_transport","time":1781341551718,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551718,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551718,"message":"redis_subscriber_stopped"}
--- PASS: TestFullPipeline_NilExecutionPort (0.01s)
=== RUN   TestFullPipeline_TASymbolErrorStatus
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551718,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551719,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551721,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551721,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551721,"message":"redis_subscriber_stopped"}
--- PASS: TestFullPipeline_TASymbolErrorStatus (0.00s)
=== RUN   TestFullPipeline_SnDCandidatesOnly
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551722,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551723,"message":"redis_subscriber_started"}
    edge_cases_test.go:208: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/edge_cases_test.go:208
        	Error:      	Not equal: 
        	            	expected: 1
        	            	actual  : 0
        	Test:       	TestFullPipeline_SnDCandidatesOnly
        	Messages:   	Processor should be called for SnD candidates
    edge_cases_test.go:218: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/edge_cases_test.go:218
        	Error:      	Expected value not to be nil.
        	Test:       	TestFullPipeline_SnDCandidatesOnly
{"level":"info","service":"alert","component":"redis_transport","time":1781341551728,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551728,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551728,"message":"redis_subscriber_stopped"}
--- FAIL: TestFullPipeline_SnDCandidatesOnly (0.01s)
=== RUN   TestConfirmationPulse_NestedLTFFormat
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551729,"message":"redis_transport_started"}
    edge_cases_test.go:254: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/edge_cases_test.go:254
        	Error:      	Should be true
        	Test:       	TestConfirmationPulse_NestedLTFFormat
        	Messages:   	nested {confirmed: true} format should be parsed correctly
    edge_cases_test.go:256: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/edge_cases_test.go:256
        	Error:      	Should be true
        	Test:       	TestConfirmationPulse_NestedLTFFormat
    edge_cases_test.go:257: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/edge_cases_test.go:257
        	Error:      	Not equal: 
        	            	expected: "SMC LTF confirmation met"
        	            	actual  : "News lockout: Economic-calendar data unavailable; failing closed to avoid trading blind into news"
        	            	
        	            	Diff:
        	            	--- Expected
        	            	+++ Actual
        	            	@@ -1 +1 @@
        	            	-SMC LTF confirmation met
        	            	+News lockout: Economic-calendar data unavailable; failing closed to avoid trading blind into news
        	Test:       	TestConfirmationPulse_NestedLTFFormat
{"level":"info","service":"alert","component":"redis_transport","time":1781341551730,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551730,"message":"alert_hub_closed"}
redis: 2026/06/13 09:05:51 pubsub.go:168: redis: discarding bad PubSub connection: set tcp [::1]:44782: use of closed network connection
--- FAIL: TestConfirmationPulse_NestedLTFFormat (0.00s)
=== RUN   TestFullPipeline_CounterTrendRejectedByGuard
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551730,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341551730,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551730,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551731,"message":"redis_subscriber_started"}
    guards_errors_test.go:44: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/guards_errors_test.go:44
        	Error:      	Not equal: 
        	            	expected: 1
        	            	actual  : 0
        	Test:       	TestFullPipeline_CounterTrendRejectedByGuard
    guards_errors_test.go:62: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/guards_errors_test.go:62
        	Error:      	Expected value not to be nil.
        	Test:       	TestFullPipeline_CounterTrendRejectedByGuard
{"level":"info","service":"alert","component":"redis_transport","time":1781341551736,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341551736,"message":"alert_hub_closed"}
redis: 2026/06/13 09:05:51 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:44796->[::1]:6379: use of closed network connection
{"level":"info","service":"alert","component":"redis_transport","time":1781341551736,"message":"redis_subscriber_stopped"}
--- FAIL: TestFullPipeline_CounterTrendRejectedByGuard (0.01s)
=== RUN   TestFullPipeline_TACollectionFailure
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341551736,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341551738,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341552245,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341552245,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341552245,"message":"redis_subscriber_stopped"}
--- PASS: TestFullPipeline_TACollectionFailure (0.51s)
=== RUN   TestFullPipeline_MacroCollectionFailure
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341552246,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341552247,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341552755,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341552755,"message":"alert_hub_closed"}
redis: 2026/06/13 09:05:52 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:44856->[::1]:6379: use of closed network connection
--- PASS: TestFullPipeline_MacroCollectionFailure (0.51s)
=== RUN   TestFullPipeline_RAGFailure

vel":"info","service":"alert","component":"redis_transport","time":1781341552755,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341552756,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341552757,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341552760,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341552761,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341552761,"message":"redis_subscriber_stopped"}
redis: 2026/06/13 09:05:52 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:44878->[::1]:6379: use of closed network connection
--- PASS: TestFullPipeline_RAGFailure (0.00s)
=== RUN   TestFullPipeline_ProcessorHTTPFailure
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341552761,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341552762,"message":"redis_subscriber_started"}
    guards_errors_test.go:287: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/guards_errors_test.go:287
        	Error:      	"0" is not greater than or equal to "1"
        	Test:       	TestFullPipeline_ProcessorHTTPFailure
        	Messages:   	Processor should be called at least once (may retry)
    guards_errors_test.go:308: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/guards_errors_test.go:308
        	Error:      	Should be true
        	Test:       	TestFullPipeline_ProcessorHTTPFailure
        	Messages:   	should have a failed output for EURUSD
{"level":"info","service":"alert","component":"redis_transport","time":1781341552767,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341552767,"message":"alert_hub_closed"}
redis: 2026/06/13 09:05:52 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:44894->[::1]:6379: use of closed network connection
{"level":"info","service":"alert","component":"redis_transport","time":1781341552767,"message":"redis_subscriber_stopped"}
--- FAIL: TestFullPipeline_ProcessorHTTPFailure (0.01s)
=== RUN   TestFullPipeline_TradeApproved
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341552767,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341552768,"message":"redis_subscriber_started"}
    happy_path_test.go:39: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/happy_path_test.go:39
        	Error:      	Not equal: 
        	            	expected: 1
        	            	actual  : 0
        	Test:       	TestFullPipeline_TradeApproved
        	Messages:   	Processor endpoint should be called once
    happy_path_test.go:85: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/happy_path_test.go:85
        	Error:      	Expected value not to be nil.
        	Test:       	TestFullPipeline_TradeApproved
        	Messages:   	processor output should be present
{"level":"info","service":"alert","component":"redis_transport","time":1781341552773,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341552773,"message":"alert_hub_closed"}
redis: 2026/06/13 09:05:52 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:44916->[::1]:6379: use of closed network connection
{"level":"info","service":"alert","component":"redis_transport","time":1781341552773,"message":"redis_subscriber_stopped"}
--- FAIL: TestFullPipeline_TradeApproved (0.01s)
=== RUN   TestFullPipeline_NoCandidates
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341552773,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341552775,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341552777,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341552777,"message":"alert_hub_closed"}
redis: 2026/06/13 09:05:52 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:44930->[::1]:6379: use of closed network connection
--- PASS: TestFullPipeline_NoCandidates (0.00s)
=== RUN   TestFullPipeline_ProcessorRejectsNoSetup
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341552777,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341552778,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341552779,"message":"redis_subscriber_started"}
    happy_path_test.go:246: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/happy_path_test.go:246
        	Error:      	Not equal: 
        	            	expected: 1
        	            	actual  : 0
        	Test:       	TestFullPipeline_ProcessorRejectsNoSetup
    happy_path_test.go:254: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/happy_path_test.go:254
        	Error:      	Not equal: 
        	            	expected: "NO_SETUP"
        	            	actual  : "REJECTED_BY_GUARD"
        	            	
        	            	Diff:
        	            	--- Expected
        	            	+++ Actual
        	            	@@ -1,2 +1,2 @@
        	            	-(constants.CycleOutcome) (len=8) "NO_SETUP"
        	            	+(constants.CycleOutcome) (len=17) "REJECTED_BY_GUARD"
        	            	 
        	Test:       	TestFullPipeline_ProcessorRejectsNoSetup
    happy_path_test.go:262: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/happy_path_test.go:262
        	Error:      	Expected value not to be nil.
        	Test:       	TestFullPipeline_ProcessorRejectsNoSetup
{"level":"info","service":"alert","component":"redis_transport","time":1781341552783,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341552783,"message":"alert_hub_closed"}
redis: 2026/06/13 09:05:52 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:44944->[::1]:6379: use of closed network connection
--- FAIL: TestFullPipeline_ProcessorRejectsNoSetup (0.01s)
=== RUN   TestRetry_TAFailsThenSucceeds
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341552784,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341552784,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341552785,"message":"redis_subscriber_started"}
    retry_concurrency_test.go:87: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/retry_concurrency_test.go:87
        	Error:      	Not equal: 
        	            	expected: 1
        	            	actual  : 0
        	Test:       	TestRetry_TAFailsThenSucceeds
        	Messages:   	response should have been flipped to success after threshold
    retry_concurrency_test.go:109: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/retry_concurrency_test.go:109
        	Error:      	Should be true
        	Test:       	TestRetry_TAFailsThenSucceeds
        	Messages:   	retry should succeed: second cycle attempt should produce successful output
{"level":"info","service":"alert","component":"redis_transport","time":1781341553292,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341553292,"message":"alert_hub_closed"}
redis: 2026/06/13 09:05:53 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:44968->[::1]:6379: use of closed network connection
{"level":"info","service":"alert","component":"redis_transport","time":1781341553292,"message":"redis_subscriber_stopped"}
--- FAIL: TestRetry_TAFailsThenSucceeds (0.51s)
=== RUN   TestRetry_AllAttemptsExhausted
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341553293,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341553294,"message":"redis_subscriber_started"}
    retry_concurrency_test.go:135: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/retry_concurrency_test.go:135
        	Error:      	"2" is not greater than or equal to "4"
        	Test:       	TestRetry_AllAttemptsExhausted
        	Messages:   	TA should be called multiple times across retries
{"level":"info","service":"alert","component":"redis_transport","time":1781341553801,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341553801,"message":"alert_hub_closed"}
redis: 2026/06/13 09:05:53 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:44984->[::1]:6379: use of closed network connection
{"level":"info","service":"alert","component":"redis_transport","time":1781341553802,"message":"redis_subscriber_stopped"}
--- FAIL: TestRetry_AllAttemptsExhausted (0.51s)
=== RUN   TestRetry_SuccessfulCycleDoesNotRetry
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341553802,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341553803,"message":"redis_subscriber_started"}
    retry_concurrency_test.go:184: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/retry_concurrency_test.go:184
        	Error:      	Not equal: 
        	            	expected: 1
        	            	actual  : 0
        	Test:       	TestRetry_SuccessfulCycleDoesNotRetry
        	Messages:   	Processor should be called exactly once (no retry)
{"level":"info","service":"alert","component":"redis_transport","time":1781341553808,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341553808,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341553808,"message":"redis_subscriber_stopped"}
--- FAIL: TestRetry_SuccessfulCycleDoesNotRetry (0.01s)
=== RUN   TestConcurrency_BoundedParallelism
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341553809,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341553810,"message":"redis_subscriber_started"}
    retry_concurrency_test.go:231: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/retry_concurrency_test.go:231
        	Error:      	Not equal: 
        	            	expected: 4
        	            	actual  : 0

   	Test:       	TestConcurrency_BoundedParallelism
        	Messages:   	Processor should be called once per candidate symbol
{"level":"info","service":"alert","component":"redis_transport","time":1781341553818,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341553818,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341553818,"message":"redis_subscriber_stopped"}
--- FAIL: TestConcurrency_BoundedParallelism (0.01s)
=== RUN   TestConcurrency_ContextCancellation
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341553819,"message":"redis_transport_started"}
{"level":"error","service":"alert","component":"redis_transport","error":"context canceled","event_id":"20260613090553-c8694295","time":1781341553819,"message":"redis_transport_publish_failed"}
{"level":"error","service":"alert","component":"redis_transport","error":"context canceled","event_id":"20260613090553-c0279ae9","time":1781341553819,"message":"redis_transport_publish_failed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341553819,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341553819,"message":"alert_hub_closed"}
--- PASS: TestConcurrency_ContextCancellation (0.00s)
FAIL
FAIL	github.com/flamegreat-1/etradie/src/gateway/e2etest	2.166s
=== RUN   TestGRPC_RunCycle_HappyPath
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555106,"message":"redis_transport_started"}
    cycle_confirm_test.go:40: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/cycle_confirm_test.go:40
        	Error:      	Received unexpected error:
        	            	rpc error: code = Unauthenticated desc = invalid token: missing or invalid 'status' claim
        	Test:       	TestGRPC_RunCycle_HappyPath
        	Messages:   	RunCycle RPC should not return error
{"level":"info","service":"alert","component":"redis_transport","time":1781341555112,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555112,"message":"alert_hub_closed"}
--- FAIL: TestGRPC_RunCycle_HappyPath (0.01s)
=== RUN   TestGRPC_RunCycle_NoCandidates
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555112,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555112,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341555112,"message":"redis_subscriber_stopped"}
    cycle_confirm_test.go:93: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/cycle_confirm_test.go:93
        	Error:      	Received unexpected error:
        	            	rpc error: code = Unauthenticated desc = invalid token: missing or invalid 'status' claim
        	Test:       	TestGRPC_RunCycle_NoCandidates
{"level":"info","service":"alert","component":"redis_transport","time":1781341555114,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555114,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555114,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341555115,"message":"redis_subscriber_stopped"}
--- FAIL: TestGRPC_RunCycle_NoCandidates (0.00s)
=== RUN   TestGRPC_RunCycle_EmptySymbols_UsesDefaults
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555115,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555118,"message":"redis_subscriber_started"}
    cycle_confirm_test.go:127: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/cycle_confirm_test.go:127
        	Error:      	Received unexpected error:
        	            	rpc error: code = Unauthenticated desc = invalid token: missing or invalid 'status' claim
        	Test:       	TestGRPC_RunCycle_EmptySymbols_UsesDefaults
{"level":"info","service":"alert","component":"redis_transport","time":1781341555118,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555118,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341555118,"message":"redis_subscriber_stopped"}
--- FAIL: TestGRPC_RunCycle_EmptySymbols_UsesDefaults (0.00s)
=== RUN   TestGRPC_ConfirmSetup_Confirmed
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555119,"message":"redis_transport_started"}
    cycle_confirm_test.go:161: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/cycle_confirm_test.go:161
        	Error:      	Received unexpected error:
        	            	rpc error: code = Unauthenticated desc = invalid token: missing or invalid 'status' claim
        	Test:       	TestGRPC_ConfirmSetup_Confirmed
{"level":"info","service":"alert","component":"redis_transport","time":1781341555120,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555120,"message":"alert_hub_closed"}
--- FAIL: TestGRPC_ConfirmSetup_Confirmed (0.00s)
=== RUN   TestGRPC_ConfirmSetup_ValidationError
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555120,"message":"redis_transport_started"}
redis: 2026/06/13 09:05:55 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:45106->[::1]:6379: use of closed network connection
    cycle_confirm_test.go:195: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/cycle_confirm_test.go:195
        	Error:      	Not equal: 
        	            	expected: 0x3
        	            	actual  : 0x10
        	Test:       	TestGRPC_ConfirmSetup_ValidationError
    cycle_confirm_test.go:196: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/cycle_confirm_test.go:196
        	Error:      	"invalid token: missing or invalid 'status' claim" does not contain "required"
        	Test:       	TestGRPC_ConfirmSetup_ValidationError
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555122,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341555122,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555123,"message":"redis_subscriber_started"}
    cycle_confirm_test.go:207: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/cycle_confirm_test.go:207
        	Error:      	Not equal: 
        	            	expected: 0x3
        	            	actual  : 0x10
        	Test:       	TestGRPC_ConfirmSetup_ValidationError
{"level":"info","service":"alert","component":"redis_transport","time":1781341555123,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555123,"message":"alert_hub_closed"}
--- FAIL: TestGRPC_ConfirmSetup_ValidationError (0.00s)
=== RUN   TestGRPC_NotifyExecutionCompleted_NoMgmtClient
redis: 2026/06/13 09:05:55 pubsub.go:168: redis: discarding bad PubSub connection: set tcp [::1]:45132: use of closed network connection
{"level":"info","service":"alert","component":"redis_transport","time":1781341555123,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555125,"message":"redis_transport_started"}
    handoff_config_test.go:62: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/handoff_config_test.go:62
        	Error:      	Received unexpected error:
        	            	rpc error: code = Unauthenticated desc = invalid token: missing or invalid 'status' claim
        	Test:       	TestGRPC_NotifyExecutionCompleted_NoMgmtClient
        	Messages:   	should not return gRPC error
{"level":"info","service":"alert","component":"redis_transport","time":1781341555127,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555127,"message":"alert_hub_closed"}
--- FAIL: TestGRPC_NotifyExecutionCompleted_NoMgmtClient (0.00s)
=== RUN   TestGRPC_NotifyExecutionCompleted_AllFieldsPropagated
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555127,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555127,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341555127,"message":"redis_subscriber_stopped"}
    handoff_config_test.go:110: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/handoff_config_test.go:110
        	Error:      	Received unexpected error:
        	            	rpc error: code = Unauthenticated desc = invalid token: missing or invalid 'status' claim
        	Test:       	TestGRPC_NotifyExecutionCompleted_AllFieldsPropagated
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555129,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341555129,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555129,"message":"alert_hub_closed"}
redis: 2026/06/13 09:05:55 pubsub.go:168: redis: discarding bad PubSub connection: set tcp [::1]:45148: use of closed network connection
{"level":"info","service":"alert","component":"redis_transport","time":1781341555129,"message":"redis_subscriber_stopped"}
--- FAIL: TestGRPC_NotifyExecutionCompleted_AllFieldsPropagated (0.00s)
=== RUN   TestGRPC_SetCycleInterval_Valid
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555129,"message":"redis_transport_started"}
    handoff_config_test.go:133: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/handoff_config_test.go:133
        	Error:      	Received unexpected error:
        	            	rpc error: code = Unauthenticated desc = invalid token: missing or invalid 'status' claim
        	Test:       	TestGRPC_SetCycleInterval_Valid
{"level":"info","service":"alert","component":"redis_transport","time":1781341555131,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555131,"message":"alert_hub_closed"}
--- FAIL: TestGRPC_SetCycleInterval_Valid (0.00s)
=== RUN   TestGRPC_SetCycleInterval_TooLow
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555131,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341555131,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555131,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555132,"message":"redis_subscriber_started"}
    handoff_config_test.go:157: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/handoff_config_test.go:157
        	Error:      	Not equal: 
        	            	expected: 0x3
        	            	actual  : 0x10
        	Test:       	TestGRPC_SetCycleInterval_TooLow
    handoff_config_test.go:158: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/handoff_config_test.go:158
        	Error:      	"invalid token: missing or invalid 'status' claim" does not contain "60"
        	Test:       	TestGRPC_SetCycleInterval_TooLow
{"level":"info","service":"alert","component":"redis_transport","time":1781341555134,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555134,"message":"alert_hub_closed"}
redis: 2026/06/13 09:05:55 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:45172->[::1]:6379: use of closed network connection
--- FAIL: TestGRPC_SetCycleInterval_TooLow (0.00s)
=== RUN   TestGRPC_SetCycleInterval_TooHigh


level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555134,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341555134,"message":"redis_subscriber_stopped"}
    handoff_config_test.go:178: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/handoff_config_test.go:178
        	Error:      	Not equal: 
        	            	expected: 0x3
        	            	actual  : 0x10
        	Test:       	TestGRPC_SetCycleInterval_TooHigh
    handoff_config_test.go:179: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/handoff_config_test.go:179
        	Error:      	"invalid token: missing or invalid 'status' claim" does not contain "86400"
        	Test:       	TestGRPC_SetCycleInterval_TooHigh
{"level":"info","service":"alert","component":"redis_transport","time":1781341555136,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555136,"message":"alert_hub_closed"}
--- FAIL: TestGRPC_SetCycleInterval_TooHigh (0.00s)
=== RUN   TestGRPC_GetGatewayConfig
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555137,"message":"redis_transport_started"}
    handoff_config_test.go:198: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/handoff_config_test.go:198
        	Error:      	Received unexpected error:
        	            	rpc error: code = Unauthenticated desc = invalid token: missing or invalid 'status' claim
        	Test:       	TestGRPC_GetGatewayConfig
{"level":"info","service":"alert","component":"redis_transport","time":1781341555138,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555138,"message":"alert_hub_closed"}
--- FAIL: TestGRPC_GetGatewayConfig (0.00s)
=== RUN   TestGRPC_GetActiveSymbols
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555138,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555138,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341555138,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555140,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341555140,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555140,"message":"redis_subscriber_started"}
    handoff_config_test.go:231: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/handoff_config_test.go:231
        	Error:      	Received unexpected error:
        	            	rpc error: code = Unauthenticated desc = invalid token: missing or invalid 'status' claim
        	Test:       	TestGRPC_GetActiveSymbols
{"level":"info","service":"alert","component":"redis_transport","time":1781341555141,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555141,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341555141,"message":"redis_subscriber_stopped"}
--- FAIL: TestGRPC_GetActiveSymbols (0.00s)
=== RUN   TestGRPC_SetActiveSymbols_Valid
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555142,"message":"redis_transport_started"}
    handoff_config_test.go:259: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/handoff_config_test.go:259
        	Error:      	Received unexpected error:
        	            	rpc error: code = Unauthenticated desc = invalid token: missing or invalid 'status' claim
        	Test:       	TestGRPC_SetActiveSymbols_Valid
        	Messages:   	SetActiveSymbols should not return gRPC error
{"level":"info","service":"alert","component":"redis_transport","time":1781341555143,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555143,"message":"alert_hub_closed"}
--- FAIL: TestGRPC_SetActiveSymbols_Valid (0.00s)
=== RUN   TestGRPC_ResetActiveSymbols
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555144,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555144,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341555144,"message":"redis_subscriber_stopped"}
    handoff_config_test.go:283: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/handoff_config_test.go:283
        	Error:      	Received unexpected error:
        	            	rpc error: code = Unauthenticated desc = invalid token: missing or invalid 'status' claim
        	Test:       	TestGRPC_ResetActiveSymbols
        	Messages:   	ResetActiveSymbols should not return gRPC error
{"level":"info","service":"alert","component":"redis_transport","time":1781341555146,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555146,"message":"alert_hub_closed"}
--- FAIL: TestGRPC_ResetActiveSymbols (0.00s)
=== RUN   TestGRPC_GetHealth
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555146,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555149,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341555149,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555149,"message":"redis_subscriber_started"}
    handoff_config_test.go:310: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/handoff_config_test.go:310
        	Error:      	Received unexpected error:
        	            	rpc error: code = Unauthenticated desc = invalid token: missing or invalid 'status' claim
        	Test:       	TestGRPC_GetHealth
        	Messages:   	GetHealth should not return gRPC error
{"level":"info","service":"alert","component":"redis_transport","time":1781341555150,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555150,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341555150,"message":"redis_subscriber_stopped"}
--- FAIL: TestGRPC_GetHealth (0.00s)
=== RUN   TestGRPC_RunCycle_InvalidSymbol_EmptyString
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555150,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555151,"message":"redis_subscriber_started"}
    handoff_config_test.go:354: Server returned gRPC error for empty symbol: code=Unauthenticated msg=invalid token: missing or invalid 'status' claim
{"level":"info","service":"alert","component":"redis_transport","time":1781341555152,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555152,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341555152,"message":"redis_subscriber_stopped"}
--- PASS: TestGRPC_RunCycle_InvalidSymbol_EmptyString (0.00s)
=== RUN   TestGRPC_NotifyExecutionCompleted_FullHandoff
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555154,"message":"redis_transport_started"}
    mgmt_handoff_test.go:315: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/mgmt_handoff_test.go:315
        	Error:      	Received unexpected error:
        	            	rpc error: code = Unauthenticated desc = invalid token: missing or invalid 'status' claim
        	Test:       	TestGRPC_NotifyExecutionCompleted_FullHandoff
        	Messages:   	handoff should succeed
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555156,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781341555156,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555156,"message":"alert_hub_closed"}
redis: 2026/06/13 09:05:55 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:45232->[::1]:6379: use of closed network connection
--- FAIL: TestGRPC_NotifyExecutionCompleted_FullHandoff (0.00s)
=== RUN   TestGRPC_NotifyExecutionCompleted_MgmtReturnsError
{"level":"info","service":"alert","component":"redis_transport","time":1781341555156,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555157,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781341555159,"message":"redis_subscriber_started"}
    mgmt_handoff_test.go:382: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/mgmt_handoff_test.go:382
        	Error:      	Not equal: 
        	            	expected: 0xd
        	            	actual  : 0x10
        	Test:       	TestGRPC_NotifyExecutionCompleted_MgmtReturnsError
        	Messages:   	Gateway wraps management errors as Internal
    mgmt_handoff_test.go:384: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/mgmt_handoff_test.go:384
        	Error:      	"invalid token: missing or invalid 'status' claim" does not contain "management"
        	Test:       	TestGRPC_NotifyExecutionCompleted_MgmtReturnsError
{"level":"info","service":"alert","component":"redis_transport","time":1781341555160,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555160,"message":"alert_hub_closed"}
redis: 2026/06/13 09:05:55 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:45236->[::1]:6379: use of closed network connection
--- FAIL: TestGRPC_NotifyExecutionCompleted_MgmtReturnsError (0.00s)
=== RUN   TestGRPC_NotifyExecutionCompleted_MgmtRejectsRegistration
{"level":"info","service":"alert","component":"redis_transport","time":1781341555160,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781341555161,"message":"redis_transport_started"}
    mgmt_handoff_test.go:415: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/mgmt_handoff_test.go:415
        	Error:      	Not equal: 
        	            	expected: 0xd
        	            	actual  : 0x10
        	Test:       	TestGRPC_NotifyExecutionCompleted_MgmtRejectsRegistration
{"level":"info","service":"alert","component":"redis_transport","time":1781341555168,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781341555168,"message":"alert_hub_closed"}
--- FAIL: TestGRPC_NotifyExecutionCompleted_MgmtRejectsRegistration (0.01s)
FAIL
FAIL	github.com/flamegreat-1/etradie/src/gateway/grpctest	0.073s
?   	github.com/flamegreat-1/etradie/src/gateway/internal/collectors	[no test files]
=== RUN   TestValidConfig_Passes
--- PASS: TestValidConfig_Passes (0.00s)
=== RUN   TestValidate_CycleIntervalSeconds_AtMinimum
--- PASS: TestValidate_CycleIntervalSeconds_AtMinimum (0.00s)