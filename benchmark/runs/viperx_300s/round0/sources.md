# Trossen ViperX 300 S (Interbotix ViperX-300 6DOF, vx300s): sources

Accessed 2026-11-05. docs.trossenrobotics.com could not be fetched directly from this
session (DNS blocked), so the pages were read from the source of the same documentation
site, the Trossen docs repository `TrossenRobotics/interbotix_xsarms_docs` (Sphinx `.rst`
pages, their images and the downloadable drawing PDF). This is the documentation site,
not a robot-description package; no URDF/xacro/mesh/description files were opened.
Pre-gathered inputs (`benchmark/inputs/viperx_300s/`) were also used; their values agree.

## S1. ViperX-300 6DOF specification page (vx300s)

Published: https://docs.trossenrobotics.com/interbotix_xsarms_docs/specifications/vx300s.html
Read from: https://raw.githubusercontent.com/TrossenRobotics/interbotix_xsarms_docs/main/docs/specifications/vx300s.rst

Spec table (quoted):
- "Degrees of Freedom | 6", "Reach | 750mm", "Total Span | 1500mm", "Repeatability | 1mm",
  "Accuracy | 5 - 8mm", "Working Payload | 750g*", "Total Servos | 9", "Wrist Rotate | Yes".
- Note: "Working Payload for the ViperX-300 6DOF is inside its maximum reach, if intending to use a
  750g weight we recommend no more than a 50% extension of the arm."

Default Joint Limits ("set in the firmware, defined as degrees from Zero (servo centered)"):

| Joint | Min | Max | Servo ID(s) |
|---|---|---|---|
| Waist | -180 | 180 | 1 |
| Shoulder | -101 | 101 | 2+3 |
| Elbow | -101 | 92 | 4+5 |
| Wrist Angle | -107 | 130 | 6 |
| Forearm Roll | -180 | 180 | 7 |
| Wrist Rotate | -180 | 180 | 8 |

(Servo IDs from `_data/servos_vx300s.csv`: 1 waist, 2/3 shoulder(+shadow), 4/5 elbow(+shadow),
6 forearm_roll, 7 wrist_angle, 8 wrist_rotate; the joint chain order is
waist, shoulder, elbow, forearm_roll, wrist_angle, wrist_rotate.)

Kinematic Properties, Product of Exponentials (quoted, metres; Slist rows are screw axes
[w; v] in the space frame at the zero pose):

```
M = [[1,0,0,0.536494],[0,1,0,0],[0,0,1,0.42705],[0,0,0,1]]
Slist^T =
 0.0 0.0 1.0   0.0      0.0      0.0
 0.0 1.0 0.0  -0.12705  0.0      0.0
 0.0 1.0 0.0  -0.42705  0.0      0.05955
 1.0 0.0 0.0   0.0      0.42705  0.0
 0.0 1.0 0.0  -0.42705  0.0      0.35955
 1.0 0.0 0.0   0.0      0.42705  0.0
```

Decoded (v = q x w for a point q on the axis):
- waist: axis +z through the origin.
- shoulder: axis +y through (0, 0, 127.05 mm).
- elbow: axis +y through (59.55, 0, 427.05 mm).
- forearm_roll: axis +x along the line y = 0, z = 427.05 mm.
- wrist_angle: axis +y through (359.55, 0, 427.05 mm).
- wrist_rotate: axis +x along the line y = 0, z = 427.05 mm.
- M (end-effector frame at the zero pose; the page does not say which point of the gripper it is):
  x = 536.494 mm, z = 427.05 mm. Not used as the EE site (see S3).

## S2. Specifications page (all X-Series arms)

Published: https://docs.trossenrobotics.com/interbotix_xsarms_docs/specifications.html
Read from: https://raw.githubusercontent.com/TrossenRobotics/interbotix_xsarms_docs/main/docs/specifications.rst

- "Reach - Section Length (mm)", headers "A~B Upper Arm | B~C Forearm | C~D Wrist Tilt to Rotate |
  D~E Gripper (to Rail) | E~F Finger Tip", row "ViperX-300 6DOF | 306 | 300 | 70 | 69 | 68".
- "Reach - Total Length (mm)", row "ViperX-300 6DOF | 306 | 606 | 676 | 745 | 812".
- Image `specifications/images/armreach.png` (labels A..F): A = shoulder axis, B = elbow axis,
  C = wrist-angle (tilt) axis, D = the plane where the wrist-rotate housing ends and the gripper
  begins (gripper-mount face), E = gripper rail, F = finger tip.
- "Offsets & True Upper Arm Length (mm)", headers "Upper Arm | Elbow Offset | True Upper Arm Length |
  Forearm | Offset Angle", row "ViperX-300 6DOF | 300 | 60 | 306 | 300 | 11.3°".

## S3. ViperX-300 6DOF technical drawing (VXA-300-6DOF, DWG 11, rev 0, 7/2/2020)

Published: https://docs.trossenrobotics.com/interbotix_xsarms_docs/_downloads/ViperX-300s.pdf
Read from: https://raw.githubusercontent.com/TrossenRobotics/interbotix_xsarms_docs/main/docs/_downloads/ViperX-300s.pdf
(also rendered as `specifications/images/vx300s_drawing.png`)

Side view dimensions (zero pose: upper arm vertical, forearm horizontal):
- "126.75" base plate to shoulder axis; "300" shoulder axis to elbow height; "60" horizontal
  shoulder-to-elbow offset; "305.94" true upper arm; "300" elbow to wrist axis.
- "103.62" from the start of the forearm-roll housing to the wrist-angle axis.
- "70" wrist-angle axis to the gripper-mount face (point D of S2); "68.7" to the gripper rail;
  "67.88" to the finger tip; "206.58" total wrist-angle axis to finger tip.
- Top view: "299.46" base plate length, "110" / "96.27" base widths, "84.5", "66.47" turret flats.

Cross-check: the PoE values (127.05 shoulder height, 59.55 elbow offset, 300 forearm) agree with
the drawing to 0.3 / 0.45 mm; the PoE table is used for the chain because it is the published
kinematic model with joint axis directions.

## S4. Trossen product page

https://www.trossenrobotics.com/viperx-300 (via pre-gathered inputs, search extract)
- 6 DOF, "750mm reach", "1500mm" span, working payload "750g"; product listed as discontinued.
