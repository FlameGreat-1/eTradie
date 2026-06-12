=3.15.0 (from safety==3.3.1->-r requirements/security.txt (line 5))
  Downloading marshmallow-4.3.0-py3-none-any.whl.metadata (6.8 kB)
Collecting nltk>=3.9 (from safety==3.3.1->-r requirements/security.txt (line 5))
  Downloading nltk-3.9.4-py3-none-any.whl.metadata (3.2 kB)
Collecting psutil~=6.1.0 (from safety==3.3.1->-r requirements/security.txt (line 5))
  Downloading psutil-6.1.1-cp36-abi3-manylinux_2_12_x86_64.manylinux2010_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (22 kB)
INFO: pip is looking at multiple versions of safety to determine which version is compatible with other requirements. This could take a while.
ERROR: Cannot install -r /home/runner/work/eTradie/eTradie/requirements/base.txt (line 2), -r /home/runner/work/eTradie/eTradie/requirements/base.txt (line 5), -r /home/runner/work/eTradie/eTradie/requirements/base.txt (line 55), -r /home/runner/work/eTradie/eTradie/requirements/base.txt (line 56), -r /home/runner/work/eTradie/eTradie/requirements/base.txt (line 57), -r /home/runner/work/eTradie/eTradie/requirements/base.txt (line 67), -r requirements/security.txt (line 5) and pydantic==2.10.6 because these package versions have conflicting dependencies.

ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/latest/topics/dependency-resolution/#dealing-with-dependency-conflicts
The conflict is caused by:
    The user requested pydantic==2.10.6
    fastapi 0.115.8 depends on pydantic!=1.8, !=1.8.1, !=2.0.0, !=2.0.1, !=2.1.0, <3.0.0 and >=1.7.4
    pydantic-settings 2.8.1 depends on pydantic>=2.7.0
    openai 1.14.0 depends on pydantic<3 and >=1.9.0
    anthropic 0.21.0 depends on pydantic<3 and >=1.9.0
    google-genai 0.2.0 depends on pydantic<3.0.0dev and >=2.0.0
    chromadb 0.5.20 depends on pydantic>=1.9
    safety 3.3.1 depends on pydantic<2.10.0 and >=2.6.0

Additionally, some packages in these conflicts have no matching distributions available for your environment:
    pydantic

To fix this you could try to:
1. loosen the range of package versions you've specified
2. remove package versions to allow pip to attempt to solve the dependency conflict

Error: Process completed with exit code 1.





Run govulncheck ./src/gateway/... ./src/execution/... ./src/management/... ./src/billing/... ./src/auth/...
=== Symbol Results ===

Vulnerability #1: GO-2026-5039
    Arbitrary inputs are included in errors without any escaping in
    net/textproto
  More info: https://pkg.go.dev/vuln/GO-2026-5039
  Standard library
    Found in: net/textproto@go1.23.12
    Fixed in: net/textproto@go1.25.11
    Example traces found:
Error:       #1: src/gateway/internal/pipeline/orchestrator.go:770:64: pipeline.Orchestrator.RunConfirmationPulseWithParams calls textproto.Error.Error
Error:       #2: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls textproto.Reader.ReadMIMEHeader
Error:       #3: src/mails/sender.go:103:31: mails.Sender.send calls smtp.NewClient, which calls textproto.Reader.ReadResponse

Vulnerability #2: GO-2026-5037
    Inefficient candidate hostname parsing in crypto/x509
  More info: https://pkg.go.dev/vuln/GO-2026-5037
  Standard library
    Found in: crypto/x509@go1.23.12
    Fixed in: crypto/x509@go1.25.11
    Example traces found:
Error:       #1: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls x509.Certificate.Verify
Error:       #2: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls x509.Certificate.VerifyHostname
Error:       #3: src/gateway/internal/pipeline/orchestrator.go:770:64: pipeline.Orchestrator.RunConfirmationPulseWithParams calls x509.HostnameError.Error

Vulnerability #3: GO-2026-4982
    Bypass of meta content URL escaping causes XSS in html/template
  More info: https://pkg.go.dev/vuln/GO-2026-4982
  Standard library
    Found in: html/template@go1.23.12
    Fixed in: html/template@go1.25.10
    Example traces found:



Error:       #1: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls template.Template.Execute
Error:       #2: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls template.Template.ExecuteTemplate

Vulnerability #4: GO-2026-4980
    Escaper bypass leads to XSS in html/template
  More info: https://pkg.go.dev/vuln/GO-2026-4980
  Standard library
    Found in: html/template@go1.23.12
    Fixed in: html/template@go1.25.10
    Example traces found:
Error:       #1: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls template.Template.Execute
Error:       #2: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls template.Template.ExecuteTemplate

Vulnerability #5: GO-2026-4976
    ReverseProxy forwards queries with more than urlmaxqueryparams parameters in
    net/http/httputil
  More info: https://pkg.go.dev/vuln/GO-2026-4976
  Standard library
    Found in: net/http/httputil@go1.23.12
    Fixed in: net/http/httputil@go1.25.10
    Example traces found:
Error:       #1: src/gateway/internal/server/proxy_handler.go:231:20: server.RegisterRoutes calls httputil.ReverseProxy.ServeHTTP

Vulnerability #6: GO-2026-4971
    Panic in Dial and LookupPort when handling NUL byte on Windows in net
  More info: https://pkg.go.dev/vuln/GO-2026-4971
  Standard library
    Found in: net@go1.23.12
    Fixed in: net@go1.25.10
    Example traces found:
Error:       #1: src/mails/sender.go:98:30: mails.Sender.send calls net.DialTimeout
Error:       #2: src/billing/store/usage.go:726:25: store.UsageStore.JanitorReapStaleReservations calls pgxpool.Pool.Query, which eventually calls net.Dialer.DialContext
Error:       #3: src/gateway/internal/server/grpc_server.go:137:24: server.GRPCServer.Start calls net.Listen


Error:       #4: src/execution/cmd/execution/main.go:96:36: execution.main calls pgxpool.NewWithConfig, which eventually calls net.Resolver.LookupHost
Error:       #5: src/gateway/grpctest/harness.go:210:29: grpctest.NewHarness calls grpc.NewClient, which eventually calls net.Resolver.LookupSRV
Error:       #6: src/gateway/grpctest/harness.go:210:29: grpctest.NewHarness calls grpc.NewClient, which eventually calls net.Resolver.LookupTXT

Vulnerability #7: GO-2026-4947
    Unexpected work during chain building in crypto/x509
  More info: https://pkg.go.dev/vuln/GO-2026-4947
  Standard library
    Found in: crypto/x509@go1.23.12
    Fixed in: crypto/x509@go1.25.9
    Example traces found:
Error:       #1: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls x509.Certificate.Verify

Vulnerability #8: GO-2026-4946
    Inefficient policy validation in crypto/x509
  More info: https://pkg.go.dev/vuln/GO-2026-4946
  Standard library
    Found in: crypto/x509@go1.23.12
    Fixed in: crypto/x509@go1.25.9
    Example traces found:
Error:       #1: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls x509.Certificate.Verify

Vulnerability #9: GO-2026-4918
    Infinite loop in HTTP/2 transport when given bad SETTINGS_MAX_FRAME_SIZE in
    net/http/internal/http2 in golang.org/x/net
  More info: https://pkg.go.dev/vuln/GO-2026-4918
  Module: golang.org/x/net
    Found in: golang.org/x/net@v0.30.0
    Fixed in: golang.org/x/net@v0.53.0

  Standard library
    Found in: net/http@go1.23.12
    Fixed in: net/http@go1.25.10
    Example traces found:
Error:       #1: src/gateway/internal/infra/engine_http.go:445:31: infra.EngineHTTPClient.Close calls http.Client.CloseIdleConnections
Error:       #2: src/gateway/internal/infra/engine_http.go:433:26: infra.EngineHTTPClient.HealthCheck calls http.Client.Do



Error:       #3: src/execution/brokertest/mock_broker_server.go:81:52: brokertest.MockBrokerServer.Close calls httptest.Server.Close, which calls http.Transport.CloseIdleConnections
Error:       #4: src/gateway/internal/server/proxy_handler.go:231:20: server.RegisterRoutes calls httputil.ReverseProxy.ServeHTTP, which calls http.Transport.RoundTrip

Vulnerability #10: GO-2026-4870
    Unauthenticated TLS 1.3 KeyUpdate record can cause persistent connection
    retention and DoS in crypto/tls
  More info: https://pkg.go.dev/vuln/GO-2026-4870
  Standard library
    Found in: crypto/tls@go1.23.12
    Fixed in: crypto/tls@go1.25.9
    Example traces found:
Error:       #1: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls tls.Conn.Handshake
Error:       #2: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls tls.Conn.HandshakeContext
Error:       #3: src/auth/oauth_google.go:235:25: auth.GoogleOAuthProvider.ExchangeCodeAndVerify calls io.ReadAll, which eventually calls tls.Conn.Read
Error:       #4: src/execution/cmd/executionctl/main.go:44:14: executionctl.main calls fmt.Fprintf, which calls tls.Conn.Write
Error:       #5: src/gateway/e2etest/harness.go:212:32: e2etest.NewHarness calls redis.NewClient, which eventually calls tls.DialWithDialer
Error:       #6: src/gateway/internal/infra/engine_http.go:433:26: infra.EngineHTTPClient.HealthCheck calls http.Client.Do, which eventually calls tls.Dialer.DialContext

Vulnerability #11: GO-2026-4865
    JsBraceDepth Context Tracking Bugs (XSS) in html/template
  More info: https://pkg.go.dev/vuln/GO-2026-4865
  Standard library
    Found in: html/template@go1.23.12
    Fixed in: html/template@go1.25.9
    Example traces found:
Error:       #1: src/gateway/internal/pipeline/orchestrator.go:770:64: pipeline.Orchestrator.RunConfirmationPulseWithParams calls template.Error.Error
Error:       #2: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls template.Template.Execute
Error:       #3: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls template.Template.ExecuteTemplate
Error:       #4: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls template.Template.Funcs
Error:       #5: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls template.Template.Parse
Error:       #6: src/billing/cmd/server/main.go:43:15: server.main calls fmt.Fprintln, which eventually calls template.context.String



Vulnerability #12: GO-2026-4762
    Authorization bypass in gRPC-Go via missing leading slash in :path in
    google.golang.org/grpc
  More info: https://pkg.go.dev/vuln/GO-2026-4762
  Module: google.golang.org/grpc
    Found in: google.golang.org/grpc@v1.68.1
    Fixed in: google.golang.org/grpc@v1.79.3
    Example traces found:
Error:       #1: src/gateway/internal/server/grpc_server.go:144:23: server.GRPCServer.Start calls grpc.Server.Serve

Vulnerability #13: GO-2026-4603
    URLs in meta content attribute actions are not escaped in html/template
  More info: https://pkg.go.dev/vuln/GO-2026-4603
  Standard library
    Found in: html/template@go1.23.12
    Fixed in: html/template@go1.25.8
    Example traces found:
Error:       #1: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls template.Template.Execute
Error:       #2: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls template.Template.ExecuteTemplate

Vulnerability #14: GO-2026-4602
    FileInfo can escape from a Root in os
  More info: https://pkg.go.dev/vuln/GO-2026-4602
  Standard library
    Found in: os@go1.23.12
    Fixed in: os@go1.25.8
    Example traces found:
Error:       #1: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls os.ReadDir


Vulnerability #15: GO-2026-4601
    Incorrect parsing of IPv6 host literals in net/url
  More info: https://pkg.go.dev/vuln/GO-2026-4601
  Standard library
    Found in: net/url@go1.23.12
    Fixed in: net/url@go1.25.8
    Example traces found:
Error:       #1: src/auth/cors.go:45:22: auth.BuildCORSAllowlist calls url.Parse
Error:       #2: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls url.ParseRequestURI
Error:       #3: src/gateway/internal/infra/engine_http.go:433:26: infra.EngineHTTPClient.HealthCheck calls http.Client.Do, which eventually calls url.URL.Parse

Vulnerability #16: GO-2026-4394
    OpenTelemetry Go SDK Vulnerable to Arbitrary Code Execution via PATH
    Hijacking in go.opentelemetry.io/otel/sdk
  More info: https://pkg.go.dev/vuln/GO-2026-4394
  Module: go.opentelemetry.io/otel/sdk
    Found in: go.opentelemetry.io/otel/sdk@v1.31.0
    Fixed in: go.opentelemetry.io/otel/sdk@v1.40.0
    Example traces found:
Error:       #1: src/gateway/internal/observability/tracing.go:77:24: observability.InitTracing calls trace.WithBatcher, which eventually calls env.BatchSpanProcessorExportTimeout
Error:       #2: src/gateway/internal/observability/tracing.go:77:24: observability.InitTracing calls trace.WithBatcher, which eventually calls env.BatchSpanProcessorMaxExportBatchSize
Error:       #3: src/gateway/internal/observability/tracing.go:77:24: observability.InitTracing calls trace.WithBatcher, which eventually calls env.BatchSpanProcessorMaxQueueSize
Error:       #4: src/gateway/internal/observability/tracing.go:77:24: observability.InitTracing calls trace.WithBatcher, which eventually calls env.BatchSpanProcessorScheduleDelay
Error:       #5: src/gateway/internal/observability/tracing.go:76:40: observability.InitTracing calls trace.NewTracerProvider, which eventually calls env.SpanAttributeCount
Error:       #6: src/gateway/internal/observability/tracing.go:76:40: observability.InitTracing calls trace.NewTracerProvider, which eventually calls env.SpanAttributeValueLength
Error:       #7: src/gateway/internal/observability/tracing.go:76:40: observability.InitTracing calls trace.NewTracerProvider, which eventually calls env.SpanEventAttributeCount
Error:       #8: src/gateway/internal/observability/tracing.go:76:40: observability.InitTracing calls trace.NewTracerProvider, which eventually calls env.SpanEventCount


Error:       #9: src/gateway/internal/observability/tracing.go:76:40: observability.InitTracing calls trace.NewTracerProvider, which eventually calls env.SpanLinkAttributeCount
Error:       #10: src/gateway/internal/observability/tracing.go:76:40: observability.InitTracing calls trace.NewTracerProvider, which eventually calls env.SpanLinkCount
Error:       #11: src/management/internal/observability/tracing.go:14:2: observability.init calls trace.init, which calls env.init
Error:       #12: src/management/internal/observability/tracing.go:14:2: observability.init calls trace.init, which calls instrumentation.init
Error:       #13: src/gateway/internal/observability/tracing.go:76:40: observability.InitTracing calls trace.NewTracerProvider, which eventually calls resource.Default
Error:       #14: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls resource.Default
Error:       #15: src/gateway/internal/observability/tracing.go:76:40: observability.InitTracing calls trace.NewTracerProvider, which eventually calls resource.Environment
Error:       #16: src/gateway/internal/observability/tracing.go:76:40: observability.InitTracing calls trace.NewTracerProvider, which eventually calls resource.Merge
Error:       #17: src/gateway/internal/observability/tracing.go:68:27: observability.InitTracing calls resource.New
Error:       #18: proto/gateway/v1/gateway_grpc.pb.go:115:20: gateway.gatewayServiceClient.CheckNewsWindow calls grpc.ClientConn.Invoke, which eventually calls resource.NewSchemaless
Error:       #19: src/gateway/internal/observability/tracing.go:77:24: observability.InitTracing calls trace.WithBatcher, which eventually calls resource.Resource.Equivalent
Error:       #20: src/gateway/internal/observability/tracing.go:77:24: observability.InitTracing calls trace.WithBatcher, which eventually calls resource.Resource.Iter
Error:       #21: src/gateway/internal/observability/tracing.go:77:24: observability.InitTracing calls trace.WithBatcher, which eventually calls resource.Resource.SchemaURL
Error:       #22: src/gateway/internal/observability/tracing.go:69:27: observability.InitTracing calls resource.WithAttributes
Error:       #23: src/gateway/internal/pipeline/orchestrator.go:770:64: pipeline.Orchestrator.RunConfirmationPulseWithParams calls resource.detectErrs.Error
Error:       #24: src/billing/store/usage.go:1084:15: store.UsageStore.PeekReservationOwner calls errors.Is, which eventually calls resource.detectErrs.Is
Error:       #25: src/auth/decode.go:125:14: auth.DecodeJSONError calls errors.As, which eventually calls resource.detectErrs.Unwrap
Error:       #26: src/management/internal/observability/tracing.go:13:2: observability.init calls resource.init
Error:       #27: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls sdk.Version
Error:       #28: src/management/internal/observability/tracing.go:13:2: observability.init calls resource.init, which calls sdk.init
Error:       #29: src/gateway/internal/observability/tracing.go:76:40: observability.InitTracing calls trace.NewTracerProvider
Error:       #30: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls trace.Shutdown
Error:       #31: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls trace.Shutdown
Error:       #32: src/execution/cmd/execution/main.go:627:28: execution.main calls trace.TracerProvider.Shutdown
Error:       #33: src/execution/internal/observability/tracing.go:120:21: observability.Tracer calls otel.Tracer, which calls trace.TracerProvider.Tracer
Error:       #34: src/gateway/internal/observability/tracing.go:77:24: observability.InitTracing calls trace.WithBatcher
Error:       #35: src/gateway/internal/observability/tracing.go:78:36: observability.InitTracing calls trace.WithMaxExportBatchSize


Error:       #36: src/gateway/internal/observability/tracing.go:80:25: observability.InitTracing calls trace.WithResource
Error:       #37: src/gateway/internal/pipeline/orchestrator.go:770:64: pipeline.Orchestrator.RunConfirmationPulseWithParams calls trace.errUnsupportedSampler.Error
Error:       #38: src/management/internal/observability/tracing.go:14:2: observability.init calls trace.init
Error:       #39: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls trace.init
Error:       #40: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls trace.logDropped[go.opentelemetry.io/otel/sdk/trace.Event]
Error:       #41: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls trace.logDropped[go.opentelemetry.io/otel/sdk/trace.Link]
Error:       #42: proto/gateway/v1/gateway_grpc.pb.go:115:20: gateway.gatewayServiceClient.CheckNewsWindow calls grpc.ClientConn.Invoke, which eventually calls trace.nonRecordingSpan.AddEvent
Error:       #43: src/gateway/internal/pipeline/orchestrator.go:490:18: pipeline.Orchestrator.executePipeline calls trace.nonRecordingSpan.End
Error:       #44: src/execution/internal/observability/tracing.go:128:23: observability.StartSpan calls noop.Tracer.Start, which calls trace.nonRecordingSpan.IsRecording
Error:       #45: src/gateway/internal/observability/tracing.go:129:18: observability.SetSpanError calls trace.nonRecordingSpan.RecordError
Error:       #46: proto/gateway/v1/gateway_grpc.pb.go:115:20: gateway.gatewayServiceClient.CheckNewsWindow calls grpc.ClientConn.Invoke, which eventually calls trace.nonRecordingSpan.SetAttributes
Error:       #47: src/gateway/internal/observability/tracing.go:130:16: observability.SetSpanError calls trace.nonRecordingSpan.SetStatus
Error:       #48: src/execution/internal/observability/tracing.go:128:23: observability.StartSpan calls noop.Tracer.Start, which calls trace.nonRecordingSpan.SpanContext
Error:       #49: proto/gateway/v1/gateway_grpc.pb.go:115:20: gateway.gatewayServiceClient.CheckNewsWindow calls grpc.ClientConn.Invoke, which eventually calls trace.recordingSpan.AddEvent
Error:       #50: src/gateway/internal/pipeline/orchestrator.go:490:18: pipeline.Orchestrator.executePipeline calls trace.recordingSpan.End
Error:       #51: src/execution/internal/observability/tracing.go:128:23: observability.StartSpan calls noop.Tracer.Start, which calls trace.recordingSpan.IsRecording
Error:       #52: src/gateway/internal/observability/tracing.go:129:18: observability.SetSpanError calls trace.recordingSpan.RecordError
Error:       #53: proto/gateway/v1/gateway_grpc.pb.go:115:20: gateway.gatewayServiceClient.CheckNewsWindow calls grpc.ClientConn.Invoke, which eventually calls trace.recordingSpan.SetAttributes
Error:       #54: src/gateway/internal/observability/tracing.go:130:16: observability.SetSpanError calls trace.recordingSpan.SetStatus
Error:       #55: src/execution/internal/observability/tracing.go:128:23: observability.StartSpan calls noop.Tracer.Start, which calls trace.recordingSpan.SpanContext
Error:       #56: src/gateway/internal/pipeline/orchestrator.go:770:64: pipeline.Orchestrator.RunConfirmationPulseWithParams calls trace.samplerArgParseError.Error
Error:       #57: src/auth/decode.go:125:14: auth.DecodeJSONError calls errors.As, which eventually calls trace.samplerArgParseError.Unwrap
Error:       #58: src/execution/internal/observability/tracing.go:128:23: observability.StartSpan calls trace.tracer.Start


Error:       #59: src/gateway/internal/observability/tracing.go:83:25: observability.InitTracing calls otel.SetTracerProvider, which eventually calls trace.tracerProviderConfig.MarshalLog
Error:       #60: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls x.Feature[string].Enabled[string]
Error:       #61: src/management/internal/observability/tracing.go:13:2: observability.init calls resource.init, which calls x.init

Vulnerability #17: GO-2026-4341
    Memory exhaustion in query parameter parsing in net/url
  More info: https://pkg.go.dev/vuln/GO-2026-4341
  Standard library
    Found in: net/url@go1.23.12
    Fixed in: net/url@go1.24.12
    Example traces found:
Error:       #1: src/gateway/internal/server/proxy_handler.go:231:20: server.RegisterRoutes calls httputil.ReverseProxy.ServeHTTP, which eventually calls url.ParseQuery
Error:       #2: src/gateway/cmd/gateway/main.go:664:50: gateway.requireTLSDatabaseURL calls url.URL.Query

Vulnerability #18: GO-2026-4340
    Handshake messages may be processed at the incorrect encryption level in
    crypto/tls
  More info: https://pkg.go.dev/vuln/GO-2026-4340
  Standard library
    Found in: crypto/tls@go1.23.12
    Fixed in: crypto/tls@go1.24.12
    Example traces found:
Error:       #1: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls tls.Conn.Handshake
Error:       #2: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls tls.Conn.HandshakeContext
Error:       #3: src/auth/oauth_google.go:235:25: auth.GoogleOAuthProvider.ExchangeCodeAndVerify calls io.ReadAll, which eventually calls tls.Conn.Read
Error:       #4: src/execution/cmd/executionctl/main.go:44:14: executionctl.main calls fmt.Fprintf, which calls tls.Conn.Write
Error:       #5: src/gateway/e2etest/harness.go:212:32: e2etest.NewHarness calls redis.NewClient, which eventually calls tls.DialWithDialer
Error:       #6: src/gateway/internal/infra/engine_http.go:433:26: infra.EngineHTTPClient.HealthCheck calls http.Client.Do, which eventually calls tls.Dialer.DialContext

Vulnerability #19: GO-2026-4337
    Unexpected session resumption in crypto/tls
  More info: https://pkg.go.dev/vuln/GO-2026-4337
  Standard library


  Found in: crypto/tls@go1.23.12
    Fixed in: crypto/tls@go1.24.13
    Example traces found:
Error:       #1: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls tls.Conn.Handshake
Error:       #2: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls tls.Conn.HandshakeContext
Error:       #3: src/auth/oauth_google.go:235:25: auth.GoogleOAuthProvider.ExchangeCodeAndVerify calls io.ReadAll, which eventually calls tls.Conn.Read
Error:       #4: src/execution/cmd/executionctl/main.go:44:14: executionctl.main calls fmt.Fprintf, which calls tls.Conn.Write
Error:       #5: src/gateway/e2etest/harness.go:212:32: e2etest.NewHarness calls redis.NewClient, which eventually calls tls.DialWithDialer
Error:       #6: src/gateway/internal/infra/engine_http.go:433:26: infra.EngineHTTPClient.HealthCheck calls http.Client.Do, which eventually calls tls.Dialer.DialContext

Vulnerability #20: GO-2025-4175
    Improper application of excluded DNS name constraints when verifying
    wildcard names in crypto/x509
  More info: https://pkg.go.dev/vuln/GO-2025-4175
  Standard library
    Found in: crypto/x509@go1.23.12
    Fixed in: crypto/x509@go1.24.11
    Example traces found:
Error:       #1: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls x509.Certificate.Verify

Vulnerability #21: GO-2025-4155
    Excessive resource consumption when printing error string for host
    certificate validation in crypto/x509
  More info: https://pkg.go.dev/vuln/GO-2025-4155
  Standard library
    Found in: crypto/x509@go1.23.12
    Fixed in: crypto/x509@go1.24.11
    Example traces found:
Error:       #1: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls x509.Certificate.Verify
Error:       #2: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls x509.Certificate.VerifyHostname

Vulnerability #22: GO-2025-4015
    Excessive CPU consumption in Reader.ReadResponse in net/textproto
  More info: https://pkg.go.dev/vuln/GO-2025-4015
  Standard library
    Found in: net/textproto@go1.23.12
    Fixed in: net/textproto@go1.24.8
    Example traces found:

Error:       #1: src/mails/sender.go:103:31: mails.Sender.send calls smtp.NewClient, which calls textproto.Reader.ReadResponse

Vulnerability #23: GO-2025-4013
    Panic when validating certificates with DSA public keys in crypto/x509
  More info: https://pkg.go.dev/vuln/GO-2025-4013
  Standard library
    Found in: crypto/x509@go1.23.12
    Fixed in: crypto/x509@go1.24.8
    Example traces found:
Error:       #1: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls x509.Certificate.Verify

Vulnerability #24: GO-2025-4012
    Lack of limit when parsing cookies can cause memory exhaustion in net/http
  More info: https://pkg.go.dev/vuln/GO-2025-4012
  Standard library
    Found in: net/http@go1.23.12
    Fixed in: net/http@go1.24.8
    Example traces found:
Error:       #1: src/gateway/internal/infra/engine_http.go:433:26: infra.EngineHTTPClient.HealthCheck calls http.Client.Do
Error:       #2: src/auth/cookies.go:194:23: auth.readCookieValue calls http.Request.Cookie

Vulnerability #25: GO-2025-4011
    Parsing DER payload can cause memory exhaustion in encoding/asn1
  More info: https://pkg.go.dev/vuln/GO-2025-4011
  Standard library
    Found in: encoding/asn1@go1.23.12
    Fixed in: encoding/asn1@go1.24.8
    Example traces found:
Error:       #1: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls asn1.Unmarshal

Vulnerability #26: GO-2025-4010
    Insufficient validation of bracketed IPv6 hostnames in net/url
  More info: https://pkg.go.dev/vuln/GO-2025-4010
  Standard library
    Found in: net/url@go1.23.12
    Fixed in: net/url@go1.24.8


   Example traces found:
Error:       #1: src/auth/cors.go:45:22: auth.BuildCORSAllowlist calls url.Parse
Error:       #2: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls url.ParseRequestURI
Error:       #3: src/gateway/internal/infra/engine_http.go:433:26: infra.EngineHTTPClient.HealthCheck calls http.Client.Do, which eventually calls url.URL.Parse

Vulnerability #27: GO-2025-4009
    Quadratic complexity when parsing some invalid inputs in encoding/pem
  More info: https://pkg.go.dev/vuln/GO-2025-4009
  Standard library
    Found in: encoding/pem@go1.23.12
    Fixed in: encoding/pem@go1.24.8
    Example traces found:
Error:       #1: src/execution/cmd/execution/main.go:87:37: execution.main calls pgxpool.ParseConfig, which eventually calls pem.Decode

Vulnerability #28: GO-2025-4008
    ALPN negotiation error contains attacker controlled information in
    crypto/tls
  More info: https://pkg.go.dev/vuln/GO-2025-4008
  Standard library
    Found in: crypto/tls@go1.23.12
    Fixed in: crypto/tls@go1.24.8
    Example traces found:
Error:       #1: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls tls.Conn.Handshake
Error:       #2: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls tls.Conn.HandshakeContext
Error:       #3: src/auth/oauth_google.go:235:25: auth.GoogleOAuthProvider.ExchangeCodeAndVerify calls io.ReadAll, which eventually calls tls.Conn.Read
Error:       #4: src/execution/cmd/executionctl/main.go:44:14: executionctl.main calls fmt.Fprintf, which calls tls.Conn.Write
Error:       #5: src/gateway/e2etest/harness.go:212:32: e2etest.NewHarness calls redis.NewClient, which eventually calls tls.DialWithDialer
Error:       #6: src/gateway/internal/infra/engine_http.go:433:26: infra.EngineHTTPClient.HealthCheck calls http.Client.Do, which eventually calls tls.Dialer.DialContext

Vulnerability #29: GO-2025-4007
    Quadratic complexity when checking name constraints in crypto/x509
  More info: https://pkg.go.dev/vuln/GO-2025-4007
  Standard library
    Found in: crypto/x509@go1.23.12


  Fixed in: crypto/x509@go1.24.9
    Example traces found:
Error:       #1: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls x509.CertPool.AppendCertsFromPEM
Error:       #2: src/billing/server/http.go:196:24: server.Server.Start calls http.Server.Serve, which eventually calls x509.Certificate.Verify
Error:       #3: src/execution/cmd/execution/main.go:87:37: execution.main calls pgxpool.ParseConfig, which eventually calls x509.DecryptPEMBlock
Error:       #4: src/auth/config.go:483:21: auth.Config.IPResolver calls sync.Once.Do, which eventually calls x509.ParseCertificate
Error:       #5: src/execution/cmd/execution/main.go:87:37: execution.main calls pgxpool.ParseConfig, which eventually calls x509.ParseECPrivateKey
Error:       #6: src/execution/cmd/execution/main.go:87:37: execution.main calls pgxpool.ParseConfig, which eventually calls x509.ParsePKCS1PrivateKey
Error:       #7: src/execution/cmd/execution/main.go:87:37: execution.main calls pgxpool.ParseConfig, which eventually calls x509.ParsePKCS8PrivateKey

Vulnerability #30: GO-2025-3553
    Excessive memory allocation during header parsing in
    github.com/golang-jwt/jwt
  More info: https://pkg.go.dev/vuln/GO-2025-3553
  Module: github.com/golang-jwt/jwt/v5
    Found in: github.com/golang-jwt/jwt/v5@v5.2.1
    Fixed in: github.com/golang-jwt/jwt/v5@v5.2.2
    Example traces found:
Error:       #1: src/auth/oauth_google.go:276:29: auth.GoogleOAuthProvider.VerifyIDToken calls jwt.Parser.Parse, which eventually calls jwt.Parser.ParseUnverified

Vulnerability #31: GO-2025-3540
    Potential out of order responses when CLIENT SETINFO times out during
    connection establishment in github.com/redis/go-redis
  More info: https://pkg.go.dev/vuln/GO-2025-3540
  Module: github.com/redis/go-redis/v9
    Found in: github.com/redis/go-redis/v9@v9.7.0
    Fixed in: github.com/redis/go-redis/v9@v9.7.3
    Example traces found:
Error:       #1: src/alert/redis/transport.go:314:30: redis.Transport.subscribeLoop calls redis.Client.Subscribe, which eventually calls redis.baseClient.initConn
Error:       #2: src/alert/redis/transport.go:314:30: redis.Transport.subscribeLoop calls redis.Client.Subscribe, which eventually calls redis.baseClient.initConn
Error:       #3: src/alert/redis/transport.go:314:30: redis.Transport.subscribeLoop calls redis.Client.Subscribe, which eventually calls redis.baseClient.initConn


Your code is affected by 31 vulnerabilities from 4 modules and the Go standard library.
This scan also found 6 vulnerabilities in packages you import and 35
vulnerabilities in modules you require, but your code doesn't appear to call
these vulnerabilities.
Use '-show verbose' for more details.
Error: Process completed with exit code 3.