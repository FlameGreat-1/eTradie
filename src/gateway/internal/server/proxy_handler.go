package server

// Browser-facing reverse proxy (Option B — single public entry point).
//
// The SPA now talks ONLY to the gateway origin. The gateway forwards the
// browser's /api/* dashboard calls to the correct internal service over
// HTTP, re-prefixing the path to the service-native route. The browser
// never learns engine/execution/management origins.
//
// Auth model: every proxied route is mounted behind the SAME
// auth.RequireAuth -> auth.RequireCSRF chain the gateway-native routes
// use. The reverse proxy then forwards the inbound Cookie jar and the
// X-CSRF-Token header UNCHANGED, so the upstream service re-validates
// the identical signed double-submit CSRF token and access-token cookie
// with its own middleware (defence-in-depth: validated at the gateway
// edge AND at the upstream). This works because every service shares the
// same JWT signing secret and resolves the same user_id from the same
// __Secure-access_token cookie (see src/auth/middleware.go, csrf.go).
//
// Streaming: FlushInterval is -1 so Server-Sent Events
// (/api/analysis/stream-live) and any chunked response stream to the
// browser with no buffering. WebSocket upgrades
// (/api/broker/stream-ticks, /api/broker/stream-positions) are handled
// natively by httputil.ReverseProxy: the inbound Upgrade/Connection
// headers are preserved by the Rewrite hook, the default transport
// performs the 101 handshake, and bytes are copied bidirectionally. The
// browser attaches the HttpOnly access_token cookie to the WS handshake
// automatically; RequireCSRF short-circuits because the upgrade is a GET.

import (
	"fmt"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
)

// proxyRoute maps a browser-facing path prefix to an upstream service
// and the path rewrite applied before forwarding.
//
//	browserPrefix  the prefix the SPA calls on the gateway origin.
//	upstreamPrefix the prefix the inbound browserPrefix is rewritten to
//	               before the request is sent to the upstream. The
//	               remainder of the path after browserPrefix is appended
//	               verbatim, so /api/execution/orders/cancel with
//	               browserPrefix=/api/execution and
//	               upstreamPrefix=/api/v1 becomes /api/v1/orders/cancel.
type proxyRoute struct {
	browserPrefix  string
	upstreamPrefix string
}

// ReverseProxyHandler holds the per-upstream reverse proxies and the
// route table that binds browser prefixes to them. Constructed once at
// startup by NewReverseProxyHandler and mounted by RegisterRoutes.
type ReverseProxyHandler struct {
	engineProxy     *httputil.ReverseProxy
	executionProxy  *httputil.ReverseProxy
	managementProxy *httputil.ReverseProxy

	engineRoutes     []proxyRoute
	executionRoutes  []proxyRoute
	managementRoutes []proxyRoute

	log zerolog.Logger
}

// NewReverseProxyHandler builds the reverse proxies for the three
// browser-facing upstreams. The base URLs come from gateway config
// (EngineHTTPURL, ExecutionHTTPURL, ManagementHTTPURL); config.validate
// has already guaranteed they are parseable http(s) URLs with a host and
// are not localhost in production. Returns an error only on the
// (already-validated) parse, so callers may treat a non-nil error as a
// hard startup failure.
func NewReverseProxyHandler(engineURL, executionURL, managementURL string) (*ReverseProxyHandler, error) {
	log := observability.Logger("reverse_proxy")

	engineProxy, err := newServiceProxy("engine", engineURL, log)
	if err != nil {
		return nil, fmt.Errorf("reverse_proxy: engine: %w", err)
	}
	executionProxy, err := newServiceProxy("execution", executionURL, log)
	if err != nil {
		return nil, fmt.Errorf("reverse_proxy: execution: %w", err)
	}
	managementProxy, err := newServiceProxy("management", managementURL, log)
	if err != nil {
		return nil, fmt.Errorf("reverse_proxy: management: %w", err)
	}

	return &ReverseProxyHandler{
		engineProxy:     engineProxy,
		executionProxy:  executionProxy,
		managementProxy: managementProxy,

		// Engine browser surface is already path-compatible: the SPA
		// calls /api/analysis|broker|llm|usage|processor/* and the engine
		// serves the exact same paths, so the rewrite is identity
		// (browserPrefix == upstreamPrefix). Listed explicitly so the
		// mux only forwards the engine's real browser surface and nothing
		// else.
		engineRoutes: []proxyRoute{
			{browserPrefix: "/api/analysis", upstreamPrefix: "/api/analysis"},
			{browserPrefix: "/api/broker", upstreamPrefix: "/api/broker"},
			{browserPrefix: "/api/llm", upstreamPrefix: "/api/llm"},
			{browserPrefix: "/api/usage", upstreamPrefix: "/api/usage"},
			{browserPrefix: "/api/processor", upstreamPrefix: "/api/processor"},
		},
		// Execution's native browser routes live under /api/v1/* which
		// COLLIDES with the gateway-native /api/v1/symbols|config|cycle.
		// The SPA therefore calls /api/execution/* and the proxy rewrites
		// it to the execution service's /api/v1/* surface.
		executionRoutes: []proxyRoute{
			{browserPrefix: "/api/execution", upstreamPrefix: "/api/v1"},
		},
		// Management's native browser routes live under /api/v1/management/*.
		// The SPA calls /api/management/* and the proxy rewrites it to the
		// management service's /api/v1/management/* surface.
		//
		// /api/journal is the Option-B diagram's distinct "Journal"
		// surface. There is NO separate Journal microservice in this
		// platform: the closed-trade journal is served by the MANAGEMENT
		// service at /api/v1/management/journal
		// (src/management/internal/http/server.go). We expose the diagram's
		// /api/journal path at the gateway edge and rewrite it onto exactly
		// that management endpoint.
		//
		// SCOPE NOTE (deliberate, not an omission): this maps ONLY the
		// journal feed. The sibling PnL-calendar endpoint is
		// /api/v1/management/pnl-calendar (NOT under .../journal/), so it
		// is reached via /api/management/pnl-calendar and is intentionally
		// NOT folded under /api/journal — doing so would mis-rewrite
		// /api/journal/pnl-calendar to /api/v1/management/journal/pnl-calendar,
		// a route that does not exist. Journal == the journal feed; the
		// calendar remains a management endpoint.
		managementRoutes: []proxyRoute{
			{browserPrefix: "/api/management", upstreamPrefix: "/api/v1/management"},
			{browserPrefix: "/api/journal", upstreamPrefix: "/api/v1/management/journal"},
		},
		log: log,
	}, nil
}

// newServiceProxy builds a single reverse proxy for one upstream base
// URL. The Rewrite hook (Go 1.20+) is used instead of Director because
// it preserves the inbound request headers (Cookie, X-CSRF-Token,
// Sec-WebSocket-*) by default and sets X-Forwarded-* correctly via
// ProxyRequest.SetXForwarded. The actual path rewrite per route is
// applied by the per-route closure in RegisterRoutes BEFORE the proxy
// runs, so here we only retarget scheme/host and keep the (already
// rewritten) path.
func newServiceProxy(name, baseURL string, log zerolog.Logger) (*httputil.ReverseProxy, error) {
	target, err := url.Parse(strings.TrimSpace(baseURL))
	if err != nil {
		return nil, err
	}
	if target.Scheme == "" || target.Host == "" {
		return nil, fmt.Errorf("upstream URL %q must include scheme and host", baseURL)
	}

	proxy := &httputil.ReverseProxy{
		Rewrite: func(pr *httputil.ProxyRequest) {
			// Retarget to the upstream origin. The inbound path has
			// already been rewritten to the service-native prefix by the
			// per-route handler before the request reaches here, so we
			// keep pr.Out.URL.Path as-is and only swap scheme/host.
			pr.Out.URL.Scheme = target.Scheme
			pr.Out.URL.Host = target.Host
			pr.Out.Host = target.Host
			// Preserve X-Forwarded-For/Proto/Host for the upstream's
			// client-IP resolver and audit logging.
			pr.SetXForwarded()
		},
		// FlushInterval -1 flushes each write immediately. Required for
		// SSE (/api/analysis/stream-live) and any chunked/streaming
		// response so the browser receives events without proxy
		// buffering. It is harmless for normal JSON responses.
		FlushInterval: -1,
		ErrorHandler: func(w http.ResponseWriter, r *http.Request, err error) {
			log.Error().
				Str("upstream", name).
				Str("path", r.URL.Path).
				Err(err).
				Msg("reverse_proxy_upstream_error")
			// Mirror writeJSONError's shape so the SPA's axios error
			// handlers treat an unreachable upstream like any other 502.
			writeJSONError(w, http.StatusBadGateway, "upstream service unavailable; please try again in a moment")
		},
	}
	return proxy, nil
}

// rewritePathPrefix rewrites the request URL path from the browser
// prefix to the upstream prefix, preserving the remainder and the raw
// path/query. Returns false when the path does not actually fall under
// browserPrefix (defensive; the mux only routes matching prefixes here).
func rewritePathPrefix(r *http.Request, route proxyRoute) bool {
	p := r.URL.Path
	if p != route.browserPrefix && !strings.HasPrefix(p, route.browserPrefix+"/") {
		return false
	}
	remainder := strings.TrimPrefix(p, route.browserPrefix)
	newPath := route.upstreamPrefix + remainder
	r.URL.Path = newPath
	// RawPath must be cleared so net/http re-derives it from Path;
	// leaving a stale RawPath would forward the un-rewritten path.
	r.URL.RawPath = ""
	return true
}

// RegisterRoutes mounts every browser-facing proxy route on the mux,
// wrapping each with the supplied auth + CSRF middleware chain (the same
// chain gateway-native protected routes use). A per-route handler
// rewrites the path prefix and then dispatches to the upstream's
// reverse proxy.
//
// authMiddleware MUST run before csrfMiddleware so an unauthenticated
// request is rejected with 401 (not 403) and so the user_id is present
// in context for signed-CSRF verification — identical to
// APIHandler.RegisterProtectedRoutes.
func (h *ReverseProxyHandler) RegisterRoutes(
	mux *http.ServeMux,
	authMiddleware func(http.Handler) http.Handler,
	csrfMiddleware func(http.Handler) http.Handler,
) {
	mount := func(routes []proxyRoute, proxy *httputil.ReverseProxy) {
		for _, route := range routes {
			route := route // capture
			handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				if !rewritePathPrefix(r, route) {
					writeJSONError(w, http.StatusNotFound, "not found")
					return
				}
				proxy.ServeHTTP(w, r)
			})
			wrapped := authMiddleware(csrfMiddleware(handler))
			// Register both the bare prefix and the subtree. http.ServeMux
			// treats a trailing-slash pattern as a subtree match; the bare
			// pattern catches an exact hit with no trailing path.
			mux.Handle(route.browserPrefix, wrapped)
			mux.Handle(route.browserPrefix+"/", wrapped)
		}
	}

	mount(h.engineRoutes, h.engineProxy)
	mount(h.executionRoutes, h.executionProxy)
	mount(h.managementRoutes, h.managementProxy)

	h.log.Info().
		Int("engine_routes", len(h.engineRoutes)).
		Int("execution_routes", len(h.executionRoutes)).
		Int("management_routes", len(h.managementRoutes)).
		Msg("reverse_proxy_routes_mounted")
}
