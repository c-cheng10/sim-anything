# KUKA LBR iiwa 14 R820: sources used

Accessed 2026-11-05. Direct fetches (WebFetch) of every PDF host tried were blocked by this session's network
policy (caltech.edu, unistra.fr, dndkm.org, arxiv.org), so all quotes below are web-search extracts, reproduced as
returned. Items marked "(inputs)" come from `benchmark/inputs/kuka_iiwa14/sources.md`.

## 1. KUKA LBR Med brochure: work-envelope dimension table (used for all link lengths)

https://apps.kuka.com/KUKA/virtualshowroom/assets/downloads/KUKA_LBR_Med_EN.pdf
(also https://www.kuka.com/-/media/kuka-corporate/documents/industries/healthcare/kuka-medical-robotics/kuka-lbrmed-en-brochure.pdf)
- (inputs) "A as 1,306 mm, B as 1,180 mm, G (reach) as 820 mm, and H as 255 mm" for the 14 R820.
- Search extract, LBR Med 14 R820 column: "Dimension A: 1,306 mm, and B: 1,180 mm", "C: 360 mm, and D: 420 mm",
  "E: 400 mm, and F: 126 mm", "G: 820 mm", "H: 255 mm". A separate extract: "A KUKA LBR Med datasheet lists a
  'Dimensions F' value of 126 mm for both the 7 R800 and 14 R820 variants."
- The letters are not defined in any extract (they label a drawing). Used as C = spec `joints[1].origin` z (360),
  D = `joints[3].origin` z (420), E = `joints[5].origin` z (400), F = `ee.origin` z (126). See NOTES.md for why.

## 2. KUKA KMR iiwa brochure (standard LBR iiwa 14 R820, cross-check of the same table)

https://www.dndkm.org/DOEKMDocuments/GetMedia/Technology/5392-KUKA_KMRiiwa_EN.pdf
- Search extract: "LBR iiwa 14 R820 | 1,306 mm | 1,180 mm | 360 mm | 420 mm | 400 mm | 255 mm | 820 mm | 1.8 m3";
  "Its work-envelope table gives the LBR iiwa 14 R820 values A 1,306 mm, B 1,180 mm, C 360 mm, D 420 mm,
  E 400 mm, and G 820 mm, plus a 255 mm value". (F not in this extract.) For the 7 R800: "1,266 mm for A,
  1,140 mm for B, 340 mm for C, and 800 mm for G".

## 3. my.KUKA product page, LBR iiwa 14 R820 (inputs)

https://my.kuka.com/s/product/lbr-iiwa-14-r820/01t58000002hnktAAA?language=en_US
- Range of motion: "A1, A3, and A5 are ±170°, A2, A4, and A6 are ±120°, and A7 is ±175°" -> `joints[*].limits`.
- Speed with rated payload: "85°/s for A1 and A2, 100°/s for A3, 75°/s for A4, and 130°/s for A5" (cross-check).
- Max reach "820 mm" -> `reach`; rated payload "14 kg" -> `payload`; pose repeatability "±0.15 mm" (ISO 9283)
  -> `repeatability`; weight "approx. 29.9 kg" -> `total_mass`.

## 4. KUKA specification "LBR iiwa 7 R800, LBR iiwa 14 R820" (mirror; axis data)

https://git.phschoen.de/phschoen/lwr_server/raw/commit/1debece1117ae5d940d2f15c0647304bf45473c6/lwrserv/doc/LBRiiwa_en.pdf
(a KUKA specification PDF on a third-party git server; not a robot-description file)
- Search extract, 14 R820 column (text garbled, column alignment as read by the search tool):
  "the second column shows 320 Nm and 85°/s for both" (A1, A2);
  "Axis 3 (A3) ±170° 176 Nm 100°/s"; "Axis 4 (A4) ±120° 176 Nm 75°/s"; "Axis 5 (A5) ±170° 110 Nm 130°/s";
  "Axis 6 (A6) ±120° 40 Nm 135°/s; Axis 7 (A7) ±175° 40 Nm 135°/s".
  -> `joints[*].effort_limit` 320/320/176/176/110/40/40 and `joints[*].velocity_limit` 85/85/100/75/130/135/135.
- Agrees with (inputs) distributor brochure torques "320 Nm for A1 and A2, 176 Nm for A4, 110 Nm for A5, and 40 Nm
  for A6 and A7" and with the CR product page "135°/s for both A6 and A7".

## 5. Not used

- KUKA spec V5/V8 (caltech.edu / yiliang.com.tw): envelope figure values not extractable; fetch blocked.
- Joint rotation directions: not found in any readable source (estimate).
