"""Cross-claim image reuse detection via perceptual-hash Hamming distance.

Pure, dependency-free logic: given an incoming ``phash`` and a set of stored
candidate hashes, decide whether the image has been reused from a *different*
account or claim and, if so, how strong the ``reused_score`` penalty should be.

Setting ``reused_score`` on the resulting ``ImageAnalysis`` is what drives
``ImageAuthenticitySignal`` to lower the trust score — this module never touches
the engine or the database directly.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


def hamming_distance(hex_a: str, hex_b: str) -> int:
    """Return the bit-level Hamming distance between two hex-encoded hashes.

    Raises ``ValueError`` if either hash is empty or they are different lengths,
    since only equal-width hashes are meaningfully comparable.
    """
    if not hex_a or not hex_b:
        raise ValueError("cannot compare empty hashes")
    if len(hex_a) != len(hex_b):
        raise ValueError(
            f"hash length mismatch: {len(hex_a)} != {len(hex_b)}"
        )
    return (int(hex_a, 16) ^ int(hex_b, 16)).bit_count()


@dataclass(frozen=True)
class ReuseMatch:
    """A stored image whose hash is within threshold of the incoming one."""

    evaluation_id: int
    account_id: str
    claim_id: str
    distance: int
    phash: str


def _is_legitimate_reupload(
    account_id: str, claim_id: str, cand_account: str, cand_claim: str
) -> bool:
    """True only when the same account resubmits the same claim.

    Requires both identifiers to be present and equal on each side; absent or
    unknown identifiers are treated as *not* legitimate so anonymous duplicates
    are still flagged (conservative, fraud-preventing default).
    """
    same_account = bool(account_id) and account_id == cand_account
    same_claim = bool(claim_id) and claim_id == cand_claim
    return same_account and same_claim


def detect_reuse(
    phash: str,
    account_id: str,
    claim_id: str,
    candidates: Iterable[Mapping[str, Any]],
    *,
    max_distance: int,
) -> tuple[float, list[ReuseMatch]]:
    """Score cross-account/claim reuse of ``phash`` against ``candidates``.

    Returns ``(reused_score, matches)`` where ``reused_score`` is in ``[0, 1]``
    (``1.0`` for an exact duplicate, decreasing toward ``0`` at ``max_distance``)
    and ``matches`` are the penalizable candidates within the threshold.
    """
    if not phash:
        return 0.0, []

    matches: list[ReuseMatch] = []
    reused_score = 0.0

    for candidate in candidates:
        cand_phash = str(candidate.get("phash", ""))
        if not cand_phash:
            continue
        try:
            distance = hamming_distance(phash, cand_phash)
        except ValueError:
            # Different-width hash (e.g. another provider) — not comparable.
            continue
        if distance > max_distance:
            continue

        cand_account = str(candidate.get("account_id", ""))
        cand_claim = str(candidate.get("claim_id", ""))
        if _is_legitimate_reupload(account_id, claim_id, cand_account, cand_claim):
            continue

        match = ReuseMatch(
            evaluation_id=int(candidate.get("evaluation_id", 0)),
            account_id=cand_account,
            claim_id=cand_claim,
            distance=distance,
            phash=cand_phash,
        )
        matches.append(match)

        # Closer matches penalize harder; exact match (distance 0) -> 1.0.
        score = 1.0 - distance / (max_distance + 1)
        reused_score = max(reused_score, score)

    return reused_score, matches
