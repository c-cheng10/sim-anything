# KUKA LBR iiwa 14 R820, round0

**Sources.** KUKA work-envelope dimension table (LBR Med brochure, cross-checked against the KMR iiwa brochure
for the standard arm), my.KUKA product page (ranges, mass, payload, reach, repeatability), KUKA specification
mirror (per-axis max torque and speed). All via web-search extracts; every direct PDF fetch was blocked.
Details and quotes in `sources.md`.

**Convention.** `offset` (no DH table published by KUKA). q = 0 is the arm stretched straight up.
Chain (mm): A1 at base origin (z axis); A2 at z 360 (C); A3 at A2; A4 420 (D) above A3; A5 at A4;
A6 400 (E) above A5; A7 at A6. Roll joints A1/A3/A5/A7 about the link line (z), pitch joints A2/A4/A6 about +y.

**EE site.** A7 output flange face (no media flange), 126 mm (F) above A6/A7.

**Interpretation of the drawing letters (the main assumption).** The extracts give the letter values but not
their meaning. Mapping C = base-A2, D = A2-A4, E = A4-A6, F = A6-flange is chosen because it makes the rest of
the table exact: B = C+D+E = 1180, A = B+F = 1306 (height stretched up), G = D+E = 820 = rated reach. Hence the
reach is modelled as shoulder (A2) to wrist centre (A6). H = 255 is unused (meaning unknown).

**Estimates.** Pitch-axis rotation sense (+y for A2/A4/A6, not published in what could be read); placement of
A3/A5/A7 frames on their segment lines (kinematically irrelevant); all collision radii and the base cylinder
(from photos, no housing diameters found). Link masses omitted; builder distributes the 29.9 kg ("approx.").

**Iterations.** 1 iteration: passed 11/11 checks on the first run (reach 0.820 m exact, mass exact, no
self-collision, stable hold). No fixes needed.

**Renders.** Front/side views show a straight vertical column of 360/420/400/126 mm segments, matching the
iiwa's upright "candle" zero pose in KUKA's drawings and photos.

**Doubts.** (1) Letter meanings are inferred, not quoted. (2) A2/A4/A6 positive direction may be mirrored
relative to the real robot (affects joint-sign conventions, not reach/shape). (3) Torques/speeds come from a
garbled PDF text extract; column alignment is the search tool's reading, though it agrees with two other sources.
(4) Link radii are rough.
