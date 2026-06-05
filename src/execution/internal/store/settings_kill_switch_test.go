package store

import (
	"testing"

	"github.com/rs/zerolog"
)

// ── Kill-switch settings: validateSetting (CHECKLIST Section 8) ───────────

func TestValidateSetting_HaltKeys_AcceptBool(t *testing.T) {
	for _, key := range []string{KeyGlobalTradingHalted, KeyUserTradingHalted} {
		for _, v := range []string{"true", "false", "TRUE", "0", "1"} {
			if err := validateSetting(key, v); err != nil {
				t.Errorf("validateSetting(%q,%q) unexpected error: %v", key, v, err)
			}
		}
	}
}

func TestValidateSetting_HaltKeys_RejectNonBool(t *testing.T) {
	for _, key := range []string{KeyGlobalTradingHalted, KeyUserTradingHalted} {
		for _, v := range []string{"", "yes", "halt", "2", "on"} {
			if err := validateSetting(key, v); err == nil {
				t.Errorf("validateSetting(%q,%q) expected error, got nil", key, v)
			}
		}
	}
}

// ── Kill-switch settings: applySetting ───────────────────────────────

func TestApplySetting_GlobalHalted(t *testing.T) {
	s := &Settings{}
	applySetting(s, KeyGlobalTradingHalted, "true", zerolog.Nop())
	if !s.GlobalTradingHalted {
		t.Fatal("expected GlobalTradingHalted=true after applySetting")
	}
	applySetting(s, KeyGlobalTradingHalted, "false", zerolog.Nop())
	if s.GlobalTradingHalted {
		t.Fatal("expected GlobalTradingHalted=false after applySetting")
	}
}

func TestApplySetting_UserHalted(t *testing.T) {
	s := &Settings{}
	applySetting(s, KeyUserTradingHalted, "true", zerolog.Nop())
	if !s.UserTradingHalted {
		t.Fatal("expected UserTradingHalted=true after applySetting")
	}
}
