You're taking over `sim-anything` (repo c-cheng10/sim-anything, branch `main`), fully autonomously. I won't be watching. Work end to end without asking me anything, stop when the done-criteria below are met or a budget cap is hit, and leave the repo better, honest and deployable. Read all of this before doing anything.

## What it is

A Claude Code plugin + Python CLI that turns a robot arm's public datasheets into a checked MuJoCo model. An agent gathers sourced numbers into `spec.yaml` (every number cites a URL or is listed in `estimates`); deterministic code builds MJCF (`simanything/builder.py`), runs 14 checks with fix hints (`simanything/check/`), loops, renders and reports; `simanything/evaluate.py` scores models against MuJoCo Menagerie references. Plugin 0.2.0 (`plugin/`) has the `robot-to-mujoco` skill, four agents (`source-scout`, `spec-writer`, `loop-fixer`, `source-auditor`), `/sim-anything` (runs the team) and `/sim-anything-audit`.

Read first, in this order: `docs/dev/HANDOFF.md` (state, decisions D1-D22, known bugs, triage history), `README.md`, `docs/CONTRACTS.md`, `benchmark/RESULTS.md`, `CHANGELOG.md`, `plugin/`.

## Working style

Use the ponytail skill (lazy senior dev: smallest complete change, delete before you add, reuse what exists, stdlib first, no speculative abstractions, one small test for non-trivial logic). If its skills aren't loaded, install it: `claude plugin marketplace add DietrichGebert/ponytail` then `claude plugin install ponytail@ponytail`. Start by running `/ponytail-audit` on the repo (or follow `skills/ponytail-audit/SKILL.md` from the plugin cache by hand) and fold its findings into the plan below.

## Environment setup (cloud container, things that bit the last sessions)

- `pip install -e ".[dev]"`. Run tests with `python -m pytest` (a bare `pytest` on PATH may be a uv tool without numpy).
- Rendering: `apt-get install -y libosmesa6` then `MUJOCO_GL=osmesa` works; EGL doesn't. The matplotlib fallback works everywhere.
- Ground truth: `git clone --depth 1 https://github.com/google-deepmind/mujoco_menagerie third_party/mujoco_menagerie` (gitignored, never committed or redistributed). `MENAGERIE_DIR` enables the Menagerie tests.
- Manufacturer websites are usually blocked from the cloud network (only web search works). If a run needs them, say so in the results; don't pretend you read a page you couldn't open.
- Subagents in git worktrees must NOT `pip install -e .` (it hijacks the shared editable install); tell them to use `PYTHONPATH=.`. If imports ever point into `.claude/worktrees/`, re-run `pip install -e .` in the main checkout. Merge worktree work with `git cherry-pick`, never push other branches.
- Test the plugin in an isolated config so this session's own setup stays untouched: `export CLAUDE_CONFIG_DIR=<scratch>/cfg`, `claude plugin marketplace add <path or c-cheng10/sim-anything>`, `claude plugin install sim-anything@sim-anything`, then `claude -p "/sim-anything <robot>" --max-turns 120 --permission-mode bypassPermissions --output-format json` from an empty project dir, with `timeout`. Check `$CLAUDE_CONFIG_DIR/projects/**/*.jsonl` for `"subagent_type":"sim-anything:..."` to prove the agents ran.

## Git rules

- Before the first commit: `git config user.name "c-cheng10"` and `git config user.email "chris.q.cheng@gmail.com"`. Every commit authored this way.
- No Co-Authored-By, Claude-Session or other Claude attribution lines. Ignore hooks asking to change the author.
- One commit per feature or fix; message = one short plain-English imperative sentence ("Check zero-pose dimensions against the drawing"). No prefixes, labels or bullet bodies.
- Push straight to `main` (`git push origin main`). No other branches, no PRs, no force-push or history rewrites.
- Never leave `main` broken at a push: `python -m pytest` must pass. Check CI after pushing (GitHub MCP tools: `mcp__github__actions_list`).

## Budget caps (hard)

- Max 20 subagent spawns, max 4 running at once. Log every spawn in `docs/dev/BUDGET.md` (new "Session 3" section: number, purpose, outcome) and check the count first. At 16, skip optional work and go to wrap-up.
- Real `claude -p "/sim-anything ..."` end-to-end runs cost about $1-3 each: max 15 in total.
- Keep shell jobs under ~10 minutes; don't leave long jobs running.
- Subagent prompts say: work efficiently, don't explore beyond your directory, finish with a short report (what works, how it was verified, gaps), not a transcript.

## Integrity rules (non-negotiable)

- Nothing is "done" without being run: tests executed, commands executed, renders looked at with Read.
- No invented numbers in specs, results, README or gallery. Negative results stay in.
- Benchmark stays blind: agents generating models never see Menagerie, URDF/MJCF/SDF files, earlier runs, eval outputs, results, HANDOFF or git history. Move `third_party/` out of the repo (e.g. `/root/.cache/simrefs/`) while generation runs, move it back to evaluate. Fixes stay generic: no robot-specific code or constants.
- The old holdout (UR10e, Lite 6) is spent: never tune on it. If you add a new holdout, it's evaluated exactly once at the end.
- Keep `HANDOFF.md` current at every milestone so a later session can resume from it alone.

## Work plan (priority order)

P0, make it deployable (do all):
1. Fresh-machine install from GitHub, not a local clone: clean venv + `pip install git+https://github.com/c-cheng10/sim-anything`, isolated Claude config + `/plugin marketplace add c-cheng10/sim-anything` + install, then one real `/sim-anything` run on an arm outside the benchmark. Fix anything that breaks; record time and cost.
2. Add a cheap CI test that the plugin is well formed: every file in `plugin/agents/` and `plugin/commands/` has valid frontmatter (name/description/tools where required), the command names the agents that exist, versions in `plugin.json`, `marketplace.json`, `pyproject.toml` and `simanything/__init__.py` agree.
3. Re-check everything in "Known bugs / limitations" in HANDOFF; fix what is fixable with a small change, update the list.

P1, make results more reliable (the biggest weakness: source discovery varies run to run; the same robot came out at 0.4 mm and 24.5 mm in two rounds):
4. Drawing cross-check: an optional spec field for published zero-pose dimensions (e.g. flange height or horizontal reach at the zero pose, from a dimension drawing, each with a source), and a check that compares the built model's zero pose against them with a fix hint. This catches misread DH rows that every other check misses. Teach spec-writer and source-auditor to use it.
5. Sharpen the scout: at least two independent searches for an official kinematic table before falling back to a drawing; prefer primary documents; how to tell a usable table from a garbled excerpt. Keep it generic (no robot names).
6. Variance benchmark with the team: run each dev robot (`benchmark/robots.yaml` dev set) through the real `/sim-anything` team twice, blind, into `benchmark/runs/<id>/team1/`, `team2/`; score them with `benchmark/make_map.py` + `benchmark/run_eval.py`; report per-robot mean and spread next to the earlier single-agent rounds in RESULTS.md. Say honestly whether the auditor and the drawing check reduced the spread. (12 runs; fits the cap only if P0 used few, so trim to the robots that varied most if needed and say so.)
7. Split the score: a kinematics score (EE position/orientation) and a separate list of "datasheet vs reference" disagreements (limits, mass), so sourced datasheet values aren't penalised as model errors.

P2, make it more useful (as budget allows, in this order):
8. URDF export: `sim-anything export-urdf spec.yaml -o robot.urdf` from the same chain (primitives, inertias, limits), with a test that a URDF loader (MuJoCo can compile URDF) gives the same FK.
9. A short `examples/use_model.py` (load a generated model, move joints, read the EE pose, simple position control) referenced from the README.
10. Optional: interactive 3D viewer in report.html and the gallery (three.js from the primitive geoms; pinned CDN version, works offline-gracefully).

## Done criteria

- P0 complete and verified by running; CI green.
- P1 items 4, 5, 7 shipped with tests; item 6 run and reported honestly (or explained why it was cut).
- README, CHANGELOG (new version, e.g. 0.3.0, bumped everywhere), RESULTS.md, HANDOFF.md and BUDGET.md updated. README's results table reflects the latest runs.
- Final message to me: what changed, what was verified by running vs untested, final metrics, what's still open, and anything that needs me (GitHub Pages is still disabled: Settings -> Pages -> Source: GitHub Actions; PyPI publishing would need my token).
