# HANDOFF

Resume from this file and BUDGET.md alone. Updated at every phase boundary and round.

## State
- Phases 1-3 complete: all components merged (cherry-picked from agent worktrees), pytest green, `loop` verified end to end on a toy spec (fail -> fix -> pass, renders + report written and inspected).
- Next: Phase 4 blind dev benchmark (6 subagents, max 5 concurrent).

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
- D10: ViperX reference includes gripper finger joints; they are unmapped and held at qpos0; reference mass includes the gripper.

## Known issues
- Network: manufacturer sites (universal-robots.com, frankaemika.github.io, kinovarobotics.com, ufactory.cc, trossenrobotics.com, kuka.com, even wikipedia) are unreachable from the shell and from WebFetch; only WebSearch works. Benchmark inputs are built from search excerpts. Kinova (DH values) and KUKA (link lengths) inputs have the largest gaps.
- Evaluator: when a reference base frame is yawed 180 deg relative to the datasheet frame, the fitted joint-1 offset of pi also shifts the joint-limit comparison by 180 deg (limit MAE inflated). Watch in results.
- Matplotlib fallback renderer only depth-sorts whole geoms.

## Fix list (Phase 5 triage)
(empty)
