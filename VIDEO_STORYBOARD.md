# Governance OS — Explainer Video Storyboard

## Target: ~2:00-2:30

---

## OPENING: Personal Context (0:00-0:12)

**Visual:** Simple text card or headshot.

**Voiceover:**
"I spent years in treasury and wealth management before moving to technology. I always treat hackathons as a chance to learn through doing — that's why I picked a hard problem I know from the inside. Early experiments with Gemini 3 showed the frontier had moved — what wasn't feasible before suddenly was."

---

## ACT 1: The Problem (0:12-0:27)

**Visual:** Split screen — left: a dense 6-page treasury PDF. Right: a red alert dashboard with 14 "BREACH" badges flashing.

**Voiceover:**
"A wealth manager gets a weekly portfolio pack. An AI reads it and flags 14 breaches. The problem? 12 of them are wrong. In regulated finance, false alarms are as dangerous as missed ones — they erode trust, waste time, and eventually get ignored."

---

## ACT 2: The Architecture — Two Layers (0:15-0:30)

**Visual:** Simple animated diagram: Document → [Gemini 3 box] → candidate signals → [Deterministic Kernel box] → confirmed exceptions → [Human decision screen]

**Voiceover:**
"Governance OS solves this with a two-layer architecture. Gemini 3 reads documents and extracts candidate signals. Then a deterministic kernel — no AI, no randomness — validates every single one before it reaches a human."

---

## ACT 3: Gemini Extracts — Thinking Mode (0:30-1:00)

**Visual:** CLI — run the IntakeAgent on the Meridian wealth pack. Show the thinking block expanding in the terminal. Highlight the key reasoning: Gemini spotting the equity breach, the fee discrepancy, the stale suitability questionnaire.

**Voiceover:**
"We feed a real wealth management pack to Gemini 3 with Thinking Mode enabled. Watch it reason through the document — it spots a 40.2% equity exposure against a 40% hard cap. It finds a custody fee mismatch: 0.40% charged vs 0.30% in the term sheet. And it flags a suitability questionnaire that's 16 months stale."

"This isn't a black box. Every extraction comes with the model's reasoning chain — auditable, reviewable, required by compliance."

---

## ACT 4: The Canonicalizer — Two-Thirds False Alarm Prevention (1:00-1:30)

**Visual:** Start in CLI showing the JSON output — 9 candidate signals entering the Canonicalizer. Animate/highlight: 0 breaches come out. 9 observations. Then cut to the GUI approval queue showing the same signals with their canonical status badges.

**Voiceover:**
"Gemini found 9 real issues. But zero are confirmed breaches. Why? The equity and concentration signals need lookthrough data from the underlying funds — we don't have it yet. The fee discrepancy needs an authorized source document — the term sheet PDF is missing. The withdrawal request and compliance flags are events, not threshold violations — they can never be breaches by definition."

"Every signal is tracked. Nothing is lost. But only verified violations earn the breach label. On our test documents, that's two-thirds false alarm prevention — with zero missed signals. Run `make evals` to verify."

---

## ACT 5: The Human Decision Surface (1:30-1:50)

**Visual:** GUI — the exception detail page. Show the one-screen layout: policy context on the left, symmetric options in the center (no default, no recommendation), decision commitment on the right with rationale required.

**Voiceover:**
"When a real exception does reach a human, this is what they see. One screen. No scrolling. Options are presented equally — the system never recommends. The human writes their rationale, commits the decision, and an immutable evidence pack is generated automatically."

**Visual:** Click through to the decision trace — show the evidence pack with signals, evaluation, decision, rationale all linked.

"Every decision is traceable: which signals triggered it, which policy applied, who decided, and why. That's the evidence pack — generated deterministically, audit-ready."

---

## ACT 6: Context Caching + The Numbers (1:50-2:10)

**Visual:** Split screen — left: terminal showing cache creation and second-run speed. Right: cost comparison graphic (before/after caching).

**Voiceover:**
"We cache 50 pages of policy documents and domain vocabularies using Gemini's Context Caching API. The second extraction is 2x faster and the cached tokens cost 90% less. At enterprise scale — hundreds of documents per week — that's the difference between viable and not."

---

## ACT 7: Close — The Claim (2:10-2:30)

**Visual:** Return to the split screen from Act 1. Left side now shows the same 14 signals. Right side shows 2 red breach badges and 12 yellow observation badges, neatly organized.

**Voiceover:**
"Gemini 3 reads documents with transparent reasoning. A deterministic kernel validates with zero randomness. Humans decide with full context. No hallucinated breaches. No missed signals. AI that extracts, but never decides."

"The system saves executive time from day one — two-thirds of false alarms are filtered before a human ever sees them. But the real value is structural. Weak policies mean more noise. Precise policies mean silence on what doesn't matter, and clear escalation on what does. The system makes the cost of bad policy visible and immediate. It doesn't just automate decisions — it motivates better governance."

**End card:** Governance OS — Deterministic Policy Engine with Transparent AI

---

## Production Notes

### GUI vs CLI Usage

| Section | Medium | Why |
|---------|--------|-----|
| Act 1 (Problem) | Graphic/animation | Sets the scene, no real product needed |
| Act 3 (Thinking) | **CLI** | Thinking chain is terminal output — this IS the demo |
| Act 4 (Canonicalizer) | **CLI → GUI transition** | Start with JSON filtering, cut to approval queue |
| Act 5 (Decision) | **GUI** | The decision surface is the product's crown jewel |
| Act 6 (Caching) | **CLI + graphic** | Speed/cost numbers work better as overlay |
| Act 7 (Close) | Graphic | Callback to opening, clean resolution |

### What to Actually Run on Camera

1. `make demo-thinking-auto` — captures Gemini thinking chain (Act 3)
2. `python evals/e2e_wealth_meridian.py` — shows full pipeline with canonicalization (Act 4)
3. GUI at `localhost:3000/ingest` — paste document, show extraction results
4. GUI at `localhost:3000/exceptions/{id}` — show decision surface (Act 5)
5. GUI at `localhost:3000/decisions/{id}` — show evidence pack trace (Act 5)

### Showing "Gemini as Judge" (Not in Current Storyboard)

The eval suite uses Gemini to validate narrative grounding — catching hallucinations
that regex misses. This is hard to demo visually in 2 minutes. Two options:

**Option A: Skip it.** The canonicalizer story (2/3 prevention) is stronger and
more visual. "Gemini as judge" is a testing/CI story, not a product demo story.

**Option B: 5-second insert in Act 4.** Show a test output where Gemini catches
a wrong number in a generated narrative: "Narrative says CHF 100,000 threshold,
document says definition is disputed. Test: FAIL." Red text. Move on.

Recommend Option A for time. Mention it verbally: "Our CI pipeline uses Gemini
itself to catch hallucinations in generated narratives — any unsupported claim
fails the build."

### Stylistic Alignment

The GUI uses a clean dark theme with severity color coding (red/amber/green).
The CLI demos use colored terminal output with similar severity colors.
They're visually compatible — the transition from terminal to GUI should feel
like "zooming out from the engine room to the cockpit."

### Things NOT to Show

- Don't show `make demo-safety` — the regex hallucination blocking is a weaker
  story than the Canonicalizer. It blocks obvious patterns ("we recommend...")
  but the Canonicalizer blocks subtle false positives. Lead with the stronger claim.
- Don't show raw database queries or Docker logs.
- Don't show the policy editor — it's functional but not the differentiator.
