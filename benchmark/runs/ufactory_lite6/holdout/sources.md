# UFactory Lite 6 sources (holdout run)

Accessed 2026-11-05. The ufactory hosts (docs.supportarticle.ufactory.cc etc.) could not be fetched from this
environment (DNS blocked), so values come from web-search extracts, as pre-gathered in
`benchmark/inputs/ufactory_lite6/`, plus one web search in this run.

## 1. UFACTORY support article: Kinematic and dynamic parameters, Lite6 (primary)

https://docs.supportarticle.ufactory.cc/support_articles/developer/kinematic-and-dynamic-parameters/lite6.html

First table, labelled "Modified D-H parameters", columns `theta offset (deg) | d (mm) | alpha (deg) | a (mm)`:

| Joint | theta offset (deg) | d (mm) | alpha (deg) | a (mm) | used as |
|---|---|---|---|---|---|
| 1 | 0 | 243.3 | 0 | 0 | joints[0].dh |
| 2 | -90 | 0 | -90 | 0 | joints[1].dh |
| 3 | -90 | 0 | 180 | 200 | joints[2].dh |
| 4 | 0 | 227.6 | 90 | 87 | joints[3].dh |
| 5 | 0 | 0 | 90 | 0 | joints[4].dh |
| 6 | 0 | 61.5 | -90 | 0 | joints[5].dh (flange) |

Second extract: "Joint 1 has d = 243.3 mm, and joint 4 has d = 227.6 mm with a = 87 mm. Joint 3 has a = 200 mm, and
joint 6 has d = 61.5 mm."

Link masses: "Link 1 weighs 1.411 kg, link 2 weighs 1.34 kg, link 3 weighs 0.953 kg, link 4 weighs 1.284 kg, link 5
weighs 0.804 kg, and link 6 weighs 0.13 kg" -> joints[i].link.mass. CoM only for link 2 ("[179.0, 0.0, 58.4]", frame
unstated): not used.

## 2. Hardware manual V2.6.0 (joint ranges)

https://www.ufactory.cc/wp-content/uploads/2025/05/Lite6_Hardware_Manual_V2.6.0.pdf
- "J1 ±360°, J2 ±150°, J3 -3.5° to 300°, J4 ±360°, J5 ±124°, and J6 ±360°" -> joints[*].limits
  (developer manual gives the same; a reseller page found in this run, https://www.tegakari.net/en/?p=20682, also lists
  "Joint 1 | 360 ° ±; Joint 2 | 150 ° ±; Joint 3 | -3.5 ° ~ 300 °")

## 3. Developer manual V1.11.0 (speed)

https://www.ufactory.cc/wp-content/uploads/2023/04/Lite-6-Developer-Manual-V1.11.0.pdf
- "maximum joint speed is 180°/s" ("0～180°/s") -> joints[*].velocity_limit = 180 (one value for every joint)

## 4. Technical specifications docs

https://docs.lite6.ufactory.cc/8.technical_specifications.html
- Weight "8KG" (robot alone) -> total_mass = 8 (product page spec card https://www.ufactory.us/product/lite-6 says
  "7.2kg": conflict)
- Payload "600 g" -> payload = 0.6 kg
- Reach "440 mm" -> reach.value
- Cartesian range "X: ±440mm; Y: ±440mm; Z: -165~683.5mm" -> used to infer the reach definition (see NOTES.md)
- Repeatability "±0.5 mm" -> repeatability (reseller tegakari.net lists ±0.2 mm, not used)
- Footprint "130 × 140 mm" -> base cylinder radius 65 mm (estimate)
