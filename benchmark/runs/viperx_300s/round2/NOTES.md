# Trossen ViperX 300 S round2 notes

- **Sources:** Interbotix X-Series docs (vx300s page: joint limits, reach, payload, repeatability; specifications
  page: reach and offsets tables) and the Trossen product page, all via search extracts (hosts blocked).
- **Convention:** `offset`, q = 0 = the all-zero home pose (upper arm up with its 60 mm forward offset, forearm
  horizontal). Kinematic source class: **inferred** (lengths from the reach/offset tables with an inferred column
  mapping; no DH table or readable drawing), so every origin is an estimate.
  Chain: waist at base origin (+z); shoulder 120 mm above it (+y, height estimated); elbow +60 x / +300 z (+y);
  forearm_roll at the elbow (+x); wrist_angle +300 x (+y); wrist_rotate +70 x (+x).
- **EE site:** the docs give no distance to the gripper-mount face, so ee_site sits at point D of the Interbotix
  reach table ("wrist rotate", 70 mm past the wrist_angle axis), on the wrist_rotate axis, zero offset from the
  wrist_rotate joint frame. The gripper (69 mm to the gripper rail, 68 mm to the fingertip) is not modelled.
- **Estimates:** shoulder height 120 mm (photo proportion), shoulder on the waist axis, forearm horizontal at
  q = 0, all axis signs, all geometry, reach definition. Total mass, speeds and torques omitted (not found).
- **Iterations:** 1. Passed first time.
- **Final status:** passed, 14 checks, 0 errors; warnings: reach 0.676 m vs rated 0.750 m (-9.9%) under the
  assumed shoulder -> EE definition (expected: the table's 745 mm to the gripper rail suggests 750 mm includes the
  gripper; not changed), 61% of numbers are estimates.
- **Pose check:** the side render shows the forward-leaning upper arm and horizontal forearm of the ViperX home
  pose in product photos. Cosmetic gaps between the waist cylinder and the upper-arm capsule.
- **Doubts:** shoulder height (not published in anything reachable); column mapping of the offsets table; joint
  sign conventions; exact location of point D relative to the real gripper-mount face.
