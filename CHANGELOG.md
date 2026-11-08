# Changelog

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
