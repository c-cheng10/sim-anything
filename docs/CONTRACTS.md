# sim-anything contracts

This file is the source of truth for interfaces between components. Code that
disagrees with it is a bug (in the code or in this file; fix both together).

Units everywhere in generated artifacts are SI (m, rad, kg, N·m, s) unless a
field name says otherwise (`_mm`, `_deg`).

## 1. Pipeline

```
GATHER (agent)  ->  spec.yaml  --build-->  model.xml  --check-->  check.json
      ^                                                     |
      +-------------------- FIX (agent edits spec) <--------+
                    loop until passed or --max-iter
REPORT: renders/*.png + report.html + report.md
EVAL:   model.xml vs reference.xml through map.yaml -> eval.json
```

The LLM only writes `spec.yaml` (and, rarely, hand edits to MJCF for exotic
mechanisms). All XML is written by `builder.py`.

## 2. CLI

All commands are subcommands of the `sim-anything` console script
(`python -m simanything.cli` also works).

| Command | Behaviour | Exit code |
|---|---|---|
| `sim-anything build spec.yaml -o model.xml` | Validate spec, write MJCF. | 0 ok, 1 invalid spec / build error (message on stderr) |
| `sim-anything check model.xml --spec spec.yaml --json` | Run all checks. `--json` prints the check report (section 4). Without `--spec`, spec-dependent checks are reported as `info` and pass. `--seed N` (default 0). | 0 if `passed` (no failed `error`-severity check), else 1 |
| `sim-anything render model.xml -o renders/` | Writes `front.png`, `side.png`, `top.png` (home pose) and prints a JSON map view->path plus `"backend"`. `--backend auto|mujoco|matplotlib`. | 0, 1 if the model does not load or rendering fails (message on stderr) |
| `sim-anything report run_dir/` | Writes `run_dir/report.html` (self-contained, images base64-embedded) and `run_dir/report.md`. | 0 |
| `sim-anything eval candidate.xml --reference ref.xml --map map.yaml --json` | Score candidate vs reference (section 5). `--samples N` (default 2000), `--seed`, `-o eval.json` also writes the file. | 0, 1 on an invalid map, a model that does not load or a mapped joint/site/body that does not exist (message on stderr) |
| `sim-anything loop spec.yaml --run-dir runs/x --max-iter 8 [--note "what changed"] [--json]` | ONE build+check iteration, recorded in the run dir (section 3). Every new iteration (pass, fail or build failure) re-renders and rewrites the report, so they always match `check.json`. | 0 passed, 1 checks failed (agent should edit the spec and run `loop` again), 2 max iterations reached without passing, or the spec changed but the cap kept it from being built and checked |
| `sim-anything validate spec.yaml` | Schema validation + list numbers lacking a source/estimate. Last line `ok: ...` on success, `FAILED: ...` otherwise. | 0 ok, 1 otherwise |
| `sim-anything schema [-o file]` | Print/write the spec JSON schema (`docs/spec.schema.json`). | 0 |

`loop` is deliberately a single step: the FIX step is the agent reading
`check.json` fix hints and editing `spec.yaml` between calls.

**Errors.** No command prints a Python traceback for bad input; it prints a
message to stderr (`build failed: ...`, `eval failed: ...`, `render failed:
...`, `FAILED: ...`) and exits 1. Command-line usage errors (a missing input
file, an unknown option or command, `--max-iter 0`, a missing required option)
also exit 1, with the usage line and the error on stderr; exit code 2 is never
a usage error (for `loop` it means "max iterations reached"). Schema errors (spec in `validate`, `build`,
`check`, `loop`; mapping file in `eval`) list *every* error, one per line, as
`<path>: <message>` with the repo's bracket field paths
(`joints[2].effort_limit`, `sources['joints[0].dh']`), no pydantic URLs, and
for an unknown key the closest valid field names (`joints[2].efort_limit:
unknown field; did you mean 'effort_limit'?`). `check` also prints them to
stderr before running (the spec-dependent checks then fail); in `loop` they
are the message of the failed `compiles` check, and the fix hint names the
spec file that was passed in. Formatter: `simanything.errors.describe_exception`.

## 3. Run directory layout (`loop`)

```
run_dir/
  spec.yaml                 # copy of the spec used by the latest iteration
  model.xml                 # latest built model
  check.json                # latest check report
  history.json              # schemas.History
  iterations/
    iter_01/ spec.yaml model.xml check.json   # model.xml absent if the build failed
    iter_02/ ...
  renders/ front.png side.png top.png         # rewritten every iteration; removed when the build failed
  report.html report.md                       # rewritten every iteration
```

After every new iteration (passed, failed, or build failure) `loop` deletes
`renders/`, re-renders `model.xml` if one was built, and rewrites
`report.html`/`report.md`, so the run directory never shows the result of an
earlier iteration: renders, report and `check.json` always describe the
latest iteration. To start over, delete the run directory (or pass a new
`--run-dir`); numbering then starts again at 1.

Iteration numbering starts at 1. Calling `loop` again after `status` is
`passed` or `max_iter_reached` starts no new iteration unless the spec
changed (then it continues numbering, still capped by `--max-iter`).
Rerunning an unchanged spec recomputes the status against the `--max-iter`
of that call: `passed` (exit 0) if the latest iteration passed, otherwise
`max_iter_reached` (exit 2) only while the iterations run reach the cap, and
`running` (exit 1, fix needed) after the cap was raised.
A changed spec is never reported as passed without being checked: if the cap
keeps it from being built, `loop` returns status `max_iter_reached`, exit 2,
and a summary saying the changed spec was NOT built or checked (even when the
previous spec passed; `history.json` keeps that pass). `--max-iter` must be >= 1.
A build failure counts as an iteration whose check report contains a single
failed `compiles` check with the build error as message.

`loop --json` prints `simanything.loop.LoopOutcome`:
`{iteration, status, passed, exit_code, n_errors, failed_ids, run_dir, summary,
fix_hints: [{id, fix_hint}]}`.

## 4. Check report JSON

`simanything.schemas.CheckReport` (`to_json_dict()` uses the `pass` alias):

```json
{
  "model": "runs/ur5e/model.xml",
  "spec": "runs/ur5e/spec.yaml",
  "passed": false,
  "n_checks": 14, "n_failed": 1, "n_errors": 1,
  "mujoco_version": "3.3.0",
  "checks": [
    {"id": "reach", "pass": false, "measured": 0.951, "expected": 0.85, "tolerance": 0.05,
     "severity": "error", "message": "max reach 0.951 m is 11.9% above rated 0.850 m",
     "fix_hint": "Reach is too long: re-check the lengths that set the measured reach (joints[1].dh.a, joints[2].dh.a, joints[3].dh.d; largest effect first) against the datasheet. Also check `units.length` (mm vs m). Confirm the source's reach definition: reach.measured_to = ee_site (vs wrist_center), reach.measured_from = shoulder. If the source does not state the reach definition, list reach.measured_from/measured_to in `estimates` instead of switching endpoints until it passes.",
     "details": {"samples": 5000, "measured_from": "shoulder"}}
  ]
}
```

`passed` is true iff no check with `severity == "error"` failed. `warning`
and `info` checks never block. Every failed check MUST carry a concrete
`fix_hint` naming spec field paths where possible.

### Check ids (in this order; 14 checks, `simanything.check.CHECK_IDS`)

Spec-dependent checks (`joint_structure`, `ee_site`, `kinematics_match`, `joint_limits`, `reach`,
`total_mass`, `actuators`, `sources_complete`) pass as `info` without `--spec`. `mass_plausibility`
and `collision_exclusions` are model checks (the mass-per-reach part needs the spec).

| id | What | Pass condition | Severity |
|---|---|---|---|
| `compiles` | MJCF loads with the pinned MuJoCo | loads, `mj_forward` finite | error |
| `joint_structure` | joint count, types (hinge/slide) and order vs spec | exact match by name and type, in chain order | error |
| `ee_site` | site named `spec.ee.name` exists on the last body | exists | error |
| `kinematics_match` | model vs `spec.chain().fk(q)` on 20 seeded configurations (home + 19 uniform within the spec limits): EE site position and orientation, every joint's world axis direction and (hinges) the distance of its anchor from the spec axis line | all within 1e-6 m / 1e-6 rad (measured: the max of each) | error (info + fail, non-blocking, while `joint_structure`/`ee_site` problems prevent it from running) |
| `joint_limits` | MJCF `range` vs spec limits (SI) | all limited joints match within 1e-3 rad / 1e-4 m; a joint without spec limits -> warning | error |
| `reach` | max of the reach metric over 5,000 uniform random configurations within limits, the best 8 polished by a short local search, vs `spec.reach` | within ±5% (relative) | error; warning when `reach.value`, `reach.measured_from` or `reach.measured_to` is an estimate (`is_estimate`: covered by `estimates` and not more specifically by `sources`), with the message saying the definition is assumed / the value is estimated; a mismatch beyond ±30% always stays an error (no definition explains it; usually a units or structure slip). A spec without `reach` gives a failed warning ("no rated reach: the chain is not checked against any external dimension"). The fix hint names the spec lengths that change the measured quantity, ranked by d(reach)/d(ln length) at the arg-max configuration (`details.length_sensitivity`) |
| `total_mass` | sum of body masses vs `spec.total_mass` | within ±5% | error (info + pass if absent) |
| `mass_plausibility` | apparent density of every body (mass / volume of its primitive geoms; bodies with meshes or no geoms skipped); mass share of every moving link (bodies grouped by weld); total mass per metre of `spec.reach.value` (when the spec has a reach) | density in [100, 20000] kg/m^3, every moving link >= 0.5% of the total mass, >= 0.1 kg per metre of reach | warning |
| `inertia_valid` | every non-world body: mass > 0, principal inertias > 0, triangle inequality `A+B >= C` (1e-9 slack) | all bodies | error |
| `self_collision_home` | contacts at the home pose between bodies that are not parent/child (and not excluded) | none with penetration > 1 mm | error |
| `collision_exclusions` | every `<exclude>` pair of the model, with its reason read from the `<!-- body1 / body2: reason -->` comment before it (section 7), listed in the message and `details.excluded` | every pair is parent/child (incl. welded) or separated only by zero-length links (all bodies after the ancestor's child sit at their parent's origin) | warning |
| `stable_hold` | 2 s simulation at home under gravity, actuators commanded to home | no NaN/instability warning, max joint drift < 0.05 rad (hinge) / 5 mm (slide), final max joint speed < 0.1 | error |
| `actuators` | each spec joint driven by exactly one actuator | all | error |
| `sources_complete` | `uncovered_fields(spec)` (numbers without a source/estimate), `bad_source_values(spec)` (a `sources` value that is not an http(s) URL or `doc:<relative path>`), `unmatched_keys(spec)` (a `sources`/`estimates` key naming no field of the spec: out-of-range index, unknown field, a field of the other convention; null/zero/default fields count as existing); `details` also has `n_numbers`, `n_estimated`, `estimate_fraction` | all three empty; then estimates <= 50% of the numbers | error; warning (fail) when only the estimate fraction exceeds 50% |

Reach metric (`spec.reach.measured_from` -> `measured_to`):
`shoulder` = world position of the 2nd joint's body origin at the home pose
(1st joint's for 1-DOF, or when the first two joints are hinges with parallel
axes, i.e. planar/SCARA-style arms; the report records the choice); `base_origin` = robot base frame origin;
`base_axis_horizontal` = distance from the 1st joint axis line, measured
perpendicular to it. `ee_site` = the EE site; `wrist_center` = origin of the
body of joint `dof-2` (0-based; the 2nd-to-last joint's body, which for a
spherical wrist lies on the wrist centre); an arm with fewer than 3 joints has
no wrist, so `wrist_center` falls back to the EE site (recorded in
`details.notes`).

## 5. Evaluation

### Joint-mapping file (`map.yaml`)

```yaml
robot: ur5e
candidate:
  joints: [shoulder_pan, shoulder_lift, elbow, wrist_1, wrist_2, wrist_3]   # in chain order
  ee: {site: ee_site}
reference:
  joints: [shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint]
  ee: {site: attachment_site}            # or {body: name, pos: [x,y,z], quat: [w,x,y,z]}
  base_body: base                        # optional: compare EE poses in this (fixed) body's frame
joint_conventions:                       # optional, one per mapped joint:
  - {sign: 1, offset: 0.0}               #   q_ref = sign * q_cand + offset
base_yaw: null                           # optional, rad; null = fitted (see below)
fit_conventions: true                    # default true; see below
```

`simanything.schemas.Mapping` is the schema. `candidate.joints` and
`reference.joints` must have the same length; extra reference joints (e.g.
gripper fingers) are held at their `qpos0`.

**Conventions.** Zero positions and positive directions are conventions that
differ between a datasheet and a simulation model. If `joint_conventions` is
given it is used as-is. Otherwise, if `fit_conventions` is true, the evaluator
picks, per hinge joint, `sign ∈ {+1,-1}` and `offset ∈ {0, +π/2, -π/2, π}`
minimising mean EE position error on 256 configurations (steepest descent over
single changes from the identity plus 4 seeded random starts; equal-cost
alternatives resolve to the simplest: identity < sign flip < offset), and
reports the choice in `conventions` with `conventions_fitted: true`. Before
the joints it also considers a candidate base yaw (rotation of the whole
candidate about world z, from the same four angles) unless `base_yaw` is
given; reported as `base_yaw_deg`. A base frame turned relative to the
datasheet frame is a mounting convention; fitting it explicitly keeps it out
of joint 1's offset and the limit comparison. Only these discrete conventional choices are
searched; no continuous parameters are fitted.

### Sampling

`n_samples` configurations are drawn uniformly (seeded) from the intersection
of the candidate's limits and the reference's limits mapped into candidate
coordinates. An unlimited joint imposes no constraint; a default range is used
only when both sides are unlimited: [-π, π] rad for a hinge, [-0.1, 0.1] m for
a slide (`simanything.evaluate.UNLIMITED_SLIDE_RANGE_M`; ±π *metres* would be
meaningless for a linear axis). The same defaults are the candidate bounds of
the convention-fit samples. If an intersection is empty the candidate range
is used and a note is added. Convention-fit ties (joints that don't move the
EE point, e.g. a final roll) are broken by aligned orientation error. Slide
joints are never convention-fitted and don't count toward the limit MAE; in
limit diffs an unlimited joint is compared as its default range ([-π, π] rad
hinge, [-0.1, 0.1] m slide), with a note.

### Metrics (`simanything.schemas.EvalResult`)

* `ee_position_error_mm`: |p_cand - p_ref| of the mapped EE points, both in
  world coordinates, or in each side's `base_body` frame when given (the
  benchmark maps use the robot's mounting base so a pedestal or a world
  placement offset is not counted as model error) (mean, p95, max).
* `ee_orientation_error_deg`: geodesic angle between EE frames, raw.
* `ee_orientation_error_aligned_deg`: same after the best constant tool-frame
  rotation R* (R_ref ≈ R_cand · R*, chordal L2 mean over the samples),
  because tool-frame axis conventions are arbitrary.
* `joint_limits`, `joint_limit_mae_deg`: per-joint candidate vs reference
  bounds (in reference coordinates), and the mean absolute difference over the
  lower and upper bounds of hinge joints, in degrees.
* `mass_*`: total body mass (sum of `body_mass`) of each model; the reference
  sum includes its extra bodies (e.g. a gripper) — read with care.
* `dof_match`: number of candidate joints in the model == number of mapped
  reference joints.

### Score (0–100)

```
pos    = exp(-p95_pos_mm / 25)
orient = exp(-p95_orient_aligned_deg / 10)
limits = exp(-joint_limit_mae_deg / 10)
mass   = exp(-|mass_rel_diff| / 0.2)
dof    = 1 if dof_match else 0
score  = 100 * (0.5 pos + 0.2 orient + 0.15 limits + 0.1 mass + 0.05 dof)
```

### Eval JSON example

```json
{"candidate": "...", "reference": "...", "robot": "ur5e", "n_samples": 2000, "seed": 0,
 "dof_candidate": 6, "dof_reference": 6, "dof_match": true,
 "conventions": [{"sign": 1, "offset": 0.0}, ...], "conventions_fitted": true, "base_yaw_deg": 180.0,
 "ee_position_error_mm": {"mean": 1.2, "p95": 2.0, "max": 3.1},
 "ee_orientation_error_deg": {"mean": 90.0, "p95": 90.0, "max": 90.0},
 "ee_orientation_error_aligned_deg": {"mean": 0.1, "p95": 0.2, "max": 0.3},
 "joint_limits": [{"candidate": "...", "reference": "...", "candidate_range": [-6.28, 6.28],
                   "reference_range": [-6.28, 6.28], "lower_diff": 0.0, "upper_diff": 0.0}],
 "joint_limit_mae_deg": 0.0, "mass_candidate": 20.6, "mass_reference": 21.0,
 "mass_diff": -0.4, "mass_rel_diff": -0.019, "score": 97.3,
 "score_breakdown": {"pos": 0.92, "orient": 0.98, "limits": 1.0, "mass": 0.91, "dof": 1.0},
 "notes": []}
```

## 6. Python API (module boundaries)

| Module | Public API |
|---|---|
| `simanything.spec` | `Spec`, `load_spec(path)`, `dump_spec(spec, path)`, `Spec.to_si()`, `Spec.chain()` / `build_chain(spec) -> Chain` (body poses in SI, DH folded in), `Chain.fk(q) -> 4x4`, `dh_to_offset`, `dh_fk`, `iter_numeric_fields`, `uncovered_fields`, `path_covers`, `is_estimate`, `json_schema()` |
| `simanything.schemas` | `CheckResult`, `CheckReport`, `Mapping`, `EvalResult`, `History`, `IterationRecord` |
| `simanything.builder` | `build_mjcf(spec: Spec) -> str`, `build_file(spec_path, out_path) -> Path` |
| `simanything.check` | `run_checks(model_path, spec_path=None, *, seed=0, n_reach_samples=5000) -> CheckReport` |
| `simanything.evaluate` | `load_mapping(path) -> Mapping`, `evaluate(candidate_path, reference_path, mapping, *, n_samples=2000, seed=0) -> EvalResult` |
| `simanything.render` | `detect_backend() -> str`, `render_views(model_path, out_dir, *, width=640, height=480, backend="auto") -> dict[str, Path | str]` (keys `front`, `side`, `top`, `backend`) |
| `simanything.report` | `write_report(run_dir) -> tuple[Path, Path]` |
| `simanything.loop` | `LoopOutcome`, `loop_step(spec_path, run_dir, *, max_iter=8, note=None) -> LoopOutcome` |

## 7. MJCF produced by the builder

* `<compiler angle="radian" autolimits="true"/>`, gravity on, `<option timestep="0.002"/>` (or smaller).
* One `<body>` per joint, named `<link.name or joint.name + "_link">`, nested in chain order under a
  base body named `base` placed at `spec.base.origin`.
* Joint names equal spec joint names; `range` from spec limits (SI).
* Geoms: primitives only, from the geometry hints (auto-placed when no explicit pose).
* Inertia: explicit `<inertial>` per body from the link mass (or volume x default density 1000 kg/m^3
  scaled so the total matches `spec.total_mass` when given) and the primitive shape.
* One `<position>` actuator per joint named `<joint>_act`, `ctrlrange` = joint range, `forcerange`
  from `effort_limit` when known; gains chosen so the home pose holds under gravity.
* A site named `spec.ee.name` on the last body at the EE offset.
* A `<keyframe name="home">` with the spec `home` values.
* Parent/child contacts are excluded (MuJoCo default). The builder adds `<exclude>` only for:
  1. the base and the first link (parent/child, but MuJoCo does not filter a world-fixed parent);
  2. bodies whose origins coincide (zero-length links, e.g. a spherical wrist), pairwise, together with the
     body whose segment ends at the shared origin (bodies separated only by zero-length links);
  3. a grandparent/grandchild pair (k, k+2) whose capsule/cylinder geoms overlap in every one of 32
     sampled configurations (home + 31 seeded) and, at home, only as two end caps meeting around the
     short middle link: for every contact, with e1, e2 the ends of the two geoms' axis segments adjacent
     to the middle link (nearest its segment), the overlap of the two segments' capsules is at most
     r1 + r2 - |e1 - e2| (+1 mm), i.e. e1 and e2 are the closest points of the two segments, and the
     contact lies within the thicker geom's radius of the middle link's segment. Any box or sphere
     contact between the pair disqualifies it.

  No other overlap is excluded: an oversized primitive, geometry reaching back over a joint or a deep
  overlap is left for `self_collision_home` to report. Each `<exclude>` is preceded by an XML comment
  `<!-- body1 / body2: reason -->`; the `collision_exclusions` check reports them all.

## 8. Benchmark layout

```
benchmark/robots.yaml                     # dev + holdout sets, reference paths (third_party/, gitignored)
benchmark/inputs/<robot>/sources.md       # URLs + quoted values (no simulation model files)
benchmark/inputs/<robot>/facts.yaml       # structured facts extracted from those sources
benchmark/runs/<robot>/roundN/
    spec.yaml                             # what the agent wrote
    run/                                  # the loop run directory (section 3)
    NOTES.md                              # agent's short report: sources used, assumptions, iterations
    map.yaml, eval.json                   # written by the orchestrator, not the generating agent
benchmark/RESULTS.md
```

Blindness: agents that write specs never read `third_party/`, Menagerie, URDF/MJCF/SDF/xacro
robot-description files, or any eval output. Fixes to the tool are generic: no robot-specific
code or constants.
