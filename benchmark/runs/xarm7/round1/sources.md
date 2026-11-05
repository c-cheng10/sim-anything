# UFactory xArm 7 (no gripper): sources

Accessed 2026-11-05. Direct fetches of every UFACTORY host (docs.supportarticle.ufactory.cc,
docs.xarm.ufactory.cc, download.ufactory.cc, www.ufactory.cc) and of manual mirrors
(static.generation-robots.com) were refused by this session's network policy. All values are
web-search extracts of the cited manufacturer pages (benchmark/inputs/xarm7/sources.md plus my own
searches), reproduced as returned.

## 1. UFACTORY support article: Kinematic and dynamic parameters, xArm 7 (manufacturer, primary)

https://docs.supportarticle.ufactory.cc/zhHans/support_articles/developer/kinematic-and-dynamic-parameters/xArm_Series/xarm-7.html
(English index: https://help.ufactory.cc/en/articles/4330809-kinematic-and-dynamic-parameters-of-ufactory-xarm-series,
whose outline lists "xArm7 Standard D-H Parameters"; values of that table were not extracted.)

Section "Modified D-H parameters". Columns `theta(rad) | d(mm) | alpha(rad) | a(mm) | offset(rad)`:

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
"Joint2 | 0 | 0 | -pi/2 | 0 | 0", "Joint7 | 0 | 97 | -pi/2 | 76 | 0". -> `joints[*].dh`

## 2. xArm user manual, chapter 8 technical specifications (manufacturer, primary)

https://docs.xarm.ufactory.cc/8.technical_specifications.html
- Joint ranges J1-J7: "(±360°, -117~116°, ±360°, -6~225°, ±360°, -97~180°, ±360°)" -> `joints[*].limits`
- "Repeatability ±0.1mm" -> `repeatability`
- maximum joint speed "180°/s" -> `joints[*].velocity_limit`
- Weight (arm only) "14.3kg" (not used; conflict with 13.7 kg)

## 3. UFACTORY support article: difference between xArm5, xArm6 and xArm7 (manufacturer)

https://docs.supportarticle.ufactory.cc/support_articles/hardware/the-difference-between-ufactory-xarm5-xarm6-and-xarm7.html
- J2 "-118° to 120°", J4 "-11° to 225°" (conflict with section 2; not used)
- Weight "13.7 kg"; payload 3.5 kg; reach 700 mm.

## 4. Product page (manufacturer)

https://www.ufactory.us/product/ufactory-xarm-7
- "xArm 7 has 3.5kg payload and ±0.1mm repeatability" -> `payload`; reach "700 mm" -> `reach.value`;
  weight "13.7 kg" -> `total_mass`.
- No reach definition found (searched the product pages and the "What's the working range of the
  UFACTORY xArm?" help article, https://help.ufactory.cc/en/articles/4362304-what-s-the-working-range-of-the-ufactory-xarm,
  whose extract only says the working-range diagrams "are only for safety assessment").
