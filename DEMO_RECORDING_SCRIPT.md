# Demo Video Recording Script

## Target Duration: ~2:50 (under 3:00 limit)

## Pre-Recording Setup

### Environment Checklist

- [ ] Terminal: dark theme, large font (16-18pt), clean prompt
- [ ] Browser: dark mode if available, zoom 110-125% for readability
- [ ] Screen resolution: 1920x1080 (standard YouTube HD)
- [ ] Close all unrelated tabs/windows — only terminal + browser visible
- [ ] Recording tool ready (OBS / Loom / QuickTime)
- [ ] Microphone test done — clear audio, no echo

### Services Running

```bash
# Option A: Full Docker (simplest — everything in containers)
cd Governance-OS
docker compose up -d          # PostgreSQL + API + UI at localhost:3000

# Option B: Docker backend + local UI (for UI development/hot reload)
cd Governance-OS
docker compose up -d postgres backend   # Only PostgreSQL + API
cd ui && npm run dev                     # UI at localhost:3000 with hot reload

# Option C: Live deployment (no local services needed)
# UI: https://governance-os.web.app
# API: https://govos-api-1064412167254.europe-west4.run.app
```

### Seed Demo Data

```bash
python -m core.scripts.seed_fixtures --all
```

### Pre-Open These Tabs

1. Terminal — ready to run `python demo_video.py --auto`
2. Browser Tab 1 — Dashboard (`/`)
3. Browser Tab 2 — Ingest page (`/ingest`) with document text pre-pasted
4. Browser Tab 3 — Exception detail page (`/exceptions/{id}`) — pick a seeded critical exception
5. Browser Tab 4 — Decision trace page (`/decisions/{id}`) — pick a completed decision

### Test Run

Do one full dry run. Make sure the CLI demo runs cleanly and all UI pages load with data.

---

## THE SCRIPT

---

### INTRO — Personal Hook (0:00 – 0:12)

**Screen:** Simple title card (you can use a slide or just text on dark background)

> **Title card text:**
> GOVERNANCE OS
> Deterministic Policy Engine with Transparent AI

**Voiceover:**
> "I spent years in treasury and wealth management before moving to tech.
> I picked a problem I know from the inside — and Gemini 3 made solving it possible."

**On-screen text overlay:** `Built with Gemini 3 · Context Caching · Thinking Mode · JSON Mode`

---

### ACT 1 — The Problem (0:12 – 0:30)

**Screen:** Split visual — left side: a dense financial PDF (screenshot of a treasury report).
Right side: a red dashboard mockup showing 14 "BREACH" alerts flashing.

> You can use a simple slide for this, or show the dashboard with seeded data.

**Voiceover:**
> "A wealth manager gets a weekly portfolio pack. An AI reads it and flags 14 breaches.
> The problem? Nine of them are wrong. In regulated finance, false alarms are as dangerous
> as missed ones — they erode trust and eventually get ignored."

**On-screen text overlay (appears at 0:25):**
> `The Problem: 64% of AI-flagged breaches are false positives`

---

### ACT 2 — Architecture Overview (0:30 – 0:45)

**Screen:** Simple diagram (slide or animated). Three boxes connected by arrows:

```
[Document] → [Gemini 3 Extraction] → [Deterministic Kernel] → [Human Decision]
                  AI coprocessor          No AI. No randomness.       Full context.
```

**Voiceover:**
> "Governance OS solves this with two layers. Gemini 3 reads documents and extracts
> candidate signals. Then a deterministic kernel — no AI, no randomness — validates
> every single one before it reaches a human."

**On-screen text overlay:**
> `AI proposes. The kernel disposes. Humans decide.`

---

### ACT 3 — Gemini Extraction with Thinking Mode (0:45 – 1:20)

**Screen:** Switch to terminal. Run the demo.

```bash
python demo_video.py --auto
```

> The demo auto-advances. ACT 1 of demo_video.py shows Gemini reading a treasury report
> with its reasoning chain visible.

**Voiceover (speak over the terminal output as it appears):**
> "We feed a real treasury report to Gemini 3 with Thinking Mode enabled.
> Watch it reason through the document line by line."
>
> *(pause as thinking chain appears)*
>
> "It spots a cash covenant breach — but notices the definition of 'unrestricted cash'
> is disputed in a footnote. It finds an FX exposure gap — EUR 260,000 unhedged.
> And it correctly identifies a payment hold as a settlement event, not a threshold violation."
>
> "Every extraction comes with the model's full reasoning chain —
> auditable, reviewable, required by compliance."

**On-screen text overlay (bottom of screen):**
> `Gemini 3 Thinking Mode · Every extraction is auditable`

---

### ACT 4 — The Canonicalizer (1:20 – 1:55)

**Screen:** Terminal continues — ACT 2 of demo_video.py runs automatically.
Shows 14 signals filtering down to 5 confirmed breaches.

**Voiceover (speak as signals scroll through):**
> "Gemini found 14 issues across two financial packs.
> Without validation, all 14 would be flagged as breaches."
>
> *(pause as signals appear one by one with BREACH / obs labels)*
>
> "The Canonicalizer applies deterministic rules.
> Equity and concentration signals need lookthrough data from underlying funds — we don't have it yet.
> The fee discrepancy needs an authorized source document.
> Settlement events can never be breaches by definition."
>
> *(pause as summary bars appear)*
>
> "14 breach candidates enter. 5 confirmed breaches exit.
> Two-thirds false alarm prevention. Zero missed signals.
> Same inputs, same outputs. Deterministic. Replayable.
> Run `make evals` to verify."

**On-screen text overlay (when summary bars appear):**
> `2/3 false alarm prevention · 0 missed signals · Fully reproducible`

---

### ACT 5 — The Human Decision Surface (1:55 – 2:25)

**Screen:** Switch to browser. Open the exception detail page (`/exceptions/{id}`).

**Voiceover:**
> "When a real exception reaches a human, this is what they see. One screen."

**Action:** Slowly pan across the three-column layout. Pause on each section:

1. **Left column** — "On the left: the policy that triggered it, and the contributing signals with their evidence."
2. **Center column** — "In the center: decision options presented symmetrically. No default. No recommendation. The system never tells you what to do."
3. **Right column** — "On the right: the human writes their rationale and commits."

**Action:** Type a brief rationale in the text area, e.g.:
> "FX exposure confirmed. Approved hedging increase to cover EUR gap."

**Action:** Click "Commit Decision".

**Voiceover:**
> "The decision is recorded immutably. An evidence pack is generated automatically."

**Action:** Navigate to the decision trace page (`/decisions/{id}`).

**Voiceover:**
> "Every decision is fully traceable. Which signals triggered it.
> Which policy applied. Who decided. Why.
> That's the evidence pack — deterministic, audit-ready, exportable."

**On-screen text overlay:**
> `Immutable evidence pack · Full audit trail · Deterministic generation`

---

### ACT 6 — Context Caching (2:25 – 2:35)

**Screen:** Brief return to terminal or a simple overlay graphic.

**Voiceover:**
> "Behind the scenes, Gemini's Context Caching API stores our policy documents and domain vocabularies.
> Cached tokens cost 90% less. At enterprise scale — hundreds of documents per week —
> that's the difference between viable and not."

**On-screen text overlay:**
> `Context Caching: 50-60% cost reduction at scale`

---

### CLOSING — The Claim (2:35 – 2:50)

**Screen:** Return to a clean title card or the dashboard.

**Voiceover:**
> "Gemini 3 reads documents with transparent reasoning.
> A deterministic kernel validates with zero randomness.
> Humans decide with full context.
> No hallucinated breaches. No missed signals.
> AI that extracts — but never decides."

**End card text:**

```
GOVERNANCE OS
Deterministic Policy Engine with Transparent AI

github.com/Silveroboros-dev/Governance-OS
```

**On-screen text overlay:**
> `AI that extracts, but never decides.`

---

## Post-Production Notes

### On-Screen Text / Subtitles

Since you're doing both voiceover and on-screen text, here are the key text overlays to add in editing:

| Timestamp | Overlay Text |
|-----------|-------------|
| 0:00-0:12 | GOVERNANCE OS — Deterministic Policy Engine with Transparent AI |
| 0:25 | The Problem: 64% of AI-flagged breaches are false positives |
| 0:35 | AI proposes. The kernel disposes. Humans decide. |
| 0:50 | Gemini 3 Thinking Mode |
| 1:15 | Every extraction is auditable |
| 1:45 | 2/3 false alarm prevention · 0 missed signals |
| 2:15 | Immutable evidence pack · Full audit trail |
| 2:25 | Context Caching: 50-60% cost reduction |
| 2:40 | AI that extracts, but never decides. |

### English Subtitles

Required by hackathon rules. Options:

1. **YouTube auto-captions** — Upload to YouTube, let it generate captions, then review/edit for accuracy. Fastest.
2. **Manual SRT file** — Use the voiceover text above to create a `.srt` subtitle file. Most accurate.
3. **Loom** — If recording with Loom, it auto-generates subtitles.

### Recording Tips

- Record terminal and browser separately if easier — stitch in editing
- Terminal font should be large enough to read comfortably at 1080p
- For the CLI demo, `--auto` mode pauses 2 seconds between sections — enough to talk over
- For the UI demo, move mouse slowly and deliberately
- Aim for 2:50 total — leaves 10 seconds of buffer under the 3-minute limit
- If running long, cut Act 6 (Context Caching) — it's the least visual section

### Upload Requirements

- Upload to YouTube (recommended) or Vimeo
- Set visibility to **Public** (required by hackathon)
- Add the video link to the submission form
- Recommended title: "Governance OS — Deterministic Policy Engine with Transparent AI | Gemini 3 Hackathon"
- Add description with GitHub link and key features

---

## Quick Reference — What to Run

```bash
# 1. Start services
docker compose up -d
cd ui && npm run dev &

# 2. Seed data
python -m core.scripts.seed_fixtures --all

# 3. CLI demo (terminal recording)
python demo_video.py --auto

# 4. UI pages to visit (browser recording)
# Dashboard:        http://localhost:3000/
# Ingest:           http://localhost:3000/ingest
# Exceptions list:  http://localhost:3000/exceptions
# Exception detail: http://localhost:3000/exceptions/{id}
# Decision trace:   http://localhost:3000/decisions/{id}
# Approvals:        http://localhost:3000/approvals
```
