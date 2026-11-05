# Benchmark results

Generated models are scored against MuJoCo Menagerie reference models
(`benchmark/robots.yaml`, commit 98a70c5 of mujoco_menagerie). Menagerie is an
external reference; it is not redistributed. Reproduce with
`python benchmark/make_map.py <round>` then `python benchmark/run_eval.py <round>`
(2,000 samples, seed 0). Metric definitions: docs/CONTRACTS.md section 5.

Each model was written blind by an agent that saw only `benchmark/inputs/<id>/`,
the web and the tool's own docs/code; never Menagerie or robot-description files.

## Round 0 (dev set, first blind run)

| Robot | DH published | Checks | Iterations | EE pos mean / p95 / max (mm) | Orient p95 aligned (deg) | Limit MAE (deg) | Mass cand / ref (kg) | Conventions fitted | Score |
|---|---|---|---|---|---|---|---|---|---|
| UR5e | True | all pass | 2 | 1.0 / 1.4 / 1.5 | 0.0 | 30.0 | 20.60 / 20.99 | yaw +180°, 0 sign flip(s), 0 offset(s) | 82.2 |
| Franka Emika Panda | True | all pass | 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 17.80 / 16.69 | yaw +0°, 0 sign flip(s), 0 offset(s) | 97.2 |
| Kinova Gen3 (7-DOF) | True | all pass | 1 | 0.4 / 0.4 / 0.5 | 0.0 | 0.2 | 8.20 / 8.19 | yaw +0°, 0 sign flip(s), 0 offset(s) | 98.7 |
| UFactory xArm 7 | True | fail: reach | 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.7 | 13.70 / 11.32 | yaw +0°, 0 sign flip(s), 0 offset(s) | 92.5 |
| KUKA LBR iiwa 14 R820 | False | all pass | 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 29.90 / 30.61 | yaw +0°, 1 sign flip(s), 0 offset(s) | 98.9 |
| Trossen ViperX 300 S | False | all pass | 1 | 0.3 / 0.3 / 0.3 | 0.0 | 3.0 | 2.85 / 3.74 | yaw +0°, 0 sign flip(s), 0 offset(s) | 88.6 |

Median p95 EE position error, robots with published DH: 0.2 mm (n=4)

### How to read this

* **Position error** is the EE (tool flange) position difference over 2,000
  random configurations, after discrete convention alignment (joint sign flips,
  multiples-of-90-degree zero offsets and base yaw; listed per robot). The
  reference side is expressed in its mounting-base body frame (xArm's Menagerie
  model stands on a 120 mm pedestal that the datasheet arm does not have).
* Sub-millimetre errors are expected when the manufacturer publishes a
  kinematic table and the reference model was built from the same data; they
  say the agent copied the table and conventions correctly, not that primitive
  geoms are accurate shapes. Geometry, inertia and collision shapes are not
  scored beyond total mass.
* **UR5e limit MAE 30 deg** is one joint: the datasheet gives ±360 deg for the
  elbow, the reference model limits it to ±180 deg. Not fixed: the datasheet
  value is the sourced one.
* **xArm 7 fails the reach check** (772 mm to the flange vs a rated 700 mm with
  an unstated definition). The agent correctly refused to change sourced
  numbers to pass. The kinematics are exact (0.0 mm).
* **ViperX 300 S:** no flange; the agent put the EE at the gripper-mount face on
  the wrist-rotate link, and the orchestrator mapped it to the reference's
  `gripper_link` body origin (the same physical point). Mass is a density
  estimate (no published arm mass).
* **Masses** differ where the datasheet total (e.g. Panda 17.8 kg, xArm 13.7 kg)
  differs from the reference model's body-mass sum.

### Caveats on sources

* Manufacturer sites were blocked from this environment, so most values come
  from web-search excerpts of the cited pages, not the pages themselves.
* Kinova Gen3's DH table came from a third-party GitHub design note that
  quotes Kinova's parameters (6 of 7 lengths cross-checked against the official
  user guide's length table); KUKA iiwa's link lengths come from a dimension
  table whose letter meanings the agent inferred; ViperX's kinematics come from
  Trossen's documentation (screw-axis table) read from its docs repository.

### Evaluator changes made while scoring round 0

The evaluator was corrected after the first round-0 outputs exposed alignment
bugs (none of these changes touch the generated models or know robot values):
base-yaw fitting separate from joint-1 offsets; optional mounting-base frames
in the mapping; multi-start steepest-descent convention fitting that prefers
the simplest equivalent conventions (the first version got stuck in a local
minimum on Kinova, reporting 570 mm for a model that matches to 0.4 mm).
