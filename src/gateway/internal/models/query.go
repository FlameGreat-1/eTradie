package models

// RAGQueryParams holds the parameters for RAGOrchestrator.retrieve_context().
// Maps to: gateway/query_builder/builder.py (RAGQueryParams)
type RAGQueryParams struct {
	QueryText         string   `json:"query_text"`
	Strategy          string   `json:"strategy,omitempty"`
	Framework         string   `json:"framework,omitempty"`
	SetupFamily       string   `json:"setup_family,omitempty"`
	Direction         string   `json:"direction,omitempty"`
	Timeframe         string   `json:"timeframe,omitempty"`
	Style             string   `json:"style,omitempty"`
	Symbol            string   `json:"symbol,omitempty"`
	AllFrameworks     []string `json:"all_frameworks"`
	AllSetupFamilies  []string `json:"all_setup_families"`
	HasSMCCandidates  bool     `json:"has_smc_candidates"`
	HasSnDCandidates  bool     `json:"has_snd_candidates"`
	HasMacroData      bool     `json:"has_macro_data"`
	HasCOTData        bool     `json:"has_cot_data"`
	HasRateDecision   bool     `json:"has_rate_decision"`
	HasHighImpactEvent bool    `json:"has_high_impact_event"`
	HasDXYData        bool     `json:"has_dxy_data"`
}
