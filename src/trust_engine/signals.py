"""Signal definitions used by the Trust Engine.

Each signal inspects a :class:`~trust_engine.models.TrustSubject` and returns a
:class:`~trust_engine.models.SignalResult` with a normalized score in
``[0.0, 1.0]`` (higher means more trustworthy) plus a human-readable reason.
Signals are intentionally small and independent so they can be composed,
re-weighted, or replaced without touching the engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .models import SignalResult, TrustSubject

# Severity assumed for a risk flag the engine does not explicitly know about.
DEFAULT_FLAG_SEVERITY = 0.5


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Constrain ``value`` to the ``[low, high]`` range."""
    return max(low, min(high, value))


@runtime_checkable
class Signal(Protocol):
    """Protocol implemented by every scoring signal."""

    name: str
    weight: float

    def evaluate(self, subject: TrustSubject) -> SignalResult: ...


@dataclass(frozen=True)
class AccountHistorySignal:
    """Rewards established, verified accounts and penalizes dispute history."""

    name: str = "account_history"
    weight: float = 1.0
    # Account age (days) at which the age component saturates to full credit.
    maturity_days: int = 365

    def evaluate(self, subject: TrustSubject) -> SignalResult:
        account = subject.account

        age_score = _clamp(account.account_age_days / self.maturity_days)
        verification = (
            0.5 * account.verified_email + 0.5 * account.verified_phone
        )

        # Disputes relative to total claims erode trust; a clean history is neutral.
        if account.prior_claims > 0:
            dispute_ratio = account.prior_disputes / account.prior_claims
        else:
            dispute_ratio = 0.0
        dispute_penalty = _clamp(dispute_ratio)

        raw = 0.5 * age_score + 0.3 * verification + 0.2 * (1.0 - dispute_penalty)
        score = _clamp(raw)

        reason = (
            f"age={account.account_age_days}d, "
            f"verified_email={account.verified_email}, "
            f"verified_phone={account.verified_phone}, "
            f"disputes={account.prior_disputes}/{account.prior_claims}"
        )
        return SignalResult(self.name, score, self.weight, reason)


@dataclass(frozen=True)
class ClaimDetailsSignal:
    """Scores the claim itself: documentation, recency, and amount."""

    name: str = "claim_details"
    weight: float = 1.0
    # Claim amount (currency units) at which the amount component bottoms out.
    high_amount: float = 10_000.0
    # Beyond this many days since the incident, recency credit is exhausted.
    stale_after_days: int = 90

    def evaluate(self, subject: TrustSubject) -> SignalResult:
        claim = subject.claim

        documentation = 1.0 if claim.has_documentation else 0.0

        # Prompt claims read as more trustworthy than long-delayed ones.
        recency = 1.0 - _clamp(claim.days_since_incident / self.stale_after_days)

        # Larger amounts carry more risk, so they contribute less trust.
        amount_score = 1.0 - _clamp(claim.amount / self.high_amount)

        raw = 0.5 * documentation + 0.25 * recency + 0.25 * amount_score
        score = _clamp(raw)

        reason = (
            f"documented={claim.has_documentation}, "
            f"days_since_incident={claim.days_since_incident}, "
            f"amount={claim.amount:g}"
        )
        return SignalResult(self.name, score, self.weight, reason)


@dataclass(frozen=True)
class RiskFlagsSignal:
    """Deducts trust for raised risk flags, weighted by severity.

    Starts from full trust (``1.0``) and subtracts the combined severity of all
    raised flags, so a subject with no flags is unaffected by this signal.
    """

    name: str = "risk_flags"
    weight: float = 1.5

    def evaluate(self, subject: TrustSubject) -> SignalResult:
        flags = subject.risk.flags

        if not flags:
            return SignalResult(self.name, 1.0, self.weight, "no risk flags raised")

        total_severity = sum(
            _clamp(severity if severity is not None else DEFAULT_FLAG_SEVERITY)
            for severity in flags.values()
        )
        score = _clamp(1.0 - total_severity)

        raised = ", ".join(sorted(flags))
        reason = f"{len(flags)} flag(s) raised: {raised}"
        return SignalResult(self.name, score, self.weight, reason)


@dataclass(frozen=True)
class ImageConditionSignal:
    """Scores the physical condition of an analyzed return photo.

    Higher ``damage_score`` (visible damage, spoilage, or wrong item) lowers
    trust. Neutral (``1.0``) when no photo was analyzed, mirroring
    :class:`RiskFlagsSignal`'s empty-input convention.
    """

    name: str = "image_condition"
    weight: float = 1.0

    def evaluate(self, subject: TrustSubject) -> SignalResult:
        image = subject.image

        if not image.analyzed:
            return SignalResult(
                self.name, 1.0, self.weight, "no photo analyzed", applicable=False
            )

        score = _clamp(1.0 - image.damage_score)
        reason = f"damage_score={image.damage_score:.2f} (provider={image.provider or 'unknown'})"
        return SignalResult(self.name, score, self.weight, reason)


@dataclass(frozen=True)
class ImageAuthenticitySignal:
    """Scores whether an analyzed photo is authentic vs synthetic/edited/reused.

    Trust is driven down by the most severe of the synthetic, edited, and reused
    likelihoods. Neutral (``1.0``) when no photo was analyzed.
    """

    name: str = "image_authenticity"
    weight: float = 2.0

    def evaluate(self, subject: TrustSubject) -> SignalResult:
        image = subject.image

        if not image.analyzed:
            return SignalResult(
                self.name, 1.0, self.weight, "no photo analyzed", applicable=False
            )

        components = {
            "synthetic": image.synthetic_score,
            "edited": image.edited_score,
            "reused": image.reused_score,
        }
        fraud = _clamp(max(components.values()))
        score = _clamp(1.0 - fraud)

        raised = ", ".join(
            f"{name}={value:.2f}"
            for name, value in sorted(components.items())
            if value > 0.0
        )
        reason = raised if raised else "no authenticity concerns"
        return SignalResult(self.name, score, self.weight, reason)


def default_signals() -> list[Signal]:
    """Return the standard signal set with default weights."""
    return [
        AccountHistorySignal(),
        ClaimDetailsSignal(),
        RiskFlagsSignal(),
        ImageConditionSignal(),
        ImageAuthenticitySignal(),
    ]
