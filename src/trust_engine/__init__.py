"""Trust Engine — computing and managing trust scores."""

from .engine import TrustEngine
from .models import (
    AccountHistory,
    ClaimDetails,
    RiskFlags,
    SignalResult,
    TrustBand,
    TrustScore,
    TrustSubject,
)
from .signals import (
    AccountHistorySignal,
    ClaimDetailsSignal,
    RiskFlagsSignal,
    Signal,
    default_signals,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "TrustEngine",
    "TrustSubject",
    "TrustScore",
    "TrustBand",
    "SignalResult",
    "AccountHistory",
    "ClaimDetails",
    "RiskFlags",
    "Signal",
    "AccountHistorySignal",
    "ClaimDetailsSignal",
    "RiskFlagsSignal",
    "default_signals",
]
