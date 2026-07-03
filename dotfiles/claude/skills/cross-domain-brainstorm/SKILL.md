---
name: cross-domain-brainstorm
description: >
  Deliberately-invoked interdisciplinary ideation technique. Use ONLY when
  explicitly invoked via /cross-domain-brainstorm or when the user explicitly
  asks for cross-domain, interdisciplinary, or lateral-thinking brainstorming
  on a problem that's already scoped. This is a supplementary deep-dive step
  that can be used inside the mandatory superpowers:brainstorming flow (e.g.
  during "Propose 2-3 approaches") or standalone before it — it does NOT
  replace superpowers:brainstorming's hard-gated design-approval workflow and
  must never auto-trigger on generic "build a feature" requests.
trigger: /cross-domain-brainstorm
---

# Cross-Domain Brainstorming

A technique for generating ideas by deliberately searching outside a problem's home discipline, while staying grounded enough to reject what doesn't actually transfer.

## When to use

Only when explicitly invoked (`/cross-domain-brainstorm`) or explicitly requested ("brainstorm this from other fields", "what would a biologist/physicist/economist do here"). Never fires automatically on ordinary feature or implementation requests — `superpowers:brainstorming` owns that gate. If this technique is used mid-brainstorming, return control to that flow's next step afterward; do not write specs or start implementation from here.

## Pipeline

1. **State the problem plainly.** One or two sentences, no jargon.
2. **Extract the assumptions.** List the implicit constraints the problem statement takes for granted (e.g. "must be synchronous", "one writer at a time", "state lives in one place").
3. **Challenge each assumption.** For each one, ask: what if it's false, or inverted?
4. **Pick 3-5 relevant adjacent disciplines** for *this* problem specifically — don't run the full list mechanically. Candidates: information theory, biology/evolution, control systems, game theory, cryptography, thermodynamics, economics/market design, distributed systems, signal processing, compiler design, robotics, networking, optimization.
5. **Pull one or two transferable concepts per chosen discipline** and translate each into a candidate idea for the actual problem.
6. **Reject implausible ideas immediately**, with a one-line reason each. Be honest, not exhaustive — most cross-domain analogies don't survive contact with the real constraints.
7. **Rank the survivors** on four axes: novelty, impact, feasibility, evidence (existing precedent). A quick per-idea call, not a formal scoring rubric.
8. **Present the ranked list** back to the user: idea, source analogy, why it might work, why it's ranked where it is.

## Output shape

A short ranked list (rarely more than 5-8 surviving ideas), each with: one-line idea, source discipline/analogy, one-line rationale, rough novelty/impact/feasibility/evidence read. Skip ideas that didn't survive step 6 — don't pad the list with rejects, just note how many were considered and cut.

## Next step

Once the user picks a direction from the ranked list:
- **If invoked mid-`superpowers:brainstorming`**: return control to that flow's next step (it owns the design-approval gate and will hand off to `superpowers:writing-plans` itself once a design is approved).
- **If invoked standalone**: this technique only produces ideas, not an approved design — do not go straight to `superpowers:writing-plans` from here. Route back through `superpowers:brainstorming` first to get the chosen idea properly scoped and approved; that flow is what invokes `superpowers:writing-plans` once approved.
