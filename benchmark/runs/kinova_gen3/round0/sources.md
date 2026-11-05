# Kinova Gen3 (7-DOF, spherical wrist, no gripper): sources

Accessed 2026-11-05. Direct fetches of kinovarobotics.com, manualslib, scribd, csis.pace.edu, arxiv,
researchgate etc. were refused by this session's network proxy; github.com was reachable through WebFetch.
Values from Kinova documents are therefore from web-search extracts (via the pre-gathered
`benchmark/inputs/kinova_gen3/sources.md`), quoted as returned.

## 1. DH table (secondary source)

https://github.com/Sahilnarola-1007/kinova-kinematics/blob/main/design.md (section 5.1; a C++ forward-kinematics
library, not a robot-description file). Its attribution: "[SPEC — Kinova Gen3 7-DOF kinematic parameters; Sahil to
record the exact User Guide table/figure reference]". Table as returned (columns frame, alpha, a, d [m], theta offset):

| Frame | alpha | a | d [m] | theta offset |
|---|---|---|---|---|
| 0 (base) | pi | 0 | 0 | 0 |
| 1 | pi/2 | 0 | -0.2848 | 0 |
| 2 | pi/2 | 0 | -0.0118 | pi |
| 3 | pi/2 | 0 | -0.4208 | pi |
| 4 | pi/2 | 0 | -0.0128 | pi |
| 5 | pi/2 | 0 | -0.3143 | pi |
| 6 | pi/2 | 0 | 0 | pi |
| 7 | pi | 0 | -0.1674 | pi |
| tool | — | — | +0.113 along local z | — |

The README describes the library as "Classical DH convention". The "tool" row (gripper) is not used (arm only).
The same page says the flange is at "z = 1.1873 m at q = 0" (labelled [COMPUTED]); this model reproduces it.

The official table is in the Kinova Gen3 User Guide, section "Denavit-Hartenberg (DH) parameters - 7 DoF spherical
wrist" (p.197 in R07, https://www.kinovarobotics.com/uploads/User-Guide-Gen3-R07.pdf); its values could not be
retrieved here, so the secondary table is cross-checked against Table 9 below.

## 2. Kinova Gen3 User Guide (R07) and copies

https://www.kinovarobotics.com/uploads/User-Guide-Gen3-R07.pdf
(copies: https://www.manualslib.com/manual/1529186/Kinova-Gen3.html?page=49, https://www.scribd.com/document/624143328/gen3,
https://manualmachine.com/kinova/gen3/2576994-user-manual/)

- "Table 9: 7 DoF spherical wrist robot geometric parameters", Length (mm): "Base to actuator 1 156.4",
  "Base to shoulder 284.8", "First half upper arm length 210.4", "Second half upper arm length 210.4",
  "Forearm length (elbow to wrist) 208.4", "First wrist length 105.9", "Second wrist length 105.9",
  "Last actuator to end efector 61.5", joint offsets "5.4" and "6.4".
  Cross-check of DH d values: 284.8 = base to shoulder; 11.8 = 5.4 + 6.4; 420.8 = 210.4 + 210.4;
  314.3 = 208.4 + 105.9; 167.4 = 105.9 + 61.5. (12.8 not directly checkable.)
- Joint limits, "Table 35: 7 DoF spherical wrist robot angular limits": actuators 1, 3, 5, 7 "no limit";
  "actuator 2 is limited to ±128.9°, actuator 4 to ±147.8°, and actuator 6 to ±120.3°".
  (Older "Table 10": ±126° / ±147° / ±117°.)
- Reach: "902 mm", "from the shoulder (Actuator 2 frame) to the end effector frame".
- Actuators: "maximum unloaded speed is 25 RPM (small) and 13 RPM (large)"; small "13 N·m (nominal)", "34 N·m (peak)";
  large "39 N·m (nominal) for robots built after 2022-09", "54 N·m (peak)".
  Converted: 13 RPM x 6 = 78 deg/s; 25 RPM x 6 = 150 deg/s.
- Weight: "8.3 kg" with vision module, no gripper.

## 3. Gen3 specifications sheet

https://hotrobotics.co.uk/wp-content/uploads/2021/07/Gen3-Specifications-R01.pdf
- "large actuators drive joints #1, 2, 3, 4 and the small actuators drive joints #5, 6 and 7".

## 4. Product page / one-pager

https://www.kinovarobotics.com/product/gen3-robots — weight "8.2 kg / 18 lbs" (7-DoF); reach "902 mm".
https://www.kinovarobotics.com/uploads/Kinova_Onepager_Gen3_2024_EN.pdf — payload "4.0 kg" mid-range continuous,
"2.0 kg" full-range continuous.

## Estimates

- Link capsule radii (45 mm large-actuator links, 35 mm small-actuator links): no housing diameter found.
