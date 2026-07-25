"""Tests for perceptual-hash Hamming matching and reuse detection."""

import pytest

from trust_engine.reuse import ReuseMatch, detect_reuse, hamming_distance


def test_hamming_identical_is_zero():
    assert hamming_distance("ffff", "ffff") == 0


def test_hamming_counts_differing_bits():
    # 0x0 vs 0x1 differs in one bit; 0x0 vs 0xf differs in four.
    assert hamming_distance("0", "1") == 1
    assert hamming_distance("0", "f") == 4


def test_hamming_rejects_empty():
    with pytest.raises(ValueError):
        hamming_distance("", "ffff")


def test_hamming_rejects_length_mismatch():
    with pytest.raises(ValueError):
        hamming_distance("ff", "ffff")


def _cand(phash, account_id="", claim_id="", evaluation_id=1):
    return {
        "phash": phash,
        "account_id": account_id,
        "claim_id": claim_id,
        "evaluation_id": evaluation_id,
    }


def test_detect_reuse_no_phash():
    score, matches = detect_reuse("", "A", "1", [_cand("ffff")], max_distance=10)
    assert score == 0.0
    assert matches == []


def test_exact_duplicate_cross_account_scores_full():
    candidates = [_cand("ffffffffffffffff", account_id="A", claim_id="1", evaluation_id=7)]
    score, matches = detect_reuse(
        "ffffffffffffffff", "B", "2", candidates, max_distance=10
    )
    assert score == 1.0
    assert len(matches) == 1
    assert isinstance(matches[0], ReuseMatch)
    assert matches[0].evaluation_id == 7
    assert matches[0].distance == 0


def test_near_duplicate_scaled_by_distance():
    # One differing bit within a threshold of 10.
    candidates = [_cand("fffffffffffffffe", account_id="A")]
    score, matches = detect_reuse(
        "ffffffffffffffff", "B", "1", candidates, max_distance=10
    )
    assert matches[0].distance == 1
    assert 0.0 < score < 1.0
    assert abs(score - (1.0 - 1 / 11)) < 1e-9


def test_beyond_threshold_no_match():
    # 0x0000... vs 0xffff... differ in 64 bits, well beyond threshold 10.
    candidates = [_cand("ffffffffffffffff", account_id="A")]
    score, matches = detect_reuse(
        "0000000000000000", "B", "1", candidates, max_distance=10
    )
    assert score == 0.0
    assert matches == []


def test_same_account_same_claim_is_ignored():
    candidates = [_cand("ffffffffffffffff", account_id="A", claim_id="1")]
    score, matches = detect_reuse(
        "ffffffffffffffff", "A", "1", candidates, max_distance=10
    )
    assert score == 0.0
    assert matches == []


def test_same_account_different_claim_is_penalized():
    candidates = [_cand("ffffffffffffffff", account_id="A", claim_id="1")]
    score, matches = detect_reuse(
        "ffffffffffffffff", "A", "2", candidates, max_distance=10
    )
    assert score == 1.0
    assert len(matches) == 1


def test_empty_ids_are_penalized():
    # Anonymous duplicates cannot be proven legitimate, so they are flagged.
    candidates = [_cand("ffffffffffffffff")]
    score, matches = detect_reuse(
        "ffffffffffffffff", "", "", candidates, max_distance=10
    )
    assert score == 1.0
    assert len(matches) == 1


def test_incomparable_hash_widths_skipped():
    candidates = [_cand("ffff", account_id="A")]  # 16-bit vs 64-bit incoming
    score, matches = detect_reuse(
        "ffffffffffffffff", "B", "1", candidates, max_distance=10
    )
    assert score == 0.0
    assert matches == []


def test_score_is_max_over_matches():
    candidates = [
        _cand("fffffffffffffff0", account_id="A"),  # distance 4
        _cand("ffffffffffffffff", account_id="A"),  # exact -> 1.0
    ]
    score, matches = detect_reuse(
        "ffffffffffffffff", "B", "1", candidates, max_distance=10
    )
    assert score == 1.0
    assert len(matches) == 2
