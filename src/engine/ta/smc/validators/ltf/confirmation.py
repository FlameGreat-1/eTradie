from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.session import SessionAnalyzer
from engine.ta.constants import Session, Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.liquidity_event import LiquiditySweep, InducementEvent
from engine.ta.models.structure_event import ChangeOfCharacter, BreakInMarketStructure
from engine.ta.models.zone import OrderBlock
from engine.ta.smc.config import SMCConfig

logger = get_logger(__name__)


class LTFConfirmationValidator:
    """
    Validates LTF confirmation requirements for SMC candidate eligibility.

    6 LTF Confirmations (all required for full confirmation):
    1. Liquidity has been taken (sweep completed, closed back inside)
    2. CHOCH on LTF (earliest signal of order flow shift)
    3. BMS confirmed on LTF (reversal direction confirmed)
    4. Price returns to LTF Order Block (RTO - entry point)
    5. Session timing (London 09:00-11:00 or NY 14:00-16:00 UTC+2)
    6. Inducement cleared (internal highs/lows swept before entry)

    IMPORTANT: LTF confirmation is for EXECUTION timing, not detection.
    A candidate is built regardless of LTF confirmation status.  When
    all 6 confirmations are present, ltf_confirmation=True and the
    execution engine can enter immediately.  When some are missing
    (e.g. price hasn't returned to the OB yet), ltf_confirmation=False
    and the execution engine monitors 24/7 until they are satisfied.
    """

    def __init__(
        self,
        config: SMCConfig,
        session_analyzer: SessionAnalyzer,
    ) -> None:
        self.config = config
        self.session_analyzer = session_analyzer
        self._logger = get_logger(__name__)

    def validate_liquidity_taken(
        self,
        sweep: Optional[LiquiditySweep],
    ) -> bool:
        """Confirmation 1: Liquidity has been taken."""
        if not sweep:
            return False

        return sweep.closed_back_inside

    def validate_choch_present(
        self,
        choch: Optional[ChangeOfCharacter],
        sweep: Optional[LiquiditySweep],
    ) -> bool:
        """Confirmation 2: CHOCH on LTF."""
        if not choch:
            return False

        # If no sweep, we can still validate CHOCH exists
        if not sweep:
            return True

        # Compare candle_index instead of timestamp, because multi-candle confirmations
        # could delay the official timestamp of the CHOCH past the sweep.
        return choch.candle_index >= sweep.candle_index

    def validate_bms_confirmed(
        self,
        bms: Optional[BreakInMarketStructure],
        choch: Optional[ChangeOfCharacter],
    ) -> bool:
        """Confirmation 3: BMS confirmed on LTF."""
        if not bms:
            return False

        # If no CHOCH yet, BMS alone is not sufficient for full confirmation
        if not choch:
            return False

        # Compare candle_index to decouple the actual breakout moment from the
        # variable delays caused by dynamic multi-candle confirmations.
        return (
            bms.candle_index >= choch.candle_index and bms.direction == choch.direction
        )

    def validate_rto_to_ob(
        self,
        ob: Optional[OrderBlock],
        bms: Optional[BreakInMarketStructure],
        current_price: float,
    ) -> bool:
        """Confirmation 4: Price returns to LTF Order Block."""
        if not ob or not bms:
            return False

        if ob.timestamp <= bms.timestamp:
            return False

        if ob.direction == Direction.BULLISH:
            return ob.lower_bound <= current_price <= ob.upper_bound
        else:
            return ob.lower_bound <= current_price <= ob.upper_bound

    def validate_session_timing(
        self,
        sequence: CandleSequence,
    ) -> bool:
        """Confirmation 5: Session timing (London/NY opens)."""
        if not self.config.require_session_timing:
            return True

        latest_candle = sequence.candles[-1]
        session_state = self.session_analyzer.identify_session(latest_candle.timestamp)

        valid_sessions = [Session.LONDON, Session.NEW_YORK, Session.OVERLAP_LONDON_NY]

        return session_state.active_session in valid_sessions

    def validate_inducement_cleared(
        self,
        inducement_events: list[InducementEvent],
        ob: Optional[OrderBlock],
    ) -> bool:
        """Confirmation 6: Inducement has been cleared."""
        if not ob:
            return False

        relevant_inducements = [
            idm
            for idm in inducement_events
            if idm.timestamp < ob.timestamp and idm.direction == ob.direction
        ]

        if not relevant_inducements:
            return True

        all_cleared = all(idm.cleared for idm in relevant_inducements)

        return all_cleared

    def validate_all_ltf_confirmations(
        self,
        sweep: Optional[LiquiditySweep],
        choch: Optional[ChangeOfCharacter],
        bms: Optional[BreakInMarketStructure],
        ob: Optional[OrderBlock],
        inducement_events: list[InducementEvent],
        sequence: CandleSequence,
        current_price: float,
    ) -> bool:
        """Validate all 6 LTF confirmations.

        Returns True only when ALL 6 confirmations are satisfied.
        Returns False (not an error) when any confirmation is missing,
        which simply means the execution engine should wait.
        """
        liquidity_ok = self.validate_liquidity_taken(sweep)
        choch_ok = self.validate_choch_present(choch, sweep)
        bms_ok = self.validate_bms_confirmed(bms, choch)
        rto_ok = self.validate_rto_to_ob(ob, bms, current_price)
        session_ok = self.validate_session_timing(sequence)
        inducement_ok = self.validate_inducement_cleared(inducement_events, ob)

        all_confirmed = (
            liquidity_ok
            and choch_ok
            and bms_ok
            and rto_ok
            and session_ok
            and inducement_ok
        )

        # Diagnostic logging at INFO level
        self._logger.info(
            "ltf_confirmation_result",
            extra={
                "symbol": sequence.symbol if hasattr(sequence, "symbol") else "unknown",
                "timeframe": str(
                    sequence.timeframe
                    if hasattr(sequence, "timeframe")
                    else "unknown"
                ),
                "liquidity_taken": liquidity_ok,
                "choch_present": choch_ok,
                "bms_confirmed": bms_ok,
                "rto_to_ob": rto_ok,
                "session_timing": session_ok,
                "inducement_cleared": inducement_ok,
                "all_confirmed": all_confirmed,
                "has_sweep": sweep is not None,
                "has_choch": choch is not None,
                "has_bms": bms is not None,
                "has_ob": ob is not None,
            },
        )

        return all_confirmed
