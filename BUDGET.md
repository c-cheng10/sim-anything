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

## Refinement rounds used: 0 / 3
