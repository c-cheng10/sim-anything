# Trossen ViperX 300 S (round2): sources

Accessed 2026-11-05. docs.trossenrobotics.com and www.trossenrobotics.com do not resolve from this environment,
so all values are web-search extracts of the cited Trossen pages (the pre-gathered
`benchmark/inputs/viperx_300s/` plus three searches in this run). No second-hand sources were used for numbers.

## 1. Interbotix X-Series Arms docs: ViperX-300 6DOF (vx300s) specifications (primary, via search extract)
https://docs.trossenrobotics.com/interbotix_xsarms_docs/specifications/vx300s.html
- Default joint limits (deg, "set in the firmware, and represent the safe range of operation"): waist "±180",
  shoulder "±101", elbow "-101 to 92", forearm roll "±180", wrist angle "-107 to 130", wrist rotate "±180"
  -> `joints[*].limits`
- "Reach 750mm Total Span 1500mm Repeatability 1mm" -> `reach.value`, `repeatability`
- "Working Payload 750g*" -> `payload` (0.75 kg)
- "Accuracy 5 - 8mm" (not used)

## 2. Interbotix X-Series Arms docs: Specifications, all arms (primary, via search extract)
https://docs.trossenrobotics.com/interbotix_xsarms_docs/specifications.html
- Reach table row "ViperX-300 6DOF 306 300 70 69 68": upper arm (A~B) 306, forearm (B~C) 300,
  wrist tilt -> wrist rotate (C~D) 70, -> gripper rail (D~E) 69, -> fingertip (E~F) 68 mm; cumulative
  "306 mm to the elbow, 606 mm to wrist tilt, 676 mm to wrist rotate, 745 mm to the gripper rail, and 812 mm to
  the fingertip". (One search extract labels C~D "wrist" and D~E "tilt-to-rotate"; the cumulative labels
  "676 mm to wrist rotate" were used to resolve it.)
- "Offsets & True Upper Arm Length (mm)" row, ViperX-300 6DOF: "300, 60, 306, 300, and 11.3°"; second extract:
  "elbow offset of 60 mm, a true upper arm length of 306 mm, a forearm offset angle of 11.3°, and a 300 mm forearm
  offset", "the offsets are measured from the arm's home position". Column mapping is ambiguous in both extracts.
- Used (as estimates, mapping inferred) for `joints[*].origin`: elbow at [60, 0, 300] from the shoulder,
  wrist_angle 300 mm forward of the elbow, wrist_rotate 70 mm forward of wrist_angle.

## 3. Trossen product page (primary, via search extract)
https://www.trossenrobotics.com/viperx-300
- "750mm reach", "1500mm" span, 6 DOF, "750g" payload; marked discontinued; lists a "ViperX 300 S Technical
  Drawing" that could not be retrieved. (A stale "300 mm reach / 600 mm span / 5 mm repeatability" snippet on the
  same page is ignored.)

## Not found
Shoulder height above the base, waist-to-shoulder offset, gripper-mount-face distance, joint axis directions,
total mass, speeds, torques, housing dimensions.
