# UFactory xArm 7: sources

Accessed 2026-11-05.

**How these were retrieved.** Direct page fetches were blocked by this
session's network policy, so all values come from web-search extracts of the
cited pages. Quotes are reproduced as returned.

## 1. UFACTORY support article: Kinematic and dynamic parameters, xArm 7

https://docs.supportarticle.ufactory.cc/zhHans/support_articles/developer/kinematic-and-dynamic-parameters/xArm_Series/xarm-7.html
(Chinese-language page; English index: http://help.ufactory.cc/en/articles/4330809-kinematic-and-dynamic-parameters-of-ufactory-xarm-series)

Section 1 "Modified D-H parameters". Columns: `theta(rad) | d(mm) | alpha(rad) | a(mm) | offset(rad)`.
Rows (two queries; joints 1, 2, 7 from the first, 3-6 from the second):

| Joint | theta (rad) | d (mm) | alpha (rad) | a (mm) | offset (rad) |
|---|---|---|---|---|---|
| Joint1 | 0 | 267 | 0 | 0 | 0 |
| Joint2 | 0 | 0 | -pi/2 | 0 | 0 |
| Joint3 | 0 | 293 | pi/2 | 0 | 0 |
| Joint4 | 0 | 0 | pi/2 | 52.5 | 0 |
| Joint5 | 0 | 342.5 | pi/2 | 77.5 | 0 |
| Joint6 | 0 | 0 | pi/2 | 0 | 0 |
| Joint7 | 0 | 97 | -pi/2 | 76 | 0 |

Exact extract strings: "theta(rad): 0. d(mm): 267. alpha(rad): 0. a(mm): 0. offset(rad): 0.",
"Joint2 | 0 | 0 | -pi/2 | 0 | 0", "Joint7 | 0 | 97 | -pi/2 | 76 | 0".
The page also has a Standard D-H table and link mass parameters (not extracted). In modified DH, the `a` and
`alpha` on row i are a_{i-1}, alpha_{i-1}.

## 2. xArm technical specifications (user manual chapter 8)

https://docs.xarm.ufactory.cc/8.technical_specifications.html
- Joint ranges J1–J7: "(±360°, -117~116°, ±360°, -6~225°, ±360°, -97~180°, ±360°)"
- "Repeatability ±0.1mm", maximum joint speed "180°/s", max end-effector speed "1 m/s"
- Weight (arm only): "14.3kg"

## 3. UFACTORY support article: difference between xArm5, xArm6 and xArm7

https://docs.supportarticle.ufactory.cc/support_articles/hardware/the-difference-between-ufactory-xarm5-xarm6-and-xarm7.html
- Joint ranges: J2 "-118° to 120°", J4 "-11° to 225°", others as above.
- Weight "13.7 kg"; payload 3.5 kg; reach 700 mm.

## 4. Product page

https://www.ufactory.us/product/ufactory-xarm-7
- "xArm 7 has 3.5kg payload and ±0.1mm repeatability"; reach "700 mm"; weight "13.7 kg".
