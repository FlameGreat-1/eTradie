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
    
    6 LTF Confirmations (all required):
    1. Liquidity has been taken (sweep completed, closed back inside)
    2. CHOCH on LTF (earliest signal of order flow shift)
    3. BMS confirmed on LTF (reversal direction confirmed)
    4. Price returns to LTF Order Block (RTO - entry point)
    5. Session timing (London 09:00-11:00 or NY 14:00-16:00 UTC+2)
    6. Inducement cleared (internal highs/lows swept before entry)
    
    No entry without all 6 confirmations.
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
        if not choch or not sweep:
            return False
        
        return choch.timestamp >= sweep.timestamp
    
    def validate_bms_confirmed(
        self,
        bms: Optional[BreakInMarketStructure],
        choch: Optional[ChangeOfCharacter],
    ) -> bool:
        """Confirmation 3: BMS confirmed on LTF."""
        if not bms or not choch:
            return False
        
        return bms.timestamp >= choch.timestamp and bms.direction == choch.direction
    
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
            idm for idm in inducement_events
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
        """Validate all 6 LTF confirmations."""
        if not self.validate_liquidity_taken(sweep):
            self._logger.debug("ltf_validation_failed_liquidity_not_taken")
            return False
        
        if not self.validate_choch_present(choch, sweep):
            self._logger.debug("ltf_validation_failed_no_choch")
            return False
        
        if not self.validate_bms_confirmed(bms, choch):
            self._logger.debug("ltf_validation_failed_bms_not_confirmed")
            return False
        
        if not self.validate_rto_to_ob(ob, bms, current_price):
            self._logger.debug("ltf_validation_failed_no_rto")
            return False
        
        if not self.validate_session_timing(sequence):
            self._logger.debug("ltf_validation_failed_session_timing")
            return False
        
        if not self.validate_inducement_cleared(inducement_events, ob):
            self._logger.debug("ltf_validation_failed_inducement_not_cleared")
            return False
        
        return True
