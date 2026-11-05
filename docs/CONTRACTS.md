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
| `sim-anything render model.xml -o renders/` | Writes `front.png`, `side.png`, `top.png` (home pose) and prints a JSON map view->path plus `"backend"`. `--backend auto|mujoco|matplotlib`. | 0 |
| `sim-anything report run_dir/` | Writes `run_dir/report.html` (self-contained, images base64-embedded) and `run_dir/report.md`. | 0 |
| `sim-anything eval candidate.xml --reference ref.xml --map map.yaml --json` | Score candidate vs reference (section 5). `--samples N` (default 2000), `--seed`, `-o eval.json` also writes the file. | 0 |
| `sim-anything loop spec.yaml --run-dir runs/x --max-iter 8 [--note "what changed"] [--json]` | ONE build+check iteration, recorded in the run dir (section 3). On pass it also renders and writes the report. | 0 passed, 1 checks failed (agent should edit the spec and run `loop` again), 2 max iterations reached without passing |
| `sim-anything validate spec.yaml` | Schema validation + list numbers lacking a source/estimate. | 0 ok, 1 otherwise |
| `sim-anything schema [-o file]` | Print/write the spec JSON schema (`docs/spec.schema.json`). | 0 |

`loop` is deliberately a single step: the FIX step is the agent reading
`check.json` fix hints and editing `spec.yaml` between calls.

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
  renders/ front.png side.png top.png         # written when checks pass (or at max iter)
  report.html report.md                       # written when checks pass (or at max iter)
```

Iteration numbering starts at 1. Calling `loop` again after `status` is
`passed` or `max_iter_reached` starts no new iteration unless the spec
changed (then it continues numbering, still capped by `--max-iter`).
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
  "n_checks": 11, "n_failed": 1, "n_errors": 1,
  "mujoco_version": "3.3.0",
  "checks": [
    {"id": "reach", "pass": false, "measured": 0.951, "expected": 0.85, "tolerance": 0.05,
     "severity": "error", "message": "max reach 0.951 m is 11.9% above rated 0.850 m",
     "fix_hint": "Reach is too long: check link lengths a2/a3 (joints[1].dh.a, joints[2].dh.a) against the datasheet, and whether rated reach is measured to the wrist centre or the flange (reach.measured_to).",
     "details": {"samples": 5000, "measured_from": "shoulder"}}
  ]
}
```

`passed` is true iff no check with `severity == "error"` failed. `warning`
and `info` checks never block. Every failed check MUST carry a concrete
`fix_hint` naming spec field paths where possible.

### Check ids (in this order)

| id | What | Pass condition | Severity |
|---|---|---|---|
| `compiles` | MJCF loads with the pinned MuJoCo | loads, `mj_forward` finite | error |
| `joint_structure` | joint count, types (hinge/slide) and order vs spec | exact match by name and type, in chain order | error |
| `ee_site` | site named `spec.ee.name` exists on the last body | exists | error |
| `joint_limits` | MJCF `range` vs spec limits (SI) | all limited joints match within 1e-3 rad / 1e-4 m; a joint without spec limits -> warning | error |
| `reach` | max of the reach metric over 5,000 uniform random configurations within limits, the best 8 polished by a short local search, vs `spec.reach` | within ±5% (relative) | error (info + pass if spec has no reach) |
| `total_mass` | sum of body masses vs `spec.total_mass` | within ±5% | error (info + pass if absent) |
| `inertia_valid` | every non-world body: mass > 0, principal inertias > 0, triangle inequality `A+B >= C` (1e-9 slack) | all bodies | error |
| `self_collision_home` | contacts at the home pose between bodies that are not parent/child | none with penetration > 1 mm | error |
| `stable_hold` | 2 s simulation at home under gravity, actuators commanded to home | no NaN/instability warning, max joint drift < 0.05 rad (hinge) / 5 mm (slide), final max joint speed < 0.1 | error |
| `actuators` | each spec joint driven by exactly one actuator | all | error |
| `sources_complete` | `spec.uncovered_fields()` is empty | empty | error |

Reach metric (`spec.reach.measured_from` -> `measured_to`):
`shoulder` = world position of the 2nd joint's body origin at the home pose
(1st joint's for 1-DOF, or when the first two joints are hinges with parallel
axes, i.e. planar/SCARA-style arms; the report records the choice); `base_origin` = robot base frame origin;
`base_axis_horizontal` = distance from the 1st joint axis line, measured
perpendicular to it. `ee_site` = the EE site; `wrist_center` = origin of the
body of joint `dof-2` (0-based; the 2nd-to-last joint's body, which for a
spherical wrist lies on the wrist centre).

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
joint_conventions:                       # optional, one per mapped joint:
  - {sign: 1, offset: 0.0}               #   q_ref = sign * q_cand + offset
fit_conventions: true                    # default true; see below
```

`simanything.schemas.Mapping` is the schema. `candidate.joints` and
`reference.joints` must have the same length; extra reference joints (e.g.
gripper fingers) are held at their `qpos0`.

**Conventions.** Zero positions and positive directions are conventions that
differ between a datasheet and a simulation model. If `joint_conventions` is
given it is used as-is. Otherwise, if `fit_conventions` is true, the evaluator
picks, per hinge joint, `sign ∈ {+1,-1}` and `offset ∈ {0, +π/2, -π/2, π}`
minimising mean EE position error on 256 configurations (coordinate descent,
2 sweeps), and reports the choice in `conventions` with
`conventions_fitted: true`. Only these discrete conventional choices are
searched; no continuous parameters are fitted.

### Sampling

`n_samples` configurations are drawn uniformly (seeded) from the intersection
of the candidate's limits and the reference's limits mapped into candidate
coordinates. An unlimited joint imposes no constraint; [-π, π] is used only
when both sides are unlimited. If an intersection is empty the candidate range
is used and a note is added. Convention-fit ties (joints that don't move the
EE point, e.g. a final roll) are broken by aligned orientation error. Slide
joints are never convention-fitted and don't count toward the limit MAE; an
unlimited joint is compared as [-π, π] in limit diffs.

### Metrics (`simanything.schemas.EvalResult`)

* `ee_position_error_mm`: |p_cand - p_ref| of the mapped EE points, both in
  world coordinates (mean, p95, max).
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
 "conventions": [{"sign": 1, "offset": 3.14159}, ...], "conventions_fitted": true,
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
* Parent/child contacts are excluded (MuJoCo default); the builder may also add `<exclude>` for bodies
  whose origins coincide (zero-length links in spherical wrists) and documents it in an XML comment.

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
