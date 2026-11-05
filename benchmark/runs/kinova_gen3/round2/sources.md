# Kinova Gen3 (7-DOF, spherical wrist, no gripper) sources (round2)

Accessed 2026-11-05. Direct fetches failed in this environment (kinovarobotics.com per the inputs; manualshive.com and
arxiv.org tried on 2026-11-05: host not resolvable). Values are web-search extracts as gathered in
`benchmark/inputs/kinova_gen3/sources.md` (quotes reproduced from there). Three extra searches on 2026-11-05 for the
guide's DH table values and for the zero pose returned nothing usable.

## Gen3 User Guide R07 (primary, manufacturer)
https://www.kinovarobotics.com/uploads/User-Guide-Gen3-R07.pdf
(copies: https://csis.pace.edu/robotlab/papers/Gen3Manual.pdf, https://www.manualslib.com/manual/1529186/Kinova-Gen3.html,
https://www.scribd.com/document/624143328/gen3, https://manualmachine.com/kinova/gen3/2576994-user-manual/)

- "Table 9: 7 DoF spherical wrist robot geometric parameters", "Length (mm)" (manualslib page 49,
  https://www.manualslib.com/manual/1529186/Kinova-Gen3.html?page=49; values from the Scribd copy extract, second-hand host):
  "Base to actuator 1 156.4", "Base to shoulder 284.8", "First half upper arm length 210.4", "Second half upper arm
  length 210.4", "Forearm length (elbow to wrist) 208.4", "First wrist length 105.9", "Second wrist length 105.9",
  "Last actuator to end efector 61.5"; joint offsets "5.4" and "6.4" (joints not identified in the extract).
  Used (mapping to joints is my estimate): joints[*].origin z values, ee.origin.
- "Table 35: 7 DoF spherical wrist robot angular limits": actuators 1, 3, 5, 7 "no limit"; "actuator 2 is limited to
  ±128.9°, actuator 4 to ±147.8°, and actuator 6 to ±120.3°". (Older guide Table 10: ±126 / ±147 / ±117.)
  Used: joints[1,3,5].limits; no limits on joints 1, 3, 5, 7 (0-based 0, 2, 4, 6).
- Reach "902 mm", "from the shoulder (Actuator 2 frame) to the end effector frame". Used: reach.
- "maximum unloaded speed is 25 RPM (small) and 13 RPM (large)"; torque small "13 N·m (nominal)", "34 N·m (peak)";
  large "39 N·m (nominal) for robots built after 2022-09", "54 N·m (peak)". (Older guide: 17 RPM, 74 N·m peak.)
  Used: velocity_limit 78 / 150 deg/s (exact conversion of 13 / 25 RPM), effort_limit 54 / 34 (peak).
- Weight "8.3 kg" with vision module, no gripper (not used; product page value used).

## Gen3 specifications sheet R01 (reseller-hosted copy = second-hand host)
https://hotrobotics.co.uk/wp-content/uploads/2021/07/Gen3-Specifications-R01.pdf
- "large actuators drive joints #1, 2, 3, 4 and the small actuators drive joints #5, 6 and 7".
Used: which speed/torque applies to which joint.

## Kinova product page and one-pager (primary)
https://www.kinovarobotics.com/product/gen3-robots - weight "8.2 kg / 18 lbs" (7-DoF). Used: total_mass.
https://www.kinovarobotics.com/uploads/Kinova_Onepager_Gen3_2024_EN.pdf - payload "2.0 kg" full-range continuous,
"4.0 kg" mid-range continuous; reach "902 mm". Used: payload 4.0.

## Not found
DH table values (exist in the guide, not extractable), assignment/direction of the 5.4 / 6.4 mm offsets, joint axis
signs, zero-pose statement, repeatability, link masses/CoMs, housing diameters.
