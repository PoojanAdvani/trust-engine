# Trust Engine

[![CI](https://github.com/PoojanAdvani/trust-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/PoojanAdvani/trust-engine/actions/workflows/ci.yml)

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
- `POST /returns/evaluate` — verify an uploaded return photo (multipart) and
  score it through the full pipeline; returns the same fields plus the extracted
  `image` features. Accepts an optional `context_json` form field with the same
  shape as the `/evaluate` body.
- `GET /evaluations/{id}` — fetch a logged evaluation.
- `GET /evaluations?limit=N` — list recent evaluations, newest first.
- `GET /health` — liveness check.
- `GET /docs` — interactive Swagger UI.

## Image fraud detection (vision pipeline)

`POST /returns/evaluate` verifies return photos for two signals that feed the
same trust score:

- **`image_condition`** — visible damage, spoilage, or wrong item.
- **`image_authenticity`** — synthetic (AI-generated), edited, or reused-from-the-internet.

Vision analysis runs upstream in the async endpoint; only the extracted
*features* (scores + a perceptual hash) are carried on the subject and persisted
— **never the raw image bytes**. The two signals are neutral (excluded from the
average) for non-photo evaluations.

Backends are pluggable via a `VisionProvider`, selected by
`TRUST_ENGINE_VISION_PROVIDER`:

| Provider | Deps | Notes |
| -------- | ---- | ----- |
| `stub` (default) | none | Deterministic; for dev/tests. Keeps the base image slim. |
| `cloud` | `[vision]` (`httpx`) | Calls an external HTTP vision API (`TRUST_ENGINE_VISION_API_URL`/`_API_KEY`). |
| `onnx` | `[vision]` (`onnxruntime`, `opencv-python-headless`, `pillow`) | Local model at `TRUST_ENGINE_VISION_MODEL_PATH`. |

Install the heavy backends with `pip install .[vision]`, or build the dedicated
image: `docker build -f Dockerfile.vision -t trust-engine:vision .`

Example:

```bash
curl -F "file=@return.jpg;type=image/jpeg" http://127.0.0.1:8000/returns/evaluate
```

## Configuration

Signal weights and trust-band cutoffs live in [`config.yaml`](config.yaml) and
are loaded at startup, so they can be tuned without code changes. Each signal
block also accepts that signal's tuning parameters (e.g. `maturity_days`). If
the file is absent, built-in defaults are used.

### Environment variables

Runtime settings are read from the environment (or a local `.env` file):

| Variable                   | Default            | Purpose                          |
| -------------------------- | ------------------ | -------------------------------- |
| `TRUST_ENGINE_CONFIG_PATH` | `config.yaml`      | Path to the YAML config file     |
| `TRUST_ENGINE_DB_PATH`     | `trust_engine.db`  | Path to the SQLite audit database |
| `TRUST_ENGINE_API_KEY`     | _(unset)_          | Required API key; unset disables auth |
| `TRUST_ENGINE_VISION_PROVIDER` | `stub`         | Vision backend: `stub`, `cloud`, or `onnx` |
| `TRUST_ENGINE_VISION_API_URL`  | _(unset)_      | Cloud provider endpoint URL |
| `TRUST_ENGINE_VISION_API_KEY`  | _(unset)_      | Cloud provider API key |
| `TRUST_ENGINE_VISION_MODEL_PATH` | _(unset)_    | ONNX model path for the local provider |
| `TRUST_ENGINE_VISION_MAX_BYTES` | `8000000`     | Max accepted upload size (bytes) |

## Authentication

When `TRUST_ENGINE_API_KEY` is set, `/evaluate` and the `/evaluations` endpoints
require a matching `X-API-Key` request header (missing/invalid → `401`). The
`/health` and `/docs` endpoints stay public. If no key is configured,
authentication is disabled for local development.

## Persistence

Every evaluation is written to a SQLite database (`trust_engine.db` by default)
capturing the full input payload, score, band, per-signal results, and
explanation for audit history.

## Docker

Build and run the API in a container with [`docker-compose.yml`](docker-compose.yml):

```bash
docker compose up --build
```

The service listens on http://127.0.0.1:8000 (Swagger UI at `/docs`). The
SQLite audit database is persisted to `./data` on the host, and `./config.yaml`
is mounted read-only so weights/cutoffs can be changed without rebuilding. Set
`TRUST_ENGINE_API_KEY` in your shell (or a `.env` file) to require authentication.

The image is a multi-stage build on `python:3.13-slim` and runs uvicorn as a
non-root user.

## Project Structure

```
trust-engine/
├── src/
│   └── trust_engine/
│       ├── models.py     # Input/output data models
│       ├── signals.py    # Pluggable scoring signals (incl. image signals)
│       ├── engine.py     # TrustEngine aggregator
│       ├── config.py     # YAML config loader
│       ├── storage.py    # SQLite audit store
│       ├── vision.py     # Pluggable vision providers (stub/cloud/onnx)
│       ├── settings.py   # Environment configuration
│       └── api.py        # FastAPI application
├── tests/                # Test suite
├── docs/                 # Documentation
├── config.yaml           # Signal weights & band cutoffs
├── Dockerfile            # Slim base image (stub provider)
├── Dockerfile.vision     # Image with the [vision] extra
├── pyproject.toml        # Project metadata & dependencies
└── README.md
```

## License

TBD
