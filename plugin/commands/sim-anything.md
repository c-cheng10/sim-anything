---
description: Build a verified MuJoCo model of a real robot arm from its public datasheets, with a four-agent team (scout -> spec writer -> loop fixer -> auditor)
argument-hint: <robot name, e.g. "UR5e" or "Franka Emika Panda">
---

Build a verified MuJoCo simulation of this robot arm: **$ARGUMENTS**

You are the lead. The `robot-to-mujoco` skill holds the rules (load it). Four team agents do the
work in order and hand off through files in `runs/<slug>/`. Use the plugin's agents through the
Agent tool (`subagent_type`: `sim-anything:source-scout`, `sim-anything:spec-writer`,
`sim-anything:loop-fixer`, `sim-anything:source-auditor`; drop the `sim-anything:` prefix if the
agents were installed by hand). If agents are unavailable in this harness, do each step yourself
by the skill.

## Setup

Pick a slug (lowercase, underscores: `ur5e`, `kuka_iiwa14`) and create `runs/<slug>/`. All paths
are relative to the project root. If `runs/<slug>/spec.yaml` already exists, start at step 3. If
the `sim-anything` CLI is missing: `pip install git+https://github.com/c-cheng10/sim-anything`
(`python -m simanything.cli` also works).

Give every agent the robot name, the slug and the paths below. Never paste file contents from
other runs into a prompt: generated outputs are not sources.

## Steps

1. **source-scout** writes `runs/<slug>/sources.md`.
2. **spec-writer** writes `runs/<slug>/spec.yaml` from it and gets `sim-anything validate` to exit 0.
   If it reports missing facts that matter (no kinematic table and no drawing), send the scout back
   once with exactly those gaps, then the writer again.
3. **loop-fixer** runs `sim-anything loop runs/<slug>/spec.yaml --run-dir runs/<slug>/run
   --max-iter 8` until exit 0 or 2, then checks the renders.
4. **source-auditor** audits `runs/<slug>/`. If its verdict is "not ready", send its findings once
   to spec-writer (source or transcription problems) or loop-fixer (loop problems), then audit
   again. One rework round only; report whatever is left.

Run the steps one after another; each needs the previous one's files. Don't redo an agent's work
yourself; you may read its files to decide the next step.

## Report to the user (a few lines)

- Kinematic source class and its URL; any second-hand sources.
- Check result: errors and warnings, iterations used.
- The auditor's verdict and open caveats.
- Paths: `runs/<slug>/spec.yaml`, `runs/<slug>/sources.md`, `runs/<slug>/run/report.html`,
  `runs/<slug>/run/renders/`.
