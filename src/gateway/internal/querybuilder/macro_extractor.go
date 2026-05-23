package querybuilder

import (
	"strings"

	"github.com/flamegreat-1/etradie/src/gateway/internal/models"
)

// MacroSignals holds extracted macro signals for RAG query construction.
type MacroSignals struct {
	MacroBiasUSD string

	DXYValue      *float64
	DXYTrend      string
	DXYMomentum   string
	DXYBias       string
	DXYDivergence map[string]interface{}

	COTNetEUR *float64
	COTNetGBP *float64
	COTNetJPY *float64
	COTNetAUD *float64
	COTNetCAD *float64
	COTNetNZD *float64
	COTNetCHF *float64

	COTWoWShifts       map[string]float64
	COTExtremesFlagged []string
	COTHasTFFData      bool
	COTPositions       []COTPositionSignal

	FedTone             string
	ECBTone             string
	BOETone             string
	BOJTone             string
	RBATone             string
	BOCTone             string
	RBNZTone            string
	SNBTone             string
	HasRateChange       bool
	RateChangeBank      string
	RateChangeDirection string
	HasQEQT             bool
	QEQTBank            string
	QEQTAction          string
	BalanceSheetDir     string

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

	EconomicSurprises []map[string]interface{}
	CoreInflationData []map[string]interface{}

	RetailSentiment         map[string]float64
	RiskEnvironment         string
	StagflationDetected     bool
	SafeHavenElevated       bool
	CommodityCurrenciesWeak bool
	RiskYieldCurveInverted  bool
	RiskVIXLevel            *float64
	RiskReasoning           []string

	GoldPrice          *float64
	SilverPrice        *float64
	OilPrice           *float64
	IronOre            *float64
	DairyGDT           *float64
	Copper             *float64
	NaturalGas         *float64
	US2YYield          *float64
	US10YYield         *float64
	US30YYield         *float64
	SP500              *float64
	VIX                *float64
	YieldCurveInverted *bool
}

// COTPositionSignal holds enriched COT data per currency for RAG query construction.
type COTPositionSignal struct {
	Currency        string
	Net             float64
	WoWChange       float64
	PercentileRank  float64
	ExtremeFlag     bool
	SignalStrength  string
	Divergence      bool
	LeveragedNet    float64
	AssetManagerNet float64
}

// ExtractMacroSignals extracts ALL RAG-relevant signals from the aggregated macro output.
func ExtractMacroSignals(result *models.MacroResult) *MacroSignals {
	if result == nil {
		return &MacroSignals{}
	}
	cb := extractCentralBank(result.CentralBank)
	cot := extractCOT(result.COT)
	econ := extractEconomic(result.Economic)
	cal := extractCalendar(result.Calendar)
	dxy := extractDXY(result.DXY)
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

	cotPositions := extractCOTPositions(result.COT)

	return &MacroSignals{
		MacroBiasUSD: macroBias,

		DXYValue:      getOptFloat(dxy, "value"),
		DXYTrend:      getOptStr(dxy, "trend"),
		DXYMomentum:   getOptStr(dxy, "momentum"),
		DXYBias:       getOptStr(dxy, "bias"),
		DXYDivergence: getMapNested(dxy, "divergence_signals"),

		COTNetEUR: getOptFloat(cot, "eur_net"),
		COTNetGBP: getOptFloat(cot, "gbp_net"),
		COTNetJPY: getOptFloat(cot, "jpy_net"),
		COTNetAUD: getOptFloat(cot, "aud_net"),
		COTNetCAD: getOptFloat(cot, "cad_net"),
		COTNetNZD: getOptFloat(cot, "nzd_net"),
		COTNetCHF: getOptFloat(cot, "chf_net"),

		COTWoWShifts:       getOptFloatMap(cot, "wow_shifts"),
		COTExtremesFlagged: getOptStrSlice(cot, "extremes_flagged"),
		COTHasTFFData:      getOptBool(cot, "has_tff_data"),
		COTPositions:       cotPositions,

		FedTone:             getOptStr(cb, "fed_tone"),
		ECBTone:             getOptStr(cb, "ecb_tone"),
		BOETone:             getOptStr(cb, "boe_tone"),
		BOJTone:             getOptStr(cb, "boj_tone"),
		RBATone:             getOptStr(cb, "rba_tone"),
		BOCTone:             getOptStr(cb, "boc_tone"),
		RBNZTone:            getOptStr(cb, "rbnz_tone"),
		SNBTone:             getOptStr(cb, "snb_tone"),
		HasRateChange:       getOptBool(cb, "has_rate_change"),
		RateChangeBank:      getOptStr(cb, "rate_change_bank"),
		RateChangeDirection: getOptStr(cb, "rate_change_direction"),
		HasQEQT:             getOptBool(cb, "has_qe_qt"),
		QEQTBank:            getOptStr(cb, "qe_qt_bank"),
		QEQTAction:          getOptStr(cb, "qe_qt_action"),
		BalanceSheetDir:     getOptStr(cb, "balance_sheet_direction"),

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

		EconomicSurprises: getOptMapSlice(econ, "surprise_directions"),
		CoreInflationData: getOptMapSlice(econ, "core_inflation_releases"),

		RetailSentiment:         getOptFloatMap(sent, "all_currencies"),
		RiskEnvironment:         getOptStr(sent, "risk_environment"),
		StagflationDetected:     getOptBool(sent, "stagflation_detected"),
		SafeHavenElevated:       getOptBool(sent, "safe_haven_demand_elevated"),
		CommodityCurrenciesWeak: getOptBool(sent, "commodity_currencies_weak"),
		RiskYieldCurveInverted:  getOptBool(sent, "risk_yield_curve_inverted"),
		RiskVIXLevel:            getOptFloat(sent, "vix_level"),
		RiskReasoning:           getOptStrSlice(sent, "risk_reasoning"),

		GoldPrice:          getOptFloat(inter, "gold_price"),
		SilverPrice:        getOptFloat(inter, "silver_price"),
		OilPrice:           getOptFloat(inter, "oil_price"),
		IronOre:            getOptFloat(inter, "iron_ore"),
		DairyGDT:           getOptFloat(inter, "dairy_gdt"),
		Copper:             getOptFloat(inter, "copper"),
		NaturalGas:         getOptFloat(inter, "natural_gas"),
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
	signals := map[string]interface{}{
		"has_rate_change": false,
		"has_qe_qt":       false,
	}

	for _, source := range []string{"speeches", "forward_guidance"} {
		for _, item := range getSliceOfMaps(data, source) {
			bank := strings.ToUpper(getStrDefault(item, "bank", ""))
			tone := strings.ToUpper(getStrDefault(item, "tone", ""))
			key := strings.ToLower(bank) + "_tone"
			if _, exists := signals[key]; !exists {
				signals[key] = tone
			}

			policyAction := strings.ToUpper(getStrDefault(item, "monetary_policy_action", "NONE"))
			if policyAction == "QE" || policyAction == "QT" {
				signals["has_qe_qt"] = true
				signals["qe_qt_bank"] = bank
				signals["qe_qt_action"] = policyAction
				balDir := getStrDefault(item, "balance_sheet_direction", "")
				if balDir == "" {
					if policyAction == "QE" {
						balDir = "EXPANDING"
					} else {
						balDir = "CONTRACTING"
					}
				}
				signals["balance_sheet_direction"] = balDir
			}
		}
	}

	for _, action := range getSliceOfMaps(data, "policy_actions") {
		actionType := strings.ToUpper(getStrDefault(action, "action", "NONE"))
		if actionType == "QE" || actionType == "QT" {
			bank := strings.ToUpper(getStrDefault(action, "bank", ""))
			signals["has_qe_qt"] = true
			signals["qe_qt_bank"] = bank
			signals["qe_qt_action"] = actionType
			if actionType == "QE" {
				signals["balance_sheet_direction"] = "EXPANDING"
			} else {
				signals["balance_sheet_direction"] = "CONTRACTING"
			}
		}
	}

	for _, decision := range getSliceOfMaps(data, "rate_decisions") {
		bank := strings.ToUpper(getStrDefault(decision, "bank", ""))
		tone := strings.ToUpper(getStrDefault(decision, "tone", ""))
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

		policyAction := strings.ToUpper(getStrDefault(decision, "monetary_policy_action", "NONE"))
		if policyAction == "QE" || policyAction == "QT" {
			signals["has_qe_qt"] = true
			signals["qe_qt_bank"] = bank
			signals["qe_qt_action"] = policyAction
			if policyAction == "QE" {
				signals["balance_sheet_direction"] = "EXPANDING"
			} else {
				signals["balance_sheet_direction"] = "CONTRACTING"
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

	if wowShifts := getMap(data, "wow_shifts"); wowShifts != nil {
		signals["wow_shifts"] = wowShifts
	}
	if extremes := getSliceOrStrSlice(data, "extremes_flagged"); len(extremes) > 0 {
		signals["extremes_flagged"] = extremes
	}
	signals["has_tff_data"] = getOptBool(data, "has_tff_data")

	return signals
}

func extractCOTPositions(data map[string]interface{}) []COTPositionSignal {
	if data == nil {
		return nil
	}
	var positions []COTPositionSignal
	for _, pos := range getSliceOfMaps(data, "latest_positions") {
		currency := strings.ToUpper(getStrDefault(pos, "currency", ""))
		if currency == "" {
			continue
		}
		net, _ := getFloat(pos, "non_commercial_net")
		wow, _ := getFloat(pos, "wow_change")
		pctRank, _ := getFloat(pos, "percentile_rank")
		leveragedNet, _ := getFloat(pos, "leveraged_net")
		assetMgrNet, _ := getFloat(pos, "asset_manager_net")

		positions = append(positions, COTPositionSignal{
			Currency:        currency,
			Net:             net,
			WoWChange:       wow,
			PercentileRank:  pctRank,
			ExtremeFlag:     getOptBool(pos, "extreme_flag"),
			SignalStrength:  getStrDefault(pos, "signal_strength", "NEUTRAL"),
			Divergence:      getOptBool(pos, "commercial_vs_speculator_divergence"),
			LeveragedNet:    leveragedNet,
			AssetManagerNet: assetMgrNet,
		})
	}
	return positions
}

func extractEconomic(data map[string]interface{}) map[string]interface{} {
	if data == nil {
		return map[string]interface{}{}
	}
	var surprises []map[string]interface{}
	var coreInflation []map[string]interface{}

	for _, release := range getSliceOfMaps(data, "releases") {
		surpriseDir := getStrDefault(release, "surprise_direction", "")
		indicator := getStrDefault(release, "indicator", "")
		inflationType := getStrDefault(release, "inflation_type", "")

		if surpriseDir != "" && indicator != "" {
			entry := map[string]interface{}{
				"indicator":      indicator,
				"indicator_name": getStrDefault(release, "indicator_name", ""),
				"direction":      surpriseDir,
				"currency":       getStrDefault(release, "currency", ""),
				"impact":         getStrDefault(release, "impact", ""),
			}
			if inflationType != "" {
				entry["inflation_type"] = inflationType
			}
			surprises = append(surprises, entry)
		}

		if strings.ToUpper(inflationType) == "CORE" {
			coreInflation = append(coreInflation, map[string]interface{}{
				"indicator":      indicator,
				"indicator_name": getStrDefault(release, "indicator_name", ""),
				"currency":       getStrDefault(release, "currency", ""),
				"actual":         getStrDefault(release, "actual", ""),
				"forecast":       getStrDefault(release, "forecast", ""),
				"previous":       getStrDefault(release, "previous", ""),
				"surprise":       surpriseDir,
				"impact":         getStrDefault(release, "impact", ""),
			})
		}
	}
	return map[string]interface{}{
		"surprise_directions":     surprises,
		"core_inflation_releases": coreInflation,
	}
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
	if v, ok := latest["dxy_momentum"]; ok {
		out["momentum"] = v
	} else if v, ok := latest["momentum"]; ok {
		out["momentum"] = v
	}
	if v, ok := latest["bias"]; ok {
		out["bias"] = v
	}
	if v, ok := latest["divergence_signals_json"]; ok {
		out["divergence_signals"] = v
	} else if v, ok := latest["divergence_signals"]; ok {
		out["divergence_signals"] = v
	}
	return out
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
	out := map[string]interface{}{"all_currencies": allCurrencies}

	// Populate risk_environment if present in the sentiment data.
	if riskEnv := getStrDefault(data, "risk_environment", ""); riskEnv != "" {
		out["risk_environment"] = riskEnv
	}

	// Extract the full risk assessment from the cached sentiment result.
	riskAssessment := getMap(data, "risk_assessment")
	if riskAssessment != nil {
		out["stagflation_detected"] = getOptBool(riskAssessment, "stagflation_detected")
		out["safe_haven_demand_elevated"] = getOptBool(riskAssessment, "safe_haven_demand_elevated")
		out["commodity_currencies_weak"] = getOptBool(riskAssessment, "commodity_currencies_weak")
		out["risk_yield_curve_inverted"] = getOptBool(riskAssessment, "yield_curve_inverted")
		out["vix_level"] = riskAssessment["vix_level"]
		out["risk_reasoning"] = riskAssessment["reasoning"]
	}

	return out
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
	for _, key := range []string{
		"gold_price", "silver_price", "oil_price",
		"iron_ore", "dairy_gdt", "copper", "natural_gas",
		"us2y_yield", "us10y_yield", "us30y_yield",
		"sp500", "vix", "dxy_value",
	} {
		if v, ok := latest[key]; ok {
			out[key] = v
		}
	}
	return out
}

func deriveUSDBias(cb map[string]interface{}) string {
	fedTone := strings.ToUpper(getStrDefault(cb, "fed_tone", ""))

	// Primary signal: Fed tone.
	switch fedTone {
	case "HAWKISH":
		return "BULLISH"
	case "DOVISH":
		return "BEARISH"
	}

	// Secondary signal: QE/QT policy action directly impacts USD.
	if getOptBool(cb, "has_qe_qt") {
		action := strings.ToUpper(getStrDefault(cb, "qe_qt_action", ""))
		switch action {
		case "QT":
			return "BULLISH"
		case "QE":
			return "BEARISH"
		}
	}

	return "NEUTRAL"
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

func getMapNested(m map[string]interface{}, key string) map[string]interface{} {
	return getMap(m, key)
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

func getSliceOrStrSlice(m map[string]interface{}, key string) []string {
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
