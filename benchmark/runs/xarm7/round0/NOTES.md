# UFactory xArm 7 (round0): notes

**Sources.** UFACTORY support article "Kinematic and dynamic parameters, xArm 7" (modified DH table);
xArm user manual ch. 8 technical specifications (joint ranges, 180 deg/s, Ø126 mm footprint); ufactory.us
product page (13.7 kg, 3.5 kg payload, 700 mm reach). Manufacturer hosts were unreachable; values come from
search extracts. Quotes in `sources.md`.

**Convention.** `dh_modified`, published table copied row by row (a, alpha on row i = a_{i-1}, alpha_{i-1});
rad converted exactly to deg; all theta offsets 0 as published. q = 0 is the manufacturer zero: upper arm vertical,
forearm folded back down, flange facing down at (206, 0, 120.5) mm in the base frame.

**EE site.** At DH frame 7 (no extra offset): the table's d7 = 97 mm is taken as the tool flange face.
There is no separate flange row in the extract.

**Estimates.** Base cylinder height (120 mm) and all link capsule radii (38-50 mm), judged from product photos
against the 126 mm base. `reach.measured_from` (horizontal from J1 axis, to flange), because the source gives no
definition. No link masses: the builder spreads 13.7 kg by volume.

**Conflicts.** J2 -117~116 / J4 -6~225 (manual, used) vs -118~120 / -11~225 (support article). Mass 13.7 kg
(product page and article, used) vs 14.3 kg (manual ch. 8).

**Iterations.** 1 loop iteration. 10 of 11 checks pass: compiles, joint structure, EE site, limits, mass,
inertia, no self-collision at home, stable hold, actuators, sources complete. Renders and the report were made with
`sim-anything render` / `sim-anything report`, because `loop` only renders on pass or at max iterations.
I stopped after one iteration because no remaining change would be backed by a source.

**Failing check: reach.** The model reaches 772 mm (J1 axis to flange); the rated value is 700 mm (+10.3%, tolerance 5%).
Offline FK with the sourced table and limits: 649 mm to the wrist centre (frame 6, -7.3%), 725 mm to the point
where the J7 axis meets the a6 = 76 mm offset (flange minus d7, +3.5%, not a definition the tool offers).
None of the definitions the tool offers comes within 5%, so the published 700 mm is probably measured to a point the tool can't
represent, or it is a family-wide rounded figure (xArm 5/6/7 all say 700 mm). I did not change the DH lengths.
A forum user's estimate of "about 679mm radius" fits this explanation.

**Doubts.** The DH rows came from two separate search extracts (joints 1, 2, 7 and 3-6). The table couldn't be re-read
directly. Renders (front/side/top) show the planar folded zero pose the table implies. I could not compare them with a
manufacturer drawing because the pages wouldn't load. Link shapes are crude capsules, and the elbow/wrist offsets show as diagonal capsules.
