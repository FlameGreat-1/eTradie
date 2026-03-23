package execution_broker

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"sync"
	"sync/atomic"
)

// EndpointCall records a single HTTP call made to the mock broker.
type EndpointCall struct {
	Path   string
	Method string
	Query  string
	Body   map[string]interface{}
}

// MockBrokerServer simulates the Python engine's broker bridge HTTP API.
// It serves the 7 endpoints that the Go Execution Module B (mt5.Bridge) calls.
// Each endpoint returns a configurable response. Thread-safe.
type MockBrokerServer struct {
	Server *httptest.Server

	// Configurable responses. Set these before running the test.
	AccountInfoResponse   map[string]interface{}
	PositionsResponse     []map[string]interface{}
	PendingOrdersResponse []map[string]interface{}
	SymbolInfoResponse    map[string]interface{}
	TickPriceResponse     map[string]interface{}
	PlaceOrderResponse    map[string]interface{}
	CancelOrderResponse   map[string]interface{}

	// Configurable error status codes. When non-zero, the endpoint
	// returns this HTTP status code instead of 200.
	AccountInfoStatusCode   int
	PositionsStatusCode     int
	PendingOrdersStatusCode int
	SymbolInfoStatusCode    int
	TickPriceStatusCode     int
	PlaceOrderStatusCode    int
	CancelOrderStatusCode   int

	// Per-endpoint call counters.
	AccountInfoCalls   atomic.Int64
	PositionsCalls     atomic.Int64
	PendingOrdersCalls atomic.Int64
	SymbolInfoCalls    atomic.Int64
	TickPriceCalls     atomic.Int64
	PlaceOrderCalls    atomic.Int64
	CancelOrderCalls   atomic.Int64

	// Call tracking.
	mu    sync.Mutex
	calls []EndpointCall
}

// NewMockBrokerServer creates and starts a mock broker HTTP server.
func NewMockBrokerServer() *MockBrokerServer {
	m := &MockBrokerServer{}

	mux := http.NewServeMux()
	mux.HandleFunc("/internal/broker/account_info", m.handleAccountInfo)
	mux.HandleFunc("/internal/broker/positions", m.handlePositions)
	mux.HandleFunc("/internal/broker/pending_orders", m.handlePendingOrders)
	mux.HandleFunc("/internal/broker/symbol_info", m.handleSymbolInfo)
	mux.HandleFunc("/internal/broker/tick_price", m.handleTickPrice)
	mux.HandleFunc("/internal/broker/place_order", m.handlePlaceOrder)
	mux.HandleFunc("/internal/broker/cancel_order", m.handleCancelOrder)

	m.Server = httptest.NewServer(mux)
	return m
}

// URL returns the base URL of the mock server.
func (m *MockBrokerServer) URL() string { return m.Server.URL }

// Close shuts down the mock server.
func (m *MockBrokerServer) Close() { m.Server.Close() }

// Calls returns a copy of all recorded endpoint calls.
func (m *MockBrokerServer) Calls() []EndpointCall {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := make([]EndpointCall, len(m.calls))
	copy(out, m.calls)
	return out
}

// CallsForPath returns all recorded calls for a specific path.
func (m *MockBrokerServer) CallsForPath(path string) []EndpointCall {
	m.mu.Lock()
	defer m.mu.Unlock()
	var out []EndpointCall
	for _, c := range m.calls {
		if c.Path == path {
			out = append(out, c)
		}
	}
	return out
}

// Reset clears all recorded calls and resets counters.
func (m *MockBrokerServer) Reset() {
	m.mu.Lock()
	m.calls = nil
	m.mu.Unlock()
	m.AccountInfoCalls.Store(0)
	m.PositionsCalls.Store(0)
	m.PendingOrdersCalls.Store(0)
	m.SymbolInfoCalls.Store(0)
	m.TickPriceCalls.Store(0)
	m.PlaceOrderCalls.Store(0)
	m.CancelOrderCalls.Store(0)
}

func (m *MockBrokerServer) recordCall(path, method, query string, body map[string]interface{}) {
	m.mu.Lock()
	m.calls = append(m.calls, EndpointCall{Path: path, Method: method, Query: query, Body: body})
	m.mu.Unlock()
}

func (m *MockBrokerServer) handleAccountInfo(w http.ResponseWriter, r *http.Request) {
	m.AccountInfoCalls.Add(1)
	m.recordCall("/internal/broker/account_info", r.Method, r.URL.RawQuery, nil)

	statusCode := m.AccountInfoStatusCode
	if statusCode == 0 {
		statusCode = http.StatusOK
	}
	if m.AccountInfoResponse == nil {
		http.Error(w, `{"detail": "no account_info response configured"}`, http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(m.AccountInfoResponse)
}

func (m *MockBrokerServer) handlePositions(w http.ResponseWriter, r *http.Request) {
	m.PositionsCalls.Add(1)
	m.recordCall("/internal/broker/positions", r.Method, r.URL.RawQuery, nil)

	statusCode := m.PositionsStatusCode
	if statusCode == 0 {
		statusCode = http.StatusOK
	}
	if m.PositionsResponse == nil {
		http.Error(w, `{"detail": "no positions response configured"}`, http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(m.PositionsResponse)
}

func (m *MockBrokerServer) handlePendingOrders(w http.ResponseWriter, r *http.Request) {
	m.PendingOrdersCalls.Add(1)
	m.recordCall("/internal/broker/pending_orders", r.Method, r.URL.RawQuery, nil)

	statusCode := m.PendingOrdersStatusCode
	if statusCode == 0 {
		statusCode = http.StatusOK
	}
	if m.PendingOrdersResponse == nil {
		http.Error(w, `{"detail": "no pending_orders response configured"}`, http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(m.PendingOrdersResponse)
}

func (m *MockBrokerServer) handleSymbolInfo(w http.ResponseWriter, r *http.Request) {
	m.SymbolInfoCalls.Add(1)
	m.recordCall("/internal/broker/symbol_info", r.Method, r.URL.RawQuery, nil)

	statusCode := m.SymbolInfoStatusCode
	if statusCode == 0 {
		statusCode = http.StatusOK
	}
	if m.SymbolInfoResponse == nil {
		http.Error(w, `{"detail": "no symbol_info response configured"}`, http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(m.SymbolInfoResponse)
}

func (m *MockBrokerServer) handleTickPrice(w http.ResponseWriter, r *http.Request) {
	m.TickPriceCalls.Add(1)
	m.recordCall("/internal/broker/tick_price", r.Method, r.URL.RawQuery, nil)

	statusCode := m.TickPriceStatusCode
	if statusCode == 0 {
		statusCode = http.StatusOK
	}
	if m.TickPriceResponse == nil {
		http.Error(w, `{"detail": "no tick_price response configured"}`, http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(m.TickPriceResponse)
}

func (m *MockBrokerServer) handlePlaceOrder(w http.ResponseWriter, r *http.Request) {
	m.PlaceOrderCalls.Add(1)
	body := m.readBody(r)
	m.recordCall("/internal/broker/place_order", r.Method, r.URL.RawQuery, body)

	statusCode := m.PlaceOrderStatusCode
	if statusCode == 0 {
		statusCode = http.StatusOK
	}
	if m.PlaceOrderResponse == nil {
		http.Error(w, `{"detail": "no place_order response configured"}`, http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(m.PlaceOrderResponse)
}

func (m *MockBrokerServer) handleCancelOrder(w http.ResponseWriter, r *http.Request) {
	m.CancelOrderCalls.Add(1)
	body := m.readBody(r)
	m.recordCall("/internal/broker/cancel_order", r.Method, r.URL.RawQuery, body)

	statusCode := m.CancelOrderStatusCode
	if statusCode == 0 {
		statusCode = http.StatusOK
	}
	if m.CancelOrderResponse == nil {
		http.Error(w, `{"detail": "no cancel_order response configured"}`, http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(m.CancelOrderResponse)
}

func (m *MockBrokerServer) readBody(r *http.Request) map[string]interface{} {
	if r.Body == nil {
		return nil
	}
	defer r.Body.Close()
	raw, err := io.ReadAll(r.Body)
	if err != nil {
		return nil
	}
	var body map[string]interface{}
	if err := json.Unmarshal(raw, &body); err != nil {
		return nil
	}
	return body
}

// ---------------------------------------------------------------------------
// Fixture Responses
// ---------------------------------------------------------------------------

// AccountInfoFixture returns a realistic account info response.
func AccountInfoFixture() map[string]interface{} {
	return map[string]interface{}{
		"balance":     10000.0,
		"equity":      10250.50,
		"margin":      500.0,
		"margin_free": 9750.50,
		"currency":    "USD",
	}
}

// PositionsFixture returns a realistic open positions response.
func PositionsFixture() []map[string]interface{} {
	return []map[string]interface{}{
		{
			"symbol":        "EURUSD",
			"type":          0, // BUY
			"price_open":    1.10000,
			"price_current": 1.10250,
			"sl":            1.09500,
			"tp":            1.11500,
			"volume":        0.10,
			"profit":        25.0,
			"ticket":        int64(12345678),
			"comment":       "SMC-EURUSD-H4-001",
			"time_setup":    int64(1711200000),
		},
	}
}

// PendingOrdersFixture returns a realistic pending orders response.
func PendingOrdersFixture() []map[string]interface{} {
	return []map[string]interface{}{
		{
			"symbol":     "GBPUSD",
			"type":       2, // BUY_LIMIT
			"price_open": 1.25000,
			"sl":         1.24500,
			"tp":         1.26500,
			"volume":     0.15,
			"ticket":     int64(87654321),
			"comment":    "SMC-GBPUSD-H4-002",
			"time_setup": int64(1711200000),
		},
	}
}

// SymbolInfoFixture returns a realistic EURUSD symbol info response.
// Matches the exact JSON contract from Python's broker_symbol_info endpoint.
func SymbolInfoFixture() map[string]interface{} {
	return map[string]interface{}{
		"symbol":              "EURUSD",
		"point":               0.00001,
		"digits":              int32(5),
		"spread":              12,
		"trade_contract_size": 100000.0,
		"volume_min":          0.01,
		"volume_max":          100.0,
		"volume_step":         0.01,
		"trade_tick_value":    1.0,
		"trade_tick_size":     0.00001,
	}
}

// TickPriceFixture returns a realistic tick price response.
func TickPriceFixture() map[string]interface{} {
	return map[string]interface{}{
		"bid":  1.10245,
		"ask":  1.10257,
		"time": int64(1711200060),
	}
}

// PlaceOrderSuccessFixture returns a successful order placement response.
func PlaceOrderSuccessFixture() map[string]interface{} {
	return map[string]interface{}{
		"order_id": int64(99887766),
		"price":    1.10000,
		"status":   "PLACED",
		"error":    "",
	}
}

// PlaceOrderFilledFixture returns a filled market order response.
func PlaceOrderFilledFixture() map[string]interface{} {
	return map[string]interface{}{
		"order_id": int64(99887767),
		"price":    1.10003,
		"status":   "FILLED",
		"error":    "",
	}
}

// PlaceOrderRejectedFixture returns a rejected order response.
func PlaceOrderRejectedFixture() map[string]interface{} {
	return map[string]interface{}{
		"order_id": int64(0),
		"price":    0.0,
		"status":   "REJECTED",
		"error":    fmt.Sprintf("Insufficient margin"),
	}
}

// CancelOrderSuccessFixture returns a successful cancel response.
func CancelOrderSuccessFixture() map[string]interface{} {
	return map[string]interface{}{
		"success": true,
		"error":   "",
	}
}

// CancelOrderFailFixture returns a failed cancel response.
func CancelOrderFailFixture() map[string]interface{} {
	return map[string]interface{}{
		"success": false,
		"error":   "Order not found",
	}
}
