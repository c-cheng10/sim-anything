# BUDGET

Caps: 30 subagent spawns total, max 5 concurrent, max 3 refinement rounds, max 8 build/check iterations per robot per run. At 26 spawns: skip optional work, go to Phase 6.

Planned allocation: Phase 2: 5 | Phase 4: 6 | Round 1: ~3 review + 2 fix + 3 re-run (2 robots each) | Round 2: ~2 review + 1 fix + 3 re-run | Phase 6: 1-2.

## Spawn log
| # | Phase | Purpose | Outcome |
|---|---|---|---|
| 1 | 2 | A: builder (spec -> MJCF) | done: builder.py + 28 tests, merged |
| 2 | 2 | B: checker | done: check/ package + 40 tests, merged |
| 3 | 2 | C: evaluator | done: evaluate.py + 40 tests, merged |
| 4 | 2 | D: render + report | done: render.py, report.py + 11 tests, merged |
| 5 | 2 | E: plugin, loop, benchmark inputs | done: SKILL.md, command, marketplace, loop.py + tests, inputs for 8 robots (search excerpts only; manufacturer hosts blocked), merged |
| 6 | 4 | blind round0: ur5e | done: all pass in 2 iterations (reach definition changed to wrist center) |
| 7 | 4 | blind round0: franka_panda | done: all checks pass in 1 iteration (modified DH from FCI docs) |
| 8 | 4 | blind round0: kinova_gen3 | done: all pass in 1 iteration (DH from third-party quote of Kinova table) |
| 9 | 4 | blind round0: xarm7 | done: reach fails (unstated definition), refused to alter sourced numbers |
| 10 | 4 | blind round0: kuka_iiwa14 | done: all pass in 1 iteration (offset chain from dimension table) |
| 11 | 4 | blind round0: viperx_300s | done: all pass in 1 iteration (Trossen docs screw-axis table) |
| 12 | 5 r1 | review: new-user tester | done: quickstart works (23 s); stale report, name clash, hint/validate issues |
| 13 | 5 r1 | review: code reviewer | done: 12 findings (no kinematic-consistency check, silent collision exclusions, ...) |
| 14 | 5 r1 | review: benchmark auditor | done: no leakage found, metrics reproduce; framing + weak sources |
| 15 | 5 r1 | fixer A: checker/builder/spec | done: 7 fixes merged (kinematics_match, exclusion rules + report, reach warnings, plausibility, source hygiene, validation, math tests); orchestrator relaxed the end-cap exclusion depth afterwards |
| 16 | 5 r1 | fixer B: loop/CLI/report/eval/plugin/docs | done: 7 fixes merged (report every iteration, cap exit 2, skill renamed robot-to-mujoco, friendly errors, slide range, skill docs) |
| 17 | 5 r1 | blind round1: ur5e + franka_panda | done: both pass (2 iterations each) |
| 18 | 5 r1 | blind round1: kinova_gen3 + xarm7 | done: both pass (2 / 1 iterations) |
| 19 | 5 r1 | blind round1: kuka_iiwa14 + viperx_300s | done: both pass (1 iteration each) |
| 20 | 5 r2 | review: new-user tester (incl. one capped real /sim-anything run) | done: gates 2-3 verified; validate parity, exit-code clash, blindness gap |
| 21 | 5 r2 | review: code reviewer | done: eval fit local minima + tie-break, exit codes, exclusion depth, weak tests |
| 22 | 5 r2 | fixer C: evaluator | done: multi-move fit + limit-aware tie-break merged (resumed once after a usage-limit stop); re-scored rounds 0-1, numbers unchanged |
| 24 | 5 r2 | blind round2: ur5e + franka_panda + kinova_gen3 | done: all pass |
| 25 | 5 r2 | blind round2: xarm7 + kuka_iiwa14 + viperx_300s | done: all pass |
| 26 | 6 | holdout (once): ur10e + ufactory_lite6 | done: both pass all error checks; UR10e 17.2 mm (reference flange discrepancy), Lite 6 1.3 mm |
| 23 | 5 r2 | fixer D: CLI/loop/check/builder/spec/skill | done: 9 fixes merged (resumed once after a usage-limit stop) |

## Refinement rounds used: 2 / 3 (round 1: checks 5/6 -> 6/6; round 2 improved no metric (Kinova and ViperX accuracy regressed from stricter/less available sources) -> loop stopped). Spawn 26 reached -> Phase 6.

## Final tally
- Subagent spawns: 26 / 30 (Phase 2: 5, Phase 4: 6, round 1: 8, round 2: 6, Phase 6: 1). Two fixers were resumed once (SendMessage) after an account usage-limit stop; resumes are not new spawns.
- Max concurrent: 5 (Phase 2 and Phase 4).
- Refinement rounds: 2 / 3 (stopped: round 2 improved no metric; spawn 26 reached).
- Build/check iterations per robot per run: max 2 used (cap 8).
- Phase 6 optional work skipped at the 26-spawn mark: in-browser 3D viewer.
- Outside the spawn count: one `claude -p "/sim-anything Trossen WidowX 250 6DOF"` session run by the round-2 tester to verify gate 3 ($0.79 reported).


# Session 3

Caps (hard): 12 subagent spawns (max 3 at once); 8 real `/sim-anything` end-to-end runs and $15 combined
`total_cost_usd`; soft stop at 75% of any cap; P2 skipped once any cap passes 50%.

**Running tally:** subagents 0 / 12 (0 tokens) | e2e runs 5 / 8 | e2e cost $12.11 / $15 (past the 75% soft stop: no more runs; P2 skipped) | other `claude -p` $0.10

## Subagent spawns
| # | Purpose | Outcome | Tokens |
|---|---|---|---|

## End-to-end runs
| # | Command | Result | Time | Cost (USD) |
|---|---|---|---|---|
| 1 | P0.1 `/sim-anything UR3e` (plugin + CLI 0.2.0 installed from GitHub, isolated config) | all four agents ran; 2 iterations, both passed (0 errors, 2 warnings: unlimited wrist 3, reach definition unstated); auditor "ready with caveats"; UR host blocked, values from search excerpts | 416 s | 2.31 |
| 2 | P1.6 `/sim-anything Kinova Gen3 (7-DOF), no gripper` (0.3.0 from GitHub, blind) | stopped by the account usage limit after sources.md + spec.yaml; not scored | 398 s | 2.05 |
| 3 | P1.6 `/sim-anything Trossen ViperX 300 S ...` (0.3.0 from GitHub, blind, in parallel with #2) | stopped by the account usage limit; not scored | 394 s | 2.00 |
| 4 | P1.6 `/sim-anything Kinova Gen3 (7-DOF), no gripper` (retry after the limit reset; blind) | all four agents; passed (iteration 2 after audit relabelling); kinematics inferred; 13.1 mm p95 | 592 s | 3.07 |
| 5 | P1.6 `/sim-anything Trossen ViperX 300 S ...` (retry, blind, in parallel with #4) | all four agents; 15/15 checks on iteration 1, drawing dims within 1 mm; EE at the table's tool point: 107.2 mm p95 | 620 s | 2.68 |

Other: one `claude -p "Reply with the single word: ok"` auth smoke test in the isolated config, $0.10.

# Session 4 (overnight feature build: controller + MCP, rollouts + Gymnasium env, URDF import)

Caps: 6 subagent spawns (max 3 at once), no `/sim-anything` end-to-end runs needed.

**Running tally:** subagents 4 / 6 (615k tokens)

| # | Purpose | Outcome | Tokens |
|---|---|---|---|
| 1 | controller (`simanything/control.py`: IK, joint control) + MCP server + `serve` CLI + examples/use_model.py | done: 11 commits merged; IK 1e-6 m on 200 toy poses; MCP checked over real stdio | 175k |
| 2 | `import-urdf`: official URDF import with collision simplification (primitives / hull / coacd) | done: 8 commits merged (builder gains refactored into `servo_gains`); FK = MuJoCo's own URDF compile to 1e-9 | 184k |
| 3 | `rollouts` exporter + Gymnasium `ReachEnv` + examples/train_reach.py | done: 7 commits merged; check_env passes; IK expert solves the env | 129k |
| 4 | read-only ponytail review of tonight's code | done: 6 findings, all fixed with tests (MCP parallel-call segfault, mm .dae units, scene contacts in `collides`, mimic joints, file:// paths, zero episodes) | 128k |
