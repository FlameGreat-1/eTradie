package querybuilder

import (
	"strings"

	"github.com/flamegreat/etradie/src/gateway/internal/models"
)

// MacroSignals holds extracted macro signals for RAG query construction.
type MacroSignals struct {
	MacroBiasUSD string

	DXYValue *float64
	DXYTrend string

	COTNetEUR *float64
	COTNetGBP *float64
	COTNetJPY *float64
	COTNetAUD *float64
	COTNetCAD *float64
	COTNetNZD *float64
	COTNetCHF *float64

	FedTone            string
	ECBTone            string
	BOETone            string
	BOJTone            string
	HasRateChange      bool
	RateChangeBank     string
	RateChangeDirection string

	HighImpactEventsWithin24h []string
	HasRateDecision           bool
	HasNFP                    bool
	HasCPI                    bool
	HasPPI                    bool
	HasGDP                    bool
	HasEmployment             bool
	HasPMI                    bool
	HasRetailSales            bool
	HasCBSpeech               bool

	NewsHeadlines     []string
	EconomicSurprises []map[string]interface{}

	RetailSentiment map[string]float64
	RiskEnvironment string

	GoldPrice          *float64
	OilPrice           *float64
	US2YYield          *float64
	US10YYield         *float64
	US30YYield         *float64
	SP500              *float64
	VIX                *float64
	YieldCurveInverted *bool
}

// ExtractMacroSignals extracts ALL RAG-relevant signals from the aggregated macro output.
func ExtractMacroSignals(result *models.MacroResult) *MacroSignals {
	cb := extractCentralBank(result.CentralBank)
	cot := extractCOT(result.COT)
	econ := extractEconomic(result.Economic)
	cal := extractCalendar(result.Calendar)
	dxy := extractDXY(result.DXY)
	news := extractNews(result.News)
	sent := extractSentiment(result.Sentiment)
	inter := extractIntermarket(result.Intermarket)

	macroBias := deriveUSDBias(cb)

	var yieldInverted *bool
	us2y := getOptFloat(inter, "us2y_yield")
	us10y := getOptFloat(inter, "us10y_yield")
	if us2y != nil && us10y != nil {
		v := *us2y > *us10y
		yieldInverted = &v
	}

	return &MacroSignals{
		MacroBiasUSD: macroBias,

		DXYValue: getOptFloat(dxy, "value"),
		DXYTrend: getOptStr(dxy, "trend"),

		COTNetEUR: getOptFloat(cot, "eur_net"),
		COTNetGBP: getOptFloat(cot, "gbp_net"),
		COTNetJPY: getOptFloat(cot, "jpy_net"),
		COTNetAUD: getOptFloat(cot, "aud_net"),
		COTNetCAD: getOptFloat(cot, "cad_net"),
		COTNetNZD: getOptFloat(cot, "nzd_net"),
		COTNetCHF: getOptFloat(cot, "chf_net"),

		FedTone:             getOptStr(cb, "fed_tone"),
		ECBTone:             getOptStr(cb, "ecb_tone"),
		BOETone:             getOptStr(cb, "boe_tone"),
		BOJTone:             getOptStr(cb, "boj_tone"),
		HasRateChange:       getOptBool(cb, "has_rate_change"),
		RateChangeBank:      getOptStr(cb, "rate_change_bank"),
		RateChangeDirection: getOptStr(cb, "rate_change_direction"),

		HighImpactEventsWithin24h: getOptStrSlice(cal, "high_impact_events"),
		HasRateDecision:           getOptBool(cal, "has_rate_decision"),
		HasNFP:                    getOptBool(cal, "has_nfp"),
		HasCPI:                    getOptBool(cal, "has_cpi"),
		HasPPI:                    getOptBool(cal, "has_ppi"),
		HasGDP:                    getOptBool(cal, "has_gdp"),
		HasEmployment:             getOptBool(cal, "has_employment"),
		HasPMI:                    getOptBool(cal, "has_pmi"),
		HasRetailSales:            getOptBool(cal, "has_retail_sales"),
		HasCBSpeech:               getOptBool(cal, "has_cb_speech"),

		NewsHeadlines:     getOptStrSlice(news, "headlines"),
		EconomicSurprises: getOptMapSlice(econ, "surprise_directions"),

		RetailSentiment: getOptFloatMap(sent, "all_currencies"),
		RiskEnvironment: getOptStr(sent, "risk_environment"),

		GoldPrice:          getOptFloat(inter, "gold_price"),
		OilPrice:           getOptFloat(inter, "oil_price"),
		US2YYield:          us2y,
		US10YYield:         us10y,
		US30YYield:         getOptFloat(inter, "us30y_yield"),
		SP500:              getOptFloat(inter, "sp500"),
		VIX:                getOptFloat(inter, "vix"),
		YieldCurveInverted: yieldInverted,
	}
}

func extractCentralBank(data map[string]interface{}) map[string]interface{} {
	if data == nil {
		return map[string]interface{}{}
	}
	signals := map[string]interface{}{"has_rate_change": false}

	for _, source := range []string{"speeches", "forward_guidance"} {
		for _, item := range getSliceOfMaps(data, source) {
			bank := strings.ToUpper(getStrDefault(item, "bank", ""))
			tone := strings.ToUpper(getStrDefault(item, "tone", "NEUTRAL"))
			key := strings.ToLower(bank) + "_tone"
			if _, exists := signals[key]; !exists {
				signals[key] = tone
			}
		}
	}

	for _, decision := range getSliceOfMaps(data, "rate_decisions") {
		bank := strings.ToUpper(getStrDefault(decision, "bank", ""))
		tone := strings.ToUpper(getStrDefault(decision, "tone", "NEUTRAL"))
		key := strings.ToLower(bank) + "_tone"
		signals[key] = tone

		rateChange := getFloatFromEither(decision, "rate_change_bps", "change")
		if rateChange != 0 {
			signals["has_rate_change"] = true
			signals["rate_change_bank"] = bank
			if rateChange > 0 {
				signals["rate_change_direction"] = "hike"
			} else {
				signals["rate_change_direction"] = "cut"
			}
		}
	}
	return signals
}

func extractCOT(data map[string]interface{}) map[string]interface{} {
	if data == nil {
		return map[string]interface{}{}
	}
	currencyMap := map[string]string{
		"EUR": "eur_net", "GBP": "gbp_net", "JPY": "jpy_net",
		"AUD": "aud_net", "CAD": "cad_net", "NZD": "nzd_net",
		"CHF": "chf_net",
	}
	signals := map[string]interface{}{}
	for _, pos := range getSliceOfMaps(data, "latest_positions") {
		currency := strings.ToUpper(getStrDefault(pos, "currency", ""))
		if key, ok := currencyMap[currency]; ok {
			if net, ok := getFloat(pos, "non_commercial_net"); ok {
				signals[key] = net
			}
		}
	}
	return signals
}

func extractEconomic(data map[string]interface{}) map[string]interface{} {
	if data == nil {
		return map[string]interface{}{}
	}
	var surprises []map[string]interface{}
	for _, release := range getSliceOfMaps(data, "releases") {
		surpriseDir := getStrDefault(release, "surprise_direction", "")
		indicator := getStrDefault(release, "indicator", "")
		if surpriseDir != "" && indicator != "" {
			surprises = append(surprises, map[string]interface{}{
				"indicator":      indicator,
				"indicator_name": getStrDefault(release, "indicator_name", ""),
				"direction":      surpriseDir,
				"currency":       getStrDefault(release, "currency", ""),
				"impact":         getStrDefault(release, "impact", ""),
			})
		}
	}
	return map[string]interface{}{"surprise_directions": surprises}
}

func extractCalendar(data map[string]interface{}) map[string]interface{} {
	if data == nil {
		return map[string]interface{}{}
	}
	signals := map[string]interface{}{
		"high_impact_events": []string{},
		"has_rate_decision":  false, "has_nfp": false, "has_cpi": false,
		"has_ppi": false, "has_gdp": false, "has_employment": false,
		"has_pmi": false, "has_retail_sales": false, "has_cb_speech": false,
	}
	var highImpact []string

	for _, event := range getSliceOfMaps(data, "events") {
		impact := strings.ToUpper(getStrDefault(event, "impact", ""))
		eventName := getStrDefault(event, "event_name", "")

		if impact == "HIGH" {
			highImpact = append(highImpact, eventName)
		}

		nameUpper := strings.ToUpper(eventName)
		if strings.Contains(nameUpper, "RATE") && strings.Contains(nameUpper, "DECISION") {
			signals["has_rate_decision"] = true
		}
		if strings.Contains(nameUpper, "NFP") || strings.Contains(nameUpper, "NON-FARM") || strings.Contains(nameUpper, "NONFARM") {
			signals["has_nfp"] = true
		}
		if strings.Contains(nameUpper, "CPI") || strings.Contains(nameUpper, "CONSUMER PRICE INDEX") {
			signals["has_cpi"] = true
		}
		if strings.Contains(nameUpper, "PPI") || strings.Contains(nameUpper, "PRODUCER PRICE") {
			signals["has_ppi"] = true
		}
		if strings.Contains(nameUpper, "GDP") || strings.Contains(nameUpper, "GROSS DOMESTIC") {
			signals["has_gdp"] = true
		}
		if strings.Contains(nameUpper, "EMPLOYMENT") || strings.Contains(nameUpper, "UNEMPLOYMENT") || strings.Contains(nameUpper, "JOBLESS") {
			signals["has_employment"] = true
		}
		if strings.Contains(nameUpper, "PMI") || strings.Contains(nameUpper, "PURCHASING MANAGER") {
			signals["has_pmi"] = true
		}
		if strings.Contains(nameUpper, "RETAIL SALES") {
			signals["has_retail_sales"] = true
		}
		if strings.Contains(nameUpper, "SPEECH") || strings.Contains(nameUpper, "SPEAKS") || strings.Contains(nameUpper, "TESTIMONY") {
			signals["has_cb_speech"] = true
		}
	}
	signals["high_impact_events"] = highImpact
	return signals
}

func extractDXY(data map[string]interface{}) map[string]interface{} {
	if data == nil {
		return map[string]interface{}{}
	}
	latest := getMap(data, "latest")
	if latest == nil {
		if snapshots := getSliceOfMaps(data, "snapshots"); len(snapshots) > 0 {
			latest = snapshots[len(snapshots)-1]
		}
	}
	if latest == nil {
		return map[string]interface{}{}
	}
	out := map[string]interface{}{}
	if v, ok := latest["dxy_value"]; ok {
		out["value"] = v
	}
	if v, ok := latest["trend"]; ok {
		out["trend"] = v
	}
	return out
}

func extractNews(data map[string]interface{}) map[string]interface{} {
	if data == nil {
		return map[string]interface{}{}
	}
	var headlines []string
	for _, item := range getSliceOfMaps(data, "items") {
		if h := getStrDefault(item, "headline", ""); h != "" {
			headlines = append(headlines, h)
		}
	}
	return map[string]interface{}{"headlines": headlines}
}

func extractSentiment(data map[string]interface{}) map[string]interface{} {
	if data == nil {
		return map[string]interface{}{}
	}
	allCurrencies := map[string]float64{}
	for _, s := range getSliceOfMaps(data, "sentiments") {
		currency := strings.ToUpper(getStrDefault(s, "currency", ""))
		if longPct, ok := getFloat(s, "long_percentage"); ok && currency != "" {
			allCurrencies[currency] = longPct
		}
	}
	return map[string]interface{}{"all_currencies": allCurrencies}
}

func extractIntermarket(data map[string]interface{}) map[string]interface{} {
	if data == nil {
		return map[string]interface{}{}
	}
	latest := getMap(data, "latest")
	if latest == nil {
		if snapshots := getSliceOfMaps(data, "snapshots"); len(snapshots) > 0 {
			latest = snapshots[len(snapshots)-1]
		}
	}
	if latest == nil {
		return map[string]interface{}{}
	}
	out := map[string]interface{}{}
	for _, key := range []string{"gold_price", "silver_price", "oil_price", "us2y_yield", "us10y_yield", "us30y_yield", "sp500", "vix", "dxy_value"} {
		if v, ok := latest[key]; ok {
			out[key] = v
		}
	}
	return out
}

func deriveUSDBias(cb map[string]interface{}) string {
	fedTone := strings.ToUpper(getStrDefault(cb, "fed_tone", "NEUTRAL"))
	switch fedTone {
	case "HAWKISH":
		return "BULLISH"
	case "DOVISH":
		return "BEARISH"
	default:
		return "NEUTRAL"
	}
}

// Helpers for map[string]interface{} access.

func getMap(m map[string]interface{}, key string) map[string]interface{} {
	if m == nil {
		return nil
	}
	v, ok := m[key]
	if !ok || v == nil {
		return nil
	}
	result, ok := v.(map[string]interface{})
	if !ok {
		return nil
	}
	return result
}

func getStrDefault(m map[string]interface{}, key, def string) string {
	if m == nil {
		return def
	}
	v, ok := m[key]
	if !ok || v == nil {
		return def
	}
	s, ok := v.(string)
	if !ok {
		return def
	}
	return s
}

func getSliceOfMaps(m map[string]interface{}, key string) []map[string]interface{} {
	if m == nil {
		return nil
	}
	v, ok := m[key]
	if !ok || v == nil {
		return nil
	}
	slice, ok := v.([]interface{})
	if !ok {
		return nil
	}
	out := make([]map[string]interface{}, 0, len(slice))
	for _, item := range slice {
		if mp, ok := item.(map[string]interface{}); ok {
			out = append(out, mp)
		}
	}
	return out
}

func getFloatFromEither(m map[string]interface{}, key1, key2 string) float64 {
	if v, ok := getFloat(m, key1); ok {
		return v
	}
	if v, ok := getFloat(m, key2); ok {
		return v
	}
	return 0
}

func getOptFloat(m map[string]interface{}, key string) *float64 {
	if m == nil {
		return nil
	}
	v, ok := m[key]
	if !ok || v == nil {
		return nil
	}
	switch n := v.(type) {
	case float64:
		return &n
	case int:
		f := float64(n)
		return &f
	case int64:
		f := float64(n)
		return &f
	default:
		return nil
	}
}

func getOptStr(m map[string]interface{}, key string) string {
	return getStrDefault(m, key, "")
}

func getOptBool(m map[string]interface{}, key string) bool {
	if m == nil {
		return false
	}
	v, ok := m[key]
	if !ok || v == nil {
		return false
	}
	b, ok := v.(bool)
	if !ok {
		return false
	}
	return b
}

func getOptStrSlice(m map[string]interface{}, key string) []string {
	if m == nil {
		return nil
	}
	v, ok := m[key]
	if !ok || v == nil {
		return nil
	}
	switch s := v.(type) {
	case []string:
		return s
	case []interface{}:
		out := make([]string, 0, len(s))
		for _, item := range s {
			if str, ok := item.(string); ok {
				out = append(out, str)
			}
		}
		return out
	default:
		return nil
	}
}

func getOptMapSlice(m map[string]interface{}, key string) []map[string]interface{} {
	return getSliceOfMaps(m, key)
}

func getOptFloatMap(m map[string]interface{}, key string) map[string]float64 {
	if m == nil {
		return nil
	}
	v, ok := m[key]
	if !ok || v == nil {
		return nil
	}
	switch fm := v.(type) {
	case map[string]float64:
		return fm
	case map[string]interface{}:
		out := make(map[string]float64, len(fm))
		for k, val := range fm {
			if f, ok := val.(float64); ok {
				out[k] = f
			}
		}
		return out
	default:
		return nil
	}
}
