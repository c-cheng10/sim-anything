# UR5e round0 notes

**Sources.** UR "DH parameters for calculations of kinematics and dynamics" article (DH table, link masses,
CoMs), UR5e datasheet 08/2023 (mass, payload, reach, footprint), UR5e techsheet (joint ranges, speeds,
repeatability), user manual SW5.19 (reach is measured from the base joint), UR torque article plus a UR forum
post (effort limits). universal-robots.com could not be fetched, so all values come from web-search extracts
(see sources.md).

**Convention.** `dh_standard`, rows copied as published (m; π/2 written as 90 deg), theta_i = q_i.
q = 0 is UR's zero pose: arm stretched horizontally along -x, wrist 2 hanging down, flange facing -y.
FK at q = 0 puts the flange at (-0.8172, -0.2329, 0.0628) m, i.e. (a2+a3, -(d4+d6), d1-d5).

**EE site.** Tool flange face centre = DH frame 6 (d6 = 0.0996 m from the wrist 3 axis); `ee.origin` is zero.

**Estimates.** None in the spec. The base mass is not given: the builder assigns the remainder of the 20.6 kg
total to it (20.6 - 17.7 = 2.9 kg, which also absorbs the cable). Link radii are not published and are not
set; the builder derives them from the sourced link masses. The base is a Ø149 mm cylinder (datasheet).

**Iterations.**
1. Fail, reach: with `measured_to: ee_site` the flange reaches 0.969 m from the J1 axis (14% over 850 mm).
2. Pass (11/11): `measured_to: wrist_center` (wrist 2 joint origin), 0.828 m, 2.6% under 850 mm. No sourced
   number changed.

**Renders.** Front/side/top match UR's zero pose as described above: thick shoulder and upper arm, thinner
forearm, wrist 1 offset sideways, wrist 2 down, flange pointing sideways. Stable hold and self-collision pass.

**Doubts.**
- Reach endpoint is not stated by UR. The flange gets 0.93-0.97 m from the J1 axis, the wrist 0.828 m.
  None of them gives exactly 850 mm, so the choice of `wrist_center` is an interpretation.
- The extracted CoMs for links 4 and 5 differ only in the sign of y. The link 6 CoM (z = -0.001159 m) is
  questioned on the UR forum. All CoMs come from search extracts and should be checked against the live page.
- Effort limits for base/shoulder/elbow/wrist 1 come from a forum post only, and they are damage ratings.
- Collision geometry follows the DH frames, so the real lateral offsets of the shoulder and elbow housings
  (collapsed into d4 = 0.1333 m by DH) are not shown. Radii are builder defaults, not housing sizes.
- Mass conflict 20.6 kg (datasheet) vs 20.7 kg (manual); footprint Ø149 vs Ø151 mm.
