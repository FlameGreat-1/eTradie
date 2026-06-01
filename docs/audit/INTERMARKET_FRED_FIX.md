# Intermarket / DXY data source fix

## Problem (operator-confirmed)

The DXY and intermarket collectors' only providers were:
  - `TwelveDataProvider` (macro), using tickers like USDX/US02Y/SPX/VIX/CL/HG/NG
    that the configured TwelveData plan does not serve, and a multi-symbol
    response-parse shape that did not match single-symbol responses; and
  - `CommodityProxyProvider`, scraping iron-ore/dairy HTML with loose regexes.

Neither returned data in production. Result: `dxy_value`, the 2/10/30y yields,
`vix`, `sp500`, and the commodity fields were all None -- so the DXY collector's
momentum/trend/bias defaulted to FLAT/NEUTRAL and the risk-environment
yield-curve + VIX inputs were empty. DXY and intermarket were effectively dead.

## Fix

Added `FREDIntermarketProvider`, using the same FRED API + `observations[].value`
shape the central-bank rate providers already use reliably (operator-verified
that DGS10/VIXCLS/DTWEXBGS return clean JSON). Series:

| Field | FRED series |
|-------|-------------|
| dxy_value | DTWEXBGS (broad USD index) |
| us2y_yield | DGS2 |
| us10y_yield | DGS10 |
| us30y_yield | DGS30 |
| vix | VIXCLS |
| sp500 | SP500 |
| oil_price | DCOILWTICO (WTI) |

Wired into BOTH the DXY and intermarket collectors. Deleted the dead
TwelveDataProvider + CommodityProxyProvider and their commodity-proxy config.

The SEPARATE TwelveData CANDLE client (engine.ta.broker.twelve_data, used as a
TA broker fallback) is untouched -- different object, still uses the retained
twelvedata_* config.

## Limitations / not-guessed

- gold, silver, copper, natural gas, iron ore, dairy are left None: no verified
  FRED series for these yet. They are nullable on IntermarketSnapshot and will
  be wired once a working source is confirmed -- not guessed.
- DTWEXBGS is the BROAD trade-weighted dollar index (~119), not the ICE DXY
  futures level (~104). The DXY collector derives momentum/trend/bias from
  RELATIVE change, so direction is correct regardless of absolute scale.
