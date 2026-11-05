# UR10e holdout run: notes

- **Sources:** UR DH-parameters support article / developer page (DH table, link masses), UR10e techsheet (limits,
  speeds, payload, reach, repeatability), user manual (33.3 kg), UR joint-torque article (Size 2 wrists), UR forum
  (second-hand: base/shoulder/elbow torques). All via web-search extracts; universal-robots.com was not fetchable.
- **Convention:** published DH table, `dh_standard`, theta offsets 0, lengths in m copied verbatim, alpha in deg.
- **EE site:** DH frame 6 = tool flange face (d6 = 0.11655 m), no extra offset. Arm only.
- **Estimates:** collision geometry radii (photos scaled by the 190 mm footprint), base cylinder, wrist 1 torque
  (54 Nm, assumed Size 2), reach endpoints (base axis horizontal -> flange, from the R1300 drawing).
- **Iterations:** 1. Passed on the first build (14 checks, 0 errors, 2 informational warnings).
- **Final checks:** kinematics_match exact; reach 1.364 m vs rated 1.300 m (+4.9%, within tolerance); mass 33.3 kg;
  stable hold and no self-collision at home (q = 0, arm stretched horizontally as in UR's zero pose).
- **Renders:** match the UR zero configuration (shoulder and elbow straight, horizontal arm, wrist 2 axis down,
  flange pointing sideways).
- **Doubts:** elbow ±360° vs a single ±160° extract; reach overshoot of 4.9% suggests UR's R1300 is measured
  slightly differently (e.g. to the wrist or excluding the d4 offset); CoMs/inertias not extracted; base mass is the
  remainder (4.196 kg).
