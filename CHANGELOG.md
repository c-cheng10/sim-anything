# Changelog

## 0.4.0

- Control: `simanything.control.Arm` drives any built or imported model: state, joint targets, damped
  least-squares IK (about 1e-6 m on 200 random toy-arm poses), smooth joint-space `move_to` (no path
  planning), renders, and a self-collision test that ignores free scene objects. Gravity compensation is
  enabled in memory.
- Agents: `sim-anything serve model.xml` runs an MCP server (stdio) with get_state, set_joint_targets,
  step, move_ee, reset and render; tool calls run one at a time (parallel calls used to crash it).
- Data: `sim-anything rollouts` records smooth, self-collision-free random motion as npz episodes plus
  meta.json (optional 128x128 frames); `simanything.gym_env.ReachEnv` is a Gymnasium reach task.
- Import: `sim-anything import-urdf` loads an official URDF with MuJoCo's importer (kinematics, limits
  and inertials kept), converts meshes (units to metres), keeps visuals, adds servos, a home keyframe
  and an EE site, and simplifies collision (`hull` default, `primitives`, `coacd`). Rejects mimic joints.
  Checked on a public UR5 URDF: 15/15 checks.
- Optional extras: `mcp`, `rl`, `mesh`; CI installs them so their tests run.

## 0.3.0

- Checker: new `drawing` check (15 checks). A spec can carry published drawing dimensions (`drawing`:
  flange or wrist-centre height above the base, or horizontal distance from joint 1, at a stated pose,
  each sourced); the built model is compared against them (2 mm default) with a fix hint that ranks
  the lengths that move each dimension. Catches misread table rows that leave a spec self-consistent.
  spec-writer and source-auditor use it.
- Evaluator: `kinematics_score` (EE position and orientation only) and `disagreements` (joint limits and
  total mass where the candidate's datasheet value and the reference differ), so sourced values are
  no longer read as model error. `score` is unchanged; all benchmark rounds re-scored.
- Scout: at least two searches for an official kinematic table before a drawing; rejects garbled
  search excerpts; keeps a cross-checked second-hand table over a primary list that omits offsets.
- Plugin well-formedness test (frontmatter, agent names, versions) in CI.
- Verified: install from GitHub (`pip install git+...`, marketplace `c-cheng10/sim-anything`) and one
  real `/sim-anything UR3e` run (7 min, $2.31).

## 0.2.0

- Plugin: `/sim-anything` now runs a four-agent team (source scout, spec writer, loop fixer,
  read-only source auditor) handing off through `runs/<slug>/` files, with one rework round when
  the auditor says "not ready". New `/sim-anything-audit` command. Verified with one end-to-end
  run (WidowX 250 6DOF: all four agents ran, 14/14 checks, auditor "ready with caveats").
- Checker: a world-fixed base overlapping its first link now counts as a self-collision (MuJoCo
  does not filter that pair; hand-edited models without the builder's `<exclude>` passed before).
- Lean: one shared configuration sampler and motion transform for builder and checker; removed the
  always-zero `ChainJoint.qpos_offset`.
- Internal build logs moved to `docs/dev/`.

## 0.1.0

- First usable draft: spec schema, builder, 14 checks, loop, renders/report, evaluator,
  `robot-to-mujoco` skill and `/sim-anything` command, blind benchmark (6 dev + 2 holdout arms).
