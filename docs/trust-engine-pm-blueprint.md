# Trust Engine — PM Case Study Blueprint

**Instant refunds for honest customers. A speed bump for fraud.**
Poojan Advani · Product Case Study · Quick-commerce refund verification

> Drop-in content blueprint (9 modular slides) for Gamma / Canva / any deck builder.
> All numeric targets below are **design SLAs and thresholds**, not measured results or user research.

---

## Slide 1 — The Quick-Commerce Refund Dilemma

**Subhead:** One refund policy can't be both fast and safe. Trust Engine scores every claim in-flight so you don't have to choose.

**Two-card split — the trade-off today**

| Zero-friction refunds | Review everything |
| --- | --- |
| **Win:** money back in seconds, high CSAT, retention | **Win:** fraud drops, spend controlled |
| **Cost:** refund leakage, policy-gaming, reused photos | **Cost:** honest customers wait, agent queues grow |

**Thesis strip (one line, full width)**
> Pay the honest instantly. Slow down only the suspicious. Prove every decision.

**What it is (4 chips)**
`5-signal risk score` · `client-side darkness gate` · `photo-reuse detection (pHash)` · `configurable trust bands`

---

## Slide 2 — Problem Framing Canvas

**Subhead:** Is this a real problem worth solving now?

**5-cell canvas grid**

| True problem | Abuse evidence |
| --- | --- |
| A single refund policy is forced to be either fast **or** safe — today teams pick one and pay for the other. | The same "damaged item" photo reused across accounts; "no-questions" policies circulated and gamed; refund/return abuse is an industry-recognized loss line; genuine claims still queue behind manual checks. |

| Value — honest users | Value — business |
| --- | --- |
| Money back in seconds, no forms, no back-and-forth. | Less paid on fake claims, fewer manual reviews, protected margin, retained trust. |

**Why solve now (full-width card)**
- Quick-commerce claim volume is scaling; manual review does not scale with it.
- Photo-backed claims are already the norm — the signal is there to use.
- On-device photo checks + image fingerprinting make in-flight verification fast and cheap.

---

## Slide 3 — Personas

**Subhead:** Two customers on the same app with opposite intent, and the two teams caught in between.

**2×2 persona grid** — each card: *Goal · Pain · What Trust Engine does*

| **Honest customer** | **Refund abuser** |
| --- | --- |
| **Goal:** fast refund when food arrives damaged | **Goal:** extract refunds on fine orders |
| **Pain:** treated like a suspect, made to wait | **Pain (for us):** reuses one photo across accounts |
| **We give them:** instant credit, no friction | **We give them:** a fingerprint match → review |

| **Support ops agent** | **Finance / risk owner** |
| --- | --- |
| **Goal:** resolve real issues quickly | **Goal:** cut refund leakage without hurting CSAT |
| **Pain:** buried in claims that are mostly genuine | **Pain:** refund cost rising with volume |
| **We give them:** only the risky few, with context | **We give them:** measurable leakage control + audit trail |

---

## Slide 4 — Core Product: 5-Signal Scoring & Policy Bands

**Subhead:** Every claim gets a 0–100 trust score from five weighted checks, then a policy band decides the route.

**Card A — the five signals (table)**

| Signal | What it asks | Weight |
| --- | --- | :--: |
| Account history | Is this a normal, established account? | 1.0 |
| Claim details | Does the claim make sense — amount, timing, proof? | 1.0 |
| Risk flags | Anything upstream already flagged? | 1.5 |
| Photo condition | Does the photo show real damage/spoilage? | 1.0 |
| Photo authenticity | Genuine photo — not edited, generated, or reused? | **2.0** |

*Score = weighted average of applicable signals → 0–100. Photo authenticity carries the most weight — that's where fraud hides. Photo signals apply only when a photo was analyzed.*

**Card B — policy bands (table)**

| Band | Score | Action |
| --- | :--: | --- |
| 🟢 High trust | ≥ 70 | **Auto-credit** on the spot |
| 🟡 Medium trust | 40–69 | Route to **manual review** |
| 🔴 Low trust | < 40 | Route to **priority review** |

*Never auto-decline — a low score means a human looks, not "denied." Weights and cutoffs are configuration, tuned without code changes.*

---

## Slide 5 — 3-Layer System Architecture

**Subhead:** A thin user layer, a deterministic scoring layer, and an auditable data layer.

**Layer diagram (top → down, with the decision returning to the user)**

```
┌─ USER LAYER ─────────────────────────────────────────────┐
│ Consumer PWA (3 screens) · camera + darkness gate ·       │
│ instant-resolution card    →   POST /returns/evaluate     │
└───────────────────────────────┬──────────────────────────┘
                                 ▼
┌─ SCORING LOGIC LAYER ────────────────────────────────────┐
│ Vision check (damage + authenticity, heuristic fallback)  │
│      →  photo-reuse check (pHash, Hamming distance)       │
│      →  5-signal weighted engine (deterministic)          │
│      →  policy band → decision                            │
└───────────────────────────────┬──────────────────────────┘
                                 ▼
┌─ AUDIT & DATA LAYER ─────────────────────────────────────┐
│ Claim log + photo-fingerprint store (indexed) ·           │
│ per-signal explanation ·  lookup: GET /evaluations/{id}   │
└──────────────────────────────────────────────────────────┘
         ▲ decision + explanation returned to the user
```

**Three supporting captions (one per layer)**
- **User:** deferred camera, dark-photo gate, upload fallback — no raw photo leaves the device unchecked.
- **Scoring:** pure and deterministic; heavy/photo work happens before it, so the decision is explainable and repeatable.
- **Audit:** only extracted features + a photo fingerprint are stored — never the raw image.

---

## Slide 6 — Consumer UX Journey & Mechanics

**Subhead:** Three taps — report, snap, done — with a quality gate the honest user never notices.

**3-screen flow (left → right), each with its mechanic**

| 1 · Order Details | 2 · Camera + Darkness Gate | 3 · Instant Resolution |
| --- | --- | --- |
| Itemized order + "Report damaged/spoiled food" CTA | Camera opens only on tap; snap or upload | Score + band shown in seconds |
| — | Client-side luminance check blocks dark/blank photos **before upload** | 🟢 "₹340 credited" or 🟡 "sent to review" |
| — | Camera shuts off right after the snap | Full per-signal breakdown behind an inspector toggle |

**Mechanic callouts (chips)**
`decision in ~1s` · `no raw photo stored` · `honest users feel no checkpoint` · `dark photo → clear prompt, not a failed claim`

---

## Slide 7 — Edge Cases & Resilience Matrix

**Subhead:** The failure modes that matter, and the specific mechanic that covers each.

| Scenario | Risk if unhandled | How Trust Engine handles it |
| --- | --- | --- |
| Dark / blank photo | Unscoreable image, wasted round trip | Client-side luminance gate rejects it before upload; prompt for a clearer shot |
| Same photo across accounts | Serial refund fraud | pHash fingerprint match (Hamming distance) flags reuse from a **different** account/claim → review |
| Legit re-upload on own order | False accusation of a real customer | Same account **and** claim re-upload is allowed, not penalized |
| Vision model downtime | Scoring stalls, refunds blocked | Graceful fallback to lightweight photo heuristics + manual review — refunds never fully blocked |
| Oversized / non-image upload | Errors, abuse vector | Size + type gate rejects before processing |
| No photo provided | Can't verify condition | Photo signals excluded (not penalized); decide on remaining signals or route to review |

---

## Slide 8 — Metrics & Guardrails

**Subhead:** What we'd measure, how it's computed, and the target SLA. *(Targets are design goals, validated in shadow mode before enforcement.)*

**Metrics table**

| Metric | Formula | Why it matters | Target SLA |
| --- | --- | --- | :--: |
| Auto-approval rate | auto-credited ÷ total claims | Friction removed for honest users | > 90% of legit claims |
| Fraud catch rate | fraud flagged ÷ total fraud | Leakage stopped at claim time | > 80% |
| Decision latency | time to score + decide (p95) | Keeps the experience instant | < 1s |
| Review deflection | 1 − (claims to agent ÷ total) | Ops load removed | > 60% |
| Reuse detection recall | duplicates caught ÷ true duplicates | Serial photo fraud caught | high on exact dup; tuned threshold |

**Guardrails (must not cross — red card)**

| Guardrail | Line |
| --- | --- |
| False-positive rate | Honest claims sent to review **< 5%** |
| Decisioning | **Never auto-decline** — low trust = human review |
| Privacy | Store check results + a photo **fingerprint**, never the raw photo |

---

## Slide 9 — Phased GTM & Roadmap

**Subhead:** Prove the numbers before enforcing them, then expand.

**Rollout (3-step, left → right)**

| 1 · Shadow launch | 2 · Beta pilot | 3 · Full GA |
| --- | --- | --- |
| Score every claim, **act on none** | Auto-credit high-trust in one category/region | Enforce policy bands across categories |
| Tune weights + band cutoffs on live traffic | Route the rest to review; watch guardrails | Expand as accuracy and false-positive rate hold |

**Now / Next / Later roadmap**

| Now (delivered) | Next | Later |
| --- | --- | --- |
| 5-signal engine, photo checks (with fallback), pHash reuse detection, policy bands, darkness gate, audit trail, consumer PWA | Trained damage/authenticity model, indexed reuse matching at scale, agent review console, fingerprint backfill, scoped API keys | Learn from agent overrides, per-region/category tuning, chargeback/dispute hooks |

**Out of scope (explicit):** payments & settlement · chargeback operations · identity / KYC · ticketing / CRM
