"""Trust Engine — computing and managing trust scores."""

from .engine import TrustEngine
from .models import (
    AccountHistory,
    ClaimDetails,
    ImageAnalysis,
    RiskFlags,
    SignalResult,
    TrustBand,
    TrustScore,
    TrustSubject,
)
from .signals import (
    AccountHistorySignal,
    ClaimDetailsSignal,
    ImageAuthenticitySignal,
    ImageConditionSignal,
    RiskFlagsSignal,
    Signal,
    default_signals,
)
from .vision import (
    CloudVisionProvider,
    OnnxVisionProvider,
    StubVisionProvider,
    VisionProvider,
    get_vision_provider,
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
    "ImageAnalysis",
    "Signal",
    "AccountHistorySignal",
    "ClaimDetailsSignal",
    "RiskFlagsSignal",
    "ImageConditionSignal",
    "ImageAuthenticitySignal",
    "default_signals",
    "VisionProvider",
    "StubVisionProvider",
    "CloudVisionProvider",
    "OnnxVisionProvider",
    "get_vision_provider",
]
