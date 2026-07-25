# Trust Engine — AI-Powered Instant Refund & Fraud Prevention for Quick-Commerce (Zomato Case Study)

[![CI](https://github.com/PoojanAdvani/trust-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/PoojanAdvani/trust-engine/actions/workflows/ci.yml)

**Author:** Poojan Advani · **Stack:** Python 3.11+ · FastAPI · ONNX Runtime · OpenCV · SQLite · Vanilla JS PWA

> An end-to-end system that verifies quick-commerce return photos with computer vision and a multi-signal trust score, then decides — in real time — whether to credit an **instant refund** or **flag the claim for review**.
>
> *Independent portfolio prototype and case study. Zomato branding is used illustratively; this project is not affiliated with or endorsed by Zomato.*

---

## Executive Overview

Quick-commerce lives or dies on **speed of resolution**. When a customer reports a
damaged or spoiled order, every minute of friction — forms, agents, "we'll get
back to you" — erodes retention and lifetime value. The industry answer is the
**instant refund**: credit the customer immediately, no questions asked.

That convenience creates the opposite problem: **revenue leakage from refund
fraud**. Bad actors reuse the same "damaged item" photo across accounts, submit
AI-generated or edited images, or file claims for orders that were perfectly
fine. A no-questions-asked refund policy is, by construction, a no-questions-asked
fraud policy.

**Trust Engine resolves the trade-off instead of picking a side.** It keeps the
refund *instant for the honest majority* while pricing risk on every claim in
milliseconds:

- **Low friction where it's safe** — a verified account with a clear, authentic
  photo of genuinely damaged food is credited on the spot.
- **A speed bump where it isn't** — a reused photo, a synthetic image, or a
  low-trust account is transparently routed to manual review before any money
  moves.

The result is a policy that is simultaneously **customer-friendly** (instant for
the 95% acting in good faith) and **margin-protective** (fraud is caught at the
point of claim, not discovered in a month-end reconciliation).

---

## Product Highlights

| Capability | What it delivers |
| ---------- | ---------------- |
| **Authentic 3-Screen Zomato UX** | A high-fidelity consumer flow — **Home → Order Details → Verification** — with a branded header, bottom tab bar (Home / Delivery / Orders), and smooth screen transitions, served straight from FastAPI at `GET /app`. |
| **Privacy-First WebRTC Camera Hygiene** | The webcam is **never started on page load** — it initializes only when the user taps *Open Camera*, and all video tracks are **torn down the instant a photo is snapped** (`getTracks().forEach(t => t.stop())`), so the hardware and its indicator light turn off immediately. |
| **Pre-flight Client Luminance Gate** | Before a byte hits the network, the image is sampled on a canvas and its average luminance computed. **Pitch-black / blank images (luminance < 15) are rejected client-side** with a clear prompt — no wasted round trip, no garbage claims. |
| **ONNX Vision Pipeline** | A pluggable `OnnxVisionProvider` decodes and normalizes the photo to a `1×3×224×224` tensor and runs **local damage / synthetic classification** via ONNX Runtime, plus a **64-bit perceptual hash (pHash)** for cross-claim reuse detection. Falls back gracefully to OpenCV/Pillow heuristics when no model is configured. |
| **Pure, Synchronous, I/O-Free Core** | The scoring engine is a **deterministic, side-effect-free** weighted evaluation of **5 signals**. All heavy/remote work (vision, DB, hashing) happens upstream in the async API layer, keeping the core trivially testable and reasoned-about. |
| **Persistent Audit Logging** | Every evaluation — full input payload, score, band, per-signal breakdown, and explanation — is written to **SQLite** and retrievable at `GET /evaluations/{id}`, giving operations a complete, queryable trail for every refund decision. |

---

## System Architecture & 5-Signal Breakdown

### Request flow

```
                       ┌───────────────────────────────────────────────┐
                       │  Consumer PWA  (GET /app)                      │
                       │  Home ──► Order Details ──► Verification        │
                       │  • deferred WebRTC camera + track teardown      │
                       │  • client luminance gate (< 15 → reject)        │
                       └───────────────────────┬───────────────────────┘
                                               │  multipart: file + context_json
                                               ▼
                       ┌───────────────────────────────────────────────┐
                       │  FastAPI  ·  POST /returns/evaluate  (async)    │
                       └───────────────────────┬───────────────────────┘
                                               ▼
        ┌───────────────────────────┐   features   ┌──────────────────────────────┐
        │  Vision Provider (ONNX)    │─────────────►│  Reuse Detection             │
        │  decode → 224×224 tensor   │  damage,     │  pHash Hamming distance vs.  │
        │  → onnxruntime inference   │  synthetic,  │  image_analyses history      │
        │  → damage / synthetic      │  pHash       │  → reused_score (x-account)  │
        │  (heuristic fallback)      │              └──────────────┬───────────────┘
        └────────────────────────────┘                             ▼
                                          ┌──────────────────────────────────────┐
                                          │  TrustSubject (account, claim, risk,  │
                                          │                image features)        │
                                          └──────────────────┬────────────────────┘
                                                             ▼
                              ┌────────────────────────────────────────────────┐
                              │  Trust Engine — PURE, SYNC, I/O-FREE            │
                              │  weighted avg of 5 signals → value 0–100 + band │
                              └──────────────────┬─────────────────────────────┘
                                                 ▼
                    ┌───────────────────────────────┐     ┌──────────────────────┐
                    │  SQLite audit log             │     │  Resolution Card      │
                    │  evaluations + image_analyses │◄────│  Instant Refund ✔     │
                    │  GET /evaluations/{id}        │     │  vs. Flagged ⚠         │
                    └───────────────────────────────┘     └──────────────────────┘
```

### The 5 signals

Each signal returns a normalized score in **`[0.0, 1.0]`** (higher = more
trustworthy). The engine combines them as a **weighted average**, scales to
`0–100`, and buckets the result into a trust band.

| # | Signal | Weight | Measures | Score formula (normalized `[0,1]`) |
| - | ------ | :----: | -------- | ---------------------------------- |
| 1 | `account_history` | **1.0** | Account age, email/phone verification, dispute ratio | `0.5·age + 0.3·verification + 0.2·(1 − disputeRatio)` |
| 2 | `claim_details` | **1.0** | Documentation, recency, claim amount | `0.5·documented + 0.25·recency + 0.25·(1 − amountRisk)` |
| 3 | `risk_flags` | **1.5** | Upstream fraud flags, by severity | `1 − Σ severity` |
| 4 | `image_condition` | **1.0** | Visible damage / spoilage / wrong item | `1 − damage_score` |
| 5 | `image_authenticity` | **2.0** | Synthetic / edited / reused photo | `1 − max(synthetic, edited, reused)` |

**Aggregation.** For the set of *applicable* signals *S* (image signals are
excluded, not zeroed, when no photo was analyzed):

```
              Σ_{i∈S} (scoreᵢ × weightᵢ)
value = 100 × ─────────────────────────────
                   Σ_{i∈S} weightᵢ
```

**Trust bands** (`config.yaml`, tunable without code changes):

| Band | Condition |
| ---- | --------- |
| 🟢 **HIGH** | `value ≥ 70` |
| 🟡 **MEDIUM** | `40 ≤ value < 70` |
| 🔴 **LOW** | `value < 40` |

> With a photo present, total weight is **6.5** (all 5 signals). For the JSON-only
> `POST /evaluate` path with no photo, image signals drop out and total weight is
> **3.5** — so non-photo scoring is never diluted by neutral image signals.

---

## Local Setup & Usage

**Requirements:** Python 3.11+ (CI and containers pin 3.13).

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 2. Install (with the ONNX vision stack)

```bash
pip install -e ".[dev,vision]"
```

The `vision` extra pulls `onnxruntime`, `opencv-python-headless`, `pillow`, and
`numpy`. Omit it (`pip install -e ".[dev]"`) for the dependency-free default
provider.

### 3. Enable the ONNX vision provider

```bash
export TRUST_ENGINE_VISION_PROVIDER=onnx                       # Windows: $env:TRUST_ENGINE_VISION_PROVIDER="onnx"
export TRUST_ENGINE_VISION_MODEL_PATH=/path/to/model.onnx      # optional — omit to use heuristic fallback
```

If no model path is set (or the model fails to load), the provider **gracefully
falls back** to OpenCV/Pillow heuristics (Canny edge density → damage, Laplacian
variance → synthetic) and records the reason in the evaluation notes.

### 4. Launch with Uvicorn on port 8000

```bash
uvicorn trust_engine.api:create_app --factory --host 0.0.0.0 --port 8000
```

Then open:

- **Consumer app:** http://127.0.0.1:8000/app
- **Swagger UI:** http://127.0.0.1:8000/docs

### 5. Run the test suite

```bash
pytest -q                # full suite
pytest -m vision -q      # ONNX / OpenCV vision-provider tests (needs the [vision] extra)
```

### Configuration (environment variables)

All settings are read from `TRUST_ENGINE_*` env vars (or a local `.env`):

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `TRUST_ENGINE_VISION_PROVIDER` | `stub` | `stub` · `ahash` · `cloud` · `onnx` |
| `TRUST_ENGINE_VISION_MODEL_PATH` | _(unset)_ | ONNX model for the `onnx` provider |
| `TRUST_ENGINE_PHASH_HAMMING_THRESHOLD` | `10` | Max bit distance counted as an image reuse match |
| `TRUST_ENGINE_DB_PATH` | `trust_engine.db` | SQLite audit database path |
| `TRUST_ENGINE_API_KEY` | _(unset)_ | Require `X-API-Key`; unset ⇒ auth disabled |
| `TRUST_ENGINE_VISION_MAX_BYTES` | `8000000` | Max accepted upload size |

---

## API Reference

Base URL: `http://127.0.0.1:8000`. When `TRUST_ENGINE_API_KEY` is set, scoring and
audit endpoints require a matching **`X-API-Key`** header; `/health` and `/docs`
stay public.

### `POST /returns/evaluate`

Verify an uploaded return photo and score it through the full pipeline.
**Content-Type:** `multipart/form-data`.

| Field | Type | Description |
| ----- | ---- | ----------- |
| `file` | file *(required)* | The return photo (`image/*`, ≤ `VISION_MAX_BYTES`). |
| `context_json` | string *(optional)* | JSON with `account` / `claim` / `risk`, e.g. account & claim IDs for cross-account reuse detection. |

```bash
curl -F "file=@damaged.jpg;type=image/jpeg" \
     -F 'context_json={"account":{"account_id":"acct_42"},"claim":{"claim_id":"clm_9"}}' \
     http://127.0.0.1:8000/returns/evaluate
```

**`200 OK`**

```json
{
  "evaluation_id": 12,
  "value": 82.4,
  "band": "high",
  "results": [
    { "name": "account_history",    "score": 0.90, "weight": 1.0, "reason": "…", "applicable": true },
    { "name": "claim_details",      "score": 0.75, "weight": 1.0, "reason": "…", "applicable": true },
    { "name": "risk_flags",         "score": 1.00, "weight": 1.5, "reason": "no risk flags raised", "applicable": true },
    { "name": "image_condition",    "score": 0.60, "weight": 1.0, "reason": "damage_score=0.40 …", "applicable": true },
    { "name": "image_authenticity", "score": 0.95, "weight": 2.0, "reason": "…", "applicable": true }
  ],
  "explanation": "Trust score: 82.4/100 (high) …",
  "image": {
    "analyzed": true, "damage_score": 0.40, "synthetic_score": 0.05,
    "edited_score": 0.0, "reused_score": 0.0, "phash": "c1a2…", "provider": "onnx", "notes": "onnx inference (…)"
  },
  "reuse_matches": 0
}
```

Error responses: `415` (non-image upload), `413` (too large), `422` (invalid
`context_json`), `401` (missing/invalid API key when auth is enabled).

### `GET /evaluations/{id}`

Fetch a single logged evaluation for audit — including the full input payload,
score, band, per-signal results, and explanation.

```bash
curl http://127.0.0.1:8000/evaluations/12
```

**`200 OK`**

```json
{
  "id": 12,
  "created_at": "2026-07-25T12:00:00+00:00",
  "payload": { "account": { … }, "claim": { … }, "risk": { … }, "image": { … } },
  "score": 82.4,
  "band": "high",
  "results": [ … ],
  "explanation": "Trust score: 82.4/100 (high) …"
}
```

Returns `404` if the evaluation id does not exist. *(Related: `GET /evaluations?limit=N`
lists recent evaluations, newest first.)*

### `GET /health`

Public, unauthenticated liveness probe used by Docker/CI healthchecks.

```bash
curl http://127.0.0.1:8000/health
```

**`200 OK`**

```json
{ "status": "ok", "evaluations_logged": 12 }
```

---

## Project at a Glance

```
src/trust_engine/
├── models.py     # Frozen dataclasses: TrustSubject, ImageAnalysis, SignalResult, …
├── signals.py    # The 5 pure scoring signals + registry
├── engine.py     # Weighted-average aggregation → TrustScore (pure, sync)
├── config.py     # YAML-driven weights & band cutoffs
├── vision.py     # Pluggable providers: stub · ahash · cloud · onnx
├── reuse.py      # Perceptual-hash Hamming matching (cross-claim reuse)
├── storage.py    # SQLite audit log (evaluations + image_analyses)
├── settings.py   # Environment configuration
└── api.py        # FastAPI app, /returns/evaluate, audit endpoints, /app UI
frontend/index.html   # 3-screen Zomato consumer PWA
```

Continuous integration runs the full test suite, a `[vision]`-extra job, and a
Docker build-and-smoke-test on every push and pull request.
