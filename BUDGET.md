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
| 26 | 6 | holdout (once): ur10e + ufactory_lite6 | running |
| 23 | 5 r2 | fixer D: CLI/loop/check/builder/spec/skill | done: 9 fixes merged (resumed once after a usage-limit stop) |

## Refinement rounds used: 2 / 3 (round 1: checks 5/6 -> 6/6; round 2 improved no metric (Kinova and ViperX accuracy regressed from stricter/less available sources) -> loop stopped). Spawn 26 reached -> Phase 6.
