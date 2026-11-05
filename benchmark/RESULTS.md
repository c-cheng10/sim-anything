# Benchmark results

Generated models are scored against MuJoCo Menagerie reference models
(`benchmark/robots.yaml`, commit 98a70c5 of mujoco_menagerie). Menagerie is an
external reference; it is not redistributed. Reproduce with
`python benchmark/make_map.py <round>` then `python benchmark/run_eval.py <round>`
(2,000 samples, seed 0). Metric definitions: docs/CONTRACTS.md section 5.

Each model was written blind by an agent that saw only `benchmark/inputs/<id>/`,
the web and the tool's own docs/code; never Menagerie or robot-description files.

## Round-over-round (dev set)

All rounds scored with the final evaluator (rounds 0 and 1 were re-scored after
the round-2 evaluator fix; their numbers did not change).

| Robot | Checks R0 / R1 / R2 | p95 EE error (mm) R0 / R1 / R2 | Score R0 / R1 / R2 | R2 warnings |
|---|---|---|---|---|
| UR5e | pass / pass / pass | 1.4 / 1.4 / 1.4 | 82.2 / 82.2 / 82.2 | reach (definition estimated) |
| Franka Emika Panda | pass / pass / pass | 0.0 / 0.0 / 0.0 | 97.2 / 97.2 / 97.2 | collision_exclusions |
| Kinova Gen3 (7-DOF) | pass / pass / pass | 0.4 / 0.4 / **24.5** | 98.7 / 98.7 / 68.3 | joint_limits (continuous joints) |
| UFactory xArm 7 | **fail: reach** / pass / pass | 0.0 / 0.0 / 0.0 | 92.5 / 92.5 / 92.5 | reach (definition estimated), collision_exclusions |
| KUKA LBR iiwa 14 R820 | pass / pass / pass | 0.0 / 0.0 / 0.0 | 98.9 / 98.9 / 98.9 | estimate share 51% |
| Trossen ViperX 300 S | pass / pass / pass | 0.3 / 0.3 / **7.6** | 88.6 / 91.2 / 74.1 | reach (rated reach includes gripper), estimate share 61% |
| **All error checks pass** | **5/6 / 6/6 / 6/6** | median p95 over DH-publishing robots: 0.2 / 0.2 / 0.7 | | |

**What the rounds show.**
* Round 1 changed the tool, not the models: 14 checks instead of 11, stricter
  sources and collision exclusions, and reach treated as advisory when its
  definition is not stated (never beyond ±30%). xArm 7 moved from fail to pass
  because of that rule; its kinematics were already exact.
* Round 2 (fresh runs after the round-2 fixes) **improved no metric and
  regressed two robots**, so the refinement loop stopped (diminishing returns):
  * Kinova Gen3: the round-2 agent, following the stricter rule that
    second-hand sources must be flagged and primary ones preferred, did not use
    the third-party transcription of Kinova's DH table that rounds 0-1 used
    (Kinova's own guide was unreachable). It built the arm from the official
    guide's link-length table and left out two lateral offsets (5.4 and 6.4 mm)
    it could not assign to joints, with every joint origin listed as an
    estimate: 24.5 mm p95 instead of 0.4 mm. The fitted conventions (7 sign
    flips, base yaw 180°) reflect its inferred axis directions.
  * ViperX 300 S: the round-2 agent did not reach Trossen's screw-axis table
    (rounds 0-1 read it from Trossen's documentation repository) and estimated
    the shoulder height (120 mm) from photo proportions; the table value is
    127.05 mm: 7.6 mm p95 instead of 0.3 mm.
  Both regressions trace to which public source an agent found or accepted,
  not to tool bugs, and both were flagged honestly as estimates in the specs.
  Run-to-run variance in source discovery is the dominant error source.
* Median p95 over the robots whose makers publish DH tables (UR5e, Panda, xArm 7,
  Kinova) is 0.7 mm in round 2; over the robots whose round-2 agent actually
  used a DH table (UR5e, Panda, xArm 7) it is 0.0 mm. The goal was < 10 mm.

## Round 0 (dev set, first blind run)

| Robot | Kinematic source | Checks | Iterations | EE pos mean / p95 / max (mm) | Orient p95 aligned (deg) | Limit MAE (deg) | Mass cand / ref (kg) | Conventions fitted | Score |
|---|---|---|---|---|---|---|---|---|---|
| UR5e | DH table | all pass | 2 | 1.0 / 1.4 / 1.5 | 0.0 | 30.0 | 20.60 / 20.99 | yaw +180°, 0 sign flip(s), 0 offset(s) | 82.2 |
| Franka Emika Panda | DH table (modified) | all pass | 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 17.80 / 16.69 | yaw +0°, 0 sign flip(s), 0 offset(s) | 97.2 |
| Kinova Gen3 (7-DOF) | DH table (via third-party quote) | all pass | 1 | 0.4 / 0.4 / 0.5 | 0.0 | 0.2 | 8.20 / 8.19 | yaw +0°, 0 sign flip(s), 0 offset(s) | 98.7 |
| UFactory xArm 7 | DH table (modified) | fail: reach | 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.7 | 13.70 / 11.32 | yaw +0°, 0 sign flip(s), 0 offset(s) | 92.5 |
| KUKA LBR iiwa 14 R820 | dimension table | all pass | 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 29.90 / 30.61 | yaw +0°, 1 sign flip(s), 0 offset(s) | 98.9 |
| Trossen ViperX 300 S | screw-axis (PoE) table | all pass | 1 | 0.3 / 0.3 / 0.3 | 0.0 | 3.0 | 2.85 / 3.74 | yaw +0°, 0 sign flip(s), 0 offset(s) | 88.6 |

Median p95 EE position error, robots with published DH: 0.2 mm (n=4)

### How to read this

* **Position error** is the EE (tool flange) position difference over 2,000
  random configurations, after discrete convention alignment (joint sign flips,
  multiples-of-90-degree zero offsets and base yaw; listed per robot). The
  reference side is expressed in its mounting-base body frame (xArm's Menagerie
  model stands on a 120 mm pedestal that the datasheet arm does not have).
* **Every robot here had a complete public kinematic description** (DH table,
  screw-axis table or dimension table). Sub-millimetre errors then mean the agent
  found and transcribed it correctly (the reference models appear to be built
  from the same data: the remaining 0.2-1.5 mm come from rounding in the
  references, e.g. 0.163 vs the published 0.1625 m for UR5e). They do not say
  primitive geoms are accurate shapes; geometry, inertia and collision shapes
  are not scored beyond total mass.
* **Score** (0-100) also counts joint limits and mass, where the candidate's
  value is the sourced datasheet value and the reference may have made a
  different choice: UR5e loses ~14 points because the datasheet gives ±360°
  for the elbow while the reference limits it to ±180°; Panda and xArm lose
  points because the datasheet total mass (17.8 kg, 13.7 kg) differs from the
  reference's body-mass sum. About a quarter of the score (aligned orientation,
  DOF match) is nearly free for any correctly structured chain. Read the
  sub-metrics, not just the score.
* **UR5e** passed only after its agent changed the reach endpoint from the
  flange (0.969 m, 14% over the rated 0.850 m) to the wrist centre (0.828 m) in
  iteration 2. UR does not state the definition; this is an interpretation
  chosen after a failure (disclosed in its NOTES.md). The round-1 tool treats
  reach as advisory when the definition is not stated by a source.
* **xArm 7 fails the reach check** (772 mm to the flange vs a rated 700 mm,
  definition not stated). Its agent kept the sourced numbers.
* **KUKA iiwa**: the fitted A4 sign flip absorbs an axis direction the agent
  marked as an estimate; the metric cannot distinguish a convention from a
  wrong estimate.
* **ViperX 300 S:** no flange; the agent put the EE at the gripper-mount face on
  the wrist-rotate link; the reference side uses its `gripper_link` body origin
  (chosen in `reference_sides.yaml` before the run; a constant 0.26 mm remains).
  Mass is a density estimate (no published arm mass).

### Caveats on sources (from the round-1 benchmark audit)

* Manufacturer sites were blocked from this environment, so most values come
  from web-search excerpts of the cited pages, not the pages themselves.
* Kinova Gen3: the whole DH table and base frame come from one third-party
  GitHub design note whose attribution to the Kinova user guide is an unfilled
  placeholder; 6 of 7 lengths were cross-checked against the official guide's
  length table, the 12.8 mm offset was not.
* KUKA iiwa: link lengths come from an unlabelled dimension table (letters
  C/D/E/F) in search summaries of a brochure for a related product (LBR Med);
  the letter-to-link mapping is the agent's inference but was recorded as
  sourced rather than estimated.
* ViperX: Trossen's published screw-axis table is probably generated from
  Trossen's own robot description, the same lineage as the reference model
  (suspected, not verified).
* Weaker secondary sources: UR5e per-joint torques (UR forum post), Panda
  speeds/limits (reseller copy of the datasheet), KUKA torques/speeds (garbled
  search extract of a spec PDF).
* Blindness is self-reported: generation agents ran on a machine where the
  reference models existed on disk. Evidence against copying: no
  reference-only number appears in any spec, and the specs differ from the
  references exactly where the references differ from the datasheets (UR5e
  0.1625 m, Kinova offsets, ViperX 70 mm and shoulder limits, xArm joint
  ranges). From round 1 on, the reference models are moved out of the
  repository tree while generation agents run.

### Evaluator changes made while scoring round 0

The evaluator was corrected after the first round-0 outputs exposed alignment
bugs (none of these changes touch the generated models or know robot values):
base-yaw fitting separate from joint-1 offsets; optional mounting-base frames
in the mapping; multi-start steepest-descent convention fitting that prefers
the simplest equivalent conventions (the first version got stuck in a local
minimum on Kinova, reporting 570 mm for a model that matches to 0.4 mm). The
round-1 auditor re-ran the final evaluator on all six maps and reproduced every
number, and confirmed with an independent FK script and sensitivity tests
(+10 mm on one Panda link gives exactly 10.0 mm).

## Round 1 (dev set, fresh blind runs with the round-1 tool)

| Robot | Kinematic source | Checks | Iterations | EE pos mean / p95 / max (mm) | Orient p95 aligned (deg) | Limit MAE (deg) | Mass cand / ref (kg) | Conventions fitted | Score |
|---|---|---|---|---|---|---|---|---|---|
| UR5e | DH table | all pass | 2 | 1.0 / 1.4 / 1.5 | 0.0 | 30.0 | 20.60 / 20.99 | yaw +180°, 0 sign flip(s), 0 offset(s) | 82.2 |
| Franka Emika Panda | DH table (modified) | all pass | 2 | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 17.80 / 16.69 | yaw +0°, 0 sign flip(s), 0 offset(s) | 97.2 |
| Kinova Gen3 (7-DOF) | DH table (via third-party quote) | all pass | 2 | 0.4 / 0.4 / 0.5 | 0.0 | 0.2 | 8.20 / 8.19 | yaw +0°, 0 sign flip(s), 0 offset(s) | 98.7 |
| UFactory xArm 7 | DH table (modified) | all pass | 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.7 | 13.70 / 11.32 | yaw +0°, 0 sign flip(s), 0 offset(s) | 92.5 |
| KUKA LBR iiwa 14 R820 | dimension table | all pass | 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 29.90 / 30.61 | yaw +0°, 0 sign flip(s), 0 offset(s) | 98.9 |
| Trossen ViperX 300 S | screw-axis (PoE) table | all pass | 1 | 0.3 / 0.3 / 0.3 | 0.0 | 3.0 | 3.31 / 3.74 | yaw +0°, 0 sign flip(s), 0 offset(s) | 91.2 |

Median p95 EE position error, robots with published DH: 0.2 mm (n=4)

* Fresh runs: agents could not read earlier rounds; the reference models were
  moved out of the repository tree while they ran. One agent reported seeing a
  round-0 agent's downloaded copy of Trossen's public docs page and the
  orchestrator's rebuild of the round-0 ViperX candidate in a shared scratch
  folder (no reference model); it says it did not use them.
* Kinova's DH table is still from the same third-party transcription (Kinova's
  own guide stayed unreachable); KUKA's letter-to-link mapping and all joint
  axis directions are now listed as estimates; xArm's and UR5e's reach
  definitions are listed as estimates.
* Two agents' first iteration had a units slip (a reach in mm in a metres spec
  or vice versa); the reach check caught one directly, and the other exposed a
  loophole (a 1000x reach mismatch only warned because the definition was
  estimated) that the tool now closes (mismatches beyond ±30% stay errors).

## Round 2 (dev set, fresh blind runs with the final tool)

| Robot | Kinematic source | Checks | Iterations | EE pos mean / p95 / max (mm) | Orient p95 aligned (deg) | Limit MAE (deg) | Mass cand / ref (kg) | Conventions fitted | Score |
|---|---|---|---|---|---|---|---|---|---|
| UR5e | DH table | all pass | 1 | 1.0 / 1.4 / 1.5 | 0.0 | 30.0 | 20.60 / 20.99 | yaw +180°, 0 sign flip(s), 0 offset(s) | 82.2 |
| Franka Emika Panda | DH table (modified) | all pass | 2 | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 17.80 / 16.69 | yaw +0°, 0 sign flip(s), 0 offset(s) | 97.2 |
| Kinova Gen3 (7-DOF) | dimension table (official guide lengths, lateral offsets omitted) | all pass | 1 | 15.6 / 24.5 / 24.8 | 0.0 | 0.2 | 8.20 / 8.19 | yaw +180°, 7 sign flip(s), 0 offset(s) | 68.3 |
| UFactory xArm 7 | DH table (modified) | all pass | 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.7 | 13.70 / 11.32 | yaw +0°, 0 sign flip(s), 0 offset(s) | 92.5 |
| KUKA LBR iiwa 14 R820 | dimension table | all pass | 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 29.90 / 30.61 | yaw +0°, 0 sign flip(s), 0 offset(s) | 98.9 |
| Trossen ViperX 300 S | reach/offset tables (shoulder height estimated) | all pass | 1 | 7.0 / 7.6 / 7.7 | 0.0 | 3.0 | 2.09 / 3.74 | yaw +0°, 0 sign flip(s), 0 offset(s) | 74.1 |

Median p95 EE position error, robots with published DH: 0.7 mm (n=4)

* Reference models were moved to a hidden location outside the repository and
  the shared scratch area while the agents ran; agents were told not to read
  earlier runs, logs, results or git history.
* "Kinematic source" for Kinova and ViperX differs from earlier rounds (see above).
* Panda's home pose is listed as an estimate the agent recalled from Franka's
  example code without a source; it does not affect the scored kinematics.
