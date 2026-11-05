# ur5e

Universal Robots · UR5e (e-Series) · UR5e collaborative robot arm, arm only (no tool); EE site at the tool flange (DH frame 6).

**Status: ✔ PASSED** · 13/14 checks passed · 0 blocking error(s) · 1 iteration(s), status `passed` · MuJoCo 3.3.0

## Views (home pose)

![front view](renders/front.png)
![side view](renders/side.png)
![top view](renders/top.png)

## Verification checks

| Check | Result | Measured | Expected | Tolerance | Severity | Message / fix hint |
|---|---|---|---|---|---|---|
| `compiles` | ✔ pass | — | — | — | error | loads with MuJoCo 3.3.0, mj_forward finite |
| `joint_structure` | ✔ pass | [[shoulder_pan, hinge], [shoulder_lift, hinge], [elbow, hinge], [wrist_1, hinge], [wrist_2, hinge], [wrist_3, hinge]] | [[shoulder_pan, hinge], [shoulder_lift, hinge], [elbow, hinge], [wrist_1, hinge], [wrist_2, hinge], [wrist_3, hinge]] | — | error | 6 joints match by name, type and chain order |
| `ee_site` | ✔ pass | ee_site | ee_site | — | error | site 'ee_site' on last body 'wrist_3_link' |
| `kinematics_match` | ✔ pass | ee_position_m: 4.710e-16, ee_orientation_rad: 1.208e-15, joint_axis_rad: 1.212e-15, joint_position_m: 3.993e-16 | 0 | position_m: 1.000e-06, orientation_rad: 1.000e-06 | error | model kinematics match the spec on 20 configurations (max EE error 4.7e-16 m, 1.2e-15 rad) |
| `joint_limits` | ✔ pass | shoulder_pan: [-6.283, 6.283], shoulder_lift: [-6.283, 6.283], elbow: [-6.283, 6.283], wrist_1: [-6.283, 6.283], wrist_2: [-6.283, 6.283], wrist_3: [-6.283, 6.283] | shoulder_pan: [-6.283, 6.283], shoulder_lift: [-6.283, 6.283], elbow: [-6.283, 6.283], wrist_1: [-6.283, 6.283], wrist_2: [-6.283, 6.283], wrist_3: [-6.283, 6.283] | hinge_rad: 0.001, slide_m: 1.000e-04 | error | all joint ranges match the spec (max diff 4.14e-13) |
| `reach` | ✘ fail | 0.9688 | 0.85 | 0.05 | warning | max reach 0.969 m is 14.0% above rated 0.850 m; warning only: the reach definition is assumed (reach.measured_to listed in estimates)<br>**Fix:** Reach is too long: re-check the lengths that set the measured reach (joints[1].dh.a, joints[2].dh.a, joints[5].dh.d, joints[4].dh.d; largest effect first) against the datasheet. Also check `units.length` (mm vs m). The reach definition (measured_from = base_axis_horizontal, measured_to = ee_site) is assumed (reach.measured_to not stated in the spec or listed in estimates), so this is only a warning. If the source does not state the reach definition, leave reach.measured_from/measured_to unstated or list them in `estimates` instead of switching endpoints until it passes; if it does, write them in the spec and source them. |
| `total_mass` | ✔ pass | 20.6 | 20.6 | 0.05 | error | model mass 20.600 kg within 0.0% of 20.600 kg |
| `mass_plausibility` | ✔ pass | — | — | — | warning | link densities, mass shares and mass per reach are plausible |
| `inertia_valid` | ✔ pass | — | — | — | error | 7 bodies have positive mass and valid inertia |
| `self_collision_home` | ✔ pass | 0 | 0 | 0.001 | error | no self-collision deeper than 1 mm at home (0 touching pairs) |
| `collision_exclusions` | ✔ pass | 0 | 0 | — | warning | 1 excluded pair(s), all parent/child or separated only by zero-length links: base / shoulder_pan_link (parent/child; MuJoCo does not filter a world-fixed parent) |
| `stable_hold` | ✔ pass | 0.01084 | 0 | drift_hinge_rad: 0.05, drift_slide_m: 0.005, final_speed: 0.1 | error | holds home for 2 s: max drift 0.0108, final speed 0.0000 |
| `actuators` | ✔ pass | 6 | 6 | — | error | every spec joint is driven by exactly one actuator |
| `sources_complete` | ✔ pass | 0 | 0 | — | error | every number in the spec has a source or is listed as an estimate (7 of 53 estimated) |

## Key specifications

| | |
|---|---|
| DOF | 6 |
| Total mass | 20.6 kg |
| Reach | 0.85 m (base_axis_horizontal → ee_site) |
| Payload | 5 kg |
| Repeatability | ± 0.03 m |
| Convention | dh_standard |
| Units | length m, angle deg |

## Joints

| # | Joint | Type | Lower | Upper | Effort limit | Velocity limit | Home |
|---|---|---|---|---|---|---|---|
| 1 | `shoulder_pan` | hinge | -360 deg | 360 deg | 150 N·m | 180 deg/s | 0 deg |
| 2 | `shoulder_lift` | hinge | -360 deg | 360 deg | 150 N·m | 180 deg/s | 0 deg |
| 3 | `elbow` | hinge | -360 deg | 360 deg | 150 N·m | 180 deg/s | 0 deg |
| 4 | `wrist_1` | hinge | -360 deg | 360 deg | 28 N·m | 180 deg/s | 0 deg |
| 5 | `wrist_2` | hinge | -360 deg | 360 deg | 28 N·m | 180 deg/s | 0 deg |
| 6 | `wrist_3` | hinge | -360 deg | 360 deg | 28 N·m | 180 deg/s | 0 deg |

## Sources

| Field path | Source |
|---|---|
| `joints[*].dh` | <https://www.universal-robots.com/articles/ur/application-installation/dh-parameters-for-calculations-of-kinematics-and-dynamics/> |
| `joints[*].link.mass` | <https://www.universal-robots.com/articles/ur/application-installation/dh-parameters-for-calculations-of-kinematics-and-dynamics/> |
| `joints[*].link.com` | <https://www.universal-robots.com/articles/ur/application-installation/dh-parameters-for-calculations-of-kinematics-and-dynamics/> |
| `joints[*].limits` | <https://www.universal-robots.com/manuals/EN/TechSheets/UR5e_techsheet_pdf_online/UR5e_techsheet_en.pdf> |
| `joints[*].velocity_limit` | <https://www.universal-robots.com/manuals/EN/TechSheets/UR5e_techsheet_pdf_online/UR5e_techsheet_en.pdf> |
| `joints[4].effort_limit` | <https://www.universal-robots.com/articles/ur/robot-care-maintenance/max-joint-torques-cb3-and-e-series/> |
| `joints[5].effort_limit` | <https://www.universal-robots.com/articles/ur/robot-care-maintenance/max-joint-torques-cb3-and-e-series/> |
| `joints[0].effort_limit` | <https://forum.universal-robots.com/t/maximum-axis-speed-acceleration/13338> |
| `joints[1].effort_limit` | <https://forum.universal-robots.com/t/maximum-axis-speed-acceleration/13338> |
| `joints[2].effort_limit` | <https://forum.universal-robots.com/t/maximum-axis-speed-acceleration/13338> |
| `joints[3].effort_limit` | <https://forum.universal-robots.com/t/maximum-axis-speed-acceleration/13338> |
| `total_mass` | <https://www.universal-robots.com/media/1807465/ur5e_e-series_datasheets_web.pdf> |
| `payload` | <https://www.universal-robots.com/media/1807465/ur5e_e-series_datasheets_web.pdf> |
| `repeatability` | <https://www.universal-robots.com/manuals/EN/TechSheets/UR5e_techsheet_pdf_online/UR5e_techsheet_en.pdf> |
| `reach.value` | <https://www.universal-robots.com/media/1807465/ur5e_e-series_datasheets_web.pdf> |
| `reach.measured_from` | <https://www.universal-robots.com/manuals/EN/PDF/SW5_19/user-manual-UR5e-PDF_online/710-965-00_UR5e_User_Manual_en_Global.pdf> |

## Estimates

Fields whose values were estimated rather than read from a source:

- `base.link.geometry`
- `joints[*].link.geometry`
- `reach.measured_to`

## Spec notes

Kinematic source: published DH table (Universal Robots support article "DH parameters for calculations of kinematics and dynamics", primary; retrieved as web-search extracts because universal-robots.com could not be fetched directly). Standard DH, theta_i = q_i (no offsets); rows copied verbatim, alpha pi/2 written as 90 deg. The datasheet drawing labels (162.5, 425, 392.2, 99.7, 133 mm) agree with d1, a2, a3, d5, d4. EE site = DH frame 6 = tool flange face (UR's d6 = 0.0996 m is the distance to the flange), so ee.origin is zero. Joint ranges: techsheet working range +-360 deg on every joint; speeds 180 deg/s each (techsheet). Link masses (3.761, 8.058, 2.846, 1.37, 1.3, 0.365 kg) and the CoMs of links 1, 2 and 5 from the same UR article (CoMs are offsets from the DH frame of that link); CoMs of links 3, 4, 6 were not extracted, so left to the builder. total_mass 20.6 kg is the datasheet weight including cable (user manual says 20.7 kg); the base gets the remainder (about 2.9 kg) since its mass is not published. Effort limits: wrist 2/3 = Size 1 = 28 Nm from the official UR torque article extract; base/shoulder/elbow 150 Nm and wrist 1 28 Nm are SECOND-HAND (UR forum post); per the forum these are damage thresholds, not continuous output torques. Reach: datasheet R850 working-area radius; the manual describes it as measured from the base joint (J1 axis), so measured_from = base_axis_horizontal. That it ends at the flange (not the wrist centre) is my assumption, listed as an estimate. Footprint: datasheet says 149 mm, techsheet 151 mm. Estimated geometry (no housing diameters are published except the footprint): base cylinder radius 0.0745 m = half the 149 mm footprint; link capsule radii 0.06/0.055/0.04/0.04/0.04 m and the 0.032 m flange cylinder are judged from product photos relative to the 149 mm base. Capsules follow the DH segments, so the real lateral shoulder/elbow offsets (folded into d4 by the DH table) are not drawn where the real housings are.


## Iteration history

| # | Time | Result | Errors | Failed | Failed checks | Note |
|---|---|---|---|---|---|---|
| 1 | 2026-11-05T10:52:49+00:00 | ✔ pass | 0 | 1 |  | initial spec from UR DH article (standard DH), techsheet limits/speeds, datasheet mass/reach |

Status: `passed` · max iterations 8

---
Generated by sim-anything on 2026-11-05 10:52 UTC.
