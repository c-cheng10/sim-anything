# UR5e round2 notes

- **Sources:** UR DH/dynamics support article (DH rows, link masses, 3 CoMs), UR5e datasheet 08/2023 (mass 20.6 kg,
  payload, reach 850 mm, Ø149 footprint), techsheet (±360° ranges, 180°/s, ±0.03 mm), user manual SW5.19 (reach
  measured from base joint), UR torque article + UR forum post (torques; forum = second-hand). All via web-search
  extracts (direct fetch of universal-robots.com blocked). See `sources.md`.
- **Convention:** `dh_standard`, rows copied verbatim (m; π/2 -> 90 deg), theta_i = q_i.
- **EE site:** DH frame 6 = tool flange face (d6 = 0.0996 m), `ee.origin` zero.
- **Estimates:** all link/base collision radii (base = half the Ø149 footprint, others from photos);
  `reach.measured_to` (flange assumed). Base mass is the 20.6 kg remainder after published link masses (~2.9 kg).
- **Iterations:** 1. Passed on the first build (14 checks, 0 errors, 1 warning).
- **Final status:** pass. Warning: reach (max over all configs, base axis -> flange) 0.969 m vs rated 0.850 m.
  At q = 0 (arm stretched, wrist at UR's zero) the flange is 0.8497 m from the J1 axis, i.e. the rated 850 mm
  matches the stretched zero pose, not the absolute maximum with the wrist folded outward. Left as a warning; the
  sourced DH values were not changed.
- **Renders:** q = 0 pose shows the classic UR zero pose (upper arm and forearm horizontal, wrist 1 pointing down,
  flange facing sideways), consistent with product drawings.
- **Doubts:** effort limits for joints 1-4 are second-hand and are damage thresholds; capsules follow DH segments, so
  the lateral shoulder/elbow housing offsets are not where the real housings are.
