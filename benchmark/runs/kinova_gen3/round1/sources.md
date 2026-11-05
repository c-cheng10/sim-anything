# Kinova Gen3 (7-DoF spherical wrist, no gripper): sources

Accessed 2026-11-05. Direct fetches of kinovarobotics.com and every mirror of the user guide
(csis.pace.edu, manualslib.com, scribd.com, manualmachine.com, manuals.plus, manuals.online,
uploads.unchainedrobotics.de, manualshive.com, researchgate.net) were refused by this session's
network policy. Values marked "search extract" were taken from web-search extracts of the cited
page (via benchmark/inputs/kinova_gen3/sources.md and my own searches).

## 1. DH table (SECOND-HAND)

Primary document (not readable from here): Kinova Gen3 Ultra lightweight robot User Guide,
section "Denavit-Hartenberg (DH) parameters - 7 DoF spherical wrist" (TOC: p.197 in R07,
p.134/141/163 in other editions), https://www.kinovarobotics.com/uploads/User-Guide-Gen3-R07.pdf.
Several targeted searches (row values, "Classical DH", "q2 + pi" etc.) only returned the TOC entry.

Values used come from a third-party transcription:
https://raw.githubusercontent.com/Sahilnarola-1007/kinova-kinematics/main/design.md (section 5.1;
a C++/Eigen forward-kinematics library, not a URDF/robot-description package). Quality:
**second-hand, no page/table reference** (the doc tags it "[SPEC - Kinova Gen3 7-DOF kinematic
parameters; ... record the exact User Guide table/figure reference]"). As returned:

> "T_i = Rot_z(θ)·Trans_z(d)·Trans_x(a)·Rot_x(α)" (classical DH)

| Frame | α | a | d [m] | θ offset |
|---|---|---|---|---|
| 0 (base) | π | 0 | 0 | 0 |
| 1 | π/2 | 0 | −0.2848 | 0 |
| 2 | π/2 | 0 | −0.0118 | π |
| 3 | π/2 | 0 | −0.4208 | π |
| 4 | π/2 | 0 | −0.0128 | π |
| 5 | π/2 | 0 | −0.3143 | π |
| 6 | π/2 | 0 | 0 | π |
| 7 | π | 0 | −0.1674 | π |
| tool | — | — | +0.113 along local z | — |  (gripper tool offset, NOT used)

Also from that page: "flange z = 1.1873 m at q = 0 before the tool offset".

## 2. User Guide geometric parameters (primary, search extract)

https://www.manualslib.com/manual/1529186/Kinova-Gen3.html?page=49 (copy of the user guide;
values from the Scribd copy extract https://www.scribd.com/document/624143328/gen3), "Table 9: 7 DoF
spherical wrist robot geometric parameters", Length (mm):
"Base to actuator 1 156.4", "Base to shoulder 284.8", "First half upper arm length 210.4",
"Second half upper arm length 210.4", "Forearm length (elbow to wrist) 208.4",
"First wrist length 105.9", "Second wrist length 105.9", "Last actuator to end efector 61.5",
joint offsets "5.4" and "6.4".
Used only as a cross-check of the DH d values (all consistent, see NOTES.md).

## 3. User Guide R07 (primary, search extract)

https://www.kinovarobotics.com/uploads/User-Guide-Gen3-R07.pdf
- Joint limits, "Table 35: 7 DoF spherical wrist robot angular limits": actuators 1, 3, 5, 7
  "no limit"; "actuator 2 is limited to ±128.9°, actuator 4 to ±147.8°, and actuator 6 to ±120.3°".
  (Older guide Table 10: "±126°", "±147°", "±117°".) -> `joints[*].limits`
- "maximum unloaded speed is 25 RPM (small) and 13 RPM (large)" -> `velocity_limit` 13 RPM x 360/60
  = 78 deg/s (large, joints 1-4), 25 RPM = 150 deg/s (small, joints 5-7). Older guide: 17 RPM large.
- torque small "34 N·m (peak)", large "54 N·m (peak)" -> `effort_limit` 34 / 54. (Older: 74 N·m peak.)
- Reach "902 mm", "from the shoulder (Actuator 2 frame) to the end effector frame" (extract
  paraphrase) -> `reach` 902, shoulder -> ee_site.

## 4. Gen3 specifications sheet R01 (second-hand host: reseller copy)

https://hotrobotics.co.uk/wp-content/uploads/2021/07/Gen3-Specifications-R01.pdf
- "large actuators drive joints #1, 2, 3, 4 and the small actuators drive joints #5, 6 and 7"
  (used to assign the large/small speed and torque figures).

## 5. Product page and one-pager (primary, search extract)

https://www.kinovarobotics.com/product/gen3-robots - Weight "8.2 kg / 18 lbs" (7-DoF) -> `total_mass`.
https://www.kinovarobotics.com/uploads/Kinova_Onepager_Gen3_2024_EN.pdf - Payload "4.0 kg" mid-range
continuous ("2.0 kg" full-range continuous) -> `payload`; reach "902 mm".
