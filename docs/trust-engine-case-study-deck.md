# Trust Engine — PM Case Study Deck

**Instant refunds for honest customers. A speed bump for fraud.**

Poojan Advani · Product case study · Quick-commerce refunds (shown with a Zomato-style order)

> Deck blueprint: 12 slides. Each slide has a title, layout guidance, and content.
> Any numbers are illustrative and used for framing, not measured results.

---

## Slide 1 — Title

**Visual layout**
Full-bleed title slide. Product name large in the center, one-line tagline beneath it. Small footer with name, "Product Case Study," and date. One simple icon: a receipt next to a shield.

**Content**
- **Trust Engine**
- Instant refunds for honest customers. A speed bump for fraud.
- A refund verification system for quick-commerce platforms
- Poojan Advani · Product Case Study

---

## Slide 2 — Fast refunds or careful checks: today you pick one

**Visual layout**
Two-column split with a center divider. Left column: "Instant, no questions" (happy face, money leaking out). Right column: "Check everything" (clock, frustrated face, stacked tickets). A banner across the middle: "Today, you have to choose."

**Content**
- Platforms are stuck between two bad options
- **No-questions refunds** → customers are happy, but abuse is easy
- **Review everything** → fraud drops, but honest people wait and agents pile up
- The same policy that delights customers is the one that invites fraud

---

## Slide 3 — Why it matters: the money and the frustration

**Visual layout**
Three metric cards in a row, each labeled "directional / for framing." Card 1: refund abuse cost. Card 2: honest-customer wait. Card 3: agent time wasted. Thin caption line underneath: "Industry context — figures are illustrative."

**Content**
- Refund and return abuse is a real, growing cost in quick commerce
- "No-questions" refund policies get shared and reused across accounts
- Honest customers still wait days when every claim is checked by hand
- Agents spend most of their time on claims that turn out to be fine

---

## Slide 4 — Problem framing

**Visual layout**
Five-box canvas grid (like a lean canvas). Boxes: True Problem · Evidence · Value Created · Who Feels It · Why Now. Keep each box to one short line.

**Content**
- **True problem:** speed and safety pull against each other — today it's one or the other
- **Evidence:** known refund-abuse losses, the same "damage" photo reused across accounts, steady slow-refund complaints
- **Value:** customers get fast, fair refunds; the business stops paying for fake claims; agents focus on the few real edge cases
- **Who feels it:** customers, ops agents, finance, the platform
- **Why now:** order volume is booming, phone photos are everywhere, and simple photo checks are finally practical

---

## Slide 5 — Who we're building for

**Visual layout**
Four persona cards in a 2×2 grid. Each card: a name, a one-line goal, a one-line pain. Two customer personas on top, two internal on the bottom.

**Content**
- **Priya — honest customer:** "My paneer arrived spoiled. I just want my ₹340 back, now."
- **Rahul — refund abuser:** reuses the same photo to claim refunds again and again
- **Sana — trust & safety agent:** buried in claims that are mostly genuine
- **Arjun — finance/risk lead:** watching refund costs climb every quarter

---

## Slide 6 — Goals and non-goals

**Visual layout**
Two columns. Left: "Goals" with check marks. Right: "Non-goals" with no-entry icons. Equal weight so the non-goals read as deliberate choices, not leftovers.

**Content**
- **Goals**
  - Instant refunds for clearly honest claims
  - Catch obvious abuse the moment a claim is made
  - Send only the tricky few to a human
  - Keep every decision easy to explain
- **Non-goals**
  - Not replacing human judgment on hard cases
  - Not auto-rejecting customers — a low score means "review," never a hard "no"
  - Not a payments, chargeback, or identity system
  - Not storing customers' photos

---

## Slide 7 — The idea: a quick trust check on every claim

**Visual layout**
Simple left-to-right flow diagram. "Claim + photo" → "Trust check" → "Score 0–100" → splits into two arrows: "High → Instant refund" (green) and "Low / flagged → Quick human review" (amber). Keep it to five nodes.

**Content**
- Most refund claims are honest — approve them instantly if we can tell them apart from the few that aren't
- Every claim gets a **trust score from 0 to 100**
- High score, no red flags → refund credited on the spot
- Low score or a red flag → fast human review (not a rejection)
- The customer feels one smooth flow either way

---

## Slide 8 — What the trust check looks at (in plain words)

**Visual layout**
Five small check cards in a row or grid. The two "photo" cards are visually larger or highlighted. A tiny bar or label underneath: "Photo checks carry the most weight."

**Content**
- **Account history** — is this a normal, established customer?
- **Claim details** — does the claim make sense (amount, timing, proof)?
- **Risk flags** — anything our systems already flagged?
- **Photo — real damage?** — does it actually show spoiled or damaged food?
- **Photo — genuine?** — is it a real photo, not edited, computer-generated, or reused from another account?
- The two photo checks count the most — that's where fraud usually hides

---

## Slide 9 — End-to-end user journey

**Visual layout**
Three phone mockups side by side with arrows between them: Home → Order details → Capture & result. Under the last phone, two small result chips: green "₹340 credited" and amber "Taking a closer look."

**Content**
- **Home:** your recent order with a clear "Report an issue" button
- **Order details:** the itemized order and a "Report damaged/spoiled food" button
- **Capture:** open the camera or upload a photo — dark or blank photos are caught before they're even sent
- **Result in seconds:** "₹340 credited" or "We're taking a closer look"
- Honest customers never feel like they hit a checkpoint

---

## Slide 10 — Metrics and guardrails

**Visual layout**
Two rows of cards. Top row: "Success metrics" (green header). Bottom row: "Guardrails — don't cross these" (red header). Label the whole slide "Illustrative targets."

**Content**
- **Success**
  - Instant approval for honest claims: **> 90%**
  - Fraud caught at claim time: **> 80%**
  - Decision in **under ~1 second**
  - Claims reaching an agent: **> 60% fewer**
- **Guardrails**
  - Honest claims wrongly sent to review: **keep under 5%**
  - Never auto-decline — low trust means a human looks
  - Store the check results and a photo "fingerprint," never the raw photo

---

## Slide 11 — Risks and how we handle them

**Visual layout**
Two-column table: "What could go wrong" on the left, "How we handle it" on the right. Six short rows.

**Content**
- **Dark or blurry photo** → caught on the phone before sending; ask for a clearer one
- **Camera blocked or missing** → simple upload option instead
- **Network drops mid-claim** → clear retry; the claim isn't lost
- **Same photo reused across accounts** → a photo fingerprint matches it and flags it for review
- **Real customer re-uploads on their own order** → allowed, not punished
- **Photo check unsure or offline** → fall back to simpler checks plus a human; refunds are never fully blocked

---

## Slide 12 — Go-to-market and roadmap

**Visual layout**
Two panels. Left: a three-step rollout arrow (Shadow → High-trust auto → Expand). Right: a Now / Next / Later roadmap as three short stacked lists.

**Content**
- **Go-to-market**
  - Start in one high-abuse category (fresh/grocery) on one platform
  - Run in shadow mode first: score claims but don't act — tune on real data
  - Turn on instant refunds for high-trust claims; review the rest
  - Expand category by category as accuracy holds up
- **Roadmap**
  - **Now:** trust score, photo checks, reused-photo detection, instant decisions, audit trail
  - **Next:** sharper photo checks, faster photo matching at scale, an agent review screen
  - **Later:** learn from agent decisions, tune by region and category
