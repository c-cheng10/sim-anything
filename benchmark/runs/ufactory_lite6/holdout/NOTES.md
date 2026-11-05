# UFactory Lite 6 holdout run: notes

- **Sources:** UFACTORY support article (modified DH table, link masses), hardware manual V2.6.0 (joint ranges),
  developer manual (180 deg/s), technical-specifications docs (8 kg, 0.6 kg payload, 440 mm reach, Cartesian range,
  ±0.5 mm). All via web-search extracts; the ufactory hosts were not fetchable.
- **Convention:** published table labelled "Modified D-H parameters" -> `dh_modified`, rows stored verbatim (incl.
  theta offsets -90 on J2 and J3), mm/deg. No separate flange row.
- **EE site:** modified-DH frame 6 (d6 = 61.5 mm) = tool flange face, no extra offset. No gripper.
- **Estimates:** all collision geometry (radii from photos and the 130 x 140 mm footprint; explicit J1 column,
  L-shaped forearm, flange disk); reach endpoints shoulder -> wrist_center, inferred from the Cartesian range top
  683.5 = 243.3 (shoulder height) + 440.2 and from 440 mm being much shorter than shoulder-to-flange (505 mm).
- **Iterations:** 2. Iter 1 failed self_collision_home only (auto capsules: zero-length J1 link left a gap and a
  diagonal forearm capsule hit the shoulder). Iter 2 gave explicit geometry following the product shape -> PASSED
  (14 checks, 0 errors).
- **Final checks:** kinematics exact; reach 0.444 m vs 0.440 m (+0.8%); mass 8.000 kg; no self-collision; stable hold.
- **Renders:** q = 0 is the compact folded pose (upper arm vertical, forearm hanging beside it 87 mm forward,
  flange pointing down), which matches the Lite 6's shipping/zero posture as I understand it.
- **Doubts:** mass 8 kg (docs) vs 7.2 kg (product page); joint torques not published (omitted); CoMs omitted;
  reach definition inferred, not stated.
