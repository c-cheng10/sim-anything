# Benchmark results

Generated models are scored against MuJoCo Menagerie reference models
(`benchmark/robots.yaml`, commit 98a70c5 of mujoco_menagerie). Menagerie is an
external reference; it is not redistributed. Reproduce with
`python benchmark/make_map.py <round>` then `python benchmark/run_eval.py <round>`
(2,000 samples, seed 0). Metric definitions: docs/CONTRACTS.md section 5.

Each model was written blind by an agent that saw only `benchmark/inputs/<id>/`,
the web and the tool's own docs/code; never Menagerie or robot-description files.

## Holdout set (run once, with the final tool)

The holdout robots were never used during development or refinement. One blind
agent generated both with the final tool (reference models hidden outside the
repository while it ran), and they were scored exactly once. These are the
honest generalisation numbers.

| Robot | Kinematic source | Checks | Iterations | EE pos mean / p95 / max (mm) | Orient p95 aligned (deg) | Limit MAE (deg) | Mass cand / ref (kg) | Conventions fitted | Score | Kin. score |
|---|---|---|---|---|---|---|---|---|---|---|
| UR10e | DH table | all pass | 1 | 16.6 / 17.2 / 17.7 | 0.0 | 30.0 | 33.30 / 32.70 | yaw +180°, 0 sign flip(s), 0 offset(s) | 60.0 | 64.5 |
| UFactory Lite 6 | DH table (modified) | all pass | 2 | 1.0 / 1.3 / 1.4 | 0.0 | 0.0 | 8.00 / 7.58 | yaw +0°, 0 sign flip(s), 0 offset(s) | 94.9 | 96.3 |

Datasheet vs reference disagreements (listed, not counted in the kinematics score):

* UR10e: elbow limits: candidate [-360, 360] deg vs reference elbow_joint [-180, 180] deg
* UFactory Lite 6: total mass: candidate 8.00 kg vs reference 7.58 kg (+6%)

Median p95 EE position error, robots with published DH: 9.3 mm (n=2)

* **UR10e, 17.2 mm p95, is almost entirely a reference-model difference.** The
  agent copied UR's published DH table exactly (d6 = 0.11655 m to the tool
  flange). The Menagerie UR10e places its `attachment_site` 0.100 m past the
  wrist-3 frame (the UR5e's flange distance), 16.55 mm shorter than UR's
  published value, so the flange points differ by ~16.6 mm in every pose.
  Diagnostic only (not the official number): measuring the reference at UR's
  published flange distance on the same wrist-3 axis gives 0.7 mean / 1.1 p95 /
  1.3 max mm, the same rounding-level residual as the UR5e. The official score
  above is unchanged; the mapping was fixed before the run and was not altered
  after seeing results.
* UR10e also loses ~14 score points on joint limits for the same reason as the
  UR5e (datasheet ±360° on the elbow vs ±180° in the reference). One search
  extract gave ±160° for the elbow; the agent kept ±360° and noted the conflict.
* **UFactory Lite 6, 1.3 mm p95:** UFactory's modified DH table copied exactly;
  passed on iteration 2 after replacing auto-placed capsules (which collided at
  the folded zero pose) with explicit estimated geometry.
* Both passed all error checks (UR10e in 1 iteration, Lite 6 in 2).
* As in the dev set, all values came from web-search excerpts because
  manufacturer hosts were blocked; torques for three UR10e joints come from a
  UR forum post (second-hand), the wrist-1 torque is an estimate.

## Team variance (session 3, 0.3.0 four-agent team, blind)

Planned: every dev robot twice through the real `/sim-anything` team (12 runs). Run: **one team run each
for the two robots that varied most** (Kinova Gen3, ViperX 300 S). The session cap was 8 end-to-end runs and
$15; one run went to the GitHub-install check, and two earlier attempts at these runs were stopped by the
account usage limit ($4.05, not scored). Plugin and CLI 0.3.0 were installed from GitHub into an isolated
config, the reference models were moved outside the repository while the agents ran, and the transcripts show
all four agents running in both runs. Manufacturer and WebFetch access was blocked; values came from search
excerpts (ViperX: Trossen's documentation repository on GitHub).

| Robot | Kinematic source | Checks | Iterations | EE pos mean / p95 / max (mm) | Orient p95 aligned (deg) | Limit MAE (deg) | Mass cand / ref (kg) | Conventions fitted | Score | Kin. score |
|---|---|---|---|---|---|---|---|---|---|---|
| Kinova Gen3 (7-DOF) | inferred from the guide's link-length list (search excerpts of user-uploaded copies) | all pass | 2 | 12.8 / 13.1 / 13.2 | 0.0 | 0.8 | 8.20 / 8.19 | yaw +0°, 4 sign flip(s), 0 offset(s) | 78.4 | 70.8 |
| Trossen ViperX 300 S | screw-axis (PoE) table, EE at the table's home tool point | all pass | 1 | 107.2 / 107.2 / 107.2 | 0.0 | 3.0 | 2.69 / 3.74 | yaw +0°, 0 sign flip(s), 0 offset(s) | 39.3 | 29.6 |

Datasheet vs reference disagreements (listed, not counted in the kinematics score):

* Kinova Gen3 (7-DOF): joint_2 limits: candidate [-126, 126] deg vs reference joint_2 [-128, 128] deg
* Kinova Gen3 (7-DOF): joint_6 limits: candidate [-117, 117] deg vs reference joint_6 [-120, 120] deg
* Trossen ViperX 300 S: shoulder limits: candidate [-101, 101] deg vs reference shoulder [-106, 72] deg
* Trossen ViperX 300 S: wrist_angle limits: candidate [-107, 130] deg vs reference wrist_angle [-107, 128] deg
* Trossen ViperX 300 S: total mass: candidate 2.69 kg vs reference 3.74 kg (-28%)

p95 EE error across all runs so far (single-agent rounds 0 / 1 / 2, then team run 1):

| Robot | R0 | R1 | R2 | Team 1 | Mean | Range |
|---|---|---|---|---|---|---|
| Kinova Gen3 (7-DOF) | 0.4 | 0.4 | 24.5 | 13.1 | 9.6 | 0.4 - 24.5 |
| Trossen ViperX 300 S | 0.3 | 0.3 | 7.6 | 107.2 | 28.9 | 0.3 - 107.2 |

**Did the auditor and the drawing check reduce the spread? Not measurably.**
* Kinova: the team found neither Kinova's DH table nor a zero-pose drawing (no `drawing` dimension, so the new
  check could not run) and inferred the kinematics from the guide's link-length list, labelling every joint
  placement an estimate and predicting "about 10 mm" error itself. 13.1 mm p95: between the earlier runs.
* ViperX: the team found Trossen's screw-axis table, reproduced it exactly and added two drawing dimensions
  that the `drawing` check confirmed within 1 mm. Its EE site, though, is the table's home tool point (177 mm
  past the wrist-angle axis; the agent noted it is probably on the gripper), while the reference point is the
  gripper-link origin fixed before round 0 (D15). The error is the same 107.2 mm in every configuration
  (mean = p95 = max), the signature of a constant tool offset, not a joint error. The mapping was not changed
  after seeing this.
* The auditor said "ready with caveats" both times and flagged the right weaknesses (Kinova's inferred
  kinematics, ViperX's EE point), but it cannot supply sources the scout did not find.
* Two runs per robot cannot estimate spread; the dominant error is still which public source an agent can reach
  and how it reads ambiguous points (here, where the "end effector" is).

## Round-over-round (dev set)

All rounds scored with the final evaluator (rounds 0 and 1 were re-scored after
the round-2 evaluator fix; their numbers did not change). Session 3 re-scored
every round once more to add the kinematics score (EE position and orientation
only; docs/CONTRACTS.md section 5); no other number changed. The re-run picks a
different but kinematically equivalent convention for Kinova rounds 0-1 (1 sign
flip, 1 offset instead of none; same error, limits and score).

| Robot | Checks R0 / R1 / R2 | p95 EE error (mm) R0 / R1 / R2 | Score R0 / R1 / R2 | Kin. score R0 / R1 / R2 | R2 warnings |
|---|---|---|---|---|---|
| UR5e | pass / pass / pass | 1.4 / 1.4 / 1.4 | 82.2 / 82.2 / 82.2 | 96.1 / 96.1 / 96.1 | reach (definition estimated) |
| Franka Emika Panda | pass / pass / pass | 0.0 / 0.0 / 0.0 | 97.2 / 97.2 / 97.2 | 100.0 / 100.0 / 100.0 | collision_exclusions |
| Kinova Gen3 (7-DOF) | pass / pass / pass | 0.4 / 0.4 / **24.5** | 98.7 / 98.7 / 68.3 | 98.7 / 98.7 / 55.4 | joint_limits (continuous joints) |
| UFactory xArm 7 | **fail: reach** / pass / pass | 0.0 / 0.0 / 0.0 | 92.5 / 92.5 / 92.5 | 100.0 / 100.0 / 100.0 | reach (definition estimated), collision_exclusions |
| KUKA LBR iiwa 14 R820 | pass / pass / pass | 0.0 / 0.0 / 0.0 | 98.9 / 98.9 / 98.9 | 100.0 / 100.0 / 100.0 | estimate share 51% |
| Trossen ViperX 300 S | pass / pass / pass | 0.3 / 0.3 / **7.6** | 88.6 / 91.2 / 74.1 | 99.3 / 99.3 / 81.3 | reach (rated reach includes gripper), estimate share 61% |
| **All error checks pass** | **5/6 / 6/6 / 6/6** | median p95 over DH-publishing robots: 0.2 / 0.2 / 0.7 | | | |

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

| Robot | Kinematic source | Checks | Iterations | EE pos mean / p95 / max (mm) | Orient p95 aligned (deg) | Limit MAE (deg) | Mass cand / ref (kg) | Conventions fitted | Score | Kin. score |
|---|---|---|---|---|---|---|---|---|---|---|
| UR5e | DH table | all pass | 2 | 1.0 / 1.4 / 1.5 | 0.0 | 30.0 | 20.60 / 20.99 | yaw +180°, 0 sign flip(s), 0 offset(s) | 82.2 | 96.1 |
| Franka Emika Panda | DH table (modified) | all pass | 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 17.80 / 16.69 | yaw +0°, 0 sign flip(s), 0 offset(s) | 97.2 | 100.0 |
| Kinova Gen3 (7-DOF) | DH table (via third-party quote) | all pass | 1 | 0.4 / 0.4 / 0.5 | 0.0 | 0.2 | 8.20 / 8.19 | yaw +0°, 1 sign flip(s), 1 offset(s) | 98.7 | 98.7 |
| UFactory xArm 7 | DH table (modified) | fail: reach | 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.7 | 13.70 / 11.32 | yaw +0°, 0 sign flip(s), 0 offset(s) | 92.5 | 100.0 |
| KUKA LBR iiwa 14 R820 | dimension table | all pass | 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 29.90 / 30.61 | yaw +0°, 1 sign flip(s), 0 offset(s) | 98.9 | 100.0 |
| Trossen ViperX 300 S | screw-axis (PoE) table | all pass | 1 | 0.3 / 0.3 / 0.3 | 0.0 | 3.0 | 2.85 / 3.74 | yaw +0°, 0 sign flip(s), 0 offset(s) | 88.6 | 99.3 |

Datasheet vs reference disagreements (listed, not counted in the kinematics score):

* UR5e: elbow limits: candidate [-360, 360] deg vs reference elbow_joint [-180, 180] deg
* Franka Emika Panda: total mass: candidate 17.80 kg vs reference 16.69 kg (+7%)
* UFactory xArm 7: joint2 limits: candidate [-117, 116] deg vs reference joint2 [-118, 120] deg
* UFactory xArm 7: joint4 limits: candidate [-6, 225] deg vs reference joint4 [-11, 225] deg
* UFactory xArm 7: total mass: candidate 13.70 kg vs reference 11.32 kg (+21%)
* Trossen ViperX 300 S: shoulder limits: candidate [-101, 101] deg vs reference shoulder [-106, 72] deg
* Trossen ViperX 300 S: wrist_angle limits: candidate [-107, 130] deg vs reference wrist_angle [-107, 128] deg
* Trossen ViperX 300 S: total mass: candidate 2.85 kg vs reference 3.74 kg (-24%)

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
* **Kinematics score** (0-100) counts only EE position and aligned orientation,
  so it measures the model; limits and mass are listed under "datasheet vs
  reference disagreements" instead.
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

| Robot | Kinematic source | Checks | Iterations | EE pos mean / p95 / max (mm) | Orient p95 aligned (deg) | Limit MAE (deg) | Mass cand / ref (kg) | Conventions fitted | Score | Kin. score |
|---|---|---|---|---|---|---|---|---|---|---|
| UR5e | DH table | all pass | 2 | 1.0 / 1.4 / 1.5 | 0.0 | 30.0 | 20.60 / 20.99 | yaw +180°, 0 sign flip(s), 0 offset(s) | 82.2 | 96.1 |
| Franka Emika Panda | DH table (modified) | all pass | 2 | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 17.80 / 16.69 | yaw +0°, 0 sign flip(s), 0 offset(s) | 97.2 | 100.0 |
| Kinova Gen3 (7-DOF) | DH table (via third-party quote) | all pass | 2 | 0.4 / 0.4 / 0.5 | 0.0 | 0.2 | 8.20 / 8.19 | yaw +0°, 1 sign flip(s), 1 offset(s) | 98.7 | 98.7 |
| UFactory xArm 7 | DH table (modified) | all pass | 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.7 | 13.70 / 11.32 | yaw +0°, 0 sign flip(s), 0 offset(s) | 92.5 | 100.0 |
| KUKA LBR iiwa 14 R820 | dimension table | all pass | 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 29.90 / 30.61 | yaw +0°, 0 sign flip(s), 0 offset(s) | 98.9 | 100.0 |
| Trossen ViperX 300 S | screw-axis (PoE) table | all pass | 1 | 0.3 / 0.3 / 0.3 | 0.0 | 3.0 | 3.31 / 3.74 | yaw +0°, 0 sign flip(s), 0 offset(s) | 91.2 | 99.3 |

Datasheet vs reference disagreements (listed, not counted in the kinematics score):

* UR5e: elbow limits: candidate [-360, 360] deg vs reference elbow_joint [-180, 180] deg
* Franka Emika Panda: total mass: candidate 17.80 kg vs reference 16.69 kg (+7%)
* UFactory xArm 7: joint2 limits: candidate [-117, 116] deg vs reference joint2 [-118, 120] deg
* UFactory xArm 7: joint4 limits: candidate [-6, 225] deg vs reference joint4 [-11, 225] deg
* UFactory xArm 7: total mass: candidate 13.70 kg vs reference 11.32 kg (+21%)
* Trossen ViperX 300 S: shoulder limits: candidate [-101, 101] deg vs reference shoulder [-106, 72] deg
* Trossen ViperX 300 S: wrist_angle limits: candidate [-107, 130] deg vs reference wrist_angle [-107, 128] deg
* Trossen ViperX 300 S: total mass: candidate 3.31 kg vs reference 3.74 kg (-12%)

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

| Robot | Kinematic source | Checks | Iterations | EE pos mean / p95 / max (mm) | Orient p95 aligned (deg) | Limit MAE (deg) | Mass cand / ref (kg) | Conventions fitted | Score | Kin. score |
|---|---|---|---|---|---|---|---|---|---|---|
| UR5e | DH table | all pass | 1 | 1.0 / 1.4 / 1.5 | 0.0 | 30.0 | 20.60 / 20.99 | yaw +180°, 0 sign flip(s), 0 offset(s) | 82.2 | 96.1 |
| Franka Emika Panda | DH table (modified) | all pass | 2 | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 17.80 / 16.69 | yaw +0°, 0 sign flip(s), 0 offset(s) | 97.2 | 100.0 |
| Kinova Gen3 (7-DOF) | dimension table (official guide lengths, lateral offsets omitted) | all pass | 1 | 15.6 / 24.5 / 24.8 | 0.0 | 0.2 | 8.20 / 8.19 | yaw +180°, 7 sign flip(s), 0 offset(s) | 68.3 | 55.4 |
| UFactory xArm 7 | DH table (modified) | all pass | 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.7 | 13.70 / 11.32 | yaw +0°, 0 sign flip(s), 0 offset(s) | 92.5 | 100.0 |
| KUKA LBR iiwa 14 R820 | dimension table | all pass | 1 | 0.0 / 0.0 / 0.0 | 0.0 | 0.0 | 29.90 / 30.61 | yaw +0°, 0 sign flip(s), 0 offset(s) | 98.9 | 100.0 |
| Trossen ViperX 300 S | reach/offset tables (shoulder height estimated) | all pass | 1 | 7.0 / 7.6 / 7.7 | 0.0 | 3.0 | 2.09 / 3.74 | yaw +0°, 0 sign flip(s), 0 offset(s) | 74.1 | 81.3 |

Datasheet vs reference disagreements (listed, not counted in the kinematics score):

* UR5e: elbow limits: candidate [-360, 360] deg vs reference elbow_joint [-180, 180] deg
* Franka Emika Panda: total mass: candidate 17.80 kg vs reference 16.69 kg (+7%)
* UFactory xArm 7: joint2 limits: candidate [-117, 116] deg vs reference joint2 [-118, 120] deg
* UFactory xArm 7: joint4 limits: candidate [-6, 225] deg vs reference joint4 [-11, 225] deg
* UFactory xArm 7: total mass: candidate 13.70 kg vs reference 11.32 kg (+21%)
* Trossen ViperX 300 S: shoulder limits: candidate [-101, 101] deg vs reference shoulder [-106, 72] deg
* Trossen ViperX 300 S: wrist_angle limits: candidate [-107, 130] deg vs reference wrist_angle [-107, 128] deg
* Trossen ViperX 300 S: total mass: candidate 2.09 kg vs reference 3.74 kg (-44%)

Median p95 EE position error, robots with published DH: 0.7 mm (n=4)

* Reference models were moved to a hidden location outside the repository and
  the shared scratch area while the agents ran; agents were told not to read
  earlier runs, logs, results or git history.
* "Kinematic source" for Kinova and ViperX differs from earlier rounds (see above).
* Panda's home pose is listed as an estimate the agent recalled from Franka's
  example code without a source; it does not affect the scored kinematics.
