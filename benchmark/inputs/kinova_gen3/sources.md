# Kinova Gen3 (7-DOF, spherical wrist): sources

Accessed 2026-11-05.

**How these were retrieved.** Direct page fetches were blocked by this
session's network policy (all hosts tried), so all values come from
web-search extracts of the cited pages. Quotes are reproduced as returned.

## 1. Kinova Gen3 Ultra lightweight robot User Guide (R07)

https://www.kinovarobotics.com/uploads/User-Guide-Gen3-R07.pdf
(copies: https://csis.pace.edu/robotlab/papers/Gen3Manual.pdf, https://www.manualslib.com/manual/1529186/Kinova-Gen3.html,
https://www.scribd.com/document/624143328/gen3, https://manualmachine.com/kinova/gen3/2576994-user-manual/)

- The guide contains a section "Denavit-Hartenberg (DH) parameters - 7 DoF spherical wrist" (TOC: page 197 in R07;
  page 134/141/163 in other editions) and "Homogeneous transform matrices - 7 DoF spherical wrist". **The DH table
  values could not be extracted by search** (several targeted queries returned only the TOC).
- "Table 9: 7 DoF spherical wrist robot geometric parameters", column "Length (mm)" (manualslib page 49,
  https://www.manualslib.com/manual/1529186/Kinova-Gen3.html?page=49; values from the Scribd copy extract):
  - "Base to actuator 1 156.4"
  - "Base to shoulder 284.8"
  - "First half upper arm length 210.4"
  - "Second half upper arm length 210.4"
  - "Forearm length (elbow to wrist) 208.4"
  - "First wrist length 105.9" (actuator 5 to actuator 6, confirmed in the ManualMachine copy, there "Table 12")
  - "Second wrist length 105.9" (actuator 6 to actuator 7)
  - "Last actuator to end efector 61.5"
  - joint offsets "5.4" and "6.4" mm (which joints they belong to was not in the extract)
- Joint position limits, newer manual "Table 35: 7 DoF spherical wrist robot angular limits": actuators 1, 3, 5, 7
  "no limit"; "actuator 2 is limited to ±128.9°, actuator 4 to ±147.8°, and actuator 6 to ±120.3°".
- Older manual "Table 10: Joint limits - 7 DoF spherical wrist": "actuator 2 is ±126°, actuator 4 is ±147°, and
  actuator 6 is ±117°", others unlimited.
- "For joints 2, 4 and 6 there are physical limits to how far the joint can turn without the arm shell segments
  running into each other. The robot enforces software joint angle limits to prevent these joints from reaching the
  physical limits."
- Reach: "902 mm", measured "from the shoulder (Actuator 2 frame) to the end effector frame" (extract paraphrase of the
  guide; "90.2 cm").
- Payload: "4.5 kg peak" for short full-reach periods (guide).
- Weight: "8.3 kg" with the vision module and no gripper (guide).
- Actuators (R07): "maximum unloaded speed is 25 RPM (small) and 13 RPM (large)"; torque small "13 N·m (nominal)" and
  "34 N·m (peak)"; large "32 N·m (nominal) for robots built before 2022-09, 39 N·m (nominal) for robots built after
  2022-09", "54 N·m (peak)". Older manual: large actuator "17 RPM", peak "74 N·m". (Search-tool conversion 13 RPM ≈ 78°/s,
  25 RPM ≈ 150°/s; not Kinova's wording.)

## 2. Gen3 specifications sheet

https://hotrobotics.co.uk/wp-content/uploads/2021/07/Gen3-Specifications-R01.pdf
- "large actuators drive joints #1, 2, 3, 4 and the small actuators drive joints #5, 6 and 7".

## 3. Kinova product page and one-pager

https://www.kinovarobotics.com/product/gen3-robots
https://www.kinovarobotics.com/uploads/Kinova_Onepager_Gen3_2024_EN.pdf
- Weight "8.2 kg / 18 lbs" (7-DoF).
- Payload "2.0 kg" full-range continuous, "4.0 kg" mid-range continuous.
- Max Cartesian translation speed "50 cm/s" (older TS-014 sheet: 40 cm/s / 30 cm/s).
- Reach "902 mm".
