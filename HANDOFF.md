# HANDOFF

Resume from this file and BUDGET.md alone. Updated at every phase boundary and round.

## State
- Phases 1-3 complete: all components merged (cherry-picked from agent worktrees), pytest green, `loop` verified end to end on a toy spec (fail -> fix -> pass, renders + report written and inspected).
- Phase 4 complete: 6 dev robots generated blind into benchmark/runs/<id>/round0/, evaluated (benchmark/RESULTS.md). 5/6 pass all checks (xArm7 fails reach: unstated reach definition). Median p95 EE error on DH-published robots 0.2 mm; all six robots <= 1.4 mm p95.
- Phase 5 round 1: reviews done (3), triage below, fixes merged (fixer A: 7, fixer B: 7, orchestrator: end-cap exclusion rule, friendly check errors, README/RESULTS framing). Blind re-run into round1/ done: 6/6 pass all error checks, kinematic metrics unchanged (RESULTS.md round-over-round table). Orchestrator fixes after the re-run: gross reach mismatch (>30%) stays an error; .gitignore `runs/` anchored to root.
- Phase 5 round 2 in progress: new-user tester (verifies gates 2-3 incl. one real /sim-anything run on a non-benchmark arm) + code reviewer.
- Menagerie is back in third_party/. While generation agents run, Menagerie is moved OUT of the repo to /tmp/claude-0/-home-user-sim-anything/a95fd57d-4f5a-5b98-a53c-0a6678d950af/scratchpad/.refs/third_party (move back with `mv <that>/third_party .` before evaluating; if the container was recycled, re-clone it).

## How to run
- `pip install -e ".[dev]"`; run tests with `python -m pytest` (the bare `pytest` on PATH in the dev container is a uv tool without numpy).
- Menagerie (ground truth, gitignored): `git clone --depth 1 https://github.com/google-deepmind/mujoco_menagerie third_party/mujoco_menagerie`
- Rendering: `MUJOCO_GL=osmesa` works in the dev container after `apt-get install libosmesa6`; EGL does not. Fallback: matplotlib.

## Decisions
- D1: Push straight to `main` as instructed by the user (session default branch ignored).
- D2: Spec units are declared per file (`units.length` m|mm, `units.angle` deg|rad) so agents can copy datasheet values verbatim; all code uses `Spec.to_si()`.
- D3: Kinematic convention is per spec (`offset`, `dh_standard`, `dh_modified`), not per joint. DH theta/d offsets are folded into body poses so MJCF joint values equal spec joint values.
- D4: Numbers that are exactly zero or left at schema defaults need no source.
- D5: "All checks passing" means no failed check with severity `error`.
- D6: `loop` is one build+check step per call; the agent edits the spec between calls (that is the FIX step).
- D7: Eval may fit discrete joint conventions (sign ±1, offset 0/±90/180 deg per joint) and a constant tool-frame rotation; both reported. Position error is otherwise raw (world frames). Rationale: zero/direction/tool-axis conventions are arbitrary between a datasheet and a sim model, link geometry is not.
- D8: Benchmark agents may use manufacturer docs, datasheets, manuals and dimension drawings, but NOT URDF/MJCF/SDF/xacro robot-description files from anywhere (those are what Menagerie models are derived from; using them would not be reverse engineering from public specs).
- D9: Dev set: UR5e, Franka Panda (no hand), Kinova Gen3 7-DOF, xArm7 (no hand), KUKA iiwa14, ViperX 300 S (low-cost arm). Holdout: UR10e, UFactory Lite 6.
- D11: The checker's "shoulder" is joint 1 when the first two joints are parallel hinges (planar/SCARA); reach is sampled then locally refined (documented in CONTRACTS).
- D12: `loop` never starts a new iteration when the spec is unchanged (also after a failure), so agents can't burn iterations.
- D13: MuJoCo front render uses a 3/4 camera; matplotlib fallback keeps orthographic front/side/top.
- D14: Eval mapping (orchestrator-written via benchmark/make_map.py) compares the candidate in world coordinates and the reference in its mounting-base body frame (removes Menagerie's xArm pedestal). Convention fitting is multi-start steepest descent preferring the simplest equivalent conventions; fitted conventions are reported per robot in RESULTS.md.
- D15: ViperX reference EE = `gripper_link` body origin, chosen to match the agent's stated EE (gripper-mount face) after reading its NOTES.md.
- D10: ViperX reference includes gripper finger joints; they are unmapped and held at qpos0; reference mass includes the gripper.

## Known issues
- GitHub Pages is not enabled on the repo and the Actions token cannot enable it. Owner action needed once: Settings -> Pages -> Build and deployment -> Source: GitHub Actions. Then re-run the Gallery workflow. The gallery builds locally with `python gallery/build.py`.
- Network: manufacturer sites (universal-robots.com, frankaemika.github.io, kinovarobotics.com, ufactory.cc, trossenrobotics.com, kuka.com, even wikipedia) are unreachable from the shell and from WebFetch; only WebSearch works. Benchmark inputs are built from search excerpts. Kinova (DH values) and KUKA (link lengths) inputs have the largest gaps.
- Evaluator: when a reference base frame is yawed 180 deg relative to the datasheet frame, the fitted joint-1 offset of pi also shifts the joint-limit comparison by 180 deg (limit MAE inflated). Watch in results.
- Matplotlib fallback renderer only depth-sorts whole geoms.
- Agents that run `pip install -e .` inside their worktree hijack the shared editable install. After merging, run `pip install -e .` in the main checkout again. Benchmark agents should use `PYTHONPATH=.` instead.

## Fix list (Phase 5 triage)

### Round 1 (from new-user tester, code reviewer, benchmark auditor + round0 eval)
Ranked by impact on the gates (4: checks pass on dev robots; 2/3: quickstart + plugin; honest reporting).

Fixer A (checker/builder/spec):
1. HIGH: no check compares model kinematics with the spec chain (wrong axis / swapped link passes). Add `kinematics_match` check (model body/EE poses vs spec.chain().fk on ~20 configs).
2. HIGH: builder silently auto-excludes any pair overlapping in all sampled poses; real interpenetration passes. Restrict to shared-joint neighbours with bounded depth; report every exclusion in a `collision_exclusions` warning check.
3. MED: reach definition unknown -> reach check can't be meaningful. When `reach.measured_from/measured_to` are listed in `estimates` (definition not stated by the source), reach failure is a warning, not an error (2/6 dev robots: one changed the endpoint after failing, one failed honestly). Reach fix hint: mention `reach.value` when it is an estimate; don't name vertical offsets for horizontal reach.
4. MED: mass plausibility warnings (density / per-link share); missing reach -> warning.
5. MED: sources accept any string and unmatched paths; require http(s) URLs (or `doc:` local file refs), reject paths matching no field, warn on high estimate fraction.
6. LOW: GeometryHint.size validation; home within limits; builder 1% mass comment; wrist_center for dof<3.
7. Tests: inertia vs MuJoCo, DH-standard link-frame COM/geometry, wrist_center + parallel-axis shoulder rule, new checks.

Fixer B (loop/CLI/report/eval/plugin/docs):
8. MED: stale report.html says PASSED after a later failure -> render+report every iteration.
9. MED: loop at cap after a pass with a changed spec returns 0 -> must not return 0 for an unchecked spec.
10. MED: skill and slash command share the name `sim-anything` -> rename skill.
11. LOW: validate prints "ok" on failure; raw pydantic errors (dotted paths, first error only); loop hint names `spec.yaml` not the actual file; CLI eval/render tracebacks -> stderr + exit 1 (update CONTRACTS section 2).
12. LOW: evaluator samples unlimited slide joints over +-pi metres.
13. SKILL/doc: classify kinematic source (DH / PoE screw table / dimension drawing); only set reach definition from the source, else list it in `estimates`; inferred mappings (e.g. unlabelled drawing letters, axis directions) go in `estimates`; record attribution quality; README doc gaps (starting over, eval example score, loop output).

Orchestrator (me):
14. RESULTS/README: replace "DH published" with kinematic-source type (DH / PoE / dimension table); note UR5e reach-endpoint change; add weak-source caveats (Kinova placeholder attribution, KUKA letter mapping, forum torques, reseller datasheets); explain score terms that compare sourced datasheet values against reference choices (UR5e elbow limit, Panda/xArm mass); soften README wording ("any", "every number cites").
15. Blindness hardening for re-runs: move third_party/ out of the repo tree while generation agents run.

### Round 2 (from new-user tester incl. a real /sim-anything run, and code reviewer)
Gates 2 and 3 verified by the round-2 tester: fresh-clone quickstart 24 s; plugin installs, skill `robot-to-mujoco` and command `/sim-anything` both discovered; one real `claude -p "/sim-anything Trossen WidowX 250 6DOF"` run completed gather -> loop -> report in 128 s ($0.79), sourced and honest.

Fixer C (evaluator):
1. HIGH: convention fit can stall in local minima (347 mm on a re-conventioned exact Panda in 3/6 random trials). Add pair moves when stuck and restart until two runs agree.
2. HIGH: among equal-cost conventions prefer the lowest joint-limit error before simplicity (exact models scored 85-89).

Fixer D (CLI/loop/check/builder/spec/skill):
3. HIGH: usage errors (missing file, bad option) exit 2 = "max iterations reached" for loop; make them exit 1.
4. MED: end-cap exclusion depth limit never rejects (geometry reaching back over a joint gets excluded). Require the closest points to be the segment ends at the short middle link / cap depth by r1+r2 minus end gap.
5. MED: loop status not recomputed when the cap is raised for an unchanged spec.
6. MED: reach definition fields left at defaults count as sourced; treat unset measured_from/measured_to as estimated (or require them).
7. MED: validate must run the same source hygiene as sources_complete (URLs, typo keys, did-you-mean for estimate/source path typos).
8. MED: reach message vs hint contradiction for gross mismatch; print small rated values with enough precision.
9. LOW: element keys like xyz[2]; doc: path traversal; same key in sources and estimates; YAML parse errors name the archived copy; README loop-output list; plugin README note that Claude Code lists commands as skills.
10. SKILL: generated runs (benchmark/runs/, runs/, HANDOFF) are outputs, not sources: never read them while gathering.
11. Tests: mutation-resistant tests for exclusion depth/location, is_estimate precedence, density bounds, kinematics_match tolerance.

