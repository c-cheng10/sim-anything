# UFactory Lite 6: sources

Accessed 2026-11-05.

**How these were retrieved.** Direct page fetches were blocked by this
session's network policy, so all values come from web-search extracts of the
cited pages. Quotes are reproduced as returned.

## 1. UFACTORY support article: Kinematic and dynamic parameters, Lite6

https://docs.supportarticle.ufactory.cc/support_articles/developer/kinematic-and-dynamic-parameters/lite6.html

First table, labelled "Modified D-H parameters", columns `theta offset (deg) | d (mm) | alpha (deg) | a (mm)`:

| Joint | theta offset (deg) | d (mm) | alpha (deg) | a (mm) |
|---|---|---|---|---|
| 1 | 0 | 243.3 | 0 | 0 |
| 2 | -90 | 0 | -90 | 0 |
| 3 | -90 | 0 | 180 | 200 |
| 4 | 0 | 227.6 | 90 | 87 |
| 5 | 0 | 0 | 90 | 0 |
| 6 | 0 | 61.5 | -90 | 0 |

A second extract of the same page confirms: "Joint 1 has d = 243.3 mm, and joint 4 has d = 227.6 mm with a = 87 mm.
Joint 3 has a = 200 mm, and joint 6 has d = 61.5 mm."

Link masses (kg): "Link 1 weighs 1.411 kg, link 2 weighs 1.34 kg, link 3 weighs 0.953 kg, link 4 weighs 1.284 kg,
link 5 weighs 0.804 kg, and link 6 weighs 0.13 kg". CoMs in mm per link, e.g. "link 2 is [179.0, 0.0, 58.4]"
(others not extracted; frame not stated in the extract).

## 2. Lite 6 technical specifications / hardware manual

https://docs.lite6.ufactory.cc/8.technical_specifications.html
https://www.ufactory.cc/wp-content/uploads/2025/05/Lite6_Hardware_Manual_V2.6.0.pdf
https://www.ufactory.cc/wp-content/uploads/2023/04/Lite-6-Developer-Manual-V1.11.0.pdf

- Joint ranges: "J1 ±360°, J2 ±150°, J3 -3.5° to 300°, J4 ±360°, J5 ±124°, and J6 ±360°" (hardware manual V2.6.0;
  developer manual gives the same).
- "maximum joint speed is 180°/s" (developer manual: "0～180°/s"), max end-effector speed "500mm/s".
- Payload "600 g", reach "440 mm"; Cartesian range "X: ±440mm; Y: ±440mm; Z: -165~683.5mm".
- Repeatability "±0.5 mm".
- Weight: documentation "8KG" (robot alone); product page spec card "7.2kg".
- Footprint "130 × 140 mm".

## 3. Product page

https://www.ufactory.us/product/lite-6
