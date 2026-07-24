"""Data models for Trust Engine inputs and outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True)
class AccountHistory:
    """Signals derived from a user's account and past behavior."""

    account_age_days: int = 0
    verified_email: bool = False
    verified_phone: bool = False
    prior_claims: int = 0
    prior_disputes: int = 0


@dataclass(frozen=True)
class ClaimDetails:
    """Attributes of the specific claim being evaluated."""

    amount: float = 0.0
    has_documentation: bool = False
    days_since_incident: int = 0
    category: str = "general"


@dataclass(frozen=True)
class RiskFlags:
    """Named risk indicators raised by upstream checks.

    ``flags`` maps a flag name to a severity in ``[0.0, 1.0]`` where ``1.0`` is
    the most severe. Unknown flags default to a moderate severity when scored.
    """

    flags: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Freeze into an immutable mapping so the frozen dataclass stays hashable
        # in spirit and callers cannot mutate shared state.
        object.__setattr__(self, "flags", dict(self.flags))

    @property
    def is_empty(self) -> bool:
        return not self.flags


@dataclass(frozen=True)
class ImageAnalysis:
    """Features extracted from a return photo by a vision provider.

    All scores are in ``[0.0, 1.0]`` where higher means *more* concerning. Only
    these lightweight features are carried on the subject (and thus persisted) —
    never the raw image bytes. When ``analyzed`` is ``False`` the image signals
    treat the subject as neutral.
    """

    analyzed: bool = False
    damage_score: float = 0.0      # visible damage / spoilage / wrong item
    synthetic_score: float = 0.0   # likelihood the image is AI-generated
    edited_score: float = 0.0      # likelihood the image was manipulated
    reused_score: float = 0.0      # likelihood the image was reused from the internet
    phash: str = ""                # perceptual hash for dedup / reuse detection
    provider: str = ""             # name of the provider that produced these features
    notes: str = ""                # optional human-readable detail


@dataclass(frozen=True)
class TrustSubject:
    """The full set of signals for one trust evaluation."""

    account: AccountHistory = field(default_factory=AccountHistory)
    claim: ClaimDetails = field(default_factory=ClaimDetails)
    risk: RiskFlags = field(default_factory=RiskFlags)
    image: ImageAnalysis = field(default_factory=ImageAnalysis)


class TrustBand(str, Enum):
    """Coarse trust classification derived from the numeric score."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class SignalResult:
    """The outcome of evaluating a single signal.

    ``applicable=False`` marks a signal that has no input to act on for this
    subject (e.g. an image signal when no photo was analyzed). The engine
    excludes such results from the weighted average so they neither inflate nor
    deflate the score.
    """

    name: str
    score: float  # normalized to [0.0, 1.0]
    weight: float
    reason: str
    applicable: bool = True


@dataclass(frozen=True)
class TrustScore:
    """Aggregate result of a trust evaluation."""

    value: float  # 0.0 - 100.0
    band: TrustBand
    results: tuple[SignalResult, ...]

    def explain(self) -> str:
        """Return a human-readable breakdown of the contributing signals."""
        lines = [f"Trust score: {self.value:.1f}/100 ({self.band.value})"]
        for r in self.results:
            lines.append(
                f"  - {r.name}: {r.score:.2f} (weight {r.weight:g}) - {r.reason}"
            )
        return "\n".join(lines)
