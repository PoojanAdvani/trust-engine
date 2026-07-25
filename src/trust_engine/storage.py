"""SQLite persistence for evaluation audit history.

Every evaluation is logged with its full input payload, the computed score and
band, the per-signal breakdown, and the rendered explanation, so past decisions
can be reviewed and audited.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import TrustScore, TrustSubject

_SCHEMA = """
CREATE TABLE IF NOT EXISTS evaluations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT    NOT NULL,
    payload     TEXT    NOT NULL,
    score       REAL    NOT NULL,
    band        TEXT    NOT NULL,
    results     TEXT    NOT NULL,
    explanation TEXT    NOT NULL
)
"""

# Additive table for cross-claim image reuse lookups. Created alongside
# `evaluations`; because it uses IF NOT EXISTS it never migrates existing tables.
_IMAGE_SCHEMA = """
CREATE TABLE IF NOT EXISTS image_analyses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_id INTEGER NOT NULL,
    created_at    TEXT    NOT NULL,
    phash         TEXT    NOT NULL,
    account_id    TEXT    NOT NULL DEFAULT '',
    claim_id      TEXT    NOT NULL DEFAULT '',
    provider      TEXT    NOT NULL DEFAULT ''
)
"""

_IMAGE_PHASH_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_image_analyses_phash "
    "ON image_analyses(phash)"
)


class EvaluationStore:
    """Append-only log of trust evaluations backed by SQLite."""

    def __init__(self, db_path: str | Path = "trust_engine.db") -> None:
        self.db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(_SCHEMA)
            conn.execute(_IMAGE_SCHEMA)
            conn.execute(_IMAGE_PHASH_INDEX)

    def log(self, subject: TrustSubject, score: TrustScore) -> int:
        """Persist one evaluation and return its new row id."""
        created_at = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(asdict(subject))
        results = json.dumps([asdict(r) for r in score.results])

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO evaluations
                    (created_at, payload, score, band, results, explanation)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    payload,
                    score.value,
                    score.band.value,
                    results,
                    score.explain(),
                ),
            )
            return int(cursor.lastrowid)

    def get(self, evaluation_id: int) -> dict[str, Any] | None:
        """Return a single evaluation record, or ``None`` if not found."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM evaluations WHERE id = ?", (evaluation_id,)
            ).fetchone()
        return self._row_to_record(row) if row else None

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent evaluations, newest first."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM evaluations ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def count(self) -> int:
        """Return the total number of logged evaluations."""
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0])

    def record_image_hash(
        self,
        evaluation_id: int,
        phash: str,
        account_id: str = "",
        claim_id: str = "",
        provider: str = "",
    ) -> None:
        """Record an image's perceptual hash for future reuse lookups.

        No-op when ``phash`` is empty (e.g. a provider that produced no hash).
        """
        if not phash:
            return
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO image_analyses
                    (evaluation_id, created_at, phash, account_id, claim_id, provider)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (evaluation_id, created_at, phash, account_id, claim_id, provider),
            )

    def fetch_image_hashes(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Return stored image-hash records (newest first) for reuse matching."""
        query = (
            "SELECT id, evaluation_id, created_at, phash, account_id, claim_id, "
            "provider FROM image_analyses ORDER BY id DESC"
        )
        params: tuple[Any, ...] = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "payload": json.loads(row["payload"]),
            "score": row["score"],
            "band": row["band"],
            "results": json.loads(row["results"]),
            "explanation": row["explanation"],
        }
