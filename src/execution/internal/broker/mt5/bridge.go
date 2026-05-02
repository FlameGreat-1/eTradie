package mt5

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
)

// Bridge implements broker.Port by calling the Python MT5 bridge
// service over HTTP. The Python service wraps MetaTrader5 trading
// functions (account_info, positions_get, orders_get, order_send,
// order_check, symbol_info) and exposes them as JSON endpoints.
//
// This leverages the existing MT5 connection managed by
// src/engine/ta/broker/mt5/client.py. The bridge service extends
// that client with execution-specific operations.
type Bridge struct {
	baseURL    string
	httpClient *http.Client
	log        zerolog.Logger
}

// NewBridge creates an MT5 bridge client.
func NewBridge(baseURL string, timeoutMs int) *Bridge {
	return &Bridge{
		baseURL: strings.TrimRight(baseURL, "/"),
		httpClient: &http.Client{
			Timeout: time.Duration(timeoutMs) * time.Millisecond,
		},
		log: observability.Logger("mt5_bridge"),
	}
}

func (b *Bridge) GetAccountInfo(ctx context.Context) (*models.AccountInfo, error) {
	var resp struct {
		Balance    float64 `json:"balance"`
		Equity     float64 `json:"equity"`
		Margin     float64 `json:"margin"`
		FreeMargin float64 `json:"margin_free"`
		Currency   string  `json:"currency"`
	}

	if err := b.get(ctx, "/internal/broker/account_info", &resp); err != nil {
		return nil, fmt.Errorf("get account info: %w", err)
	}

	return &models.AccountInfo{
		Balance:    resp.Balance,
		Equity:     resp.Equity,
		Margin:     resp.Margin,
		FreeMargin: resp.FreeMargin,
		Currency:   resp.Currency,
	}, nil
}

func (b *Bridge) GetPositions(ctx context.Context) ([]models.Position, error) {
	var resp []struct {
		Symbol       string  `json:"symbol"`
		Type         int     `json:"type"` // 0=BUY, 1=SELL
		PriceOpen    float64 `json:"price_open"`
		PriceCurrent float64 `json:"price_current"`
		SL           float64 `json:"sl"`
		TP           float64 `json:"tp"`
		Volume       float64 `json:"volume"`
		Profit       float64 `json:"profit"`
		Ticket       int64   `json:"ticket"`
		Comment      string  `json:"comment"`
		TimeSetup    int64   `json:"time_setup"`
	}

	if err := b.get(ctx, "/internal/broker/positions", &resp); err != nil {
		return nil, fmt.Errorf("get positions: %w", err)
	}

	positions := make([]models.Position, 0, len(resp))
	for _, p := range resp {
		direction := "BUY"
		if p.Type == 1 {
			direction = "SELL"
		}
		positions = append(positions, models.Position{
			Symbol:        p.Symbol,
			Direction:     direction,
			EntryPrice:    p.PriceOpen,
			CurrentPrice:  p.PriceCurrent,
			StopLoss:      p.SL,
			TakeProfit:    p.TP,
			LotSize:       p.Volume,
			UnrealizedPnL: p.Profit,
			OrderID:       fmt.Sprintf("%d", p.Ticket),
			AnalysisID:    p.Comment,
			OpenTime:      time.Unix(p.TimeSetup, 0).UTC(),
		})
	}

	return positions, nil
}

func (b *Bridge) GetPendingOrders(ctx context.Context) ([]models.BrokerPendingOrder, error) {
	var resp []struct {
		Symbol    string  `json:"symbol"`
		Type      int     `json:"type"` // 2=BUY_LIMIT, 3=SELL_LIMIT, etc.
		PriceOpen float64 `json:"price_open"`
		SL        float64 `json:"sl"`
		TP        float64 `json:"tp"`
		Volume    float64 `json:"volume"`
		Ticket    int64   `json:"ticket"`
		Comment   string  `json:"comment"`
		TimeSetup int64   `json:"time_setup"`
	}

	if err := b.get(ctx, "/internal/broker/pending_orders", &resp); err != nil {
		return nil, fmt.Errorf("get pending orders: %w", err)
	}

	orders := make([]models.BrokerPendingOrder, 0, len(resp))
	for _, o := range resp {
		direction := "BUY"
		if o.Type == 3 || o.Type == 5 {
			direction = "SELL"
		}
		orders = append(orders, models.BrokerPendingOrder{
			Symbol:        o.Symbol,
			Direction:     direction,
			EntryPrice:    o.PriceOpen,
			StopLoss:      o.SL,
			TakeProfit:    o.TP,
			LotSize:       o.Volume,
			OrderID:       fmt.Sprintf("%d", o.Ticket),
			AnalysisID:    o.Comment,
			ExecutionMode: "LIMIT",
			Status:        "PENDING",
			CreatedAt:     time.Unix(o.TimeSetup, 0).UTC(),
		})
	}

	return orders, nil
}

func (b *Bridge) GetInstrumentInfo(ctx context.Context, symbol string) (*models.InstrumentInfo, error) {
	var resp struct {
		Symbol       string  `json:"symbol"`
		Point        float64 `json:"point"`
		Digits       int32   `json:"digits"`
		Spread       int     `json:"spread"` // In points from MT5.
		ContractSize float64 `json:"trade_contract_size"`
		VolumeMin    float64 `json:"volume_min"`
		VolumeMax    float64 `json:"volume_max"`
		VolumeStep   float64 `json:"volume_step"`
		TickValue    float64 `json:"trade_tick_value"` // SYMBOL_TRADE_TICK_VALUE: profit per 1 point per 1 lot in account currency.
		TickSize     float64 `json:"trade_tick_size"`  // SYMBOL_TRADE_TICK_SIZE: smallest price change.
	}

	if err := b.get(ctx, fmt.Sprintf("/internal/broker/symbol_info?symbol=%s", url.QueryEscape(symbol)), &resp); err != nil {
		return nil, fmt.Errorf("get instrument info for %s: %w", symbol, err)
	}

	// MT5 point = smallest price increment. Pip size depends on digits.
	// For 5-digit Forex: pip = point * 10. For 3-digit JPY: pip = point * 10.
	// For 2-digit metals and ALL Synthetic Indices/Cryptos: pip = point.
	pipPointRatio := 10.0
	upperSym := strings.ToUpper(resp.Symbol)
	isSynthetic := strings.Contains(upperSym, "VOLATILITY") ||
		strings.Contains(upperSym, "BOOM") ||
		strings.Contains(upperSym, "CRASH") ||
		strings.Contains(upperSym, "STEP") ||
		strings.Contains(upperSym, "JUMP") ||
		strings.Contains(upperSym, "V75") ||
		strings.Contains(upperSym, "DEX") ||
		strings.Contains(upperSym, "RANGE")

	if resp.Digits <= 2 || isSynthetic {
		pipPointRatio = 1.0
	}
	pipSize := resp.Point * pipPointRatio

	// For Synthetics, professional discrete traders treat 1 full index point (1.0) as 1 "pip".
	// The broker's raw point (e.g. 0.0001 for Crash 1000) causes calculations in the millions.
	if isSynthetic {
		pipSize = 1.0
	}

	// Spread in price units.
	spreadPrice := float64(resp.Spread) * resp.Point

	// Pip value calculation: use MT5's SYMBOL_TRADE_TICK_VALUE for accuracy.
	// tick_value = profit in account currency for a 1-point move on 1 standard lot.
	// pip_value = tick_value * (pip_size / tick_size) = tick_value * pipPointRatio
	// This is exact for ALL pairs including cross-currencies (e.g. EURGBP on USD account).
	var pipValue float64
	if resp.TickValue > 0 && resp.TickSize > 0 {
		// Exact calculation using MT5's pre-computed tick value.
		pipValue = resp.TickValue * (pipSize / resp.TickSize)
	} else if resp.TickValue > 0 {
		// TickSize not provided; assume tick = point.
		pipValue = resp.TickValue * (pipSize / resp.Point)
	} else {
		// Fallback: approximate. This is ONLY used if the Python bridge
		// does not return trade_tick_value (old bridge version).
		// Log a warning because this can produce wrong sizing for
		// cross-currency pairs.
		pipValue = pipSize * resp.ContractSize
		if pipValue < 0.01 {
			pipValue = 10.0 // Last-resort fallback for standard forex.
		}
		b.log.Warn().
			Str("symbol", symbol).
			Float64("approx_pip_value", pipValue).
			Msg("tick_value_not_available_using_approximation")
	}

	return &models.InstrumentInfo{
		Symbol:       resp.Symbol,
		PipSize:      pipSize,
		PipValue:     pipValue,
		MinLotSize:   resp.VolumeMin,
		MaxLotSize:   resp.VolumeMax,
		LotStep:      resp.VolumeStep,
		Spread:       spreadPrice,
		AvgSpread:    spreadPrice, // MT5 doesn't provide avg; use current.
		Digits:       resp.Digits,
		ContractSize: resp.ContractSize,
	}, nil
}

func (b *Bridge) PlaceLimitOrder(ctx context.Context, order *models.OrderPlacement) (*models.OrderResult, error) {
	return b.placeOrder(ctx, order, "LIMIT")
}

func (b *Bridge) PlaceMarketOrder(ctx context.Context, order *models.OrderPlacement) (*models.OrderResult, error) {
	return b.placeOrder(ctx, order, "MARKET")
}

func (b *Bridge) placeOrder(ctx context.Context, order *models.OrderPlacement, orderType string) (*models.OrderResult, error) {
	payload := map[string]interface{}{
		"symbol":      order.Symbol,
		"direction":   order.Direction,
		"order_type":  orderType,
		"price":       order.Price,
		"stop_loss":   order.StopLoss,
		"take_profit": order.TakeProfit,
		"lot_size":    order.LotSize,
		"comment":     order.Comment,
	}

	var resp struct {
		OrderID int64   `json:"order_id"`
		Price   float64 `json:"price"`
		Status  string  `json:"status"` // "PLACED", "FILLED", "REJECTED"
		Error   string  `json:"error"`
	}

	if err := b.post(ctx, "/internal/broker/place_order", payload, &resp); err != nil {
		return nil, fmt.Errorf("place %s order for %s: %w", orderType, order.Symbol, err)
	}

	var slippage float64
	if order.Price > 0 {
		slippage = resp.Price - order.Price
	}

	return &models.OrderResult{
		BrokerOrderID: fmt.Sprintf("%d", resp.OrderID),
		FillPrice:     resp.Price,
		Slippage:      slippage,
		Status:        resp.Status,
		ErrorMessage:  resp.Error,
	}, nil
}

func (b *Bridge) CancelOrder(ctx context.Context, brokerOrderID string) error {
	payload := map[string]interface{}{
		"order_id": brokerOrderID,
	}

	var resp struct {
		Success bool   `json:"success"`
		Error   string `json:"error"`
	}

	if err := b.post(ctx, "/internal/broker/cancel_order", payload, &resp); err != nil {
		return fmt.Errorf("cancel order %s: %w", brokerOrderID, err)
	}

	if !resp.Success {
		return fmt.Errorf("cancel order %s: %s", brokerOrderID, resp.Error)
	}

	return nil
}

func (b *Bridge) GetTickPrice(ctx context.Context, symbol string) (*models.TickPrice, error) {
	var resp struct {
		Bid  float64 `json:"bid"`
		Ask  float64 `json:"ask"`
		Time int64   `json:"time"`
	}

	if err := b.get(ctx, fmt.Sprintf("/internal/broker/tick_price?symbol=%s", url.QueryEscape(symbol)), &resp); err != nil {
		return nil, fmt.Errorf("get tick price for %s: %w", symbol, err)
	}

	return &models.TickPrice{
		Bid:       resp.Bid,
		Ask:       resp.Ask,
		Timestamp: time.Unix(resp.Time, 0).UTC(),
	}, nil
}

// get performs an HTTP GET and decodes the JSON response.
func (b *Bridge) get(ctx context.Context, path string, dest interface{}) error {
	start := time.Now()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, b.baseURL+path, nil)
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}

	// Forward JWT token from gRPC context to Python engine.
	if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
		req.Header.Set("Authorization", "Bearer "+rawToken)
	}

	resp, err := b.httpClient.Do(req)
	if err != nil {
		observability.BrokerCallTotal.WithLabelValues(path, "error").Inc()
		return fmt.Errorf("http get %s: %w", path, err)
	}
	defer resp.Body.Close()

	elapsed := time.Since(start).Seconds()
	observability.BrokerCallDuration.WithLabelValues(path).Observe(elapsed)

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		observability.BrokerCallTotal.WithLabelValues(path, "http_error").Inc()
		return fmt.Errorf("http get %s: status %d: %s", path, resp.StatusCode, string(body))
	}

	observability.BrokerCallTotal.WithLabelValues(path, "success").Inc()

	if err := json.NewDecoder(resp.Body).Decode(dest); err != nil {
		return fmt.Errorf("decode response from %s: %w", path, err)
	}

	return nil
}

// post performs an HTTP POST with JSON body and decodes the response.
func (b *Bridge) post(ctx context.Context, path string, payload interface{}, dest interface{}) error {
	start := time.Now()

	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("marshal payload: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, b.baseURL+path, strings.NewReader(string(body)))
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	// Forward JWT token from gRPC context to Python engine.
	if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
		req.Header.Set("Authorization", "Bearer "+rawToken)
	}

	resp, err := b.httpClient.Do(req)
	if err != nil {
		observability.BrokerCallTotal.WithLabelValues(path, "error").Inc()
		return fmt.Errorf("http post %s: %w", path, err)
	}
	defer resp.Body.Close()

	elapsed := time.Since(start).Seconds()
	observability.BrokerCallDuration.WithLabelValues(path).Observe(elapsed)

	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		observability.BrokerCallTotal.WithLabelValues(path, "http_error").Inc()
		return fmt.Errorf("http post %s: status %d: %s", path, resp.StatusCode, string(respBody))
	}

	observability.BrokerCallTotal.WithLabelValues(path, "success").Inc()

	if err := json.NewDecoder(resp.Body).Decode(dest); err != nil {
		return fmt.Errorf("decode response from %s: %w", path, err)
	}

	return nil
}
