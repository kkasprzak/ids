"""Domain enums."""

from enum import StrEnum


class PositionType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class AlertSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ACTION_REQUIRED = "ACTION_REQUIRED"


class PositionLogStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class AlertKind(StrEnum):
    MISSING_STOP_LOSS = "MISSING_STOP_LOSS"
    STOP_LOSS_BREACH = "STOP_LOSS_BREACH"
    PROFIT_TAKE_OPPORTUNITY = "PROFIT_TAKE_OPPORTUNITY"
    CASH_RESERVE_BELOW_MINIMUM = "CASH_RESERVE_BELOW_MINIMUM"
