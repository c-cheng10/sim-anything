# KUKA LBR iiwa 14 R820: sources (round 1)

Accessed 2026-11-05. Direct fetches of every PDF below failed (proxy 403 / host not in the allowed network
domains: oir.caltech.edu, yiliang.com.tw, git.phschoen.de, howtorobot.com, cdn.machineseeker.com), so all values
come from web-search extracts, quoted as returned. Items 1-5 also appear in `benchmark/inputs/kuka_iiwa14/sources.md`.

## 1. my.KUKA product page, LBR iiwa 14 R820 (primary)

https://my.kuka.com/s/product/lbr-iiwa-14-r820/01t58000002hnktAAA?language=en_US
- "A1, A3, and A5 are ±170°, A2, A4, and A6 are ±120°, and A7 is ±175°" -> `joints[*].limits`
- "85°/s for A1 and A2, 100°/s for A3, 75°/s for A4, and 130°/s for A5" -> `joints[0..4].velocity_limit`
- Max reach "820 mm" -> `reach.value`; rated payload "14 kg"; pose repeatability "±0.15 mm"; weight "approx. 29.9 kg"

## 2. KUKA LBR iiwa specification / brochure, third-party mirror (second-hand copy of a KUKA document)

https://git.phschoen.de/phschoen/lwr_server/raw/commit/1debece1117ae5d940d2f15c0647304bf45473c6/lwrserv/doc/LBRiiwa_en.pdf
(search extracts, 2026-11-05)
- Work-envelope table, 14 R820: "A 1,306 mm, B 1,180 mm, C 360 mm, D 420 mm, E 400 mm, F 255 mm, G 820 mm, and
  volume 1.8 m³"; the table notes that a dimension depends on the media flange option.
- Same table, 7 R800: "1,266 mm, 1,140 mm, 340 mm, 400 mm, 400 mm, 260 mm, and 800 mm, with a volume of 1.7 m³".
- The extracts do not say where each letter sits on the arm. Mapping used (inference, listed in `estimates`):
  C = base to A2, D = A2 to A4, E = A4 to A6, G = D + E, B = C + G, A - B = 126 = A6 to flange
  (iiwa 7: 1266 - 1140 = 126 too).
- Axis-data table (R820 column): A1 "320 Nm" "85°/s", A2 "320 Nm" "85°/s", A6 and A7 "40 Nm", "135°/s"
  -> `joints[0,1,5,6].effort_limit`, `joints[5,6].velocity_limit`.

## 3. my.KUKA product page, LBR iiwa 14 R820 CR (cleanroom variant, cross-check)

https://my.kuka.com/s/product/lbr-iiwa-14-r820-cr/01t58000004l0ebAAA?language=pt_BR
- "135°/s for both A6 and A7" (agrees with item 2).

## 4. Distributor copy of the KUKA brochure (second-hand, extract described as garbled)

https://storage.googleapis.com/bucket-two-leobotics/product/datasheet-fiche-technique-robot-axe-industriel-collaboratif-7-axes-kuka-lbr-iiwa-7-r800-2-14-r820-2.pdf
- "roughly 320 Nm for A1 and A2, 176 Nm for A4, 110 Nm for A5, and 40 Nm for A6 and A7", plus an unlabelled
  "176 Nm" (probably A3) -> `joints[3,4].effort_limit` sourced, `joints[2].effort_limit` = 176 estimate.

## 5. KUKA LBR Med brochure (medical variant, cross-check only)

https://apps.kuka.com/KUKA/virtualshowroom/assets/downloads/KUKA_LBR_Med_EN.pdf
- 14 R820 variant: "A as 1,306 mm, B as 1,180 mm, G (reach) as 820 mm, and H as 255 mm" (agrees with item 2).

## Not found / not used
- No DH table published by KUKA; papers' MDH tables were not extractable.
- Joint axis directions/signs, housing diameters, link masses: not found (estimates).
