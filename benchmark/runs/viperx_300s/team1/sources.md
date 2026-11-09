# Sources: Trossen Robotics / Interbotix ViperX-300 6DOF (ViperX 300 S, slug vx300s)

Scope: arm joints only (waist, shoulder, elbow, forearm_roll, wrist_angle, wrist_rotate); gripper excluded.
Access date for everything below: 2026-11-09.

No URDF / xacro / MJCF / SDF / Menagerie / `*_description` package was opened. The task brief
suggested the "official interbotix URDF"; that is a forbidden source under the skill rules and
was NOT used. The M / Slist used below is the one printed on the manufacturer's documentation
page itself (Sphinx source of docs.trossenrobotics.com), not taken from a description package.

## Search queries run

1. `ViperX 300 S specifications docs.trossenrobotics.com vx300s joint limits` (standard)
2. `github Interbotix docs repository "interbotix_xsarms_docs" specifications vx300s.rst` (standard)
3. `"vx300s" "Default Joint Limits" waist shoulder elbow "forearm_roll" "wrist_angle" "wrist_rotate" degrees` (extended)
4. `github.com Interbotix "docs.trossenrobotics.com" source repository sphinx "interbotix_xsarms_docs"` (standard)
5. `ViperX-300 6-DoF "Denavit-Hartenberg" parameters table vx300s paper` (extended)  [independent DH-table search]
6. `arxiv Momani Hosseinzadeh ViperX-300 physically feasible dynamic model identification` (standard)
7. `"ViperX-300" "L1=0.12675" OR "L1 = 0.12675" D-H parameters table L2 L3` (extended)
8. `"ViperX 300 S" OR "ViperX-300 6DOF" weight kg specifications trossen arm weight` (standard)
9. `interbotix xsarm "ee_gripper_link" end-effector frame product of exponentials M Slist mr_descriptions docs` (standard)

## Blocked hosts (proxy refused the connection)

- docs.trossenrobotics.com (the spec page `.../interbotix_xsarms_docs/specifications/vx300s.html`, its
  `_sources/...rst.txt`, and therefore `/_downloads/ViperX-300s.pdf`). Alternate route used: the same page's
  Sphinx source in the maker's own GitHub repo TrossenRobotics/interbotix_xsarms_docs (section 1).
- trossenrobotics.com / www.trossenrobotics.com (product page, `_files/ugd/...pdf`)
- www.support.interbotix.com (older copy of the docs)
- web.archive.org (tool refuses)
- www.sciencedirect.com and www.researchgate.net (Momani & Hosseinzadeh paper)
- emanual.robotis.com (servo e-manual). Alternate route used: ROBOTIS's own GitHub source of the e-manual (section 4).

---

## 1. Manufacturer spec page, Sphinx source (PRIMARY)

URL: https://raw.githubusercontent.com/TrossenRobotics/interbotix_xsarms_docs/main/docs/specifications/vx300s.rst
(rendered version: https://docs.trossenrobotics.com/interbotix_xsarms_docs/specifications/vx300s.html, blocked)
Accessed 2026-11-09. Primary: Trossen Robotics' own documentation source repo, exact variant (6DOF = vx300s).
Quotes below are exact lines as returned by the fetch tool (table separator lines omitted).

Section headings in order: "ViperX-300 6DOF", "Overview", "Default Joint Limits", "Default Servo Configurations",
"Kinematic Properties", "Product of Exponentials", "Dynamical Model", "Drawings and CAD Files".

### Overview / specifications table

- "The ViperX-300 6DOF offers 6 degree of freedom and a full 360 degree of rotation."
- "The DYNAMIXEL `XM540-W270`_ & DYNAMIXEL `XM430-W350`_ servos offer high"
- "| Degrees of Freedom                     | 6                                    |"
- "| Reach                                  | 750mm                                |"
- "| Total Span                             | 1500mm                               |"
- "| Repeatability                          | 1mm                                  |"
- "| Accuracy                               | 5 - 8mm                              |"
- "| Working Payload                        | 750g*                                |"
- "| Total Servos                           | 9                                    |"
- "| Wrist Rotate                           | Yes                                  |"
- Footnote: "Working Payload for the ViperX-300 6DOF is inside its maximum reach, if intending to use a"
  / "750g weight we recommend no more than a 50% extension of the arm."
- Reach definition: NOT stated (no "from"/"to"). Total mass: not on the page.

### Default Joint Limits (deg)

- "Default joint limits are the safe range of operation for each joint. These are set in the firmware,"
- "defined as degrees from Zero (servo centered)."
- "| Joint        | Min   | Max   | Servo ID(s) |"
- "| Waist        | -180  | 180   | 1           |"
- "| Shoulder     | -101  | 101   | 2+3         |"
- "| Elbow        | -101  | 92    | 4+5         |"
- "| Wrist Angle  | -107  | 130   | 6           |"
- "| Forearm Roll | -180  | 180   | 7           |"
- "| Wrist Rotate | -180  | 180   | 8           |"
- "| Gripper      | 42mm  | 116mm | 9           |"

Note: this table lists Wrist Angle before Forearm Roll and gives them servo IDs 6 / 7; the servo CSV
(section 2) gives ID 6 = forearm_roll, ID 7 = wrist_angle. The limits are attached to joint NAMES, so map by
name (forearm_roll -180..180, wrist_angle -107..130), not by row position. No joint is stated "continuous";
waist / forearm roll / wrist rotate are limited to +/-180 in firmware. The sign convention of the limits relative to
the PoE screw-axis directions is not stated (e.g. whether shoulder +101 tilts the arm forward or back).

### Product of Exponentials (space-frame screw axes, units not stated; values are consistent with metres)

Intro text: "Read more about the product of exponential approach." (link to Wikipedia "Product_of_exponentials_formula").
No line names the frame M describes; the page does not state the zero pose in words (q = 0 is the PoE home).
`.. math::` blocks, rows quoted exactly:

M (`M & =`):
- "1.0 & 0.0 & 0.0 & 0.536494 \\"
- "0.0 & 1.0 & 0.0 & 0.0 \\"
- "0.0 & 0.0 & 1.0 & 0.42705 \\"
- "0.0 & 0.0 & 0.0 & 1.0"

Slist (`Slist & =`, written as a matrix with `^T`, so each row below is one joint's screw axis
[w_x, w_y, w_z, v_x, v_y, v_z]; row order = joint order waist, shoulder, elbow, forearm_roll, wrist_angle, wrist_rotate,
consistent with the axis directions: z, y, y, x, y, x):
- "0.0 & 0.0 & 1.0 &  0.0      & 0.0      & 0.0 \\"
- "0.0 & 1.0 & 0.0 & -0.12705  & 0.0      & 0.0 \\"
- "0.0 & 1.0 & 0.0 & -0.42705  & 0.0      & 0.05955 \\"
- "1.0 & 0.0 & 0.0 &  0.0      & 0.42705  & 0.0 \\"
- "0.0 & 1.0 & 0.0 & -0.42705  & 0.0      & 0.35955 \\"
- "1.0 & 0.0 & 0.0 &  0.0      & 0.42705  & 0.0"

Derived points on axes (p = w x v; my arithmetic, for the spec writer to re-check), metres, base frame at q = 0:
J1 (0,0,0) axis +z; J2 (0,0,0.12705) axis +y; J3 (0.05955,0,0.42705) axis +y; J4 (any x, 0, 0.42705) axis +x;
J5 (0.35955,0,0.42705) axis +y; J6 (any x, 0, 0.42705) axis +x; tool M at (0.536494, 0, 0.42705), identity rotation.
=> home pose: upper arm vertical, forearm horizontal along +x. Tool point is 0.176944 m beyond the wrist-angle axis;
the page does not say which physical frame that is (it is not the wrist-rotate flange; see drawing section 3).
The PoE base frame origin is on the waist axis at the shoulder-height reference 0.12705 m below J2; whether it lies on
the mounting face is not stated (drawing gives 126.75 mm mounting face -> shoulder axis).

### Dynamical Model

- "The Euler-Lagrange dynamical model of the ViperX-300s 6DOF arm was derived by Mu'taz Momani"
- "and Mehdi Hosseinzadeh and is available in the following paper:"
- "Physically feasible dynamic model identification and constrained control of robotic arms:"
- "A case study on the ViperX-300 6-DoF robotic manipulator"
- "https://doi.org/10.1016/j.mechatronics.2025.103419"

### Drawings and CAD

- ":download:`ViperX-300 6DOF Technical Drawing </_downloads/ViperX-300s.pdf>`" (host blocked; the GitHub copy
  https://raw.githubusercontent.com/TrossenRobotics/interbotix_xsarms_docs/main/docs/_downloads/ViperX-300s.pdf
  downloaded but the tool could not render the compressed PDF)
- "- :download:`ViperX-300 6DOF Solid STEP Files </_downloads/solids/9_VXA-300S-M.zip>`" (not opened)
- ".. image:: images/vx300s_drawing.png" -> section 3 (read instead of the PDF)

## 2. Manufacturer default servo configuration CSV (PRIMARY)

URL: https://raw.githubusercontent.com/TrossenRobotics/interbotix_xsarms_docs/main/docs/_data/servos_vx300s.csv
Accessed 2026-11-09. Primary (included by the spec page's "Default Servo Configurations" section). Full file:

```
ID,Joint Name,Servo,Baudrate
1,waist,XM540-W270,1Mbps
2,shoulder,XM540-W270,1Mbps
3,shoulder_shadow,XM540-W270,1Mbps
4,elbow,XM540-W270,1Mbps
5,elbow_shadow,XM540-W270,1Mbps
6,forearm_roll,XM540-W270,1Mbps
7,wrist_angle,XM540-W270,1Mbps
8,wrist_rotate,XM430-W350,1Mbps
9,gripper,XM430-W350,1Mbps
```

Joint order and names: waist, shoulder, elbow, forearm_roll, wrist_angle, wrist_rotate (all revolute).
Shoulder and elbow each use two XM540-W270 (a "_shadow" servo) -> two servos per joint.

## 3. Manufacturer dimension drawing (PRIMARY)

URL: https://raw.githubusercontent.com/TrossenRobotics/interbotix_xsarms_docs/main/docs/specifications/images/vx300s_drawing.png
Accessed 2026-11-09. Primary: image embedded in the vx300s spec page. Read visually (image), values in mm as printed.
Title block: "ViperX-300-6DOF Desktop Robot Arm", Technical reference "VXA-300-6DOF", Document type "X Series Quick Specs",
DWG No. "11", Rev "0", Date of issue "7/2/2020", Created by "Levi Todes", Approved by "Matt Trossen".

Side view, pose drawn: upper arm vertical, forearm horizontal, gripper pointing forward (same pose as the PoE home).
Dimensions printed (mm), with what they span as I read the extension lines:
- "126.75": vertical, from the bottom face of the base plate (mounting face) up to the shoulder joint axis.
- "300": vertical, from the shoulder axis up to the level of the elbow axis.
- "60": horizontal, from the vertical upper-arm line (shoulder axis line) to the elbow axis.
- "305.94": diagonal, shoulder axis to elbow axis (= sqrt(300^2 + 60^2) = 305.94, consistent).
- "300": horizontal, from the elbow axis to the wrist-angle axis.
- "103.62": horizontal, from a point on the forearm (left end of the forearm-roll servo housing, my reading) to the wrist-angle axis.
- "70": horizontal, from the wrist-angle axis to the start of the gripper assembly (plausibly the wrist-rotate output /
  gripper mounting face; mapping is my inference, not labelled).
- "68.7": next horizontal segment of the gripper assembly.
- "67.88": last horizontal segment, to the finger tips.
- "206.58": horizontal, from the wrist-angle axis to the gripper finger tips (= 70 + 68.7 + 67.88 = 206.58, consistent).
- "299.46": base plate length (side view).
Top view: "110" and "96.27" (base plate widths), "84.5" (twice, base turret/housing faces), "66.47" (chamfer face).

Drawing cross-check candidates (all at q = 0 / PoE home pose):
- shoulder axis height above mounting face: 126.75
- wrist-angle axis height above mounting face: 126.75 + 300 = 426.75 (sum of two labelled dims)
- wrist-angle axis horizontal distance from waist axis: 60 + 300 = 360
- finger-tip horizontal distance from waist axis: 60 + 300 + 206.58 = 566.58
(All extension-line mappings are my visual reading; treat as estimates where not explicit.)

## 4. ROBOTIS DYNAMIXEL servo specifications (PRIMARY for the servos, not for the arm)

URL: https://raw.githubusercontent.com/ROBOTIS-GIT/emanual/master/_data/dxl_x_info.yml
(rendered pages https://emanual.robotis.com/docs/en/dxl/x/xm540-w270/ and .../xm430-w350/ blocked)
Accessed 2026-11-09. Primary: ROBOTIS's own e-manual data source. Quotes as returned (YAML anchors resolved by the tool).

xm540-w270 (waist, shoulder x2, elbow x2, forearm_roll, wrist_angle):
- weight: "165 [g]"
- dimensions: "33.5 x 58.5 x 44 [mm]"
- gearratio: "272.5 : 1"
- stalltorque: "10.0 [N.m] (at 11.1 [V], 4.2 [A], 2.381 [Nm/A])<br />**10.6 [N.m] (at 12.0 [V], 4.4 [A], 2.409 [Nm/A])**<br />12.9 [N.m] (at 14.8 [V], 5.5 [A], 2.345 [Nm/A])"
- noloadspeed: "28 [rev/min] (at 11.1 [V])<br />**30 [rev/min] (at 12.0 [V])**<br />37 [rev/min] (at 14.8 [V])"

xm430-w350 (wrist_rotate, gripper):
- weight: "82 [g]"
- dimensions: "28.5 x 46.5 x 34 [mm]"
- gearratio: "353.5 : 1"
- stalltorque: "3.8 [N.m] (at 11.1 [V], 2.1 [A], 1.810 [Nm/A])<br />**4.1 [N.m] (at 12.0 [V], 2.3 [A], 1.783 [Nm/A])**<br />4.8 [N.m] (at 14.8 [V], 2.7 [A], 1.778 [Nm/A])"
- noloadspeed: "43 [rev/min] (at 11.1 [V])<br />**46 [rev/min] (at 12.0 [V])**<br />57 [rev/min] (at 14.8 [V])"

These are actuator figures (stall torque, no-load speed), not published arm joint limits. Shoulder/elbow have two
servos each (section 2), so any joint torque derived from them is an inference. The arm's supply voltage was not found.

## 5. Momani & Hosseinzadeh, Mechatronics 2025 (SECOND-HAND, SEARCH EXCERPT ONLY)

URLs: https://www.sciencedirect.com/science/article/pii/S095741582500128X (blocked),
https://www.researchgate.net/publication/397437082_Physically_feasible_dynamic_model_identification_and_constrained_control_of_robotic_arms_A_case_study_on_the_ViperX-300_6-DoF_robotic_manipulator (blocked)
Accessed 2026-11-09 via search excerpts only (queries 5 and 7). Cited by the manufacturer page (section 1).
Excerpt text: "the Denavit–Hartenberg (D-H) parameters (i.e., αi−1, ai−1, di, and θi,i∈{1,…,6}) of the manipulator are given in
Table 1, where L1=0.12675 [m]" and "𝐿1= 0.12675 [m], 𝐿2= 0.30594 [m], 𝐿3= 0.1964 [m]".
Table 1 itself: GARBLED in the excerpt (only row 1 "d1 = L1, θ1 = q1" and a fragment of row 2) -> NOT transcribed.
Modified (Craig) convention per the column names a_{i-1}, alpha_{i-1}. L1 = 126.75 mm and L2 = 305.94 mm agree with the
drawing (section 3); L3 = 0.1964 m does not match any single drawing dimension (unexplained).

---

Kinematic source: screw-axis table (Product-of-Exponentials M + Slist, space frame) on the manufacturer spec page,
https://raw.githubusercontent.com/TrossenRobotics/interbotix_xsarms_docs/main/docs/specifications/vx300s.rst
(primary; rendered at https://docs.trossenrobotics.com/interbotix_xsarms_docs/specifications/vx300s.html, blocked).
Cross-check: dimension drawing https://raw.githubusercontent.com/TrossenRobotics/interbotix_xsarms_docs/main/docs/specifications/images/vx300s_drawing.png
No official DH table found (paper's DH Table 1 only seen garbled).

Conflicts:
- Shoulder axis height: PoE 0.12705 m vs drawing "126.75" mm and paper L1 = 0.12675 m (0.3 mm). Use the PoE
  table for kinematics (the machine-readable kinematic definition); the drawing may measure from the plate underside
  differently. Set drawing-check tolerance accordingly (>= 0.5 mm).
- Shoulder-to-elbow horizontal offset: PoE 0.05955 m vs drawing "60" mm (0.45 mm); diagonal PoE sqrt(0.3^2+0.05955^2)
  = 0.30585 m vs drawing / paper 305.94 mm. Use PoE; drawing value is rounded.
- Elbow-to-wrist: PoE 0.35955 - 0.05955 = 0.300 m, drawing "300": agree. Upper arm vertical 0.42705 - 0.12705 = 0.300 m,
  drawing "300": agree.
- Reach: page says "Reach 750mm" / "Total Span 1500mm" (span = 2 x reach) with no definition. Lengths from the sources
  (my arithmetic): shoulder axis -> wrist-angle axis fully stretched ~ 305.9 + 300 = ~606 mm; shoulder -> PoE M point
  ~ 305.9 + 476.9 = ~783 mm; shoulder -> finger tips ~ 305.94 + 300 + 206.58 = ~812.5 mm; horizontal waist axis -> finger
  tips at the drawn home pose 566.58 mm. None equals 750 mm; the figure is a rounded/marketing value of unknown
  definition. Use only as an estimate-level check (warning), never tune geometry to it.
- Joint-limit table servo IDs (Wrist Angle 6, Forearm Roll 7) vs servo CSV (forearm_roll 6, wrist_angle 7): limits are
  bound by joint name; use the CSV for ordering.
- Search-engine summaries of this page claimed other numbers (e.g. a forum post with shoulder -106..72, wrist_angle
  -107..128, which appears URDF-derived): not used.

Not found:
- Tool flange position as a stated number: the PoE M is at 0.176944 m beyond the wrist-angle axis but its physical frame
  is not named; the drawing shows "70" mm from the wrist-angle axis to the gripper assembly start (unlabelled mapping).
- Reach definition (from where to where).
- Total arm mass (only per-servo weights in section 4); link masses, CoMs, inertias (paper not accessible).
- Published joint velocity limits and joint torque limits for the arm (only servo no-load speeds / stall torques).
- Official DH table (only the paper's, garbled).
- Sign convention of joint limits relative to the screw axes.
- Housing diameters beyond the drawing (base 110 x 299.46 plate, 84.5 turret faces; servo cases in section 4).
- Technical drawing PDF text (downloaded from GitHub copy, not renderable by the tool; PNG drawing used instead).
