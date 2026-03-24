package management_broker

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"sync"
	"sync/atomic"
)

// EndpointCall records a single HTTP call.
type EndpointCall struct {
	Path   string
	Method string
	Query  string
	Body   map[string]interface{}
}

// MockBrokerServer simulates the Python broker bridge endpoints
// that the Management Module C (broker.Client + broker.Stream) calls.
type MockBrokerServer struct {
	Server *httptest.Server

	// Configurable responses.
	TickPriceResponse      map[string]interface{}
	PositionResponse       map[string]interface{}
	ModifyPositionResponse map[string]interface{}
	ClosePartialResponse   map[string]interface{}
	ClosePositionResponse  map[string]interface{}

	// Configurable error status codes.
	TickPriceStatusCode      int
	PositionStatusCode       int
	ModifyPositionStatusCode int
	ClosePartialStatusCode   int
	ClosePositionStatusCode  int

	// Per-endpoint call counters.
	TickPriceCalls      atomic.Int64
	PositionCalls       atomic.Int64
	ModifyPositionCalls atomic.Int64
	ClosePartialCalls   atomic.Int64
	ClosePositionCalls  atomic.Int64

	mu    sync.Mutex
	calls []EndpointCall
}

// NewMockBrokerServer creates and starts a mock broker HTTP server.
func NewMockBrokerServer() *MockBrokerServer {
	m := &MockBrokerServer{}

	mux := http.NewServeMux()
	mux.HandleFunc("/internal/broker/tick_price", m.handleTickPrice)
	mux.HandleFunc("/internal/broker/position", m.handlePosition)
	mux.HandleFunc("/internal/broker/modify_position", m.handleModifyPosition)
	mux.HandleFunc("/internal/broker/close_partial", m.handleClosePartial)
	mux.HandleFunc("/internal/broker/close_position", m.handleClosePosition)

	m.Server = httptest.NewServer(mux)
	return m
}

func (m *MockBrokerServer) URL() string { return m.Server.URL }
func (m *MockBrokerServer) Close()      { m.Server.Close() }

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

func (m *MockBrokerServer) recordCall(path, method, query string, body map[string]interface{}) {
	m.mu.Lock()
	m.calls = append(m.calls, EndpointCall{Path: path, Method: method, Query: query, Body: body})
	m.mu.Unlock()
}

func (m *MockBrokerServer) handleTickPrice(w http.ResponseWriter, r *http.Request) {
	m.TickPriceCalls.Add(1)
	m.recordCall("/internal/broker/tick_price", r.Method, r.URL.RawQuery, nil)
	m.writeResponse(w, m.TickPriceResponse, m.TickPriceStatusCode)
}

func (m *MockBrokerServer) handlePosition(w http.ResponseWriter, r *http.Request) {
	m.PositionCalls.Add(1)
	m.recordCall("/internal/broker/position", r.Method, r.URL.RawQuery, nil)
	m.writeResponse(w, m.PositionResponse, m.PositionStatusCode)
}

func (m *MockBrokerServer) handleModifyPosition(w http.ResponseWriter, r *http.Request) {
	m.ModifyPositionCalls.Add(1)
	body := m.readBody(r)
	m.recordCall("/internal/broker/modify_position", r.Method, r.URL.RawQuery, body)
	m.writeResponse(w, m.ModifyPositionResponse, m.ModifyPositionStatusCode)
}

func (m *MockBrokerServer) handleClosePartial(w http.ResponseWriter, r *http.Request) {
	m.ClosePartialCalls.Add(1)
	body := m.readBody(r)
	m.recordCall("/internal/broker/close_partial", r.Method, r.URL.RawQuery, body)
	m.writeResponse(w, m.ClosePartialResponse, m.ClosePartialStatusCode)
}

func (m *MockBrokerServer) handleClosePosition(w http.ResponseWriter, r *http.Request) {
	m.ClosePositionCalls.Add(1)
	body := m.readBody(r)
	m.recordCall("/internal/broker/close_position", r.Method, r.URL.RawQuery, body)
	m.writeResponse(w, m.ClosePositionResponse, m.ClosePositionStatusCode)
}

func (m *MockBrokerServer) writeResponse(w http.ResponseWriter, resp interface{}, statusCode int) {
	if statusCode == 0 {
		statusCode = http.StatusOK
	}
	if resp == nil {
		http.Error(w, `{"detail": "no response configured"}`, http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(resp)
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
