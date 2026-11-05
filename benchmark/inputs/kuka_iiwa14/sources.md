# KUKA LBR iiwa 14 R820: sources

Accessed 2026-11-05.

**How these were retrieved.** Direct page fetches were blocked by this
session's network policy, so all values come from web-search extracts of the
cited pages. Quotes are reproduced as returned.

## 1. my.KUKA product page, LBR iiwa 14 R820

https://my.kuka.com/s/product/lbr-iiwa-14-r820/01t58000002hnktAAA?language=en_US
(also https://my.kuka.com/s/product/lbr-iiwa-14-r820/01tQF00000KVvjFYAT?language=en_US)
- Range of motion: "A1, A3, and A5 are ±170°, A2, A4, and A6 are ±120°, and A7 is ±175°".
- Speed with rated payload: "85°/s for A1 and A2, 100°/s for A3, 75°/s for A4, and 130°/s for A5".
- Max reach "820 mm"; rated payload "14 kg"; pose repeatability "±0.15 mm" (ISO 9283); weight "approx. 29.9 kg".
- "torque accuracy of ±2% of the maximum torque" (no per-axis torque values in the extract).

## 2. my.KUKA product page, LBR iiwa 14 R820 CR (cleanroom variant)

https://my.kuka.com/s/product/lbr-iiwa-14-r820-cr/01t58000004l0ebAAA?language=pt_BR
- Adds "135°/s for both A6 and A7". (Cleanroom variant; same axis data assumed by the extract, not confirmed for the
  standard arm.)

## 3. KUKA specification "LBR iiwa 7 R800, LBR iiwa 14 R820"

V5 (2015): https://www.oir.caltech.edu/twiki_oir/pub/Palomar/ZTF/KUKARoboticArmMaterial/Spez_LBR_iiwa_en.pdf
V8 (2019): https://www.yiliang.com.tw/data/editor/files/Spez_LBR_iiwa_en.pdf
- Weight "29.9 kg"; working envelope volume "1.8 m³" (V5) / "1.7 m³" (V8).
- Working envelope side view is a dimensioned figure ("Fig. 4-7" in V8). **The joint-to-joint dimensions are in
  the figure and could not be extracted by search.**
- Foundation loads (not joint torques): V5 "tilting moment of 310 Nm", "torque about axis 1 of 156 Nm"; V8 281.6 Nm / 172.6 Nm.

## 4. Distributor datasheet (KUKA brochure "sensitive robotics is beginning. The LBR iiwa.")

https://storage.googleapis.com/bucket-two-leobotics/product/datasheet-fiche-technique-robot-axe-industriel-collaboratif-7-axes-kuka-lbr-iiwa-7-r800-2-14-r820-2.pdf
- Per-axis max torque for the R820, extract described as garbled: "roughly 320 Nm for A1 and A2, 176 Nm for A4,
  110 Nm for A5, and 40 Nm for A6 and A7", plus an unlabelled "176 Nm" (probably A3, unconfirmed).

## 5. KUKA LBR Med brochure (medical variant, for cross-check only)

https://apps.kuka.com/KUKA/virtualshowroom/assets/downloads/KUKA_LBR_Med_EN.pdf
- Dimension table (letters A-H) for the 14 R820 variant: "A as 1,306 mm, B as 1,180 mm, G (reach) as 820 mm, and H as
  255 mm". The letters are not labelled as joint-to-joint distances in the extract. Different product (LBR Med).

## 6. Secondary (papers), not usable as values

- MDH parameter figure for the 14 R820: https://www.researchgate.net/figure/MDH-parameters-and-link-frames-of-the-KUKA-LBR-iiwa-14-R820_fig2_367031800
  (states the kinematics are described in modified DH; values not extracted)
- https://www.mdpi.com/2075-1702/13/10/944 Table 8 compares iiwa 14 R820 MDH parameters (values not extracted)
- A DergiPark paper extract gave d_bs = 340, d_se = 400, d_ew = 400, d_wf = 126 mm; those match the 7 R800, not the
  14 R820, and the table was garbled. Not used.
- Robot-Forum: "there is no unique set of DH parameters" (KUKA does not publish one).
