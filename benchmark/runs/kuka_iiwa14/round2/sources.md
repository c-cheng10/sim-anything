# KUKA LBR iiwa 14 R820 (round2): sources

Accessed 2026-11-05. Every direct fetch tried in this run failed (hosts not resolvable through this
environment's proxy: www.oir.caltech.edu, git.phschoen.de, www.dndkm.org), so all values are web-search
extracts of the cited documents, plus the pre-gathered `benchmark/inputs/kuka_iiwa14/` (also search extracts).

## 1. my.KUKA product page, LBR iiwa 14 R820 (primary, via search extract)
https://my.kuka.com/s/product/lbr-iiwa-14-r820/01t58000002hnktAAA?language=en_US
- Range of motion: "A1, A3, and A5 are ±170°, A2, A4, and A6 are ±120°, and A7 is ±175°" -> `joints[*].limits`
- Speed with rated payload: "85°/s for A1 and A2, 100°/s for A3, 75°/s for A4, and 130°/s for A5"
  -> `joints[0..4].velocity_limit`
- Max reach "820 mm" -> `reach.value`; rated payload "14 kg" -> `payload`;
  pose repeatability "±0.15 mm" (ISO 9283) -> `repeatability`; weight "approx. 29.9 kg" -> `total_mass`

## 2. my.KUKA product page, LBR iiwa 14 R820 CR (cleanroom variant; primary, via search extract)
https://my.kuka.com/s/product/lbr-iiwa-14-r820-cr/01t58000004l0ebAAA?language=pt_BR
- "135°/s for both A6 and A7" -> `joints[5..6].velocity_limit`, listed as estimates (different variant)

## 3. KUKA work-envelope dimension table (KUKA KMR iiwa document; primary KUKA document, via search extract)
https://www.dndkm.org/DOEKMDocuments/GetMedia/Technology/5392-KUKA_KMRiiwa_EN.pdf
(third-party host of a KUKA brochure; same letters A, B, G, H also in the KUKA LBR Med brochure
https://apps.kuka.com/KUKA/virtualshowroom/assets/downloads/KUKA_LBR_Med_EN.pdf)
- Search-extract row: "| LBR iiwa 14 R820 | | 1,306 mm | | 1,180 mm | | 360 mm | | 420 mm | | 400 mm | | 255 mm | | 820 mm | 1.8 m^3 |"
  i.e. A 1306, B 1180, C 360, D 420, E 400, F 255, G 820 mm.
- Letter meanings are not in the extract (the figure could not be read). Used, as estimates, for
  `joints[*].origin` (C = 360, D = 420, E = 400) and `ee.origin` (A - C - D - E = 126 mm); see NOTES.md.
- The same KUKA brochure table also appears in the LBR iiwa brochure copy below (search extract: "dimension C at
  360 mm, D at 420 mm, and E at 400 mm, with F at 255 mm and G at 820 mm").

## 4. KUKA LBR iiwa brochure copy (second-hand host: git.phschoen.de), via search extract
https://git.phschoen.de/phschoen/lwr_server/raw/commit/1debece1117ae5d940d2f15c0647304bf45473c6/lwrserv/doc/LBRiiwa_en.pdf
- 14 R820: "axis 1 range as ±170° with a maximum torque of 320 Nm and a maximum speed of 85°/s ... axis 2 at ±120°
  with 320 Nm and 85°/s" -> `joints[0..1].effort_limit` (search-tool paraphrase of a jumbled table).
- The extract notes "176 Nm and 98°/s in the column for the 7 kg LBR iiwa 7 R800": so the 176 Nm figure in the
  pre-gathered distributor extract is not trusted for the 14 R820; torques for A3-A7 omitted.

## 5. KUKA specification "LBR iiwa 7 R800, LBR iiwa 14 R820" (primary, via search extract)
https://www.oir.caltech.edu/twiki_oir/pub/Palomar/ZTF/KUKARoboticArmMaterial/Spez_LBR_iiwa_en.pdf
- "Volume of working envelope 1.8 m³"; working-envelope side view is "Fig. 4-7" (not readable);
  the specification notes the arm's height depends on the media flange mounted on it. Not used numerically.

## Not used
- Distributor datasheet torques (A4 176, A5 110, A6/A7 40 Nm), described as garbled in the inputs:
  https://storage.googleapis.com/bucket-two-leobotics/product/datasheet-fiche-technique-robot-axe-industriel-collaboratif-7-axes-kuka-lbr-iiwa-7-r800-2-14-r820-2.pdf
