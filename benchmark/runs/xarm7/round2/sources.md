# UFactory xArm 7 (round2): sources

Accessed 2026-11-05. Direct fetches of docs.supportarticle.ufactory.cc and docs.xarm.ufactory.cc fail in this
environment (host not resolvable through the proxy), so every value comes from web-search extracts of the
cited manufacturer pages (the pre-gathered `benchmark/inputs/xarm7/` plus two searches made in this run).
These are search-engine excerpts of primary manufacturer pages, not the pages themselves.

## 1. UFACTORY support article: Kinematic and dynamic parameters, xArm 7 (primary, via search extract)
https://docs.supportarticle.ufactory.cc/zhHans/support_articles/developer/kinematic-and-dynamic-parameters/xArm_Series/xarm-7.html
(English index: http://help.ufactory.cc/en/articles/4330809-kinematic-and-dynamic-parameters-of-ufactory-xarm-series)

Section "Modified D-H parameters", columns `theta(rad) | d(mm) | alpha(rad) | a(mm) | offset(rad)`:

| Joint | theta | d (mm) | alpha (rad) | a (mm) | offset |
|---|---|---|---|---|---|
| Joint1 | 0 | 267 | 0 | 0 | 0 |
| Joint2 | 0 | 0 | -pi/2 | 0 | 0 |
| Joint3 | 0 | 293 | pi/2 | 0 | 0 |
| Joint4 | 0 | 0 | pi/2 | 52.5 | 0 |
| Joint5 | 0 | 342.5 | pi/2 | 77.5 | 0 |
| Joint6 | 0 | 0 | pi/2 | 0 | 0 |
| Joint7 | 0 | 97 | -pi/2 | 76 | 0 |

Quoted extract strings: "theta(rad): 0. d(mm): 267. alpha(rad): 0. a(mm): 0. offset(rad): 0.",
"Joint2 | 0 | 0 | -pi/2 | 0 | 0", "Joint7 | 0 | 97 | -pi/2 | 76 | 0".
Used for `joints[*].dh` (pi/2 -> 90 deg).

## 2. xArm user manual, chapter 8 "Technical Specifications" (primary, via search extract)
https://docs.xarm.ufactory.cc/8.technical_specifications.html
- Joint ranges J1-J7: "(±360°, -117~116°, ±360°, -6~225°, ±360°, -97~180°, ±360°)" -> `joints[*].limits`
- Maximum joint speed "180°/s" -> `joints[*].velocity_limit`
- "Repeatability ±0.1mm" -> `repeatability`
- "Footprint | Ø 126 mm" -> base cylinder radius 63 mm
- "End Flange | DIN ISO 9409-1-A50/63(M5*6)" (not used numerically)
- Weight (arm only) "14.3kg" (not used; conflicts with 13.7 kg below)

## 3. UFACTORY support article: difference between xArm5, xArm6 and xArm7 (primary, via search extract)
https://docs.supportarticle.ufactory.cc/support_articles/hardware/the-difference-between-ufactory-xarm5-xarm6-and-xarm7.html
- "Weight(kg, body only) 13.7kg", "Payload(kg) 3.5kg", "Reach(mm) 700mm"
- J2 "-118° to 120°", J4 "-11° to 225°" (conflict with manual; manual values used)

## 4. Product page (primary)
https://www.ufactory.us/product/ufactory-xarm-7
- "xArm 7 has 3.5kg payload and ±0.1mm repeatability"; reach "700 mm"; weight "13.7 kg"
  -> `payload`, `reach.value`, `total_mass`
