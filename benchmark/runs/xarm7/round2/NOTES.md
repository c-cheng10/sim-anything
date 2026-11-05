# xArm 7 round2 notes

- **Sources:** UFACTORY kinematic-parameter support article (modified DH table), xArm manual ch. 8 technical
  specs (joint ranges, speed, repeatability, Ø126 mm footprint), product page / comparison article (13.7 kg,
  3.5 kg payload, 700 mm reach). All read as web-search extracts of the manufacturer pages (direct fetch blocked).
- **Convention:** `dh_modified`, rows copied verbatim (rad -> deg). Kinematic source class: published DH table.
- **EE site:** at DH frame 7 with no extra offset (d7 = 97 mm), taken as the tool flange face; the extract had
  no separate flange row, so this placement is an interpretation of the table.
- **Estimates:** base cylinder height, all link capsule radii (scaled by eye from product photos against the
  126 mm base); reach definition (shoulder -> flange assumed, not stated by the source).
- **Iterations:** 1. Passed first time (0 errors, 2 warnings).
- **Final status:** passed, 14 checks. Warnings: (a) reach 0.772 m vs rated 0.700 m (+10%) under the assumed
  shoulder->flange definition; not changed, the source does not say how 700 mm is measured (it may be to the
  wrist or exclude the offsets). (b) collision_exclusions: link 2 and link 4 capsules overlap around the short
  link 3 (elbow offset 52.5 mm), so that pair is never contact-checked.
- **Pose check:** q = 0 renders upper arm vertical, forearm folded back down, tool pointing down at
  x = 206 mm, z = 120.5 mm. This matches the folded zero pose seen in UFACTORY product pictures, and J4's range
  -6..225 deg (0 near the folded stop) is consistent with it.
- **Doubts:** conflicting manufacturer joint ranges (J2, J4) and mass (13.7 vs 14.3 kg); flange exactly at d7.
