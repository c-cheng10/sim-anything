# Trossen ViperX 300 S (ViperX-300 6DOF, vx300s): sources (round 1)

Accessed 2026-11-05. docs.trossenrobotics.com does not resolve from this session, so the pages were read from
their reStructuredText sources in Trossen's own documentation repository (TrossenRobotics/interbotix_xsarms_docs,
documentation only, not a robot-description package), fetched from raw.githubusercontent.com. These are the
sources of the published pages cited in `spec.yaml`. Items 2 and 3 (limits, reach, payload, repeatability,
section lengths) also appear in `benchmark/inputs/viperx_300s/sources.md`.

## 1. vx300s specification page, "Kinematic Properties / Product of Exponentials" (primary)

https://docs.trossenrobotics.com/interbotix_xsarms_docs/specifications/vx300s.html
(source: https://raw.githubusercontent.com/TrossenRobotics/interbotix_xsarms_docs/main/docs/specifications/vx300s.rst)

```
M = [[1.0, 0.0, 0.0, 0.536494],
     [0.0, 1.0, 0.0, 0.0     ],
     [0.0, 0.0, 1.0, 0.42705 ],
     [0.0, 0.0, 0.0, 1.0     ]]
Slist^T rows (w, v):
 0.0 0.0 1.0   0.0      0.0      0.0
 0.0 1.0 0.0  -0.12705  0.0      0.0
 0.0 1.0 0.0  -0.42705  0.0      0.05955
 1.0 0.0 0.0   0.0      0.42705  0.0
 0.0 1.0 0.0  -0.42705  0.0      0.35955
 1.0 0.0 0.0   0.0      0.42705  0.0
```
-> `joints[*].origin`, `joints[*].axis` (exact conversion p_i = w_i x v_i, see spec notes).
Verified: the chain FK equals the PoE product exp(S1 q1)...exp(S6 q6) M' (M moved to the site along x) to 1.7e-16
on 50 random configurations.

Same page:
- Default joint limits, "set in the firmware, defined as degrees from Zero (servo centered)":
  Waist -180/180, Shoulder -101/101 (servos 2+3), Elbow -101/92 (4+5), Wrist Angle -107/130, Forearm Roll -180/180,
  Wrist Rotate -180/180, Gripper 42mm/116mm -> `joints[*].limits`
- "Reach 750mm", "Total Span 1500mm", "Repeatability 1mm", "Accuracy 5 - 8mm", "Working Payload 750g*",
  "*... if intending to use a 750g weight we recommend no more than a 50% extension of the arm."
  -> `reach.value` (0.75 m), `repeatability` (0.001 m), `payload` (0.75 kg)
- "full 360 degree of rotation"; servos: XM540-W270 (waist, shoulder x2, elbow x2, forearm_roll, wrist_angle),
  XM430-W350 (wrist_rotate, gripper) (from `_data/servos_vx300s.csv`).

## 2. Technical drawing "ViperX-300-6DOF Desktop Robot Arm", DWG 11, rev 0, 7/2/2020 (primary, cross-check)

https://raw.githubusercontent.com/TrossenRobotics/interbotix_xsarms_docs/main/docs/specifications/images/vx300s_drawing.png
(the drawing image shown on the vx300s page above)
- Side view at the home pose: "126.75" (base plate bottom to shoulder axis), "300" (vertical upper arm), "60"
  (elbow offset), "305.94" (true upper arm), "300" (elbow to wrist-angle axis), "70", "68.7", "67.88" (wrist-angle
  axis to gripper parts), "206.58", "103.62", base plate "299.46"; front view "110", "96.27", "84.5", "66.47".
- Used: "70" as the distance from the wrist-angle axis to the gripper-mount face (interpretation -> `ee.origin`
  listed as an estimate); 299.46 only to size the base box (estimate).

## 3. X-Series Arms "Specifications" page (primary, cross-check)

https://docs.trossenrobotics.com/interbotix_xsarms_docs/specifications.html
(source: https://raw.githubusercontent.com/TrossenRobotics/interbotix_xsarms_docs/main/docs/specifications.rst)
- "Reach - Total Length (mm)", ViperX-300 6DOF: B Elbow Joint 306, C Wrist Tilt Joint 606, D Wrist Rotate 676,
  E Gripper Rail 745, F Finger Tip 812.
- "Reach - Section Length (mm)", ViperX-300 6DOF: Upper Arm 306, Forearm 300, Wrist Tilt to Rotate 70,
  Gripper (to Rail) 69, Finger Tip 68.
- "Offsets & True Upper Arm Length (mm)", ViperX-300 6DOF: A Upper Arm 300, B Elbow Offset 60,
  C True Upper Arm Length 306, D Forearm 300, E Offset Angle 11.3°.
- Arm-reach picture (images/armreach.png): point D sits at the interface between the wrist-rotate servo and the
  gripper plate.
- Gripper min/max on this page "42 / 114" vs "42mm / 116mm" on the vx300s page (gripper not modelled).

## Not found
- Total mass, link masses, joint torque/speed ratings, housing diameters.
