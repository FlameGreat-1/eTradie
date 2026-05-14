import type { TradingSystemProfile } from '../types';

/**
 * Sane default profile. Values are intentionally conservative so a
 * user who spam-clicks Next-through-the-stepper without making
 * meaningful choices still ends up with a non-dangerous configuration.
 *
 * In particular:
 *   - balanced confirmation (neither aggressive nor strict),
 *   - conservative risk appetite (server-side validation will then
 *     refuse a daily drawdown above 4%, which mirrors PRACTICE.md),
 *   - 1.5% per-trade risk, well below the 3% institutional ceiling,
 *   - 1:2 minimum RR (institutional floor for intraday),
 *   - manual_approval automation (never fully-automatic by default),
 *   - SMC + SnD frameworks selected (the engine's two flagship
 *     families; the LLM can rank either).
 *
 * schema_version is set by the backend on save; we initialise to 1
 * so the type is satisfied during local rendering.
 */
export function defaultTradingSystem(): TradingSystemProfile {
  return {
    schema_version: 1,
    identity: {
      experience: 'intermediate',
      automation: 'semi_automated',
      risk_appetite: 'balanced',
      trader_type: 'precision',
      discipline: 'rule_based',
    },
    style: 'intraday',
    sessions: {
      preferred_sessions: ['london', 'new_york'],
      avoid_low_liquidity: true,
      high_volatility_windows_only: false,
    },
    risk: {
      risk_model: 'fixed',
      fixed_risk_percent: 1.0,
      max_daily_drawdown_percent: 3.0,
      max_weekly_drawdown_percent: 6.0,
      max_simultaneous_trades: 3,
      max_correlated_exposure: 2,
      partial_take_profits: true,
      break_even_management: true,
      trailing_stop_enabled: true,
    },
    confirmation: 'balanced',
    structural: {
      frameworks: ['smc', 'snd'],
      use_fvg: true,
      use_order_blocks: true,
      use_choch_bms: true,
      use_idm: false,
      structure_emphasis: 'medium',
    },
    entry: {
      execution_mode: 'either_allowed',
      require_confirmation_candle: true,
      require_retest: false,
      require_liquidity_sweep: true,
      require_mtf_alignment: true,
    },
    filtering: {
      avoid_counter_trend: false,
      avoid_news_volatility: true,
      minimum_rr: 2.0,
      avoid_ranging_markets: true,
      avoid_overnight_holds: false,
      avoid_friday_trades: false,
      avoid_session_transitions: false,
    },
    psychology: {
      max_losses_before_cooldown: 3,
      cooldown_after_loss_streak: true,
      daily_lockout_after_target: false,
      revenge_trading_protection: true,
      overtrading_protection: true,
      emotional_volatility_sensitivity: 'medium',
    },
    confluence: {
      macro_alignment: 2,
      dxy: 2,
      cot: 1,
      htf_alignment: 3,
      wyckoff: 1,
      volume_liquidity: 2,
      session_timing: 2,
    },
    automation: {
      mode: 'manual_approval',
      require_final_confirmation: true,
      allow_unattended_execution: false,
    },
    assets: {
      asset_classes: ['forex'],
      preferred_pairs: [],
      avoid_highly_volatile: false,
      avoid_correlated_instruments: true,
    },
    goal: 'consistency',
    management: {
      partial_tp_style: 'balanced',
      trailing_stop: 'structure_based',
      break_even_trigger: 'at_tp1',
      scale_in_enabled: false,
      scale_out_enabled: true,
      hold_runners: true,
      close_before_news: true,
    },
  };
}
