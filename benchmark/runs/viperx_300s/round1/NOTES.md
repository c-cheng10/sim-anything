# Trossen ViperX 300 S, round 1

- **Sources:** Trossen's vx300s specification page (PoE screw-axis table M/Slist, firmware joint limits, reach,
  payload, repeatability), the ViperX-300-6DOF technical drawing (DWG 11) and the X-Series "Specifications" page
  (reach/offset tables). All primary; read from the docs' own source files on raw.githubusercontent.com because
  docs.trossenrobotics.com does not resolve here.
- **Convention:** `offset`, exact conversion of the published space-frame PoE table (home pose = q = 0, upper arm
  vertical, forearm horizontal along +x, all frames parallel to the base, units m/deg). Points on the roll axes:
  forearm_roll at the elbow point, wrist_rotate at the wrist_angle point (zero origin offsets; no effect on FK).
- **EE site (no tool flange):** on the wrist_rotate axis, 70 mm beyond the wrist_angle axis, i.e. at the
  gripper-mount face of the wrist_rotate link (drawing "70"; reach table "Wrist Tilt to Rotate" 70 mm, point D).
  Base-frame position at q = 0: (0.42955, 0, 0.42705) m. The PoE `M` (x = 0.536494) is a gripper frame and is
  not used.
- **Estimates:** `ee.origin` (reading the 70 mm end point as the mount face), reach definition, all collision
  geometry. 18 of 42 numbers estimated. No total mass published: the builder's default density gives 3.31 kg.
- **Iterations:** 1. Passed all error checks first time. One warning: reach 0.676 m (shoulder to mount face) is
  9.9 % below the rated 750 mm, expected because 750 mm evidently includes the gripper (gripper rail 745 mm,
  finger tip 812 mm from the shoulder in Trossen's own table); the definition is listed as an estimate.
- **Verification:** chain FK equals the published PoE product to 1.7e-16 on 50 random configurations;
  `kinematics_match` 2.5e-16 m; renders show the drawing's home pose (vertical upper arm, 60 mm elbow offset,
  horizontal forearm).
- **Doubts:** firmware limits are assumed to share the PoE zero; the PoE base origin is 0.3 mm off the drawing's
  base-plate dimension (127.05 vs 126.75); masses, torques and speeds are not modelled from data.
