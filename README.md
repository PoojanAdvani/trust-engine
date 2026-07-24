# Trust Engine

A Python engine for computing and managing trust scores.

## Overview

Trust Engine evaluates multiple trust signals — user account history, claim
details, and risk flags — and combines them into a single weighted trust score
(0–100) with a low/medium/high band and a human-readable explanation. It ships
with a FastAPI web service, YAML-based configuration, and a SQLite audit log of
every evaluation.

## Getting Started

### Requirements

- Python 3.11+

### Setup

```bash
python -m venv .venv
source .venv/bin/activate      # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Running

Run the demo evaluation:

```bash
python -m trust_engine
```

Serve the web API (Swagger UI at http://127.0.0.1:8000/docs):

```bash
trust-engine-api
```

### Testing

```bash
pytest
```

## API

- `POST /evaluate` — score a subject and log the result; returns the score,
  band, per-signal breakdown, explanation, and the audit `evaluation_id`.
- `GET /evaluations/{id}` — fetch a logged evaluation.
- `GET /evaluations?limit=N` — list recent evaluations, newest first.
- `GET /health` — liveness check.
- `GET /docs` — interactive Swagger UI.

## Configuration

Signal weights and trust-band cutoffs live in [`config.yaml`](config.yaml) and
are loaded at startup, so they can be tuned without code changes. Each signal
block also accepts that signal's tuning parameters (e.g. `maturity_days`). If
the file is absent, built-in defaults are used.

## Persistence

Every evaluation is written to a SQLite database (`trust_engine.db` by default)
capturing the full input payload, score, band, per-signal results, and
explanation for audit history.

## Project Structure

```
trust-engine/
├── src/
│   └── trust_engine/
│       ├── models.py     # Input/output data models
│       ├── signals.py    # Pluggable scoring signals
│       ├── engine.py     # TrustEngine aggregator
│       ├── config.py     # YAML config loader
│       ├── storage.py    # SQLite audit store
│       └── api.py        # FastAPI application
├── tests/                # Test suite
├── docs/                 # Documentation
├── config.yaml           # Signal weights & band cutoffs
├── pyproject.toml        # Project metadata & dependencies
└── README.md
```

## License

TBD
