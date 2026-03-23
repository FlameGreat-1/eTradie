package e2e

// This file provides factory functions that build realistic response
// payloads for the mock engine server. Every field matches the exact
// JSON contract the Gateway's collectors, adapters, and pipeline
// stages expect. Built by examining:
//   - src/gateway/internal/collectors/ta_collector.go (parseSymbolResults)
//   - src/gateway/internal/collectors/macro_collector.go (getDatasetMap)
//   - src/gateway/internal/infra/processor_http.go (Process unmarshal)
//   - src/gateway/internal/pipeline/orchestrator.go (retrieveRAG)

// ---------------------------------------------------------------------------
// TA Response Fixtures
// ---------------------------------------------------------------------------

// TAResponseWithCandidates returns a TA engine response where EURUSD has
// one SMC candidate (TURTLE_SOUP_LONG) with full snapshot data. This is
// the happy-path response that causes the pipeline to proceed through
// all phases: query building, RAG, processor, guards, execution.
func TAResponseWithCandidates() map[string]interface{} {
	return map[string]interface{}{
		"symbol_results": []interface{}{
			map[string]interface{}{
				"symbol":         "EURUSD",
				"status":         "success",
				"overall_trend":  "BULLISH",
				"htf_timeframes": []interface{}{"W1", "D1", "H4", "H1"},
				"ltf_timeframes": []interface{}{"M30", "M15", "M5", "M1"},
				"smc_candidates": []interface{}{
					map[string]interface{}{
						"analysis_id":      "SMC-EURUSD-H4-001",
						"symbol":           "EURUSD",
						"pattern":          "TURTLE_SOUP_LONG",
						"direction":        "BULLISH",
						"entry_price":      1.10000,
						"stop_loss":        1.09500,
						"take_profit":      1.11500,
						"timeframe":        "H4",
						"confidence":       0.85,
						"ltf_confirmation": true,
						"order_block": map[string]interface{}{
							"high":      1.10050,
							"low":       1.09950,
							"timeframe": "H4",
							"type":      "BULLISH_OB",
						},
						"fvg": map[string]interface{}{
							"high":      1.10100,
							"low":       1.09900,
							"timeframe": "H1",
						},
					},
				},
				"snd_candidates": []interface{}{},
				"snapshots": map[string]interface{}{
					"H4": map[string]interface{}{
						"trend":        "BULLISH",
						"bms_count":    2.0,
						"choch_events": []interface{}{},
						"order_blocks": 1.0,
						"fvg_count":    1.0,
					},
					"D1": map[string]interface{}{
						"trend":        "BULLISH",
						"bms_count":    3.0,
						"choch_events": []interface{}{},
						"order_blocks": 2.0,
						"fvg_count":    0.0,
					},
				},
				"alignment": map[string]interface{}{
					"H4": map[string]interface{}{"aligned": true, "direction": "BULLISH"},
					"D1": map[string]interface{}{"aligned": true, "direction": "BULLISH"},
				},
				"error": nil,
			},
		},
	}
}

// TAResponseNoCandidates returns a TA response where the symbol was
// analysed successfully but no SMC or SnD candidates were found.
// This causes the pipeline to complete with OutcomeInsufficientData.
func TAResponseNoCandidates() map[string]interface{} {
	return map[string]interface{}{
		"symbol_results": []interface{}{
			map[string]interface{}{
				"symbol":         "EURUSD",
				"status":         "success",
				"overall_trend":  "NEUTRAL",
				"htf_timeframes": []interface{}{"W1", "D1", "H4", "H1"},
				"ltf_timeframes": []interface{}{"M30", "M15", "M5", "M1"},
				"smc_candidates": []interface{}{},
				"snd_candidates": []interface{}{},
				"snapshots": map[string]interface{}{
					"H4": map[string]interface{}{
						"trend":     "NEUTRAL",
						"bms_count": 0.0,
					},
				},
				"alignment": map[string]interface{}{},
				"error":     nil,
			},
		},
	}
}

// TAResponseMultiSymbol returns a TA response with two symbols:
// EURUSD with candidates and GBPUSD without candidates.
// Tests the concurrent symbol processing path in executePipeline.
func TAResponseMultiSymbol() map[string]interface{} {
	return map[string]interface{}{
		"symbol_results": []interface{}{
			map[string]interface{}{
				"symbol":         "EURUSD",
				"status":         "success",
				"overall_trend":  "BULLISH",
				"htf_timeframes": []interface{}{"W1", "D1", "H4", "H1"},
				"ltf_timeframes": []interface{}{"M30", "M15", "M5", "M1"},
				"smc_candidates": []interface{}{
					map[string]interface{}{
						"analysis_id":      "SMC-EURUSD-H4-001",
						"symbol":           "EURUSD",
						"pattern":          "TURTLE_SOUP_LONG",
						"direction":        "BULLISH",
						"entry_price":      1.10000,
						"stop_loss":        1.09500,
						"take_profit":      1.11500,
						"timeframe":        "H4",
						"ltf_confirmation": true,
					},
				},
				"snd_candidates": []interface{}{},
				"snapshots":       map[string]interface{}{},
				"alignment":       map[string]interface{}{},
				"error":           nil,
			},
			map[string]interface{}{
				"symbol":         "GBPUSD",
				"status":         "success",
				"overall_trend":  "BEARISH",
				"htf_timeframes": []interface{}{"W1", "D1", "H4", "H1"},
				"ltf_timeframes": []interface{}{"M30", "M15", "M5", "M1"},
				"smc_candidates": []interface{}{},
				"snd_candidates": []interface{}{},
				"snapshots":       map[string]interface{}{},
				"alignment":       map[string]interface{}{},
				"error":           nil,
			},
		},
	}
}

// ---------------------------------------------------------------------------
// Macro Response Fixtures
// ---------------------------------------------------------------------------

// MacroResponseFull returns a complete macro collection response with all
// 8 datasets populated. Matches the JSON structure returned by the Python
// engine's /internal/macro/collect endpoint.
func MacroResponseFull() map[string]interface{} {
	return map[string]interface{}{
		"central_bank": map[string]interface{}{
			"speeches":       []interface{}{},
			"rate_decisions": []interface{}{},
		},
		"cot": map[string]interface{}{
			"latest_positions":  []interface{}{},
			"extremes_flagged":  []interface{}{},
			"has_tff_data":      false,
		},
		"economic": map[string]interface{}{
			"releases": []interface{}{},
		},
		"news": map[string]interface{}{
			"articles": []interface{}{},
		},
		"calendar": map[string]interface{}{
			"events": []interface{}{},
		},
		"dxy": map[string]interface{}{
			"latest": map[string]interface{}{
				"dxy_value":    104.5,
				"dxy_momentum": "BULLISH",
				"dxy_trend":    "UP",
			},
		},
		"intermarket": map[string]interface{}{
			"snapshots": []interface{}{},
		},
		"sentiment": map[string]interface{}{
			"risk_environment": "RISK_ON",
		},
		"errors": map[string]interface{}{},
	}
}

// MacroResponsePartial returns a macro response where some datasets
// failed to collect. Tests the pipeline's resilience to partial data.
func MacroResponsePartial() map[string]interface{} {
	return map[string]interface{}{
		"central_bank": nil,
		"cot":          nil,
		"economic": map[string]interface{}{
			"releases": []interface{}{},
		},
		"news": map[string]interface{}{
			"articles": []interface{}{},
		},
		"calendar": map[string]interface{}{
			"events": []interface{}{},
		},
		"dxy":         nil,
		"intermarket": nil,
		"sentiment":   nil,
		"errors": map[string]interface{}{
			"central_bank": "provider timeout after 30s",
			"cot":          "CFTC data not available",
			"dxy":          "market data feed disconnected",
			"intermarket":  "provider timeout after 30s",
			"sentiment":    "API rate limit exceeded",
		},
	}
}

// ---------------------------------------------------------------------------
// RAG Response Fixtures
// ---------------------------------------------------------------------------

// RAGResponseWithChunks returns a RAG retrieval response with knowledge
// chunks. Matches the JSON structure the orchestrator's retrieveRAG
// method expects from POST /internal/rag/retrieve.
func RAGResponseWithChunks() map[string]interface{} {
	return map[string]interface{}{
		"chunks": []interface{}{
			map[string]interface{}{
				"content":  "SMC Turtle Soup: Enter at the liquidity sweep low after BMS confirmation on H4. Stop loss below the sweep wick. TP1 at the nearest H4 order block.",
				"doc_type": "MASTER_RULEBOOK",
				"score":    0.92,
				"metadata": map[string]interface{}{"section": "smc_entries", "page": 47},
			},
			map[string]interface{}{
				"content":  "Risk management: Never risk more than 1% per trade. Scale to 0.5% during high-impact news windows or when confluence score is below 7.",
				"doc_type": "MASTER_RULEBOOK",
				"score":    0.88,
				"metadata": map[string]interface{}{"section": "risk_management", "page": 12},
			},
		},
		"strategy_used":        "scenario_first",
		"total_chunks_returned": 2.0,
		"coverage_result": map[string]interface{}{
			"covered":  true,
			"gaps":     []interface{}{},
		},
		"conflict_result": map[string]interface{}{
			"has_conflicts": false,
			"details":       []interface{}{},
		},
	}
}

// RAGResponseEmpty returns a RAG response with no matching chunks.
// The pipeline should still proceed; the processor handles empty knowledge.
func RAGResponseEmpty() map[string]interface{} {
	return map[string]interface{}{
		"chunks":                []interface{}{},
		"strategy_used":         "hybrid",
		"total_chunks_returned": 0.0,
		"coverage_result": map[string]interface{}{
			"covered": false,
			"gaps":    []interface{}{"no matching scenarios found"},
		},
		"conflict_result": map[string]interface{}{
			"has_conflicts": false,
			"details":       []interface{}{},
		},
	}
}

// ---------------------------------------------------------------------------
// Processor Response Fixtures
// ---------------------------------------------------------------------------

// ProcessorResponseTradeValid returns a processor LLM response that
// approves a trade. Every field matches models.ProcessorOutput exactly
// as it would be unmarshalled by HTTPProcessorAdapter.Process.
func ProcessorResponseTradeValid() map[string]interface{} {
	return map[string]interface{}{
		"trade_valid":      true,
		"direction":        "LONG",
		"symbol":           "EURUSD",
		"confidence":       0.87,
		"grade":            "A",
		"risk_percentage":  1.0,
		"reasoning":        "Strong bullish structure with BMS on H4 and D1. Order block at 1.0995-1.1005 with FVG confluence. DXY bearish divergence supports EUR strength. COT positioning neutral. No high-impact events within lockout window.",
		"entry_price":      1.10000,
		"stop_loss":        1.09500,
		"take_profit":      1.11500,
		"rejection_rules":  []interface{}{},
		"entry_zone_low":   1.09950,
		"entry_zone_high":  1.10050,
		"tp1_price":        1.10500,
		"tp1_pct":          40.0,
		"tp2_price":        1.11000,
		"tp2_pct":          30.0,
		"tp3_price":        1.11500,
		"tp3_pct":          30.0,
		"trading_style":    "INTRADAY",
		"session":          "LONDON_NY_OVERLAP",
		"rr_ratio":         3.0,
		"confluence_score":  8.5,
		"analysis_id":      "SMC-EURUSD-H4-001",
		"execution_mode":   "LIMIT",
		"ltf_confirmed":    true,
		"setup_type":       "TURTLE_SOUP",
		"raw_response":     map[string]interface{}{},
	}
}

// ProcessorResponseNoSetup returns a processor response where the LLM
// determined there is no valid trade setup. The pipeline should complete
// with OutcomeNoSetup and NOT call the execution engine.
func ProcessorResponseNoSetup() map[string]interface{} {
	return map[string]interface{}{
		"trade_valid":     false,
		"direction":       "",
		"symbol":          "EURUSD",
		"confidence":      0.35,
		"grade":           "D",
		"reasoning":       "Insufficient confluence. H4 shows potential setup but D1 structure is ranging with no clear BMS. COT data unavailable. Risk environment unclear.",
		"rejection_rules": []interface{}{"INSUFFICIENT_CONFLUENCE", "NO_HTF_ALIGNMENT"},
		"raw_response":    map[string]interface{}{},
	}
}

// ProcessorResponseCounterTrend returns a processor response approving
// a counter-trend trade (SHORT against BULLISH trend). Used to test
// the MR-REJECT-006 guard (counter-trend without CHoCH = rejection).
func ProcessorResponseCounterTrend() map[string]interface{} {
	return map[string]interface{}{
		"trade_valid":       true,
		"direction":         "SHORT",
		"symbol":            "EURUSD",
		"confidence":        0.72,
		"grade":             "B",
		"risk_percentage":   0.5,
		"reasoning":         "Counter-trend short opportunity at H4 supply zone. Bearish engulfing with displacement.",
		"entry_price":       1.10500,
		"stop_loss":         1.11000,
		"take_profit":       1.09500,
		"rejection_rules":   []interface{}{},
		"entry_zone_low":    1.10450,
		"entry_zone_high":   1.10550,
		"tp1_price":         1.10000,
		"tp1_pct":           40.0,
		"tp2_price":         1.09750,
		"tp2_pct":           30.0,
		"tp3_price":         1.09500,
		"tp3_pct":           30.0,
		"trading_style":     "INTRADAY",
		"session":           "LONDON_OPEN",
		"rr_ratio":          2.0,
		"confluence_score":  6.5,
		"analysis_id":       "SMC-EURUSD-H4-CT-001",
		"execution_mode":    "LIMIT",
		"ltf_confirmed":     false,
		"setup_type":        "SUPPLY_ZONE",
		"raw_response":      map[string]interface{}{},
	}
}
