package e2e

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"sync"
	"sync/atomic"
)

// EndpointCall records a single HTTP call made to the mock engine.
type EndpointCall struct {
	Path string
	Body map[string]interface{}
}

// MockEngineServer simulates the Python engine's internal HTTP API.
// It serves the four endpoints the Gateway calls during a pipeline cycle:
//   - POST /internal/ta/analyze
//   - POST /internal/macro/collect
//   - POST /internal/rag/retrieve
//   - POST /internal/processor/process
//
// Each endpoint returns a configurable response. The server records
// every call for assertion in tests. Thread-safe.
type MockEngineServer struct {
	Server *httptest.Server

	// Configurable responses. Set these before running the test.
	TAResponse        map[string]interface{}
	MacroResponse     map[string]interface{}
	RAGResponse       map[string]interface{}
	ProcessorResponse map[string]interface{}

	// Configurable error responses. When non-zero, the endpoint
	// returns this HTTP status code instead of 200.
	TAStatusCode        int
	MacroStatusCode     int
	RAGStatusCode       int
	ProcessorStatusCode int

	// Call tracking.
	mu    sync.Mutex
	calls []EndpointCall

	// Per-endpoint call counters for quick assertions.
	TACalls        atomic.Int64
	MacroCalls     atomic.Int64
	RAGCalls       atomic.Int64
	ProcessorCalls atomic.Int64
}

// NewMockEngineServer creates and starts a mock HTTP server.
// The caller must call Close() when done.
func NewMockEngineServer() *MockEngineServer {
	m := &MockEngineServer{}

	mux := http.NewServeMux()
	mux.HandleFunc("/internal/ta/analyze", m.handleTA)
	mux.HandleFunc("/internal/macro/collect", m.handleMacro)
	mux.HandleFunc("/internal/rag/retrieve", m.handleRAG)
	mux.HandleFunc("/internal/processor/process", m.handleProcessor)
	mux.HandleFunc("/health", m.handleHealth)

	m.Server = httptest.NewServer(mux)
	return m
}

// URL returns the base URL of the mock server.
func (m *MockEngineServer) URL() string {
	return m.Server.URL
}

// Close shuts down the mock server.
func (m *MockEngineServer) Close() {
	m.Server.Close()
}

// Calls returns a copy of all recorded endpoint calls.
func (m *MockEngineServer) Calls() []EndpointCall {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := make([]EndpointCall, len(m.calls))
	copy(out, m.calls)
	return out
}

// CallsForPath returns all recorded calls for a specific path.
func (m *MockEngineServer) CallsForPath(path string) []EndpointCall {
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
func (m *MockEngineServer) Reset() {
	m.mu.Lock()
	m.calls = nil
	m.mu.Unlock()
	m.TACalls.Store(0)
	m.MacroCalls.Store(0)
	m.RAGCalls.Store(0)
	m.ProcessorCalls.Store(0)
}

func (m *MockEngineServer) recordCall(path string, body map[string]interface{}) {
	m.mu.Lock()
	m.calls = append(m.calls, EndpointCall{Path: path, Body: body})
	m.mu.Unlock()
}

func (m *MockEngineServer) handleTA(w http.ResponseWriter, r *http.Request) {
	m.TACalls.Add(1)
	body := m.readBody(r)
	m.recordCall("/internal/ta/analyze", body)

	statusCode := m.TAStatusCode
	if statusCode == 0 {
		statusCode = http.StatusOK
	}

	if m.TAResponse == nil {
		http.Error(w, `{"error": "no TA response configured"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(m.TAResponse)
}

func (m *MockEngineServer) handleMacro(w http.ResponseWriter, r *http.Request) {
	m.MacroCalls.Add(1)
	body := m.readBody(r)
	m.recordCall("/internal/macro/collect", body)

	statusCode := m.MacroStatusCode
	if statusCode == 0 {
		statusCode = http.StatusOK
	}

	if m.MacroResponse == nil {
		http.Error(w, `{"error": "no Macro response configured"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(m.MacroResponse)
}

func (m *MockEngineServer) handleRAG(w http.ResponseWriter, r *http.Request) {
	m.RAGCalls.Add(1)
	body := m.readBody(r)
	m.recordCall("/internal/rag/retrieve", body)

	statusCode := m.RAGStatusCode
	if statusCode == 0 {
		statusCode = http.StatusOK
	}

	if m.RAGResponse == nil {
		http.Error(w, `{"error": "no RAG response configured"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(m.RAGResponse)
}

func (m *MockEngineServer) handleProcessor(w http.ResponseWriter, r *http.Request) {
	m.ProcessorCalls.Add(1)
	body := m.readBody(r)
	m.recordCall("/internal/processor/process", body)

	statusCode := m.ProcessorStatusCode
	if statusCode == 0 {
		statusCode = http.StatusOK
	}

	if m.ProcessorResponse == nil {
		http.Error(w, `{"error": "no Processor response configured"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(m.ProcessorResponse)
}

func (m *MockEngineServer) handleHealth(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status": "ok"}`))
}

func (m *MockEngineServer) readBody(r *http.Request) map[string]interface{} {
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
