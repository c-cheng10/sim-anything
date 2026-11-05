# KUKA LBR iiwa 14 R820, round 1

- **Sources:** my.KUKA product page (limits, speeds A1-A5, reach, mass, payload, repeatability); KUKA LBR iiwa
  document via a third-party mirror (work-envelope letters A-G, axis torques/speeds A1, A2, A6, A7); distributor
  brochure (torques A4, A5); LBR Med brochure and iiwa 14 CR page as cross-checks. All read as web-search
  extracts (every PDF host was blocked), so the mirror and distributor copies are second-hand.
- **Convention:** `offset`, kinematic source = dimension drawing/table. q = 0 is the arm stretched vertically.
  Pitch axes A2/A4/A6 along +y/-y/+y, roll axes A1/A3/A5/A7 along z.
- **EE site:** tool flange face, 126 mm above the A6 axis on the A7 axis (z = 1306 mm at q = 0).
- **Estimates:** the letter-to-link mapping (C = 360 base to A2, D = 420 A2 to A4, E = 400 A4 to A6,
  A - B = 126 A6 to flange), so all joint origins and `ee.origin`; axis signs (A4 reversed); positions of the roll
  joints A3/A5/A7 along their axes (210/200/0, no effect on kinematics); reach definition (820 = D + E, taken as
  shoulder to wrist centre); A3 torque 176 Nm; all collision radii. 26 of 57 numbers are estimates.
- **Iterations:** 1. Iteration 1 passed all 14 checks (0 errors, 0 warnings failing); reach 0.820 m vs 0.820 m,
  FK at q = 0 gives the flange at 1.306 m = dimension A.
- **Renders:** straight vertical arm, as in KUKA's zero position; proportions match the drawing heights.
- **Doubts:** the positive direction of each joint (only A4 vs A2 is a guess, others too); the 126 mm flange
  offset relies on the A/B letter interpretation (consistent for both iiwa variants); F = 255 not used; torques
  A3-A5 come from a garbled extract; housing radii are rough.
