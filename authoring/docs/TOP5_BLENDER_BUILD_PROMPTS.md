# The Five Assets to Build First — Blender Build Prompts

**Course:** Mobile Charging Repair Simulation (BC.1 / BC.2 / BC.3)
**Purpose:** these five assets carry the teaching load of the entire course. Build these to a genuinely high standard and 16 of 18 scenes inherit the quality. Build them weakly and no amount of polish downstream recovers it.
**Prepared:** 21 August 2026

---

## Why these five

| # | Asset | Teaching job | Scenes | Days |
|---|---|---|---|---|
| 1 | **B02 — Mainboard (PBA)** | The stage. Gives every other part a *location* the learner can find on a real board. | 7 | 4.0 |
| 2 | **B05 — USB-C receptacle assembly** | The part. Nine named components the learner must identify, exploded and pin-by-pin. | 5 | 4.0 |
| 3 | **B10 + B11 — IFC assembly (flex ribbon + ZIF socket)** | The fault. Your own voiceover calls this *"one of the most common and most misdiagnosed charging complaints there is."* | 4 | 7.0 |
| 4 | **B40 — Solder joint state set** | The judgement. Good vs cold vs cracked vs bridged vs dry. This is the actual skill being certified. | 5 | 1.5 |
| 5 | **B28 — Hot air rework station + nozzle** | The instrument. The primary tool in five of the six fixes. | 6 | 2.0 |

**Total: 18.5 person-days.** Five assets, 27 scene-appearances between them.

They form a complete teaching chain: **stage → part → fault → judgement → tool.** A learner who understands all five can be walked through any of the six fixes.

### Runners-up, and why they waited

- **B15/B16 battery connector** — safety-critical (disconnect first) and your storyboard wants a photoreal macro of it. It is asset #6. It only lost out because Fix 6 sits at the end of the learning path.
- **B13 Charger IC + BGA array** — needed for Fix 4/5, but those are Level-4 repairs most learners will escalate rather than attempt.
- **B18 multimeter** — the learner's *first* action, so tempting. But it is a box with a dial; its difficulty is the live readout, which is runtime code (U02), not modelling.

---

# HOUSE STANDARD — applies to all five

Put this at the top of every build. Do not restate it inside the individual prompts.

```
=== HOUSE STANDARD: ConveGenius Mobile Repair 3D Assets ===

AUDIENCE
Learners aged 17-25 in Indian ITI / TVET programmes. Many have never opened a
phone. Many will view this on a sub-Rs-12,000 Android phone over a 3G connection.
Every modelling and material decision is judged against one question:
"Can a first-timer point at this on screen and then find the same thing on a
real bench?" Beauty that does not survive that test is wasted work.

SCALE AND UNITS  (get this wrong and everything downstream fights you)
- Scene Unit System: Metric, Unit Scale 0.001, Length = Millimeters.
- Model at TRUE 1:1 real-world size. A USB-C port really is about 8 mm wide.
  Do not model "phone-sized" and scale later.
- Set every viewport and camera Clip Start to 0.01 mm. The default 0.1 m clips
  straight through these parts at macro zoom - this is the single most common
  setup mistake on jobs at this scale.
- Apply all scale before export (Ctrl+A > Scale). Non-uniform object scale
  breaks normals in glTF.

ORIENTATION AND ORIGINS
- +Z is up. +Y is "into the phone" (away from the viewer at rest).
- Every object's origin sits at its functional pivot, not its bounding-box
  centre: a hinged flap pivots on its hinge line, a nozzle pivots at its
  mounting collar, a chip's origin is the centre of its ball array.
- Freeze a clean rest pose. The runtime resets to it between scenes.

NAMING  (the runtime addresses objects by name - typos become bugs)
  <ASSETID>_<PART>_<detail>          e.g. B05_SHELL, B05_PIN_A01
  <ASSETID>_ANCHOR_<label>           empty objects for UI callout leader lines
  <ASSETID>_STATE_<name>             swappable variant meshes
  MAT_<material>                     e.g. MAT_GOLD_HARD, MAT_SOLDER_COLD
  ANIM_<assetid>_<action>            e.g. ANIM_B11_FLAP_OPEN
ASCII only. No spaces, no dots, no Hindi characters in object names.

TOPOLOGY
- Quads where the surface will deform or catch a highlight; triangles are fine
  on flat hard-surface faces that never bend.
- No n-gons on any curved or bevelled surface.
- Bevel every visible hard edge, 2-segment minimum, width scaled to the part
  (0.05 mm on a connector shell, 0.15 mm on a tool housing). A perfectly sharp
  90-degree edge reads as "cheap 3D" instantly and is the #1 tell of rushed work.
- Weighted normals on all hard-surface parts before export.
- Custom split normals baked. Do not ship autosmooth-only.

MATERIALS - use these values, they are calibrated for this course
  MAT_STEEL_SHELL   base #8E9194  metallic 1.0  rough 0.30  anisotropy 0.4
                    (drawn stainless, brushed along the part's long axis)
  MAT_GOLD_HARD     base #D9B551  metallic 1.0  rough 0.18
                    (hard gold over nickel - PALER and less saturated than
                     jewellery gold. Do not use #FFD700, it reads as fake.)
  MAT_SOLDER_GOOD   base #BFC4C9  metallic 1.0  rough 0.32
  MAT_SOLDER_COLD   base #A8ABAE  metallic 1.0  rough 0.68  + fine grain bump
  MAT_PCB_MASK      base #0E4F3C  metallic 0.0  rough 0.38  clearcoat 0.15
  MAT_HOUSING_LCP   base #1A1A1D  metallic 0.0  rough 0.46
  MAT_POLYIMIDE     base #C08A28  metallic 0.0  rough 0.42  transmission 0.12
                    (the amber flex-cable film - slight translucency sells it)
  MAT_FLUX_WET      clearcoat 1.0  clearcoat_rough 0.05  over the base material
All textures: 2K only for the four hero parts. 1K default. 512 for anything
that is never the subject of a macro shot. Pack to a shared atlas per asset.

LIGHTING - one rig, reused for all five assets
- Large area light, 250 x 250 mm equivalent, top-front-left, the primary source.
  Its soft reflection running along a metal edge is what makes the shape readable.
- Smaller fill, front-right, 25% intensity.
- Rim light behind and above, to separate the part from the dark background.
- Studio HDRI at 0.3 strength for reflection detail only, not for illumination.
- Background: dark neutral (#0E1420 to #16213A), matching the existing
  ConveGenius sim backdrop.

THE DEPTH-OF-FIELD RULE  (read this twice)
Shallow depth of field looks professional and HIDES THE THING YOU ARE TEACHING.
For every explanatory shot: 85-135 mm focal length, aperture stopped down so the
whole part is sharp. DOF is permitted ONLY in the single hero product shot of an
asset, never in an exploded view, a callout frame, or a step-strip panel.
If a learner cannot read a pin, the render has failed.

WEB DELIVERY BUDGET
- Export glTF 2.0 binary (.glb), +Y up, Draco mesh compression on, KTX2/Basis
  textures.
- Per-scene budget: 5 MB target, 8 MB hard ceiling. Whole course: 25 MB.
- Three LODs on every asset: LOD0 full, LOD1 at 40%, LOD2 at 15%.
  LOD0 is used only when the part is the subject of a macro or inspection shot.
- Export animations as separate named clips, not one baked timeline.
- No lights or cameras in the .glb. The runtime owns those.

DELIVERABLES PER ASSET
1. Working .blend, layers and collections named per the scheme above.
2. LOD0/1/2 .glb set, Draco + KTX2, under budget.
3. Named animation clips.
4. Turntable render, 1080p, 5 seconds, for review sign-off.
5. Six still renders at 2048 px for the infographic team to build cards from
   (see the per-asset shot list). PNG, transparent background.
6. A short text note listing every real-world dimension used and its source.

WHAT GETS A BUILD REJECTED
- Sharp unbevelled edges on visible geometry.
- #FFD700 "video game gold" on contacts.
- Solder modelled as a smooth grey blob with no fillet geometry.
- A PCB with a flat green texture and no visible traces, vias or silkscreen.
- Depth of field in an explanatory shot.
- Any part whose real-world size was guessed rather than taken from a datasheet
  or a measured teardown.
```

---

# PROMPT 1 of 5 — B02 Mainboard (PBA)

```
BUILD: B02_MAINBOARD - smartphone printed board assembly
REUSE: 7 of 18 scenes. Highest-reuse asset in the course.
BUDGET: 45k tris LOD0 | 2K colour + 1K roughness/normal | 4.0 days

--- THE TEACHING JOB ---
This is not scenery. It is the map. Every fix in BC.3 begins with the learner
locating a part ON this board. If the board is generic mush, "the IFC socket
sits a short distance in from the port" is a sentence with no picture attached.
The learner must be able to look at a real opened phone afterwards and
recognise the same four regions.

--- THE ONE THING THAT MUST BE UNMISTAKABLE ---
The spatial relationship between four zones, in this order along the board:
    charging port (at the board EDGE) -> IFC socket (a short way in)
    -> Charger IC / PMIC (mid-board, under a shield) -> battery connector.
A learner should be able to trace that path with a finger without any labels on.

--- REFERENCE ---
Use the supplied realme teardown photo (storyboard p5, the shot with two
connectors circled in red) as the layout authority. Do not copy a specific
commercial board 1:1; build a plausible generic mid-range Android layout that
matches the reference's PROPORTIONS and part positions.

--- GEOMETRY ---
Board substrate:
  - 120 x 50 x 0.9 mm, corners radiused 1.5 mm, two mounting notches.
  - Model the board edge as a real laminated edge: visible FR4 core with a
    thin solder-mask lip top and bottom. A single flat extrusion reads as
    cardboard.
  - Via field: ~200 plated through-holes as instanced geometry, NOT texture
    alone. At macro zoom, painted vias are immediately obvious.
Copper traces:
  - Solder mask with real routed traces underneath, visible as raised relief.
  - The five charging-path traces must be a SEPARATE material slot so the
    runtime can light them up in sequence for the I04 signal overlay.
    Name it MAT_TRACE_HIGHLIGHT.
Populated components (build a library, then instance):
  - 0402 and 0201 passives: ~120 instances. Two mesh variants only.
  - EMI shield cans: 3, with the largest removable (a separate object,
    B02_SHIELD_PMIC) because Fix 4 and 5 work underneath it.
  - Test pads, ~20, gold plated.
  - Silkscreen: white component designators and one board revision string.
    Real, readable, tiny. This detail does more for believability than
    another 10k tris.
Named zones - build these as real geometry AND drop an empty at each:
  B02_ZONE_PORT        + B02_ANCHOR_PORT
  B02_ZONE_IFC         + B02_ANCHOR_IFC
  B02_ZONE_PMIC        + B02_ANCHOR_PMIC
  B02_ZONE_BATTCONN    + B02_ANCHOR_BATTCONN
The anchors are where the runtime attaches callout leader lines. Place them
just above the surface, pointing +Z.

--- SOCKETS ---
Model empty mounting footprints (pads + solder mask openings) at all four
zones so B05, B11, B13 and B15 can be parented in and out. The pad geometry
must survive with the part removed - Fix 2 and Fix 3 both show a BARE CLEANED
PAD, and that shot only works if the pads exist independently.

--- STATES ---
  B02_STATE_CLEAN       factory condition
  B02_STATE_DUSTY       light dust and fingerprint film, as it arrives
  B02_STATE_PAD_BARE    port and IFC pads with the part removed, old solder
                        still on them (the "before cleaning" of Fix 2 step 5)
  B02_STATE_PAD_CLEANED same pads, wicked and IPA-wiped, flat and bright
                        (the "after" - this pair IS the lesson)

--- MATERIALS ---
MAT_PCB_MASK on the substrate, but vary it: a real board is not one flat green.
Add subtle mottling, a slightly glossier finish over dense copper areas, and
faint flux staining near the connectors. MAT_GOLD_HARD on pads and test points.
Brushed nickel on shield cans, roughness 0.42.

--- SHOT LIST for the infographic team (2048 px, transparent PNG) ---
  1. Top-down flat, no labels, whole board.
  2. Top-down with the four zones tinted for I01.
  3. Three-quarter hero with soft rim light.
  4. Macro of the board edge showing the port footprint.
  5. Bare pad vs cleaned pad, matched camera, side by side.
  6. Shield can on / off at the PMIC zone.

--- ACCEPTANCE CRITERIA ---
[ ] A learner shown the render and then a real opened phone can point to the
    charging port zone and the battery connector zone unprompted.
[ ] At maximum macro zoom, vias read as holes and silkscreen text is legible.
[ ] The four sockets accept and release their child parts with no gap or
    intersection.
[ ] LOD0 under 45k tris. LOD1 holds the four zones recognisably.
[ ] Bare-pad and cleaned-pad states are visibly, obviously different at a
    glance - not a subtle roughness change.
```

---

# PROMPT 2 of 5 — B05 USB-C Receptacle Assembly

```
BUILD: B05_PORT - USB-C female receptacle, exploded-capable
REUSE: 5 scenes. HERO ASSET. Also the subject of the course's densest scene.
BUDGET: 30k tris LOD0 | 2K + steel/gold PBR | 2 anim clips | 4.0 days

--- THE TEACHING JOB ---
BC.1 scene 2 names NINE separate components inside a part that is 8 mm wide.
The voiceover says: "the charging port looks like a simple slot - but inside,
there's a small city of pins." That sentence has to land visually. This asset
is how it lands.

--- THE ONE THING THAT MUST BE UNMISTAKABLE ---
That the port is an ASSEMBLY, not a hole. The explode animation is the whole
point: shell separates from housing separates from the flex tail, and the
learner sees three things where they thought there was one.

--- REAL DIMENSIONS ---
Approximate, and I want them verified against a real datasheet before you
model - do not take these as final:
  - Cavity opening        ~8.3 x 2.5 mm
  - Outer shell           ~8.9 x 3.2 mm, depth ~7.3 mm
  - 24 contacts, 12 per row (Row A A1-A12, Row B B1-B12), ~0.5 mm pitch
  - Board standoff, top-mount: ~0.6 mm
Pull a datasheet for a real mid-range handset receptacle and correct these.
Log what you used in the dimensions note. Proportion accuracy matters more
here than in any other asset in the course, because the learner will hold the
real part in tweezers and compare.

--- OBJECT HIERARCHY (exact names - the explode animation drives these) ---
  B05_PORT                      (empty, root)
   |- B05_SHELL                 stainless EMI shield, drawn one-piece
   |   |- B05_SHELL_TAB_L       shield/ground tabs, separate - they solder first
   |   |- B05_SHELL_TAB_R
   |- B05_HOUSING               high-temp plastic insert holding the pins
   |- B05_PINROW_A              parent empty
   |   |- B05_PIN_A01 ... A12   TWELVE SEPARATE OBJECTS. Not one mesh.
   |- B05_PINROW_B
   |   |- B05_PIN_B01 ... B12
   |- B05_TONGUE                the central tongue the pins sit on
   |- B05_LEGS                  mounting legs / solder tabs
   |- B05_GASKET                waterproof seal ring (hide by default,
                                storyboard says "on water-resistant models")
   |- B05_ANCHOR_A01 ... A12    callout anchors, one per pin
   |- B05_ANCHOR_SHELL, _HOUSING, _LEGS, _GASKET

Twelve separate pin objects per row is non-negotiable. The storyboard asks for
"each pin lights up sequentially as its label appears." One merged pin mesh
makes that impossible and there is no cheap workaround.

--- PIN COLOUR CODING ---
Assign each pin one of six material slots so the runtime can group them:
  MAT_PIN_GND    GND               A1  A12  B1  B12
  MAT_PIN_VBUS   power             A4  A9   B4  B9
  MAT_PIN_CC     config channel    A5 (CC1) B5 (CC2)
  MAT_PIN_DATA   USB 2.0 D+/D-     A6 A7 B6 B7
  MAT_PIN_SBU    sideband          A8  B8
  MAT_PIN_SS     SuperSpeed TX/RX  A2 A3 A10 A11, B2 B3 B10 B11
All six start as MAT_GOLD_HARD; the runtime swaps in an emissive variant to
light a group. This mapping is what makes the reversibility lesson work - when
you flip the plug, the learner watches Row A go dark and Row B light up.

--- ANIMATION CLIPS ---
ANIM_B05_EXPLODE       90 f. Shell lifts +Z and back -Y, housing follows,
                       flex tail separates last. Ease-out, generous spacing,
                       nothing overlapping at rest. Reversible (play backwards
                       for assembly).
ANIM_B05_CUTAWAY_180   120 f. Camera-relative 180 deg rotation with the near
                       shell wall clipped away, revealing the pin row. Bake
                       the camera move; the pin lighting is runtime.

--- MATERIALS ---
Shell: MAT_STEEL_SHELL, brushed along the long axis, with a faint draw line
where a real stamped shell is formed. Add micro-scratches at the cavity mouth -
this port has had a cable pushed into it a thousand times, and that wear is
itself a teaching detail.
Pins: MAT_GOLD_HARD. Pale, not yellow.
Housing: MAT_HOUSING_LCP, near-black, matte, with the faint sink marks of a
moulded part.
Gasket: soft black rubber, roughness 0.85, subsurface 0.02.

--- STATES (feed B41, the damage variants) ---
  B05_STATE_GOOD
  B05_STATE_BENT_PINS      2-3 contacts visibly deflected, one touching a
                           neighbour. Shape keys off GOOD, not a new model.
  B05_STATE_CRACKED_HOUSING hairline fracture at the housing corner, the
                           storyboard's "port-drop damage"
  B05_STATE_TABS_BROKEN    one shield tab lifted clear of its pad - THE most
                           common "not charging" cause per your own voiceover
  B05_STATE_DUSTY          lint and pocket debris packed into the cavity,
                           for the Fix 1 before/after

--- SHOT LIST (2048 px, transparent PNG) ---
  1. Three-quarter hero, whole port, nothing labelled.
  2. Head-on into the cavity - the "small city of pins" shot.
  3. Exploded, final frame, all three groups clear of each other.
  4. Cutaway showing the pin row inside the shell.
  5. Top-down with the pin grid legible, for the I03 pinout table overlay.
  6. GOOD vs BENT_PINS, matched camera, for I27 and the Fix 1/2 branch.

--- ACCEPTANCE CRITERIA ---
[ ] All 24 pins individually selectable and individually lightable.
[ ] Explode animation has no intersection at any frame, and reads clearly at
    720p on a 5-inch screen - test it there, not on your monitor.
[ ] Dimensions match a cited datasheet within 5%.
[ ] The cavity is visibly a metal-lined box with a tongue in it, not a
    black hole. Light it so the interior reads.
[ ] BENT_PINS is obvious to an untrained eye in under two seconds.
```

---

# PROMPT 3 of 5 — B10 + B11 IFC Assembly

```
BUILD: B10_FPC (flex ribbon) + B11_ZIF (board-side socket)
REUSE: 4 scenes, and the subject of Fix 3.
BUDGET: B10 6k tris | B11 14k tris | 2K gold/black | 4 anim clips | 7.0 days
NOTE: build these two as ONE job. They only make sense together and the
      animation depends on both.

--- THE TEACHING JOB ---
Your own voiceover, verbatim: "If that flap isn't fully closed, or if the
solder anchoring the socket to the board has cracked, you get a phone that
charges only if you hold the cable at just the right angle - ONE OF THE MOST
COMMON AND MOST MISDIAGNOSED CHARGING COMPLAINTS THERE IS."

That is the highest-value sentence in the whole storyboard. This asset is the
only thing that can teach it. A technician who learns this one relationship
will diagnose faster than one who memorised all six fixes.

--- THE ONE THING THAT MUST BE UNMISTAKABLE ---
The difference between a flap that is LATCHED and a flap that LOOKS closed but
is not. Model the half-closed state deliberately and make the visual tell
explicit: the flap sits perhaps 15 degrees proud, the ribbon's alignment marks
do not line up, and there is a sliver of gap at the hinge. Then teach it.

Second, from the same storyboard: THE SHAPE RULE. The rigid metal box (B05)
and the flat gold ribbon (B10) are two different parts with two different
fixes, and confusing them is the commonest error in BC.3. These two assets
must never be mistakable for each other in a render. Contrast them
deliberately - hard steel box vs soft amber film.

--- B10 GEOMETRY: the flex printed circuit ---
  - Polyimide film 0.12 mm thick, ~6 mm wide, ~35 mm long routed path.
  - Visible copper traces UNDER the amber film - the film's slight
    translucency showing the trace pattern through it is the detail that makes
    this part read as real. Do not paint traces on the surface.
  - Gold landing pads at the board end, ~12 contacts.
  - B10_STIFFENER: rigid strip laminated to the insertion tail. Separate
    object. The storyboard names it as a component, so it must be pointable.
  - Coverlay openings where the pads are exposed.
  - Bend relief: a real FPC has a service loop, not a taut straight run.
    Model the resting shape with a gentle curve.

--- B10 RIG (this is the hard part - it decides whether Fix 3 works) ---
  - Bone chain, 8-12 bones along the ribbon's length, named
    B10_BONE_01 .. B10_BONE_12, root at the port end.
  - Weight painted for smooth bend with NO pinching at the stiffener join.
  - DO NOT USE CLOTH SIMULATION. Blender cloth does not export to glTF and
    cannot be replayed in the runtime. If you want sim-quality motion, sim it,
    then bake to the bone chain, then delete the sim.
  - Bake all deformation to the armature and verify it in a glTF round-trip
    BEFORE animating. A ribbon that looks perfect in Blender and snaps flat on
    import has cost you the whole 3 days.

--- B11 GEOMETRY: the board-side ZIF socket ---
  B11_ZIF                        (empty, root)
   |- B11_BODY                   black LCP housing, ~7 x 3 x 1 mm
   |- B11_FLAP                   THE HINGED LATCH. Origin exactly on the
   |                             hinge axis. This is the most important pivot
   |                             in the course.
   |- B11_PIN_01 .. B11_PIN_12   gold contact fingers, separate objects,
   |                             each with visible spring geometry
   |- B11_SOLDER_L, _R           anchoring solder fillets at the socket ends -
   |                             separate objects, because "cracked solder
   |                             anchoring the socket" is a named fault
   |- B11_ANCHOR_FLAP, _PINS, _SOLDER, _BODY

  The contact fingers must look SPRUNG - a visible curve that would deflect
  when the ribbon slides in. Flat rectangular pins do not communicate why
  insertion needs "zero force, only lock".

--- ANIMATION CLIPS ---
ANIM_B11_FLAP_OPEN       30 f. Flap rotates up ~110 deg on its hinge.
ANIM_B11_FLAP_CLOSE      30 f. Down and latched, with a tiny overshoot-settle
                         at the end that reads as a click.
ANIM_B10_INSERT          60 f. Ribbon slides in with the flap open, contacts
                         deflect visibly as it seats. Then flap closes.
ANIM_B10_PEEL            120 f. FIX 3'S CENTRAL BEAT. Solder at the landing
                         pads goes molten (drive MAT_SOLDER emissive), then the
                         ribbon lifts away from the pads with a gradual peel -
                         starting at one corner, progressing across. NOT a
                         rigid lift. The storyboard says "do not force it, do
                         not pull on the port end" and the animation must
                         demonstrate the gentle version.

--- STATES ---
  B11_STATE_LATCHED        correct - flap flush, ribbon marks aligned
  B11_STATE_UNLATCHED      flap fully up, ribbon loose
  B11_STATE_HALF_CLOSED    THE TEACHING STATE. ~15 deg proud, gap at the
                           hinge, marks misaligned. This causes the
                           "charges only at one angle" symptom.
  B11_STATE_SOLDER_CRACKED hairline crack in B11_SOLDER_L, socket very
                           slightly lifted off the board at that end
  B10_STATE_GOOD
  B10_STATE_PADS_WORN      gold plating rubbed through to base copper on 3-4
                           pads - dull brown patches. Fix 3's trigger.
  B10_STATE_TORN           film cracked at the high-flex point near the port -
                           "repeated bending near the charging port is a
                           common failure point", straight from your storyboard

--- SHOT LIST (2048 px, transparent PNG) ---
  1. Full route: port -> ribbon -> socket, three-quarter, in context on B02.
  2. Socket macro, flap OPEN, contact fingers visible.
  3. LATCHED vs HALF_CLOSED, matched camera. The single most important
     comparison image in the course.
  4. Layered cross-section for I07: flap / pins / FPC / stiffener / pads.
  5. GOOD pads vs WORN pads, matched camera.
  6. B05 rigid metal box beside B10 flat gold ribbon, matched scale, for the
     I27 SHAPE RULE card.

--- ACCEPTANCE CRITERIA ---
[ ] The flap hinges on its real axis with zero geometry intersection through
    the full 110 degrees.
[ ] HALF_CLOSED is identifiable by an untrained learner in under 3 seconds
    when shown beside LATCHED. Test this on an actual person before sign-off.
[ ] The peel animation survives a glTF export/import round trip with the
    deformation intact. Verify in a browser, not in Blender.
[ ] Contact fingers visibly deflect during ANIM_B10_INSERT.
[ ] Shown B05 and B10 side by side, a learner can say which one is "the metal
    box" and which is "the gold ribbon" without being told.
[ ] Copper traces are visible THROUGH the polyimide, not painted on it.
```

---

# PROMPT 4 of 5 — B40 Solder Joint State Set

```
BUILD: B40_JOINT - five solder joint condition states
REUSE: 5 scenes. Cheapest high-value asset in the entire course.
BUDGET: ~3k tris per state | 1K shared solder atlas | 1.5 days

--- THE TEACHING JOB ---
Read your own storyboard back: "a dry or cracked solder joint here is a very
common not-charging complaint" ... "cracked or dry pads are one of the most
common causes of charges-only-in-one-position" ... "a lot of what looks like a
dead Charger IC is actually just a cold joint underneath it" ... "inspect under
magnification for solder bridges".

Joint quality is not a detail of this course. It IS the course. Every one of
the six fixes is either caused by a bad joint or ends in making a good one.
And right now there is nothing in the asset list that lets a learner SEE the
difference. This is 1.5 days that unlocks the assessment layer.

--- THE ONE THING THAT MUST BE UNMISTAKABLE ---
Good solder is CONCAVE and SHINY. Bad solder is CONVEX and DULL. That single
shape-and-finish contrast is what a technician reads across a bench in half a
second, and it is entirely communicable in 3D. Get this contrast right and the
rest is detail.

--- BUILD ALL FIVE ON ONE COMMON BASE ---
One pad + one component lead, identical in all five states, so the camera never
moves between them. The learner compares the JOINT, not the scene.
Base: gold pad 1.0 x 0.6 mm on green solder mask, one chip-component lead
descending onto it.

  B40_STATE_GOOD
    Concave fillet sweeping smoothly from pad to lead. Wetting angle low,
    roughly 20-40 degrees - the solder clearly WANTED to stick.
    Bright, near-specular, MAT_SOLDER_GOOD rough 0.32.
    Fillet reaches full pad width. This is the target every fix aims at.

  B40_STATE_COLD
    Convex, ball-like, sitting ON the pad rather than flowing into it.
    Wetting angle over 90 degrees. Visible grain and a slightly wrinkled
    surface. MAT_SOLDER_COLD rough 0.68 with a fine noise bump.
    Dull enough that the difference from GOOD is obvious in a thumbnail.
    This is what Fix 4 exists to repair.

  B40_STATE_CRACKED
    Starts from GOOD geometry, then a hairline circumferential fracture
    between fillet and lead. Model the crack as real GEOMETRY, 0.02-0.03 mm
    wide, with darkened oxidised faces inside it. A painted crack line is
    invisible at anything but one exact angle.
    This is the "charges only at one angle" fault.

  B40_STATE_BRIDGED
    Two adjacent pads with solder spanning the gap between them. Shiny, so the
    learner understands a bridge is not a "bad-looking" joint - it is a
    well-formed joint in the wrong PLACE. That distinction matters and most
    training material misses it.
    This is what "inspect under magnification for solder bridges" is looking for.

  B40_STATE_DRY
    Starved. Insufficient solder, pad partly bare gold, no fillet, the lead
    barely making contact. Visible gap at one edge.
    This is what an unwicked or under-soldered repair looks like.

--- HOW IT GETS USED ---
- Fix 2 step 8, Fix 3 step 9, Fix 5 step 7: "inspect under magnification" -
  present the learner a joint, ask them to name its state. That is the
  assessment.
- Attach these as swappable children at the B02 pad footprints so the same
  five states appear in real board context, not just in isolation.
- I17-I22 step strips: the final panel of each fix should show the GOOD state
  as the target.

--- SHOT LIST ---
  1-5. Each state, identical camera, identical light, 2048 px. These five
       matched frames are the core assessment image set.
  6.   All five in one row, labelled, for a wall-chart reference card.
       Recommend this becomes a printed handout as well as a screen graphic.

--- ACCEPTANCE CRITERIA ---
[ ] Shown GOOD and COLD at 512 px thumbnail size, an untrained person picks
    the good one correctly. If they cannot, the contrast is too subtle -
    exaggerate it. Slight didactic exaggeration is CORRECT here.
[ ] The crack in CRACKED is visible from at least three camera angles.
[ ] All five share one identical base pad and lead - no camera or lighting
    drift between states.
[ ] BRIDGED reads as shiny-but-wrong, not as dirty.
[ ] Each state under 3k tris.
```

---

# PROMPT 5 of 5 — B28 Hot Air Rework Station

```
BUILD: B28_HOTAIR - hot air rework station, handpiece and nozzle
REUSE: 6 scenes. The primary instrument in five of the six fixes.
BUDGET: 10k tris LOD0 | 1K + display texture | 1 anim clip | 2.0 days

--- THE TEACHING JOB ---
Fixes 2, 3, 4, 5 and 6 all begin with hot air. The learner is not just
identifying this tool - they are learning to AIM it, at a stated temperature,
at a stated distance, without cooking the parts next door. Three specific
numbers from your storyboard have to be readable on this model:
380-450 C, and "hold the nozzle at least 5 mm away".

--- THE ONE THING THAT MUST BE UNMISTAKABLE ---
Where the heat goes. The nozzle must be an obviously separate, aimable object
with a clear axis, and the airflow must be visible enough that the learner
understands the cone of effect - and therefore why the Kapton tape shielding
in Fixes 4, 5 and 6 is necessary rather than fussy.

--- GEOMETRY ---
  B28_HOTAIR                  (empty, root)
   |- B28_BASE                station body, ~150 x 200 x 130 mm.
   |                          Vents, rubber feet, a mains cable stub.
   |- B28_DISPLAY             SEPARATE MATERIAL SLOT. Segmented digital
   |                          readout showing set temp and airflow. Leave the
   |                          digits to a runtime texture - the number changes
   |                          per procedure step. Do NOT bake "350" in.
   |- B28_KNOB_TEMP           rotatable, own origin on its axis
   |- B28_KNOB_AIR            rotatable
   |- B28_CRADLE              the rest the handpiece returns to. The safety
   |                          beat "always return it to the stand" needs a
   |                          visible home for it.
   |- B28_HANDPIECE           the gun. Origin at the grip point where a hand
   |                          would hold it, because the runtime moves this.
   |   |- B28_HOSE            flexible, curve-deformed, base to handpiece.
   |   |                      Bake to a skinned mesh for export.
   |   |- B28_NOZZLE          SEPARATE CHILD. Swappable: 3 mm, 5 mm, 8 mm.
   |   |- B28_ANCHOR_TIP      empty at the nozzle mouth, +Y down the airflow
   |                          axis. The runtime aims and range-checks off this.
   |- B28_ANCHOR_DISPLAY, _KNOBS, _CRADLE

--- MATERIALS ---
Station body: matte ESD-safe dark grey plastic, roughness 0.55, with the
slightly grainy texture real bench equipment has. Silkscreened labels.
Nozzle: heat-discoloured stainless - a straw-to-blue oxidation gradient toward
the tip. This is a small detail that tells the learner instantly that this end
is HOT, with no label needed. Worth the extra half hour.
Handpiece: two-tone, grip section slightly rougher.
Display: dark green-black LCD substrate, emissive digit material on top.

--- THE HEAT VISUALISATION (works with B46) ---
  - Emissive gradient inside the nozzle mouth, intensity driven by set
    temperature so 380 C and 450 C look different.
  - Airflow cone: NOT a particle simulation. Build a soft alpha-gradient cone
    mesh, ~15 degree spread, parented to B28_ANCHOR_TIP, with a scrolling
    noise texture for movement. Cheap, exports cleanly, reads perfectly.
  - Bake a heat-shimmer flipbook in Blender for the runtime to composite. Do
    not attempt real refraction in a WebGL scene on a low-end phone.
  - Distance guide: an optional 5 mm ring marker on the airflow cone that the
    runtime can toggle during the "safe distance" teaching beat. Small idea,
    disproportionate teaching value.

--- ANIMATION ---
ANIM_B28_LIFT_TO_STAND   45 f. Handpiece lifted from and returned to the
                         cradle. Plays at the start and end of every rework
                         procedure - it is the safety habit being drilled.

--- STATES ---
  B28_STATE_OFF      display dark, nozzle cool grey
  B28_STATE_HEATING  display lit, nozzle emissive ramping
  B28_STATE_READY    at temperature, full airflow, cone visible

--- SHOT LIST (2048 px, transparent PNG) ---
  1. Full station, three-quarter hero, for the I13 tool card.
  2. Handpiece alone, in the pose the learner will see it working.
  3. Nozzle macro with the heat-discoloured tip.
  4. Display close-up, blank digits, for the runtime to overlay.
  5. Nozzle at correct 5 mm standoff over a board, cone visible.
  6. Same, WRONG - nozzle too close, cone hitting a neighbouring part.
     Pair 5 and 6 as a teaching comparison.

--- ACCEPTANCE CRITERIA ---
[ ] The nozzle is independently aimable and its airflow axis is unambiguous
    from any camera angle.
[ ] No digits baked into the display texture.
[ ] The airflow cone communicates "this affects an area, not a point" without
    any accompanying text.
[ ] The heat-discoloured tip reads as hot to someone who has never used one.
[ ] Nozzle swaps between 3/5/8 mm cleanly with no gap at the collar.
[ ] Under 10k tris with the hose baked.
```

---

# Build order and dependencies

```
WEEK 1-2   B02 mainboard          (4.0 d)  blocks everything - start here
           B05 port assembly      (4.0 d)  parallel, different artist
WEEK 2-3   B11 ZIF socket         (4.0 d)  needs B02 footprints
           B10 FPC + rig          (3.0 d)  RIG SIGN-OFF GATE before any anim
WEEK 3     B28 hot air station    (2.0 d)  fully independent, any artist
           B40 joint states       (1.5 d)  needs B02 pad geometry
WEEK 4     Animation pass, glTF round-trip validation, shot list renders
```

**Two gates that will cost you a week each if you skip them:**

1. **The B10 rig gate.** Export the rigged ribbon to .glb and open it in a browser *before* animating the peel. If the deformation does not survive, you find out in 2 hours instead of after 3 days of animation work.
2. **The device gate.** Render B02 and B05 at 720p and view them on an actual sub-Rs-12,000 Android phone before signing off the material pass. Metal legibility and pin readability behave completely differently there than on a colour-calibrated monitor.

**Two things to decide before anyone opens Blender** (both are on the Risks sheet of the register):

- **Hands or tool-only.** These five prompts all assume tool-only — no hands modelled. Confirm that.
- **Molten solder method.** B40 and the peel animation both touch it. Baked shader + vertex animation, not fluid sim.
