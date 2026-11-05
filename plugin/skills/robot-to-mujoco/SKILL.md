---
name: robot-to-mujoco
description: Reverse-engineer a real robot arm into a verified MuJoCo simulation from public information (datasheets, manuals, product pages). Use when asked to build, model, or simulate a specific robot arm in MuJoCo from its specs. Gathers sourced specs into spec.yaml, then runs the sim-anything build/check loop until the model passes, and writes renders plus an HTML/Markdown report.
---

# robot-to-mujoco: robot arm -> verified MuJoCo model (sim-anything)

You write exactly one file, `spec.yaml`. Deterministic code builds the MJCF,
checks it, renders it and writes the report. Your job is to get the numbers
right and prove where each one came from.

## The rule that matters most: never invent numbers

* Every number in `spec.yaml` is either **copied from a source** (listed in
  `sources` with its URL) or **an estimate** (listed in `estimates`, with the
  reasoning written in `notes`). `sim-anything validate` and the
  `sources_complete` check fail otherwise.
* Unknown and not needed? **Omit it.** The schema makes almost everything
  optional (link masses, CoMs, torques, speeds, reach, mass, repeatability).
* Never "fill in from memory" or round a published value. Copy it exactly,
  in the unit the source uses.
* **Never change a sourced number to make a check pass.** If a check
  disagrees with a sourced value, re-read the source and fix the
  *interpretation* (convention, row alignment, units, reach definition). If it
  still disagrees, say so in `notes` and in your summary.
* **Never use robot-description files as sources**: no URDF, MJCF, SDF,
  xacro, MuJoCo Menagerie, ROS `*_description` packages, Gazebo/Isaac assets,
  or GitHub repos that host them. Do not open them, even "just to check".
  Allowed: manufacturer datasheets, product pages, user/service manuals,
  dimension drawings, published DH / kinematic-parameter tables (in manuals,
  support articles, papers that quote the manufacturer).

## Workflow

Run everything from a working directory such as `runs/<slug>/` with
`spec.yaml` there and the loop run directory at `runs/<slug>/run/`.
The CLI is `sim-anything` (or `python -m simanything.cli`).

### (a) Gather sources

1. Search the manufacturer site first: datasheet / technical specifications
   PDF, user manual (kinematics, joint ranges, "dimensions" / "workspace"
   chapter), support articles ("DH parameters", "kinematics").
2. For every number you will use, record in `runs/<slug>/sources.md`: URL,
   date accessed, and the **exact quoted text or table row**. Numbers without
   a quote don't go in the spec.
3. What to collect, in priority order (kinematics dominates the score):
   * DOF, joint order and names, joint types.
   * A DH / kinematic table, or a dimension drawing with link lengths and offsets.
   * Joint ranges (deg) for every joint; note joints that are "continuous" / "infinite".
   * Tool flange offset (distance from the last joint frame / wrist to the flange face).
   * Reach and **how the source defines it** (from what, to what).
   * Total mass, payload, repeatability, max joint speeds, joint torques.
   * Housing diameters / link outer dimensions (for collision geometry).
4. If two sources disagree, prefer the newer manufacturer document for that
   exact product variant and note the conflict.

### (b) Choose the convention

* **Published DH table -> `dh_standard` or `dh_modified`.** Copy every row
  exactly: same values, same signs, same units (set `units`), same
  theta offsets. Do not "clean it up".
* **No table -> `offset`** chain built from dimension drawings: each joint gets
  `origin` (xyz + rpy of the joint frame in the parent link frame, at the
  zero/home configuration) and `axis`. Pick the drawing's zero pose as q = 0.
  Values read off a drawing are sourced (cite the drawing); values you infer
  geometrically (e.g. an axis direction implied by the picture) are estimates.

**Standard vs modified DH: how to tell a table apart**

| Sign | Standard (distal, Denavit-Hartenberg) | Modified (proximal, Craig) |
|---|---|---|
| Column headers | `a_i, alpha_i, d_i, theta_i` | `a_{i-1}, alpha_{i-1}, d_i, theta_i` |
| First row | often `alpha_1 = ±90°`, `a_1` may be non-zero | usually `a_0 = 0, alpha_0 = 0` |
| Last row | often `a = 0, alpha = 0, d = flange distance` | often a separate "flange"/"F" row |
| Transform | `Rz(θ) Tz(d) Tx(a) Rx(α)` | `Rx(α) Tx(a) Rz(θ) Tz(d)` |
| Typical users | UR, many Kinova/KUKA docs | Franka, Craig textbooks, some xArm docs |

If the headers are ambiguous, test both: at q = 0 the FK must reproduce the
drawing (e.g. arm straight up or stretched out, flange height/offset). A quick
check: `python -c "from simanything.spec import load_spec; import numpy as np; s=load_spec('spec.yaml'); print(np.round(s.chain().fk([0]*s.dof)[:3,3],4))"`.

**Pitfalls**

* **Row shift.** In a modified table, row i holds `a_{i-1}, alpha_{i-1}`.
  Putting those values into `dh_standard` shifts every link length by one
  joint (the arm looks plausible but reach and shape are wrong). Store a
  modified row on joint i exactly as published and set `dh_modified`.
* **Flange row in modified tables** (no joint): it is not a joint. Put its
  translation/rotation into `ee.origin` (e.g. `ee.origin.xyz: [0, 0, d_F]`).
* **Signs.** Negative `a` or `d` values (e.g. `a2 = -425`) are real; keep them.
  `alpha` of +90 vs -90 flips the next axis: copy exactly.
* **Theta offsets.** A table column like `theta_i = q_i - 90°` or `+π` means
  `theta_offset: -90` / `180`. This sets where q = 0 is; it matters for the
  home pose and joint limits.
* **Units.** Datasheets are usually mm and deg: set `units: {length: mm, angle: deg}`
  and copy as-is. Radians in a table (`π/2`) -> write `90` with deg units,
  or use rad units for the whole file. Never mix.
* **Reach definitions.** Check what "reach" means in the source:
  from the base axis horizontally (`base_axis_horizontal`), from the shoulder
  joint (`shoulder`) or the base origin (`base_origin`), to the flange
  (`ee_site`) or the wrist centre (`wrist_center`). A reach failure with
  sourced link lengths usually means the definition is wrong, not the lengths.
* **Joint limits** are in the spec's angle unit (deg). "±360°" stays ±360.
  "Continuous"/"infinite": omit `limits` and say so in `notes`.
  Software limits vs mechanical limits: prefer what the manual lists as the
  working range and say which you used.
* **Variants.** Same family, different arm (UR5 vs UR5e, iiwa 7 vs 14,
  6-DOF vs 7-DOF Gen3) have different tables. Check the exact model.

### (c) Write spec.yaml and validate

Schema: `sim-anything schema` (also `docs/spec.schema.json`); conventions are
in the docstring of `simanything/spec.py`. Paths in `sources` / `estimates`
cover themselves and everything below them; `[*]` matches every index.
Zero numbers and defaults need no source.

* Geometry: give each link one or two primitives (capsule/cylinder/box) with a
  radius from a housing diameter if published (sourced), otherwise an estimate
  from photos/drawings. Without explicit `pos`/`fromto`, a capsule spans from
  the joint to the next joint, which is usually right.
* Masses: give `total_mass` if published. Per-link masses are almost never
  published: omit them (the builder distributes `total_mass` by volume) or
  list them as estimates.
* `home`: a non-colliding, stable configuration (zero unless the zero pose
  self-collides); non-zero homes need a source or estimate.

```bash
sim-anything validate spec.yaml      # exit 0: schema ok and every number covered
```

### (d) Loop until it passes

```bash
sim-anything loop spec.yaml --run-dir run --max-iter 8 --note "initial spec from datasheet v2.3"
```

* Exit **0**: all error checks pass; renders and report are written.
* Exit **1**: read the printed summary or `run/check.json`: each failed check
  has `message` and `fix_hint` naming spec fields. Edit `spec.yaml` (fix the
  interpretation, not sourced numbers), then run `loop` again with a `--note`
  saying what you changed and why.
* Exit **2**: max iterations reached. Stop, keep the last result, and report
  the remaining failures honestly.

Running `loop` again with an unchanged spec does not start a new iteration.
Each iteration is archived in `run/iterations/iter_NN/`; `run/history.json`
lists them.

### (e) Look at the result

On pass (or at max iterations), `run/renders/{front,side,top}.png`,
`run/report.html` and `run/report.md` are written. Open the PNGs (Read tool)
and compare with product photos and the drawing: link proportions, which way
the shoulder/elbow bend, wrist layout, flange position. A model can pass every
check and still be wrong (e.g. a mirrored axis): fix and loop again if so.

### (f) Summarise

Report briefly: robot and variant; convention used and its source; which
numbers are sourced vs estimated (and why); checks status and number of
iterations; anything that still looks off; paths to `spec.yaml`,
`sources.md`, `run/report.html` and the renders.

## Example spec.yaml (fictional robot, fictional URLs)

```yaml
name: acme_a6                       # slug
manufacturer: ACME Robotics
model: A6
dof: 6
units: {length: mm, angle: deg}     # copy values in the source's units
convention: dh_standard             # table headers were a_i, alpha_i, d_i, theta_i
joints:                             # one DH row per joint, copied verbatim
  - {name: j1, dh: {a: 0,    alpha: 90,  d: 160}, limits: {lower: -360, upper: 360}, effort_limit: 150,
     link: {geometry: [{shape: cylinder, radius: 60}]}}
  - {name: j2, dh: {a: -420, alpha: 0,   d: 0, theta_offset: -90}, limits: {lower: -360, upper: 360},
     link: {geometry: [{shape: capsule, radius: 55}]}}
  - {name: j3, dh: {a: -380, alpha: 0,   d: 0},   limits: {lower: -160, upper: 160},
     link: {geometry: [{shape: capsule, radius: 45}]}}
  - {name: j4, dh: {a: 0,    alpha: 90,  d: 130}, limits: {lower: -360, upper: 360}}
  - {name: j5, dh: {a: 0,    alpha: -90, d: 100}, limits: {lower: -360, upper: 360}}
  - {name: j6, dh: {a: 0,    alpha: 0,   d: 95},  limits: {lower: -360, upper: 360}}
ee: {name: ee_site}                 # flange already at frame 6 (d6), so no extra offset
total_mass: 19.5
payload: 6
reach: {value: 900, measured_from: base_axis_horizontal, measured_to: ee_site}
sources:                            # field path -> URL (quotes live in sources.md)
  joints[*].dh: https://acme.example/support/a6-dh-parameters
  joints[*].limits: https://acme.example/docs/a6-datasheet.pdf
  joints[0].effort_limit: https://acme.example/docs/a6-datasheet.pdf
  total_mass: https://acme.example/docs/a6-datasheet.pdf
  payload: https://acme.example/docs/a6-datasheet.pdf
  reach: https://acme.example/docs/a6-datasheet.pdf     # "Reach: 900 mm (from base axis)"
estimates:
  - joints[*].link.geometry         # radii estimated from product photos
notes: >
  Link radii estimated from photos scaled by the 128 mm base diameter.
  j1 effort from datasheet "size 4 joint: 150 Nm"; other torques not published, omitted.
```
