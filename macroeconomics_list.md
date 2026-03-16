# Complete Macroeconomics Used by the eTradie AI Trading System

Based on a thorough examination of both `docs/txt/` and the `/knowledge` directory, below is the exact, complete list of macroeconomic elements, indicators, events, and dynamics the system uses to determine its `macro_bias`, `currency_strength`, and `risk_environment`.

## 1. Central Bank Policy & Interest Rates
This is the strongest macro signal in the system's hierarchy.
- **Interest Rate Decisions:** Actual hikes, cuts, or pauses by central banks (Fed, ECB, BOE, BOJ, RBA, RBNZ, BOC, SNB).
- **Interest Rate Differential:** The difference in rates between the two currencies in a pair. Capital flows toward the higher-yielding currency.
- **Central Bank Tone / Forward Guidance:** Parse language for hawkish (tightening) vs. dovish (easing) tilts from meeting minutes or official statements.
- **Central Bank Speeches:** Speeches from key figures like the Fed Chair, ECB President, BOE Governor, or BOJ Governor.
- **Quantitative Easing (QE) / Tightening (QT):** Balance sheet expansion or contraction.
- **Policy Divergence:** When two central banks have opposing policies (e.g., one hiking while the other cuts), creating the strongest trend driver for that specific pair.

## 2. Inflation Data
- **CPI (Consumer Price Index):** Hot prints (above forecast) generally drive hawkish pressure and currency strength; cold prints drive dovish pressure and currency weakness.
- **PCE (Personal Consumption Expenditures):** The Fed's preferred inflation gauge.
- **Core vs. Headline Inflation:** The system explicitly weights Core inflation (excluding volatile food and energy) over Headline inflation for bias determination.
- **Stagflation Conditions:** High inflation combined with low/negative growth, signaling high uncertainty and elevated volatility.

## 3. Economic Growth & Activity Data
- **NFP (Non-Farm Payrolls):** US employment data measuring job creation and unemployment rates.
- **GDP (Gross Domestic Product):** Measures economic expansion or contraction.
- **PMI (Purchasing Managers Index):** Above 50 indicates expansion; below 50 indicates contraction. Flash (preliminary) PMIs are weighted heavier as they move price more than final revisions.
- **Retail Sales:** A measure of consumer spending that influences growth and hawkish/dovish pressure.

## 4. US Dollar Index (DXY)
DXY is a mandatory, non-negotiable analytical layer for all USD-denominated pairs.
- **DXY Direction (Trend):** Broad USD strength or weakness against a basket of currencies.
- **DXY Structure:** Analyzing DXY for 1W/1D structural breaks (BOS), changes of character (CHoCH), or reactions at key Supply/Demand zones.
- **DXY Divergence:** When DXY is trending but a specific USD pair is not following, signaling a pair-specific fundamental driver overriding the DXY influence.
- **DXY Momentum:** Measuring the speed and strength of the DXY trend.

## 5. Commitment of Traders (COT) Data
Sourced weekly from the CFTC API, providing institutional positioning context.
- **Non-Commercial Positioning (Large Speculators):** The primary signal in forex. Evaluated for net long/short bias.
- **Positioning Shifts (Week-over-Week):** Increasing net positions indicate momentum/trend continuation. Rapid shifts indicate potential trend changes.
- **Position Extremes:** When speculative positioning reaches a 52-week extreme, it flags an overcrowded trade and elevated reversal risk (contrarian signal).
- **Position Crowding / Sentiment Exhaustion:** When price stops making new highs/lows despite extreme positioning building up.
- **Commercial vs. Speculator Divergence:** Used as a contrarian indicator at market turning points (Accumulation vs. Distribution phases).
- **TFF Report (Leveraged Funds):** Used as the most precise proxy for speculative hot money in forex when available.

## 6. Global Risk Sentiment & Intermarket Dynamics
- **Risk-On Environment:** Investors increase exposure to growth-sensitive and commodity-linked currencies (AUD, NZD, CAD).
- **Risk-Off Environment:** Investors move capital to safe havens (USD, JPY, CHF, Gold) due to crisis or fear.
- **Safe Haven Flows:** Sudden, violent appreciation in JPY, CHF, or USD during geopolitical conflicts, recessions, or financial crises.
- **Commodity Correlations:**
  - **Crude Oil (WTI/Brent):** Closely tracks with the Canadian Dollar (CAD).
  - **Iron Ore / Coal / China Growth Proxy:** Closely tracks with the Australian Dollar (AUD) and New Zealand Dollar (NZD).
  - **Dairy Prices:** Specific tracking for the New Zealand Dollar (NZD).
- **Real Yields (US 10Y minus inflation):** Specifically evaluated alongside DXY to determine Gold (XAU/USD) direction.

## 7. Geopolitical Events & Black Swans
- **Geopolitical Conflict / War:** Triggers immediate risk-off safe haven flows.
- **Financial Crises:** Banking failures, debt ceiling crises, etc.
- **Intervention Risk:** Historic action levels where central banks like the BOJ or SNB might intervene to manipulate their currency.
- **Black Swan Events:** Unpredictable massive shocks that immediately override any established macro bias in the system rules.
