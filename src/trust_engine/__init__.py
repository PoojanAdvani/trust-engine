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
from .reuse import ReuseMatch, detect_reuse, hamming_distance
from .vision import (
    AverageHashVisionProvider,
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
    "AverageHashVisionProvider",
    "CloudVisionProvider",
    "OnnxVisionProvider",
    "get_vision_provider",
    "hamming_distance",
    "detect_reuse",
    "ReuseMatch",
]
