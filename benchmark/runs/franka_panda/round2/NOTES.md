# Franka Emika Panda round2 notes

- **Sources:** FCI docs (modified DH table + flange row, torque limits), Gaz et al. RA-L 2019 (joint-7 alpha,
  cross-check of all lengths), Panda datasheet May 2019 (ranges, speeds, reach, payload, repeatability; reseller copy),
  university-hosted datasheet copy (17.8 kg). All via web-search extracts. See `sources.md`.
- **Convention:** `dh_modified` (Craig), rows copied verbatim, theta_i = q_i, alpha pi/2 -> 90 deg.
  FK at q = 0 gives the flange at (0.088, 0, 0.926) m pointing down, as in Franka's zero-pose drawing.
- **EE site:** tool flange face = DH "Flange" row, `ee.origin.xyz = [0, 0, 0.107]` m from frame 7. No hand.
- **Estimates:** home = "ready" pose [0, -45, 0, -135, 0, 90, 45] deg (q = 0 violates the A4 range -176..-4;
  pose from memory of Franka example code, not fetched); all link radii; reach endpoints (shoulder -> flange assumed;
  the datasheet gives no reference points). Link masses not published: builder distributes 17.8 kg by volume.
- **Iterations:** 2.
  1. Failed self_collision_home: flange cylinder overlapped the forearm (A4/A5 capsules) by 7 mm at the ready pose.
  2. Thinned the estimated A4 capsule (0.055 -> 0.05 m) and flange cylinder (0.04 -> 0.032 m). Passed.
- **Final status:** pass (14 checks, 0 errors). Reach 0.858 m vs rated 0.855 m (0.3%). One warning:
  collision_exclusions (A2/A4 capsules overlap around the short A3 link and are auto-excluded).
- **Renders:** ready pose with the flange pointing down in front of the base, matching Franka product photos.
- **Doubts:** datasheet speeds (150/180 deg/s) are higher than the FCI controller limits (2.175/2.61 rad/s); the A5-A7
  180 deg/s value was seen in one datasheet version only. Datasheet and weight came from third-party hosted copies.
