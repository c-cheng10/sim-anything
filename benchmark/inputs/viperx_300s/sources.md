# Trossen ViperX 300 S: sources

Accessed 2026-11-05.

**How these were retrieved.** Direct page fetches were blocked by this
session's network policy, so all values come from web-search extracts of the
cited pages. Quotes are reproduced as returned.

## 1. Interbotix X-Series Arms docs: ViperX-300 6DOF (vx300s) specifications

https://docs.trossenrobotics.com/interbotix_xsarms_docs/specifications/vx300s.html
- Default joint limits (deg, from the zero/centred position), "set in the firmware, and represent the safe range of
  operation": waist "±180", shoulder "±101" (two servos), elbow "-101 to 92", forearm roll "±180",
  wrist angle "-107 to 130", wrist rotate "±180"; gripper "42 to 116 mm" (linear).
- "750mm reach and a 1500mm total span"; repeatability "1 mm"; accuracy "5–8 mm".
- Working payload "750 g" ("no more than about 50% extension" recommended at 750 g).

## 2. Interbotix X-Series Arms docs: Specifications (all arms)

https://docs.trossenrobotics.com/interbotix_xsarms_docs/specifications.html
- Reach table, ViperX-300 6DOF: section lengths "306, 300, 70, 69, and 68 mm" for upper arm (A to B), forearm
  (B to C), wrist tilt to wrist rotate (C to D), gripper to rail (D to E), fingertip (E to F); cumulative
  "306 mm to the elbow, 606 mm to wrist tilt, 676 mm to wrist rotate, 745 mm to the gripper rail, and 812 mm to the
  fingertip".
- "Offsets & True Upper Arm Length (mm)" table, ViperX-300 6DOF row: "300, 60, 306, 300, and 11.3°" (columns: offsets,
  true upper arm length, forearm length, forearm offset angle; the extract warns the column mapping is a best reading).
  Consistency: sqrt(300² + 60²) = 305.9 ≈ 306 and atan(60/300) = 11.3°, so 300 and 60 are the two legs of the
  upper arm (shoulder->elbow) and 11.3° is the angle of that offset.
- Shoulder height above the base: not found.

## 3. Trossen product page

https://www.trossenrobotics.com/viperx-300
- 6 DOF, "750mm reach", "1500mm" span; working payload "750g"; product described as discontinued.
