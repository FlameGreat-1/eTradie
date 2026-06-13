","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353083936,"message":"redis_subscriber_started"}
    edge_cases_test.go:56: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/edge_cases_test.go:56
        	Error:      	Not equal: 
        	            	expected: "REJECT"
        	            	actual  : "PASS"
        	            	
        	            	Diff:
        	            	--- Expected
        	            	+++ Actual
        	            	@@ -1,2 +1,2 @@
        	            	-(constants.GuardVerdict) (len=6) "REJECT"
        	            	+(constants.GuardVerdict) (len=4) "PASS"
        	            	 
        	Test:       	TestFullPipeline_NewsProximityGuardRejects
        	Messages:   	news proximity guard should REJECT
    edge_cases_test.go:58: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/edge_cases_test.go:58
        	Error:      	"No high-impact events within lockout window" does not contain "Non-Farm Payrolls"
        	Test:       	TestFullPipeline_NewsProximityGuardRejects
    edge_cases_test.go:59: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/edge_cases_test.go:59
        	Error:      	"No high-impact events within lockout window" does not contain "minutes"
        	Test:       	TestFullPipeline_NewsProximityGuardRejects
    edge_cases_test.go:60: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/edge_cases_test.go:60
        	Error:      	Expected value not to be nil.
        	Test:       	TestFullPipeline_NewsProximityGuardRejects
{"level":"info","service":"alert","component":"redis_transport","time":1781353083941,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353083941,"message":"alert_hub_closed"}
redis: 2026/06/13 12:18:03 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:41402->[::1]:6379: use of closed network connection
{"level":"info","service":"alert","component":"redis_transport","time":1781353083942,"message":"redis_subscriber_stopped"}
--- FAIL: TestFullPipeline_NewsProximityGuardRejects (0.01s)
=== RUN   TestFullPipeline_NilExecutionPort
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353083942,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353083943,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353083948,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353083948,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353083948,"message":"redis_subscriber_stopped"}
--- PASS: TestFullPipeline_NilExecutionPort (0.01s)
=== RUN   TestFullPipeline_TASymbolErrorStatus
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353083949,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353083950,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353083952,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353083952,"message":"alert_hub_closed"}
redis: 2026/06/13 12:18:03 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:41418->[::1]:6379: use of closed network connection
{"level":"info","service":"alert","component":"redis_transport","time":1781353083952,"message":"redis_subscriber_stopped"}
--- PASS: TestFullPipeline_TASymbolErrorStatus (0.00s)
=== RUN   TestFullPipeline_SnDCandidatesOnly
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353083953,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353083954,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353083958,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353083958,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353083958,"message":"redis_subscriber_stopped"}
--- PASS: TestFullPipeline_SnDCandidatesOnly (0.01s)
=== RUN   TestConfirmationPulse_NestedLTFFormat
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353083959,"message":"redis_transport_started"}
    edge_cases_test.go:255: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/edge_cases_test.go:255
        	Error:      	Should be true
        	Test:       	TestConfirmationPulse_NestedLTFFormat
        	Messages:   	nested {confirmed: true} format should be parsed correctly
    edge_cases_test.go:257: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/edge_cases_test.go:257
        	Error:      	Should be true
        	Test:       	TestConfirmationPulse_NestedLTFFormat
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353083960,"message":"redis_subscriber_started"}
    edge_cases_test.go:258: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/edge_cases_test.go:258
        	Error:      	Not equal: 
        	            	expected: "SMC LTF confirmation met"
        	            	actual  : "SMC LTF confirmation not yet met"
        	            	
        	            	Diff:
        	            	--- Expected
        	            	+++ Actual
        	            	@@ -1 +1 @@
        	            	-SMC LTF confirmation met
        	            	+SMC LTF confirmation not yet met
        	Test:       	TestConfirmationPulse_NestedLTFFormat
{"level":"info","service":"alert","component":"redis_transport","time":1781353083960,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353083960,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353083960,"message":"redis_subscriber_stopped"}
--- FAIL: TestConfirmationPulse_NestedLTFFormat (0.00s)
=== RUN   TestFullPipeline_CounterTrendRejectedByGuard
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353083960,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353083961,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353083966,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353083966,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353083967,"message":"redis_subscriber_stopped"}
redis: 2026/06/13 12:18:03 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:41462->[::1]:6379: use of closed network connection
--- PASS: TestFullPipeline_CounterTrendRejectedByGuard (0.01s)
=== RUN   TestFullPipeline_TACollectionFailure
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353083967,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353083968,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353084477,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353084477,"message":"alert_hub_closed"}
redis: 2026/06/13 12:18:04 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:41488->[::1]:6379: use of closed network connection
{"level":"info","service":"alert","component":"redis_transport","time":1781353084477,"message":"redis_subscriber_stopped"}
--- PASS: TestFullPipeline_TACollectionFailure (0.51s)
=== RUN   TestFullPipeline_MacroCollectionFailure
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353084477,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353084479,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353084987,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353084987,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353084987,"message":"redis_subscriber_stopped"}
--- PASS: TestFullPipeline_MacroCollectionFailure (0.51s)
=== RUN   TestFullPipeline_RAGFailure
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353084988,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353084989,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353084993,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353084993,"message":"alert_hub_closed"}
redis: 2026/06/13 12:18:04 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:41532->[::1]:6379: use of closed network connection
{"level":"info","service":"alert","component":"redis_transport","time":1781353084993,"message":"redis_subscriber_stopped"}
--- PASS: TestFullPipeline_RAGFailure (0.01s)
=== RUN   TestFullPipeline_ProcessorHTTPFailure
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353084993,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353084995,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353084999,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353084999,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353084999,"message":"redis_subscriber_stopped"}
--- PASS: TestFullPipeline_ProcessorHTTPFailure (0.01s)
=== RUN   TestFullPipeline_TradeApproved
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353084999,"message":"redis_transport_started"}
redis: 2026/06/13 12:18:05 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:41546->[::1]:6379: use of closed network connection
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353085000,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353085005,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353085005,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353085005,"message":"redis_subscriber_stopped"}
--- PASS: TestFullPipeline_TradeApproved (0.01s)
=== RUN   TestFullPipeline_NoCandidates
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353085005,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353085007,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353085009,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353085009,"message":"alert_hub_closed"}
redis: 2026/06/13 12:18:05 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:41586->[::1]:6379: use of closed network connection
{"level":"info","service":"alert","component":"redis_transport","time":1781353085009,"message":"redis_subscriber_stopped"}
--- PASS: TestFullPipeline_NoCandidates (0.00s)
=== RUN   TestFullPipeline_ProcessorRejectsNoSetup
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353085009,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353085011,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353085015,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353085015,"message":"alert_hub_closed"}
redis: 2026/06/13 12:18:05 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:41598->[::1]:6379: use of closed network connection
{"level":"info","service":"alert","component":"redis_transport","time":1781353085015,"message":"redis_subscriber_stopped"}
--- PASS: TestFullPipeline_ProcessorRejectsNoSetup (0.01s)


=== RUN   TestRetry_TAFailsThenSucceeds
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353085015,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353085016,"message":"redis_subscriber_started"}
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
{"level":"info","service":"alert","component":"redis_transport","time":1781353085524,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353085524,"message":"alert_hub_closed"}
redis: 2026/06/13 12:18:05 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:41612->[::1]:6379: use of closed network connection
{"level":"info","service":"alert","component":"redis_transport","time":1781353085525,"message":"redis_subscriber_stopped"}
--- FAIL: TestRetry_TAFailsThenSucceeds (0.51s)
=== RUN   TestRetry_AllAttemptsExhausted
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353085525,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353085526,"message":"redis_subscriber_started"}
    retry_concurrency_test.go:135: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/e2etest/retry_concurrency_test.go:135
        	Error:      	"2" is not greater than or equal to "4"
        	Test:       	TestRetry_AllAttemptsExhausted
        	Messages:   	TA should be called multiple times across retries
{"level":"info","service":"alert","component":"redis_transport","time":1781353086034,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353086034,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353086034,"message":"redis_subscriber_stopped"}
--- FAIL: TestRetry_AllAttemptsExhausted (0.51s)
=== RUN   TestRetry_SuccessfulCycleDoesNotRetry
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353086035,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353086036,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353086040,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353086040,"message":"alert_hub_closed"}
redis: 2026/06/13 12:18:06 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:41648->[::1]:6379: use of closed network connection
--- PASS: TestRetry_SuccessfulCycleDoesNotRetry (0.01s)
{"level":"info","service":"alert","component":"redis_transport","time":1781353086041,"message":"redis_subscriber_stopped"}
=== RUN   TestConcurrency_BoundedParallelism
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353086041,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353086042,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353086051,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353086051,"message":"alert_hub_closed"}
redis: 2026/06/13 12:18:06 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:41672->[::1]:6379: use of closed network connection
{"level":"info","service":"alert","component":"redis_transport","time":1781353086051,"message":"redis_subscriber_stopped"}
--- PASS: TestConcurrency_BoundedParallelism (0.01s)
=== RUN   TestConcurrency_ContextCancellation
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353086052,"message":"redis_transport_started"}
{"level":"error","service":"alert","component":"redis_transport","error":"context canceled","event_id":"20260613121806-f65af419","time":1781353086052,"message":"redis_transport_publish_failed"}
{"level":"error","service":"alert","component":"redis_transport","error":"context canceled","event_id":"20260613121806-7471f810","time":1781353086052,"message":"redis_transport_publish_failed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353086052,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353086053,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353086053,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353086053,"message":"redis_subscriber_stopped"}
--- PASS: TestConcurrency_ContextCancellation (0.00s)
FAIL
FAIL	github.com/flamegreat-1/etradie/src/gateway/e2etest	2.177s
=== RUN   TestGRPC_RunCycle_HappyPath
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087248,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087252,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087262,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353087262,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087262,"message":"redis_subscriber_stopped"}
--- PASS: TestGRPC_RunCycle_HappyPath (0.01s)
=== RUN   TestGRPC_RunCycle_NoCandidates
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087262,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087264,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087273,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353087273,"message":"alert_hub_closed"}
redis: 2026/06/13 12:18:07 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:41744->[::1]:6379: use of closed network connection
--- PASS: TestGRPC_RunCycle_NoCandidates (0.01s)
=== RUN   TestGRPC_RunCycle_EmptySymbols_UsesDefaults
{"level":"info","service":"alert","component":"redis_transport","time":1781353087274,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087274,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087275,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087283,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353087283,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087283,"message":"redis_subscriber_stopped"}
--- PASS: TestGRPC_RunCycle_EmptySymbols_UsesDefaults (0.01s)
=== RUN   TestGRPC_ConfirmSetup_Confirmed
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087284,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087285,"message":"redis_subscriber_started"}
    cycle_confirm_test.go:164: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/cycle_confirm_test.go:164
        	Error:      	Should be true
        	Test:       	TestGRPC_ConfirmSetup_Confirmed
        	Messages:   	LTF should be confirmed
    cycle_confirm_test.go:165: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/cycle_confirm_test.go:165
        	Error:      	Should be true
        	Test:       	TestGRPC_ConfirmSetup_Confirmed
    cycle_confirm_test.go:166: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/cycle_confirm_test.go:166
        	Error:      	Not equal: 
        	            	expected: "SMC LTF confirmation met"
        	            	actual  : "News lockout: Economic-calendar data unavailable; failing closed to avoid trading blind into news"
        	            	
        	            	Diff:
        	            	--- Expected
        	            	+++ Actual
        	            	@@ -1 +1 @@
        	            	-SMC LTF confirmation met
        	            	+News lockout: Economic-calendar data unavailable; failing closed to avoid trading blind into news
        	Test:       	TestGRPC_ConfirmSetup_Confirmed
    cycle_confirm_test.go:170: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/cycle_confirm_test.go:170
        	Error:      	Not equal: 
        	            	expected: 1
        	            	actual  : 0
        	Test:       	TestGRPC_ConfirmSetup_Confirmed
    cycle_confirm_test.go:171: 
        	Error Trace:	/home/runner/work/eTradie/eTradie/src/gateway/grpctest/cycle_confirm_test.go:171
        	Error:      	Not equal: 
        	            	expected: 0
        	            	actual  : 1
        	Test:       	TestGRPC_ConfirmSetup_Confirmed
{"level":"info","service":"alert","component":"redis_transport","time":1781353087287,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353087287,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087287,"message":"redis_subscriber_stopped"}
--- FAIL: TestGRPC_ConfirmSetup_Confirmed (0.00s)
=== RUN   TestGRPC_ConfirmSetup_ValidationError
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087288,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087290,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087293,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353087293,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087293,"message":"redis_subscriber_stopped"}
--- PASS: TestGRPC_ConfirmSetup_ValidationError (0.01s)
=== RUN   TestGRPC_NotifyExecutionCompleted_NoMgmtClient
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087293,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087295,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087298,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353087298,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087298,"message":"redis_subscriber_stopped"}
--- PASS: TestGRPC_NotifyExecutionCompleted_NoMgmtClient (0.01s)
=== RUN   TestGRPC_NotifyExecutionCompleted_AllFieldsPropagated
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087299,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087302,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087303,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353087303,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087304,"message":"redis_subscriber_stopped"}
--- PASS: TestGRPC_NotifyExecutionCompleted_AllFieldsPropagated (0.00s)
=== RUN   TestGRPC_SetCycleInterval_Valid
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087304,"message":"

{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087304,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087307,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087311,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353087312,"message":"alert_hub_closed"}
redis: 2026/06/13 12:18:07 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:41812->[::1]:6379: use of closed network connection
--- PASS: TestGRPC_SetCycleInterval_Valid (0.01s)
=== RUN   TestGRPC_SetCycleInterval_TooLow
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087312,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087312,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087314,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353087314,"message":"alert_hub_closed"}
--- PASS: TestGRPC_SetCycleInterval_TooLow (0.00s)
=== RUN   TestGRPC_SetCycleInterval_TooHigh
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087314,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087315,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087315,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087316,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353087316,"message":"alert_hub_closed"}
--- PASS: TestGRPC_SetCycleInterval_TooHigh (0.00s)
=== RUN   TestGRPC_GetGatewayConfig
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087316,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087316,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087316,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087319,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087320,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353087320,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087320,"message":"redis_subscriber_stopped"}
--- PASS: TestGRPC_GetGatewayConfig (0.00s)
=== RUN   TestGRPC_GetActiveSymbols
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087321,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087323,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087324,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353087324,"message":"alert_hub_closed"}
redis: 2026/06/13 12:18:07 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:41904->[::1]:6379: use of closed network connection
--- PASS: TestGRPC_GetActiveSymbols (0.00s)
=== RUN   TestGRPC_SetActiveSymbols_Valid
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087325,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087325,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087327,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087331,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353087331,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087331,"message":"redis_subscriber_stopped"}
--- PASS: TestGRPC_SetActiveSymbols_Valid (0.01s)
=== RUN   TestGRPC_ResetActiveSymbols
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087331,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087335,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087337,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353087337,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087337,"message":"redis_subscriber_stopped"}
--- PASS: TestGRPC_ResetActiveSymbols (0.01s)
=== RUN   TestGRPC_GetHealth
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087338,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087339,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087342,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353087342,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087343,"message":"redis_subscriber_stopped"}
--- PASS: TestGRPC_GetHealth (0.00s)
=== RUN   TestGRPC_RunCycle_InvalidSymbol_EmptyString
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087343,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087346,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087354,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087354,"message":"redis_subscriber_stopped"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353087354,"message":"alert_hub_closed"}
--- PASS: TestGRPC_RunCycle_InvalidSymbol_EmptyString (0.01s)
=== RUN   TestGRPC_NotifyExecutionCompleted_FullHandoff
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087356,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087357,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087361,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353087363,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353087361,"message":"redis_subscriber_stopped"}
--- PASS: TestGRPC_NotifyExecutionCompleted_FullHandoff (0.01s)
=== RUN   TestGRPC_NotifyExecutionCompleted_MgmtReturnsError
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353087364,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353087365,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353090747,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353090747,"message":"alert_hub_closed"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353090748,"message":"redis_subscriber_stopped"}
--- PASS: TestGRPC_NotifyExecutionCompleted_MgmtReturnsError (3.39s)
=== RUN   TestGRPC_NotifyExecutionCompleted_MgmtRejectsRegistration
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","history_key":"etradie:alert_history","max_history":2000,"time":1781353090750,"message":"redis_transport_started"}
{"level":"info","service":"alert","component":"redis_transport","channel":"etradie:alerts","time":1781353090752,"message":"redis_subscriber_started"}
{"level":"info","service":"alert","component":"redis_transport","time":1781353090758,"message":"redis_transport_closed"}
{"level":"info","service":"alert","component":"alert_hub","time":1781353090758,"message":"alert_hub_closed"}
redis: 2026/06/13 12:18:10 pubsub.go:168: redis: discarding bad PubSub connection: read tcp [::1]:35490->[::1]:6379: use of closed network connection
--- PASS: TestGRPC_NotifyExecutionCompleted_MgmtRejectsRegistration (0.01s)
FAIL
FAIL	github.com/flamegreat-1/etradie/src/gateway/grpctest	3.521s
?   	github.com/flamegreat-1/etradie/src/gateway/internal/collectors	[no test files]
=== RUN   TestValidConfig_Passes
--- PASS: TestValidConfig_Passes (0.00s)

00s)
=== RUN   TestFail_SetsCompletedAt
--- PASS: TestFail_SetsCompletedAt (0.00s)
=== RUN   TestFail_RecordsPhaseDuration
--- PASS: TestFail_RecordsPhaseDuration (0.00s)
=== RUN   TestToState_MatchesTrackerFields
--- PASS: TestToState_MatchesTrackerFields (0.00s)
=== RUN   TestToState_DurationsMapIsCopy
--- PASS: TestToState_DurationsMapIsCopy (0.00s)
=== RUN   TestToState_RunningCycle_NoCompletedAt
--- PASS: TestToState_RunningCycle_NoCompletedAt (0.00s)
=== RUN   TestToState_FailedCycle_HasErrorFields
Error: src/gateway/internal/routing/guards_test.go:16:12: undefined: checkHighImpactEventProximity
Error: src/gateway/internal/routing/guards_test.go:34:12: undefined: checkHighImpactEventProximity
Error: src/gateway/internal/routing/guards_test.go:56:12: undefined: checkHighImpactEventProximity
Error: src/gateway/internal/routing/guards_test.go:84:12: undefined: checkHighImpactEventProximity
Error: src/gateway/internal/routing/guards_test.go:96:12: undefined: checkCounterTrend
Error: src/gateway/internal/routing/guards_test.go:106:12: undefined: checkCounterTrend
Error: src/gateway/internal/routing/guards_test.go:120:12: undefined: checkCounterTrend
Error: src/gateway/internal/routing/guards_test.go:136:12: undefined: checkCounterTrend
Error: src/gateway/internal/routing/guards_test.go:150:12: undefined: checkCounterTrend
Error: src/gateway/internal/routing/guards_test.go:164:12: undefined: checkWeekendGapRisk
Error: src/gateway/internal/routing/guards_test.go:164:12: too many errors
--- PASS: TestToState_FailedCycle_HasErrorFields (0.00s)
PASS
ok  	github.com/flamegreat-1/etradie/src/gateway/internal/pipeline	0.026s
?   	github.com/flamegreat-1/etradie/src/gateway/internal/ports	[no test files]
?   	github.com/flamegreat-1/etradie/src/gateway/internal/pulse	[no test files]
=== RUN   TestBuild_RuleFirstStrategy_NFPEvent
--- PASS: TestBuild_RuleFirstStrategy_NFPEvent (0.00s)
=== RUN   TestBuild_ScenarioFirstStrategy_WhenFrameworkAndSetupPresent
--- PASS: TestBuild_ScenarioFirstStrategy_WhenFrameworkAndSetupPresent (0.00s)
=== RUN   TestBuild_HybridStrategy_Default
--- PASS: TestBuild_HybridStrategy_Default (0.00s)
=== RUN   TestBuild_QueryTextContainsSymbol
--- PASS: TestBuild_QueryTextContainsSymbol (0.00s)
=== RUN   TestBuild_SMCFlags
--- PASS: TestBuild_SMCFlags (0.00s)
=== RUN   TestBuild_MacroFlags_DXYPresent
--- PASS: TestBuild_MacroFlags_DXYPresent (0.00s)
=== RUN   TestBuild_MacroFlags_QEQTPresent
--- PASS: TestBuild_MacroFlags_QEQTPresent (0.00s)
=== RUN   TestBuild_AllFrameworksAlwaysIncludesWyckoff
--- PASS: TestBuild_AllFrameworksAlwaysIncludesWyckoff (0.00s)
=== RUN   TestBuild_SymbolPassthrough
--- PASS: TestBuild_SymbolPassthrough (0.00s)
PASS

ols_EmptyList_ReturnsFalse (0.00s)
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
0s
0s
