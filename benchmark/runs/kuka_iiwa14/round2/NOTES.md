# KUKA LBR iiwa 14 R820 round2 notes

- **Sources:** my.KUKA product pages (ranges, speeds, mass, payload, reach, repeatability), the KUKA
  work-envelope dimension table A-G (search extract of KUKA brochures), a second-hand brochure copy for A1/A2
  torque. All via search extracts; every direct fetch was blocked.
- **Convention:** `offset`, q = 0 = stretched vertical pose. Kinematic source class: dimension table/drawing with
  an inferred letter mapping, so every origin is an estimate.
  Chain: A1 at base origin; A2 at z = 360 (C); A3 coaxial at A2; A4 at +420 (D); A5 coaxial; A6 at +400 (E);
  A7 coaxial; flange at +126 above A6. The mapping is consistent: G 820 = D + E, B 1180 = C + G, and
  A 1306 = C + D + E + 126.
- **EE site:** the A7 output flange face (no media flange), 126 mm above the A6 axis on the A7 axis. That 126 mm
  is inferred as A - C - D - E, so it is an estimate.
- **Estimates:** all origins and axis signs (A2 +y, A4 -y, A6 +y is a guess; no source gives the positive
  directions), A6/A7 speeds (cleanroom variant page), all geometry radii (no housing diameters found), reach
  definition (shoulder A2 -> wrist centre A6, inferred from G = D + E).
- **Iterations:** 1. Passed first time.
- **Final status:** passed, 14 checks, 0 errors; 1 warning (51% of numbers are estimates). Reach 0.820 m matches
  the rated 820 mm exactly under the inferred definition.
- **Pose check:** renders show the straight vertical "candle" pose with alternating roll/pitch modules, which
  matches KUKA product pictures of the iiwa stretched out. A small visual gap between the A6 sphere and A7
  cylinder is cosmetic.
- **Doubts:** letter mapping of the dimension table; A2/A4/A6 sign conventions; torques only for A1/A2.
