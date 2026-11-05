# UR5e round 1: notes

- **Sources**: UR DH article (kinematics, link masses, 3 of 6 CoMs), UR5e datasheet 08/2023 (mass,
  payload, reach, footprint), UR5e techsheet (ranges, speeds, repeatability), UR max-joint-torque article
  (effort limits). All via web-search extracts (universal-robots.com cannot be fetched from here). See
  `sources.md`.
- **Convention**: `dh_standard`, copied row for row, theta_i = q_i. Units mm/deg: the table's metres
  were written in mm (x1000) and π/2 rad as 90 deg, so the mm reach/repeatability and the ±360 deg
  ranges stay verbatim.
- **EE site**: DH frame 6 = tool flange face centre (d6 = 99.6 mm); `ee.origin` zero. FK at q = 0:
  flange at (-817.2, -232.9, 62.8) mm.
- **Estimates**: all collision radii (base 74.5 mm from the Ø149 footprint; shoulder 60, upper arm 50,
  forearm 40, wrists 35/35/32 mm, from photos); reach definition (from the base axis horizontally to the
  flange: the manual says "cylindrical volume, 850 mm from the base joint", but does not name the end point).
- **Iterations**: 2.
  1. Passed, but reach and repeatability were in mm while the file used metres (reach read as 850 m).
  2. Whole file switched to mm. PASSED, 14 checks, 0 errors, 1 warning.
- **Final status**: PASSED. Warning: the model's max reach is 0.969 m, 14% above the rated 0.850 m. This is
  only a warning because the reach definition is an estimate. Note that sqrt(817.2² + 232.9²) = 849.7 mm, the
  horizontal distance from the base axis to the flange at q = 0. That suggests UR's R850 is measured to the
  wrist-3 axis with the tool pointing down, not to the farthest flange position. Not changed.
- **Doubts**: UR's DH table puts the shoulder and elbow lateral offsets into d4, so the upper arm and
  forearm capsules lie on one line instead of being stepped like the real housings. The kinematics are
  still exact. CoMs for links 3, 4 and 6 were not in the extract, so they were omitted. The effort limits
  are UR joint-size ratings, which UR says cannot all be used in an application. The renders match the
  UR zero pose: arm stretched horizontally, wrist 1 offset sideways, wrist 2 pointing down, flange horizontal.
