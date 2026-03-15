package querybuilder

import (
	"sort"
	"strings"

	"github.com/flamegreat/etradie/src/gateway/internal/models"
)

// TASignals holds extracted TA signals for RAG query construction.
type TASignals struct {
	Symbol           string
	Framework        string
	SetupFamilies    []string
	Direction        string
	HTFTimeframes    []string
	LTFTimeframes    []string
	OverallTrend     string
	SessionContext   string
	PatternsDetected []string
	FibLevels        []string
	TrendDirection   string

	// SMC flags.
	HasBMS               bool
	HasChoCH             bool
	HasSMS               bool
	HasLiquiditySweep    bool
	HasOrderBlock        bool
	HasFVG               bool
	HasInducementCleared bool
	HasDisplacement      bool

	// SnD flags.
	HasQML            bool
	HasSRFlip         bool
	HasRSFlip         bool
	HasMPL            bool
	HasFakeout        bool
	HasMarubozu       bool
	HasCompression    bool
	HasPreviousLevels bool
	HasFibConfluence  bool
	PreviousHighs     int
	PreviousLows      int
}

// ExtractTASignals extracts ALL RAG-relevant signals from a single symbol's TA result.
func ExtractTASignals(result *models.TASymbolResult) *TASignals {
	if result.Status != "success" {
		return &TASignals{Symbol: result.Symbol}
	}

	smc := result.SMCCandidates
	snd := result.SnDCandidates

	// Use highest TF snapshot (first in map iteration) for direction fallback.
	var snapshot map[string]interface{}
	for _, snap := range result.Snapshots {
		snapshot = snap
		break
	}

	smcFlags := extractSMCFlags(smc)
	sndFlags := extractSnDFlags(snd)
	fibLevels := collectFibLevels(smc, snd)
	prevHighs, prevLows := extractPreviousLevelCounts(snd)

	return &TASignals{
		Symbol:           result.Symbol,
		Framework:        determineFramework(smc, snd),
		SetupFamilies:    collectAllSetupFamilies(smc, snd),
		Direction:        determineDirection(smc, snd, snapshot),
		HTFTimeframes:    result.HTFTimeframes,
		LTFTimeframes:    result.LTFTimeframes,
		OverallTrend:     result.OverallTrend,
		SessionContext:   extractSession(smc, snd),
		PatternsDetected: collectPatterns(smc, snd),
		FibLevels:        fibLevels,
		TrendDirection:   result.OverallTrend,

		HasBMS:               smcFlags["bms"],
		HasChoCH:             smcFlags["choch"],
		HasSMS:               smcFlags["sms"],
		HasLiquiditySweep:    smcFlags["liquidity_swept"],
		HasOrderBlock:        smcFlags["order_block"],
		HasFVG:               smcFlags["fvg"],
		HasInducementCleared: smcFlags["inducement_cleared"],
		HasDisplacement:      smcFlags["displacement"],

		HasQML:            sndFlags["qml"],
		HasSRFlip:         sndFlags["sr_flip"],
		HasRSFlip:         sndFlags["rs_flip"],
		HasMPL:            sndFlags["mpl"],
		HasFakeout:        sndFlags["fakeout"],
		HasMarubozu:       sndFlags["marubozu"],
		HasCompression:    sndFlags["compression"],
		HasPreviousLevels: prevHighs > 0 || prevLows > 0,
		HasFibConfluence:  len(fibLevels) > 0,
		PreviousHighs:     prevHighs,
		PreviousLows:      prevLows,
	}
}

func determineFramework(smc, snd []map[string]interface{}) string {
	hasSMC := len(smc) > 0
	hasSnD := len(snd) > 0
	if hasSMC && !hasSnD {
		return "smc"
	}
	if hasSnD && !hasSMC {
		return "snd"
	}
	if hasSMC && hasSnD {
		if len(smc) >= len(snd) {
			return "smc"
		}
		return "snd"
	}
	return ""
}

func determineDirection(smc, snd []map[string]interface{}, snapshot map[string]interface{}) string {
	var directions []string
	for _, c := range smc {
		if d, ok := getStr(c, "direction"); ok && d != "" {
			directions = append(directions, d)
		}
	}
	for _, c := range snd {
		if d, ok := getStr(c, "direction"); ok && d != "" {
			directions = append(directions, d)
		}
	}
	if len(directions) == 0 {
		if trend, ok := getStr(snapshot, "trend_direction"); ok && trend != "" {
			directions = append(directions, trend)
		}
	}
	if len(directions) == 0 {
		return ""
	}

	bullish, bearish := 0, 0
	for _, d := range directions {
		switch strings.ToUpper(d) {
		case "BULLISH":
			bullish++
		case "BEARISH":
			bearish++
		}
	}
	if bullish > bearish {
		return "long"
	}
	if bearish > bullish {
		return "short"
	}
	return "neutral"
}

func collectAllSetupFamilies(smc, snd []map[string]interface{}) []string {
	families := make(map[string]struct{})

	for _, c := range smc {
		if truthy(c, "order_block_upper") || truthy(c, "order_block_lower") {
			families["order_block"] = struct{}{}
		}
		if truthy(c, "fvg_upper") || truthy(c, "fvg_lower") {
			families["fair_value_gap"] = struct{}{}
		}
		if truthy(c, "liquidity_swept") {
			families["liquidity_sweep"] = struct{}{}
		}
		if truthy(c, "inducement_cleared") {
			families["inducement"] = struct{}{}
		}
		pattern, _ := getStr(c, "pattern")
		if strings.Contains(pattern, "TURTLE_SOUP") {
			families["turtle_soup"] = struct{}{}
		}
		if strings.Contains(pattern, "AMD") {
			families["amd"] = struct{}{}
		}
		if strings.Contains(pattern, "SH_BMS_RTO") {
			families["bms_rto"] = struct{}{}
		}
		if strings.Contains(pattern, "SMS_BMS_RTO") {
			families["sms_rto"] = struct{}{}
		}
	}

	for _, c := range snd {
		if truthy(c, "qml_detected") {
			families["qml"] = struct{}{}
		}
		if truthy(c, "sr_flip_detected") {
			families["sr_flip"] = struct{}{}
		}
		if truthy(c, "rs_flip_detected") {
			families["rs_flip"] = struct{}{}
		}
		if truthy(c, "mpl_detected") {
			families["mpl"] = struct{}{}
		}
		if truthy(c, "supply_zone_upper") {
			families["supply_zone"] = struct{}{}
		}
		if truthy(c, "demand_zone_upper") {
			families["demand_zone"] = struct{}{}
		}
		if truthy(c, "compression_detected") {
			families["compression"] = struct{}{}
		}
		if truthy(c, "fakeout_detected") {
			families["fakeout"] = struct{}{}
		}
		pattern, _ := getStr(c, "pattern")
		if strings.Contains(pattern, "FAKEOUT_KING") {
			families["fakeout_king"] = struct{}{}
		}
		if strings.Contains(pattern, "QML_KILLER") {
			families["qml_killer"] = struct{}{}
		}
		if strings.Contains(pattern, "QML_TRIPLE") {
			families["triple_fakeout"] = struct{}{}
		}
		if strings.Contains(pattern, "SOP") {
			families["sop"] = struct{}{}
		}
		if strings.Contains(pattern, "CONTINUATION") {
			families["continuation"] = struct{}{}
		}
	}

	return sortedKeys(families)
}

func collectPatterns(smc, snd []map[string]interface{}) []string {
	patterns := make(map[string]struct{})
	for _, c := range smc {
		if p, ok := getStr(c, "pattern"); ok && p != "" {
			patterns[p] = struct{}{}
		}
	}
	for _, c := range snd {
		if p, ok := getStr(c, "pattern"); ok && p != "" {
			patterns[p] = struct{}{}
		}
	}
	return sortedKeys(patterns)
}

func collectFibLevels(smc, snd []map[string]interface{}) []string {
	levels := make(map[string]struct{})
	for _, c := range smc {
		if f, ok := getStr(c, "fib_level"); ok && f != "" {
			levels[f] = struct{}{}
		}
	}
	for _, c := range snd {
		if f, ok := getStr(c, "fib_level"); ok && f != "" {
			levels[f] = struct{}{}
		}
	}
	return sortedKeys(levels)
}

func extractSMCFlags(candidates []map[string]interface{}) map[string]bool {
	flags := map[string]bool{
		"bms": false, "choch": false, "sms": false,
		"liquidity_swept": false, "order_block": false, "fvg": false,
		"inducement_cleared": false, "displacement": false,
	}
	for _, c := range candidates {
		if truthy(c, "bms_detected") {
			flags["bms"] = true
		}
		if truthy(c, "choch_detected") {
			flags["choch"] = true
		}
		if truthy(c, "sms_detected") {
			flags["sms"] = true
		}
		if truthy(c, "liquidity_swept") {
			flags["liquidity_swept"] = true
		}
		if truthy(c, "order_block_upper") || truthy(c, "order_block_lower") {
			flags["order_block"] = true
		}
		if truthy(c, "fvg_upper") || truthy(c, "fvg_lower") {
			flags["fvg"] = true
		}
		if truthy(c, "inducement_cleared") {
			flags["inducement_cleared"] = true
		}
		if pips, ok := getFloat(c, "displacement_pips"); ok && pips > 0 {
			flags["displacement"] = true
		}
	}
	return flags
}

func extractSnDFlags(candidates []map[string]interface{}) map[string]bool {
	flags := map[string]bool{
		"qml": false, "sr_flip": false, "rs_flip": false,
		"mpl": false, "fakeout": false, "marubozu": false,
		"compression": false,
	}
	for _, c := range candidates {
		if truthy(c, "qml_detected") {
			flags["qml"] = true
		}
		if truthy(c, "sr_flip_detected") {
			flags["sr_flip"] = true
		}
		if truthy(c, "rs_flip_detected") {
			flags["rs_flip"] = true
		}
		if truthy(c, "mpl_detected") {
			flags["mpl"] = true
		}
		if truthy(c, "fakeout_detected") {
			flags["fakeout"] = true
		}
		if truthy(c, "marubozu_detected") {
			flags["marubozu"] = true
		}
		if truthy(c, "compression_detected") {
			flags["compression"] = true
		}
	}
	return flags
}

func extractPreviousLevelCounts(snd []map[string]interface{}) (int, int) {
	maxHighs, maxLows := 0, 0
	for _, c := range snd {
		if h, ok := getInt(c, "previous_highs_count"); ok && h > maxHighs {
			maxHighs = h
		}
		if l, ok := getInt(c, "previous_lows_count"); ok && l > maxLows {
			maxLows = l
		}
	}
	return maxHighs, maxLows
}

func extractSession(smc, snd []map[string]interface{}) string {
	for _, c := range smc {
		if s, ok := getStr(c, "session_context"); ok && s != "" {
			return s
		}
	}
	for _, c := range snd {
		if s, ok := getStr(c, "session_context"); ok && s != "" {
			return s
		}
	}
	return ""
}

// Map access helpers for map[string]interface{} candidate dicts.

func getStr(m map[string]interface{}, key string) (string, bool) {
	if m == nil {
		return "", false
	}
	v, ok := m[key]
	if !ok {
		return "", false
	}
	s, ok := v.(string)
	return s, ok
}

func getFloat(m map[string]interface{}, key string) (float64, bool) {
	if m == nil {
		return 0, false
	}
	v, ok := m[key]
	if !ok {
		return 0, false
	}
	switch n := v.(type) {
	case float64:
		return n, true
	case int:
		return float64(n), true
	case int64:
		return float64(n), true
	default:
		return 0, false
	}
}

func getInt(m map[string]interface{}, key string) (int, bool) {
	if m == nil {
		return 0, false
	}
	v, ok := m[key]
	if !ok {
		return 0, false
	}
	switch n := v.(type) {
	case float64:
		return int(n), true
	case int:
		return n, true
	case int64:
		return int(n), true
	default:
		return 0, false
	}
}

// truthy checks if a map key exists and is truthy (non-nil, non-zero, non-empty).
func truthy(m map[string]interface{}, key string) bool {
	if m == nil {
		return false
	}
	v, ok := m[key]
	if !ok || v == nil {
		return false
	}
	switch val := v.(type) {
	case bool:
		return val
	case float64:
		return val != 0
	case int:
		return val != 0
	case string:
		return val != ""
	default:
		return true
	}
}

func sortedKeys(m map[string]struct{}) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}
