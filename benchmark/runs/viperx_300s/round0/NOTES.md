# ViperX 300 S (vx300s), round0: notes

## Sources
- Trossen Interbotix X-Series docs, vx300s page: spec table, firmware joint limits, and a
  **product-of-exponentials kinematic model** (Slist + M). This is the backbone of the chain.
- Same docs, all-arms specifications page: reach section lengths (A..F diagram), offsets table.
- Technical drawing VXA-300-6DOF (DWG 11): 126.75 / 300 / 60 / 300 / 103.62 / 70 / 68.7 / 67.88 mm.
- docs.trossenrobotics.com was DNS-blocked, so I read the same pages from the docs site's source
  repo (TrossenRobotics/interbotix_xsarms_docs, .rst + images + drawing PDF). No URDF/xacro,
  description packages, meshes or Menagerie files were opened. Quotes are in `sources.md`.

## Convention
`offset`, built from the PoE screw axes (space frame at the waist axis, z up, arm extends along +x at
q = 0, upper arm vertical, forearm horizontal: the drawing's zero pose). Axis points decoded from
v = q x w: shoulder (0,0,127.05) +y, elbow (59.55,0,427.05) +y, forearm_roll +x at z = 427.05,
wrist_angle (359.55,0,427.05) +y, wrist_rotate +x at z = 427.05. Axis signs as published.
Checked numerically: the spec's FK equals the PoE product (with M moved to the EE site) to 2e-16
over 200 random configurations.

## EE site
No tool flange standard. The EE site is at the **gripper-mount face on the wrist_rotate link**: point D
of the docs' reach diagram, 70 mm along the forearm axis past the wrist-angle (tilt) axis
("C~D Wrist Tilt to Rotate 70", drawing "70"). Base frame coordinates at q = 0:
(429.55, 0, 427.05) mm. The wrist_rotate joint frame is placed at the same point and `ee.origin` is
zero. (The PoE M at x = 536.494 is a gripper frame and was not used.)

## Estimates
- Where forearm_roll sits along its own axis: 196.38 mm past the elbow (= 300 - 103.62, reading the
  drawing's 103.62 as starting at the roll housing). Does not affect kinematics; the 300 mm
  elbow-to-wrist total is sourced.
- All collision geometry (radii, base cylinder r = 75 mm, waist box, 6 mm mount disc): rough, from
  drawing proportions.
- No total mass, speeds or torques published: omitted (builder default density; model 2.85 kg).
- Reach 750 mm omitted on purpose: the cumulative table gives 676 mm shoulder to point D, 745 to the
  gripper rail and 812 to the finger tip, so the advertised 750 mm includes the gripper, which is not modelled.

## Iterations
1. Initial spec: PASSED all 11 checks (0 errors; reach and total_mass are info-only since both are
   omitted). No further iterations needed.

Renders (`run/renders/`) match the drawing's side view: vertical upper arm with the 60 mm forward
elbow offset, horizontal forearm, wrist in line at 427 mm height.

## Doubts
- Shoulder height: PoE 127.05 vs drawing 126.75 (from the base plate); elbow offset PoE 59.55 vs
  drawing 60. PoE values used. The base origin is therefore the PoE space frame, which may sit
  0.3 mm off the plate's bottom face.
- Joint sign conventions are taken from the PoE table and assumed to match the firmware limits'
  sign (same doc page); not independently verified on hardware.
