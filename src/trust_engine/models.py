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
class TrustSubject:
    """The full set of signals for one trust evaluation."""

    account: AccountHistory = field(default_factory=AccountHistory)
    claim: ClaimDetails = field(default_factory=ClaimDetails)
    risk: RiskFlags = field(default_factory=RiskFlags)


class TrustBand(str, Enum):
    """Coarse trust classification derived from the numeric score."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class SignalResult:
    """The outcome of evaluating a single signal."""

    name: str
    score: float  # normalized to [0.0, 1.0]
    weight: float
    reason: str


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
