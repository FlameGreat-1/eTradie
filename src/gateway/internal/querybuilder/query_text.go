package querybuilder

import (
	"fmt"
	"math"
	"strings"
)

// BuildQueryText builds a semantic query string from ALL extracted TA + Macro signals.
func BuildQueryText(ta *TASignals, macro *MacroSignals) string {
	var parts []string
	addTASignals(&parts, ta)
	addMacroSignals(&parts, macro)
	return strings.Join(parts, " ")
}

func addTASignals(parts *[]string, ta *TASignals) {
	*parts = append(*parts, ta.Symbol)

	if ta.Direction != "" {
		dirWord := map[string]string{
			"long": "bullish", "short": "bearish", "neutral": "neutral",
		}[ta.Direction]
		if dirWord == "" {
			dirWord = ta.Direction
		}
		*parts = append(*parts, dirWord)
	}

	if ta.TrendDirection != "" && ta.TrendDirection != "NEUTRAL" {
		*parts = append(*parts, "trend "+strings.ToLower(ta.TrendDirection))
	}

	if ta.Framework != "" {
		*parts = append(*parts, strings.ToUpper(ta.Framework))
	}

	for _, pattern := range ta.PatternsDetected {
		*parts = append(*parts, strings.ToLower(strings.ReplaceAll(pattern, "_", " ")))
	}
	for _, family := range ta.SetupFamilies {
		*parts = append(*parts, strings.ReplaceAll(family, "_", " "))
	}

	if ta.HasBMS {
		*parts = append(*parts, "BOS break of structure")
	}
	if ta.HasChoCH {
		*parts = append(*parts, "CHoCH change of character")
	}
	if ta.HasSMS {
		*parts = append(*parts, "SMS shift in market structure")
	}
	if ta.HasOrderBlock {
		*parts = append(*parts, "order block")
	}
	if ta.HasFVG {
		*parts = append(*parts, "fair value gap FVG")
	}
	if ta.HasLiquiditySweep {
		*parts = append(*parts, "liquidity sweep")
	}
	if ta.HasInducementCleared {
		*parts = append(*parts, "inducement cleared")
	}
	if ta.HasDisplacement {
		*parts = append(*parts, "displacement")
	}

	if ta.HasQML {
		*parts = append(*parts, "QML quasi modo level")
	}
	if ta.HasSRFlip {
		*parts = append(*parts, "SR flip support resistance flip")
	}
	if ta.HasRSFlip {
		*parts = append(*parts, "RS flip resistance support flip")
	}
	if ta.HasMPL {
		*parts = append(*parts, "MPL mini price level")
	}
	if ta.HasFakeout {
		*parts = append(*parts, "fakeout")
	}
	if ta.HasMarubozu {
		*parts = append(*parts, "marubozu")
	}
	if ta.HasCompression {
		*parts = append(*parts, "compression")
	}

	if ta.HasPreviousLevels {
		*parts = append(*parts, "previous highs lows")
		if ta.PreviousHighs > 0 {
			*parts = append(*parts, fmt.Sprintf("%d previous highs", ta.PreviousHighs))
		}
		if ta.PreviousLows > 0 {
			*parts = append(*parts, fmt.Sprintf("%d previous lows", ta.PreviousLows))
		}
	}

	if ta.HasFibConfluence {
		*parts = append(*parts, "fibonacci confluence")
		for _, level := range ta.FibLevels {
			*parts = append(*parts, "fib "+level)
		}
	}

	for _, htf := range ta.HTFTimeframes {
		*parts = append(*parts, htf)
	}
	for _, ltf := range ta.LTFTimeframes {
		*parts = append(*parts, ltf)
	}

	if ta.SessionContext != "" {
		*parts = append(*parts, ta.SessionContext+" session")
	}
}

func addMacroSignals(parts *[]string, macro *MacroSignals) {
	if macro.MacroBiasUSD != "" {
		usdWord := map[string]string{
			"BULLISH": "USD bullish strong dollar",
			"BEARISH": "USD bearish weak dollar",
			"NEUTRAL": "USD neutral",
		}[macro.MacroBiasUSD]
		if usdWord != "" {
			*parts = append(*parts, usdWord)
		}
	}

	if macro.FedTone != "" {
		*parts = append(*parts, "Fed "+strings.ToLower(macro.FedTone))
	}
	if macro.ECBTone != "" {
		*parts = append(*parts, "ECB "+strings.ToLower(macro.ECBTone))
	}
	if macro.BOETone != "" {
		*parts = append(*parts, "BOE "+strings.ToLower(macro.BOETone))
	}
	if macro.BOJTone != "" {
		*parts = append(*parts, "BOJ "+strings.ToLower(macro.BOJTone))
	}

	if macro.HasRateChange {
		*parts = append(*parts, macro.RateChangeBank+" rate "+macro.RateChangeDirection)
	}

	if macro.HasQEQT {
		action := strings.ToLower(macro.QEQTAction)
		bank := macro.QEQTBank
		if bank == "" {
			bank = "central bank"
		}
		*parts = append(*parts, fmt.Sprintf("%s %s", bank, action))
		if macro.BalanceSheetDir != "" {
			*parts = append(*parts, "balance sheet "+strings.ToLower(macro.BalanceSheetDir))
		}
		if action == "qe" {
			*parts = append(*parts, "quantitative easing asset purchases")
		} else if action == "qt" {
			*parts = append(*parts, "quantitative tightening balance sheet reduction")
		}
	}

	if macro.DXYValue != nil {
		*parts = append(*parts, fmt.Sprintf("DXY %v", *macro.DXYValue))
	}
	if macro.DXYTrend != "" {
		*parts = append(*parts, "DXY trend "+macro.DXYTrend)
	}
	if macro.DXYMomentum != "" && macro.DXYMomentum != "FLAT" {
		*parts = append(*parts, "DXY momentum "+strings.ToLower(macro.DXYMomentum))
	}
	if macro.DXYBias != "" && macro.DXYBias != "NEUTRAL" {
		*parts = append(*parts, "DXY bias "+strings.ToLower(macro.DXYBias))
	}

	if macro.HasNFP {
		*parts = append(*parts, "NFP non-farm payrolls")
	}
	if macro.HasCPI {
		*parts = append(*parts, "CPI consumer price index inflation")
	}
	if macro.HasPPI {
		*parts = append(*parts, "PPI producer price index")
	}
	if macro.HasGDP {
		*parts = append(*parts, "GDP gross domestic product")
	}
	if macro.HasRateDecision {
		*parts = append(*parts, "rate decision interest rate")
	}
	if macro.HasEmployment {
		*parts = append(*parts, "employment unemployment")
	}
	if macro.HasPMI {
		*parts = append(*parts, "PMI purchasing managers index")
	}
	if macro.HasRetailSales {
		*parts = append(*parts, "retail sales")
	}
	if macro.HasCBSpeech {
		*parts = append(*parts, "central bank speech")
	}

	for _, event := range macro.HighImpactEventsWithin24h {
		*parts = append(*parts, event)
	}

	// Core vs headline inflation distinction.
	for _, coreRelease := range macro.CoreInflationData {
		indicator := getStrDefault(coreRelease, "indicator_name", "")
		if indicator == "" {
			indicator = getStrDefault(coreRelease, "indicator", "")
		}
		currency := getStrDefault(coreRelease, "currency", "")
		surprise := getStrDefault(coreRelease, "surprise", "")
		if indicator != "" {
			entry := fmt.Sprintf("core inflation %s %s", currency, indicator)
			if surprise != "" && surprise != "INLINE" {
				entry += " " + strings.ToLower(surprise)
			}
			*parts = append(*parts, entry)
		}
	}

	// COT enriched signals.
	addCOTSignal(parts, "EUR", macro.COTNetEUR)
	addCOTSignal(parts, "GBP", macro.COTNetGBP)
	addCOTSignal(parts, "JPY", macro.COTNetJPY)
	addCOTSignal(parts, "AUD", macro.COTNetAUD)
	addCOTSignal(parts, "CAD", macro.COTNetCAD)
	addCOTSignal(parts, "NZD", macro.COTNetNZD)
	addCOTSignal(parts, "CHF", macro.COTNetCHF)

	// COT week-over-week shifts.
	for currency, shift := range macro.COTWoWShifts {
		if math.Abs(shift) >= 5000 {
			dir := "increasing"
			if shift < 0 {
				dir = "decreasing"
			}
			*parts = append(*parts, fmt.Sprintf("%s COT wow %s %d", strings.ToUpper(currency), dir, int(shift)))
		}
	}

	// COT extreme positioning.
	for _, currency := range macro.COTExtremesFlagged {
		*parts = append(*parts, fmt.Sprintf("%s COT extreme positioning contrarian risk", strings.ToUpper(currency)))
	}

	// COT enriched per-position signals.
	for _, pos := range macro.COTPositions {
		if pos.ExtremeFlag {
			*parts = append(*parts, fmt.Sprintf("%s COT 52-week extreme percentile %.0f signal %s",
				pos.Currency, pos.PercentileRank, strings.ToLower(pos.SignalStrength)))
		}
		if pos.Divergence {
			*parts = append(*parts, fmt.Sprintf("%s COT commercial speculator divergence contrarian", pos.Currency))
		}
		if pos.LeveragedNet != 0 && math.Abs(pos.LeveragedNet) >= 5000 {
			dir := "net long"
			if pos.LeveragedNet < 0 {
				dir = "net short"
			}
			*parts = append(*parts, fmt.Sprintf("%s TFF leveraged funds %s %d", pos.Currency, dir, int(pos.LeveragedNet)))
		}
		if pos.AssetManagerNet != 0 && math.Abs(pos.AssetManagerNet) >= 5000 {
			dir := "net long"
			if pos.AssetManagerNet < 0 {
				dir = "net short"
			}
			*parts = append(*parts, fmt.Sprintf("%s TFF asset managers %s %d", pos.Currency, dir, int(pos.AssetManagerNet)))
		}
	}

	if macro.COTHasTFFData {
		*parts = append(*parts, "TFF leveraged funds data available")
	}

	for _, surprise := range macro.EconomicSurprises {
		indicator := getStrDefault(surprise, "indicator_name", "")
		if indicator == "" {
			indicator = getStrDefault(surprise, "indicator", "")
		}
		direction := getStrDefault(surprise, "direction", "")
		impact := getStrDefault(surprise, "impact", "")
		if indicator != "" && direction != "" && strings.ToUpper(impact) == "HIGH" {
			entry := fmt.Sprintf("%s %s surprise", indicator, strings.ToLower(direction))
			inflationType := getStrDefault(surprise, "inflation_type", "")
			if inflationType != "" {
				entry += " " + strings.ToLower(inflationType)
			}
			*parts = append(*parts, entry)
		}
	}

	// Risk environment signals.
	if macro.StagflationDetected {
		*parts = append(*parts, "stagflation detected high inflation negative growth")
	}
	if macro.SafeHavenElevated {
		*parts = append(*parts, "safe haven demand elevated JPY CHF gold")
	}
	if macro.CommodityCurrenciesWeak {
		*parts = append(*parts, "commodity currencies weak AUD NZD CAD risk-off")
	}
	if macro.RiskYieldCurveInverted {
		*parts = append(*parts, "yield curve inverted recession signal risk-off")
	}
	if macro.RiskEnvironment != "" && macro.RiskEnvironment != "NEUTRAL" {
		*parts = append(*parts, "risk environment "+strings.ToLower(macro.RiskEnvironment))
	}

	if macro.VIX != nil && *macro.VIX > 25 {
		*parts = append(*parts, fmt.Sprintf("VIX elevated %v", *macro.VIX))
	}
	if macro.YieldCurveInverted != nil && *macro.YieldCurveInverted {
		*parts = append(*parts, "yield curve inverted recession signal")
	}

	// Intermarket commodity correlations.
	if macro.GoldPrice != nil {
		*parts = append(*parts, "gold")
	}
	if macro.OilPrice != nil {
		*parts = append(*parts, "oil crude CAD correlation")
	}
	if macro.IronOre != nil {
		*parts = append(*parts, fmt.Sprintf("iron ore %.1f AUD China proxy", *macro.IronOre))
	}
	if macro.DairyGDT != nil {
		*parts = append(*parts, fmt.Sprintf("dairy GDT %.1f NZD correlation", *macro.DairyGDT))
	}
	if macro.Copper != nil {
		*parts = append(*parts, "copper global growth proxy")
	}
	if macro.NaturalGas != nil {
		*parts = append(*parts, "natural gas energy")
	}

	for currency, longPct := range macro.RetailSentiment {
		if longPct > 70 {
			*parts = append(*parts, fmt.Sprintf("%s retail crowded long %.0f%%", currency, longPct))
		} else if longPct < 30 {
			*parts = append(*parts, fmt.Sprintf("%s retail crowded short %.0f%%", currency, 100-longPct))
		}
	}

	for _, headline := range macro.NewsHeadlines {
		*parts = append(*parts, headline)
	}
}

func addCOTSignal(parts *[]string, currency string, net *float64) {
	if net == nil {
		return
	}
	if math.Abs(*net) < 5000 {
		return
	}
	cotDir := "net long"
	if *net < 0 {
		cotDir = "net short"
	}
	*parts = append(*parts, fmt.Sprintf("%s COT %s %d", currency, cotDir, int(*net)))
}
