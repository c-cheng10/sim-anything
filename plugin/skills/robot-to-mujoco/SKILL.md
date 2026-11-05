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
* **Sourced means read directly, not inferred.** Anything that took a step of
  your own judgement goes in `estimates`, even when the raw numbers come from
  a source: drawing dimensions without labels that you mapped to links, an
  axis direction or sign read off a picture, a letter-to-dimension mapping
  ("A" = upper arm?) the drawing does not spell out, a value scaled from a
  photo, a reach definition the source does not state. Cite the raw source in
  `sources.md` and explain the inference in `notes`.
* `sources` values are **http(s) URLs** (a `#page=N` anchor is fine) or
  `doc:<path>` for a local document (e.g. `doc:runs/acme_a6/manual.pdf`);
  nothing else (no "datasheet", no prose). Keys in `sources` and entries in
  `estimates` are spec field paths and must **match real spec fields exactly**
  (`joints[2].effort_limit`, `joints[*].dh`, `reach.measured_to`); the checker
  reports a path that names no field as an error, so a typo does not silently
  leave a number uncovered.
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
* **Generated outputs are not sources.** While gathering, never read other
  runs (`runs/`, `benchmark/runs/`, any other run directory), HANDOFF or
  RESULTS files, evaluation outputs, or the git history of this repository:
  they hold models and numbers produced earlier, not evidence. Sources are
  external public documents only. (Your own `runs/<slug>/` files from this
  task are fine to read and edit.)

## Workflow

All paths below are relative to the directory you run commands from (the
repository root, or the user's project root): the robot's files live in
`runs/<slug>/` (`spec.yaml`, `sources.md`) and the loop run directory is
`runs/<slug>/run/`. `<slug>` is lowercase with underscores (`ur5e`,
`kuka_iiwa14`). The CLI is `sim-anything` (or `python -m simanything.cli`).

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
5. **Prefer the most authoritative primary source**: the manufacturer's own
   document for the exact variant > a peer-reviewed paper quoting it > anything
   else. A **second-hand** source (forum post, reseller/distributor copy of a
   datasheet, third-party blog or wiki, a search-engine excerpt of a page you
   could not open) may be used only when nothing primary is available; mark it
   as such in `sources.md` (e.g. `second-hand: reseller copy of the v2 datasheet`)
   and in `notes`, and say so in your summary.

### (b) Classify the kinematic source, then choose the convention

Decide which of these your kinematics come from and **write it in `notes`**
as the first sentence (e.g. `Kinematic source: published DH table (manufacturer
support article, primary).`). If several exist, use the highest one on the list
that is primary:

1. **Published DH table** -> `dh_standard` or `dh_modified`. Copy every row
   exactly: same values, same signs, same units (set `units`), same theta
   offsets. Do not "clean it up".
2. **Published screw-axis (product-of-exponentials) table, or a "home
   configuration + joint axes" table** (each joint's axis direction and a point
   on it, all in the base frame, at one stated zero pose; plus the tool pose at
   that pose) -> `offset`, converted exactly as described below.
3. **Dimension drawing** (link lengths/offsets drawn on the arm at a stated
   pose) -> `offset`, with the drawing's pose as q = 0: each joint gets
   `origin` (xyz + rpy of the joint frame in the parent link frame) and
   `axis`. Labelled dimensions are sourced (cite the drawing); anything you had
   to map or infer is an estimate (see the rule above).
4. **Inferred** (no table or drawing; lengths from reach figures, photos,
   similar models) -> `offset`, every inferred value in `estimates`, and say
   plainly in `notes` and your summary that the kinematics are inferred.

**Converting a home-configuration / screw-axis table to `offset`** (exact, no
approximation). Use the table's zero pose as q = 0 and keep every frame
parallel to the base frame (all `rpy: [0, 0, 0]`), so every axis can be copied
in base-frame coordinates:

* Let `p_i` be a point on joint i's axis and `w_i` its unit direction, both in
  the base frame at the zero pose; `p_0` is the base origin `[0, 0, 0]`.
  From a space-frame screw axis `S_i = (w_i, v_i)` with `|w_i| = 1`, a point is
  `p_i = w_i × v_i` (because `v_i = -w_i × p_i`). For a prismatic joint
  (`w_i = 0`), the axis is `v_i` and `p_i` may be any convenient point, e.g. `p_{i-1}`.
  Body-frame screw axes `B_i` are relative to the tool frame at home `M`:
  convert first (`S_i = Ad_M B_i`, i.e. `w = R_M w_b`, `p = R_M p_b + t_M`).
* Joint i: `origin.xyz = p_i - p_{i-1}`, `origin.rpy = [0, 0, 0]`,
  `axis = w_i` (keep the published sign: it is the positive direction).
* Tool: `ee.origin.xyz = t_M - p_n` and `ee.origin.rpy` = the roll/pitch/yaw of
  the home tool rotation `R_M` (URDF fixed-axis convention), if it is given.
* Any point on the axis gives the same model, so you may pick whichever is
  written in the source; copy coordinates in the source's units.
* Verify: the FK at q = 0 must reproduce the table's tool position `t_M`
  (command below), and a joint's sign must match the table.

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
check: `python -c "from simanything.spec import load_spec; import numpy as np; s=load_spec('runs/<slug>/spec.yaml'); print(np.round(s.chain().fk([0]*s.dof)[:3,3],4))"`
(the flange position in metres at q = 0).

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
* **Reach definitions.** Set `reach.measured_from` / `reach.measured_to` only
  from what the source states: from the base axis horizontally
  (`base_axis_horizontal`), from the shoulder joint (`shoulder`) or the base
  origin (`base_origin`), to the flange (`ee_site`) or the wrist centre
  (`wrist_center`). If the source gives a reach figure without saying from
  where to where, pick the most likely definition **and list
  `reach.measured_from` and `reach.measured_to` in `estimates`** (with your
  reasoning in `notes`); the reach check then reports a mismatch as a warning
  instead of an error. Leaving both fields out of the spec also counts as an
  assumed definition (`shoulder` -> `ee_site`), and the check says so. **Never switch the reach endpoints just to make the
  check pass**: a reach error with sourced link lengths and a stated definition
  points at a misread table (row shift, units, wrong variant), so look there.
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
sim-anything validate runs/<slug>/spec.yaml   # exit 0: "ok: ..."; exit 1: "FAILED: ..." plus each problem
```

Schema errors name each field by its path (`joints[2].effort_limit`) and
suggest the closest valid name for a misspelt key.

### (d) Loop until it passes

```bash
sim-anything loop runs/<slug>/spec.yaml --run-dir runs/<slug>/run --max-iter 8 --note "initial spec from datasheet v2.3"
```

* Exit **0**: all error-severity checks pass. It prints a one-line summary
  (plus any warnings); details are in `runs/<slug>/run/check.json`.
* Exit **1**: read the printed summary or `runs/<slug>/run/check.json`: each
  failed check has `message` and `fix_hint` naming spec fields. Read every
  failed check, not a fixed list: new check ids may appear. Edit the spec (fix
  the interpretation, not sourced numbers), then run `loop` again with a
  `--note` saying what you changed and why. Warnings don't block, but read them.
* Exit **2**: max iterations reached, or you changed the spec after the last
  allowed iteration (the summary then says the changed spec was NOT built or
  checked). Stop, and report the latest checked result and its remaining
  failures honestly.

Running `loop` again with an unchanged spec does not start a new iteration.
Each iteration is archived in `runs/<slug>/run/iterations/iter_NN/`;
`runs/<slug>/run/history.json` lists them. The renders and `report.html` /
`report.md` are rewritten after **every** iteration, so they always show the
latest one (a build failure removes the renders).

**Starting over** (e.g. you switched to a different source or convention and
the old iterations would only confuse the history): delete the run directory
(`rm -rf runs/<slug>/run`) or use a new `--run-dir`; numbering restarts at 1.
Never edit files inside the run directory by hand.

### (e) Look at the result

`runs/<slug>/run/renders/{front,side,top}.png`, `runs/<slug>/run/report.html`
and `report.md` describe the latest iteration. Open the PNGs (Read tool)
and compare with product photos and the drawing: link proportions, which way
the shoulder/elbow bend, wrist layout, flange position. A model can pass every
check and still be wrong (e.g. a mirrored axis): fix and loop again if so.

### (f) Summarise

Report briefly: robot and variant; the kinematic source class (DH table /
screw-axis or home-config table / drawing / inferred), the convention and the
source, and any second-hand sources; which numbers are sourced vs estimated
(and why); checks status (errors and warnings) and number of iterations;
anything that still looks off; paths to `runs/<slug>/spec.yaml`,
`runs/<slug>/sources.md`, `runs/<slug>/run/report.html` and the renders.

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
  Kinematic source: published DH table (manufacturer support article, primary).
  Link radii estimated from photos scaled by the 128 mm base diameter.
  j1 effort from datasheet "size 4 joint: 150 Nm"; other torques not published, omitted.
```
