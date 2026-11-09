# HANDOFF

Final state of the autonomous build (internal development log). Resume from this file and docs/dev/BUDGET.md alone. The benchmark agent prompt is docs/dev/AGENT_PROMPT.md.

## State

## Session 3 (in progress; resume from here)
- Done: ponytail installed and audit done (no must-fix bugs; findings = plan items 2, 4, 7 plus a dead package-data entry, removed). P0.1 GitHub install: `pip install git+...` in a clean venv 15.6 s, toy loop passes; plugin marketplace add/install from `c-cheng10/sim-anything` works in an isolated config. P0.2 `tests/test_plugin.py`. P1.4 `drawing` spec field + check (15 checks).
- Done: P0.1 real `/sim-anything UR3e` run from the GitHub install (416 s, $2.31, all four agents, passes, auditor "ready with caveats"). P1.5 scout guidance. P1.7 `kinematics_score` + `disagreements` in eval, all rounds re-scored (no old number changed).
- Next: P1.6 variance runs (trimmed to fit the 8-run / $15 cap), then version 0.3.0 + docs.

## Session 2 update (0.2.0)
- Ponytail-style audit done; fixed: world-fixed base vs first-link contacts now count as self-collisions; one shared config sampler + motion transform (spec.py `sample_configs`, `motion_tf`); removed always-zero `ChainJoint.qpos_offset`; internal logs moved to docs/dev/.
- Plugin 0.2.0: four agents in plugin/agents/ (source-scout, spec-writer, loop-fixer, source-auditor), `/sim-anything` orchestrates them with one rework round, `/sim-anything-audit` runs the auditor alone. Verified once: `/sim-anything Trossen WidowX 250 6DOF` via `claude -p` in an isolated CLAUDE_CONFIG_DIR, all four agents ran, 14/14 checks, auditor "ready with caveats", 7 min, ~$2.20 (single-agent: 2 min, ~$0.80).
- README headline toned down; "verified" explained (5 checks only guard hand edits for builder output); CHANGELOG.md added.
- Next-session prompt: docs/dev/NEXT_SESSION.md.

- All phases complete (1 contracts, 2 parallel build, 3 integrate, 4 blind dev benchmark, 5 refinement x2 rounds, 6 holdout + gallery + ship). Main is pushed; pytest green locally (182+ tests incl. Menagerie-dependent ones) and in CI.
- Final metrics (details: benchmark/RESULTS.md, README):
  - Dev set, final tool (round 2): 6/6 pass all error checks. p95 EE error: UR5e 1.4, Panda 0.0, Kinova Gen3 24.5, xArm 7 0.0, KUKA iiwa 0.0, ViperX 7.6 mm. Median over DH-publishing robots 0.7 mm (rounds 0-1: 0.2 mm; Kinova 0.4 mm and ViperX 0.3 mm in rounds 0-1 with sources the round-2 agents didn't find/trust).
  - Holdout (once): UR10e 17.2 mm p95 (reference flange 16.55 mm shorter than UR's published d6; 1.1 mm diagnostic at the published flange), Lite 6 1.3 mm. Both pass all error checks.
- Gates: all 6 met (see README "Gates").
- Gallery: builds locally (`python gallery/build.py`); Pages deploy needs the owner to enable GitHub Pages (Settings -> Pages -> Source: GitHub Actions), then re-run the "Gallery" workflow. The deploy job is non-blocking until then.

## Verified by running vs untested
Verified by running:
- Unit/integration tests (spec/DH conversion vs textbook FK, builder inertia vs MuJoCo, every check incl. mutation-killing tests, loop states, CLI exit codes, evaluator incl. re-conventioned Menagerie arms, render both backends, report).
- CLI end to end on examples; quickstart from a fresh clone (orchestrator once, new-user testers twice); plugin install + `/sim-anything Trossen WidowX 250 6DOF` end to end in an isolated Claude config (round-2 tester).
- Benchmark: 3 dev rounds + holdout generated blind by agents, scored by run_eval.py; round-0 metrics independently re-derived by the auditor; renders and HTML reports looked at.
Untested:
- `pip install git+https://github.com/c-cheng10/sim-anything` and `/plugin marketplace add c-cheng10/sim-anything` from GitHub (only local-clone installs were tested; the round-1 tester did test the GitHub marketplace form once).
- GitHub Pages deployment (Pages not enabled).
- MuJoCo interactive viewer (no display), EGL rendering, Windows/macOS.
- Manufacturer pages themselves: blocked network; values came from search excerpts.

## Known bugs / limitations
(re-checked in session 3; none of the remaining items has a small, safe fix)
- Source discovery varies run to run and dominates error (Kinova 0.4 -> 24.5 mm, ViperX 0.3 -> 7.6 mm between rounds). Session 3: scout guidance sharpened and team variance runs measured (benchmark/RESULTS.md "Team variance").
- Self-consistent but wrong specs pass the checks unless the spec carries a contradicting `drawing` dimension (0.3.0); without one only the auditor or a reference eval catches them.
- Evaluator: ties needing >= 4 simultaneous joint changes or > 128 tie solutions are best-effort; near-ties on imperfect candidates are decided by EE error only. Equal-cost conventions can differ between evaluator versions (Kinova rounds 0-1 now report 1 flip + 1 offset instead of none; same numbers).
- Collinear capsules meeting end to end look like a short middle link to the end-cap exclusion rule (geometry heuristic; changing it risks hiding real collisions, so left as is; every exclusion is reported).
- Matplotlib fallback renderer only depth-sorts whole geoms (cosmetic; MuJoCo renderer works with OSMesa).
- Agents running `pip install -e .` in a worktree hijack the shared editable install (process rule, not code).
- Fixed in 0.3.0: the score penalised sourced datasheet limits/masses; `kinematics_score` now excludes them and `disagreements` lists them.

## Next 10 tasks (priority order)
1. Allow manufacturer hosts in the environment network policy and re-gather inputs from primary documents (Kinova user guide DH table, Trossen docs, KUKA spec PDF).
2. Make source discovery robust: a curated "where to look" list per manufacturer type in the skill, and a requirement to try >= 2 independent sources for kinematics before falling back to dimension tables.
3. Run each benchmark robot 3x per round and report mean/variance, since single runs are noisy.
4. Split the score into a kinematics score and a "datasheet vs reference" disagreement report so sourced values aren't penalised.
5. Enable GitHub Pages and verify the gallery deploy; optionally add an in-browser 3D viewer (MuJoCo WASM or three.js from the MJCF primitives).
6. Test the GitHub install paths (pip git+ URL, `/plugin marketplace add c-cheng10/sim-anything`) in a clean environment.
7. Add a check that compares the zero-pose EE position with a published drawing dimension when the spec provides one (catches misread DH rows that self-consistency can't).
8. Grippers/end-effector modules and closed-chain/parallel mechanisms (hand-edited MJCF path with `kinematics_match` explanations).
9. Mesh import from manufacturer CAD downloads where licences allow, with primitive fallback.
10. Expand the benchmark (Fanuc CRX, Flexiv Rizon, Unitree Z1, SO-100) and add a measured-hardware reference.

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
- D15: ViperX reference EE = `gripper_link` body origin, fixed in reference_sides.yaml before the ViperX run; the generating agent was told to put the EE at the gripper-mount face.
- D10: ViperX reference includes gripper finger joints; they are unmapped and held at qpos0; reference mass includes the gripper.
- D16: A reach mismatch is a warning when the reach definition or value is an estimate (or the definition is not written in the spec), but always an error beyond ±30% (units/structure slips).
- D17: Builder auto-excludes only parent/child, coincident-origin chains, and capsule end caps of links k/k+2 meeting around a short middle link (closest points at the segment ends, depth <= r1+r2-gap); every exclusion is reported as a `collision_exclusions` warning.
- D18: Evaluator ties between kinematically indistinguishable conventions resolve to the lowest joint-limit MAE, then the simplest; it never trades EE error for limits.
- D19: Refinement stopped after round 2 (improved no metric) and spawn 26 was reached; Phase 6 followed. Round 3 not used.
- D20: Reference models were moved outside the repository (round 1: scratchpad, rounds 2/holdout: /root/.cache/simrefs) while generation agents ran.
- D21: Fixers C and D and orchestrator fixes were made generically; no robot-specific code or constants exist in simanything/.
- D22: The UR10e holdout number is reported as measured (17.2 mm p95); the reference-flange diagnostic (1.1 mm) is labelled as diagnostic only and the mapping was not changed after seeing the result.


## Round triage history

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

