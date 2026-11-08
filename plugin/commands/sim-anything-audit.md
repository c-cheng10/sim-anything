---
description: Audit an existing sim-anything robot (runs/<slug>/) for untraceable numbers, unlabelled inferences, forbidden sources and transcription errors
argument-hint: <slug or path to runs/<slug>/>
---

Audit this sim-anything robot: **$ARGUMENTS** (a slug means `runs/<slug>/`).

Run the `sim-anything:source-auditor` agent through the Agent tool on that directory (plain
`source-auditor` if the agents were installed by hand; if agents are unavailable, follow the audit
checklist in `agents/source-auditor.md` yourself). It is read-only. Relay its verdict and findings
to the user as they are, then offer to fix them with the spec-writer or loop-fixer agents.
