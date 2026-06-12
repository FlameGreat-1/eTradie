from datetime import UTC, datetime, timedelta

from engine.shared.exceptions import ProviderValidationError
from engine.shared.logging import get_logger
from engine.ta.constants import TIMEFRAME_MINUTES, Timeframe
from engine.ta.models.candle import Candle, CandleSequence

logger = get_logger(__name__)


class BrokerDataValidator:
    def __init__(
        self,
        *,
        max_gap_multiplier: float = 2.0,
        min_candles_required: int = 1,
    ) -> None:
        self.max_gap_multiplier = max_gap_multiplier
        self.min_candles_required = min_candles_required

    def validate_candle(self, candle: Candle) -> None:
        if candle.high < candle.low:
            raise ProviderValidationError(
                "Invalid candle: high < low",
                details={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                    "high": candle.high,
                    "low": candle.low,
                },
            )

        if candle.open <= 0 or candle.close <= 0:
            raise ProviderValidationError(
                "Invalid candle: open or close <= 0",
                details={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                    "open": candle.open,
                    "close": candle.close,
                },
            )

        if candle.high < candle.open or candle.high < candle.close:
            raise ProviderValidationError(
                "Invalid candle: high < open or close",
                details={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                    "high": candle.high,
                    "open": candle.open,
                    "close": candle.close,
                },
            )

        if candle.low > candle.open or candle.low > candle.close:
            raise ProviderValidationError(
                "Invalid candle: low > open or close",
                details={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                    "low": candle.low,
                    "open": candle.open,
                    "close": candle.close,
                },
            )

        if candle.volume < 0:
            raise ProviderValidationError(
                "Invalid candle: volume < 0",
                details={
                    "symbol": candle.symbol,
                    "timestamp": candle.timestamp.isoformat(),
                    "volume": candle.volume,
                },
            )

    def validate_sequence(self, sequence: CandleSequence) -> None:
        if sequence.count < self.min_candles_required:
            raise ProviderValidationError(
                f"Insufficient candles: got {sequence.count}, required {self.min_candles_required}",
                details={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                    "count": sequence.count,
                    "required": self.min_candles_required,
                },
            )

        for candle in sequence.candles:
            self.validate_candle(candle)

        self._validate_timestamp_continuity(sequence)

        self._validate_symbol_consistency(sequence)

        self._validate_timeframe_consistency(sequence)

    def _validate_timestamp_continuity(self, sequence: CandleSequence) -> None:
        if sequence.count < 2:
            return

        timeframe_minutes = TIMEFRAME_MINUTES.get(sequence.timeframe)
        if timeframe_minutes is None:
            raise ProviderValidationError(
                f"Unknown timeframe: {sequence.timeframe}",
                details={"timeframe": sequence.timeframe},
            )

        # Special handling for monthly timeframes (MN1)
        # Months can have 28, 29, 30, or 31 days
        is_monthly = sequence.timeframe == Timeframe.MN1

        if is_monthly:
            # For monthly candles, validate range is 28-31 days
            min_monthly_delta = timedelta(days=28)  # February (non-leap year)
            max_monthly_delta = timedelta(days=31)  # Jan, Mar, May, Jul, Aug, Oct, Dec
            # Allow up to 2x for gap detection (62 days = ~2 months)
            max_allowed_gap = timedelta(days=62)
        else:
            # Standard validation for other timeframes
            expected_delta = timedelta(minutes=timeframe_minutes)
            max_allowed_gap = timedelta(minutes=int(timeframe_minutes * self.max_gap_multiplier))

        for i in range(1, len(sequence.candles)):
            prev_candle = sequence.candles[i - 1]
            curr_candle = sequence.candles[i]

            actual_delta = curr_candle.timestamp - prev_candle.timestamp

            # Validate based on timeframe type
            if is_monthly:
                # Monthly validation: must be between 28-31 days
                if actual_delta < min_monthly_delta:
                    raise ProviderValidationError(
                        "Monthly candles too close together",
                        details={
                            "symbol": sequence.symbol,
                            "timeframe": sequence.timeframe,
                            "prev_timestamp": prev_candle.timestamp.isoformat(),
                            "curr_timestamp": curr_candle.timestamp.isoformat(),
                            "actual_delta_days": actual_delta.total_seconds() / 86400,
                            "min_expected_days": 28,
                            "max_expected_days": 31,
                        },
                    )

                if actual_delta > max_monthly_delta and actual_delta <= max_allowed_gap:
                    # Delta is slightly over 31 days but within gap tolerance
                    # This can happen with incomplete current month or timezone issues
                    # Log as warning but don't fail
                    logger.warning(
                        "broker_monthly_candle_spacing_irregular",
                        extra={
                            "symbol": sequence.symbol,
                            "timeframe": sequence.timeframe,
                            "prev_timestamp": prev_candle.timestamp.isoformat(),
                            "curr_timestamp": curr_candle.timestamp.isoformat(),
                            "actual_delta_days": actual_delta.total_seconds() / 86400,
                            "expected_range_days": "28-31",
                        },
                    )
            # Standard timeframe validation
            elif actual_delta < expected_delta:
                raise ProviderValidationError(
                    "Candles too close together",
                    details={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe,
                        "prev_timestamp": prev_candle.timestamp.isoformat(),
                        "curr_timestamp": curr_candle.timestamp.isoformat(),
                        "actual_delta_minutes": actual_delta.total_seconds() / 60,
                        "expected_delta_minutes": timeframe_minutes,
                    },
                )

            # Gap detection (applies to all timeframes)
            if actual_delta > max_allowed_gap:
                logger.warning(
                    "broker_data_gap_detected",
                    extra={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe,
                        "prev_timestamp": prev_candle.timestamp.isoformat(),
                        "curr_timestamp": curr_candle.timestamp.isoformat(),
                        "gap_minutes": actual_delta.total_seconds() / 60,
                        "max_allowed_minutes": max_allowed_gap.total_seconds() / 60,
                    },
                )

    def _validate_symbol_consistency(self, sequence: CandleSequence) -> None:
        symbols = {candle.symbol for candle in sequence.candles}

        if len(symbols) > 1:
            raise ProviderValidationError(
                "Multiple symbols in sequence",
                details={
                    "expected_symbol": sequence.symbol,
                    "found_symbols": list(symbols),
                },
            )

        if sequence.symbol not in symbols:
            raise ProviderValidationError(
                "Sequence symbol mismatch",
                details={
                    "sequence_symbol": sequence.symbol,
                    "candle_symbols": list(symbols),
                },
            )

    def _validate_timeframe_consistency(self, sequence: CandleSequence) -> None:
        timeframes = {candle.timeframe for candle in sequence.candles}

        if len(timeframes) > 1:
            raise ProviderValidationError(
                "Multiple timeframes in sequence",
                details={
                    "expected_timeframe": sequence.timeframe,
                    "found_timeframes": [str(tf) for tf in timeframes],
                },
            )

        if sequence.timeframe not in timeframes:
            raise ProviderValidationError(
                "Sequence timeframe mismatch",
                details={
                    "sequence_timeframe": sequence.timeframe,
                    "candle_timeframes": [str(tf) for tf in timeframes],
                },
            )

    def validate_time_range(
        self,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> None:
        if start_time is not None and end_time is not None:
            if end_time <= start_time:
                raise ProviderValidationError(
                    "End time must be after start time",
                    details={
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                    },
                )

            _now = datetime.now(UTC) if end_time.tzinfo else datetime.now()
            if end_time > _now:
                raise ProviderValidationError(
                    "End time cannot be in the future",
                    details={
                        "end_time": end_time.isoformat(),
                        "now": _now.isoformat(),
                    },
                )
