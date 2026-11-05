# UFactory xArm 7: sources used

Accessed 2026-11-05. Direct fetches of ufactory.cc, docs.supportarticle.ufactory.cc and robotshop.com
failed (host not resolvable from this environment), so values are from the pre-gathered inputs
(`benchmark/inputs/xarm7/`, themselves from web-search extracts) plus new web-search extracts.

## 1. Modified D-H parameters (spec `joints[*].dh`)

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

Quoted extracts: "theta(rad): 0. d(mm): 267. alpha(rad): 0. a(mm): 0. offset(rad): 0.",
"Joint2 | 0 | 0 | -pi/2 | 0 | 0", "Joint7 | 0 | 97 | -pi/2 | 76 | 0".
Written in the spec with deg units (pi/2 = 90 exactly).

## 2. xArm user manual, chapter 8 "Technical Specifications" (spec `joints[*].limits`, `joints[*].velocity_limit`, `base.link.geometry[0].radius`)

https://docs.xarm.ufactory.cc/8.technical_specifications.html
- Joint ranges J1-J7: "(±360°, -117~116°, ±360°, -6~225°, ±360°, -97~180°, ±360°)"
- Maximum joint speed: "180°/s" (single value for all joints)
- Footprint: "Ø 126 mm" (web-search extract: "UFACTORY's technical specifications page gives the common
  xArm5/6/7 footprint as Ø 126 mm") -> base radius 63 mm
- Cartesian range: "X: ±700mm; Y: ±700mm; Z: -400~951.5mm" (used only to interpret reach)
- "Repeatability ±0.1mm"; weight (arm only) "14.3kg" (not used, see conflict below)

## 3. Product page (spec `total_mass`, `payload`, `reach.value`)

https://www.ufactory.us/product/ufactory-xarm-7
- "xArm 7 has 3.5kg payload and ±0.1mm repeatability"; reach "700 mm"; weight "13.7 kg".

## 4. Support article: difference between xArm5, xArm6 and xArm7 (conflict reference only)

https://docs.supportarticle.ufactory.cc/support_articles/hardware/the-difference-between-ufactory-xarm5-xarm6-and-xarm7.html
- J2 "-118° to 120°", J4 "-11° to 225°"; weight "13.7 kg"; payload 3.5 kg; reach 700 mm.

## 5. Looked for, not used

- Joint torques: only https://forum.ufactory.cc/t/torque-specifications/3531 (extract: "J1/J2 -42Nm, J3/J4 -19Nm,
  J5/J6 - 7Nm", later reply "J1/J2 -42Nm, J3/J4/J5 -19Nm, J6/J7 - 7Nm", continuous vs peak disputed). Ambiguous: omitted.
- Reach definition / working-space drawing (user manual "Working space of xArm7"): figure contents not retrievable.
  https://help.ufactory.cc/en/articles/4362304-what-s-the-working-range-of-the-ufactory-xarm says only "700mm".
