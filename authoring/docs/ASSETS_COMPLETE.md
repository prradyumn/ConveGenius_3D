# All 5 Assets Complete — three.js Ready

**Built:** 21 Aug 2026, headed Blender 5.2.0 LTS on your machine, fully script-driven
**On your PC:** `C:\Users\HP\ConveGenius_3D\` — `scripts\` · `out\` (.blend + JSON reports) · `renders\` (32 stills) · `glb\`

```
blender-launcher.exe --python C:\Users\HP\ConveGenius_3D\scripts\run_all.py -- --cg-queue build_b05_port.py,build_b10_b11_ifc.py,build_b40_joints.py,build_b02_mainboard.py,build_b28_hotair.py
```

---

## Verified GLB contents — parsed from the actual files, not assumed

| Asset | Size | Tris | Nodes | Meshes | Mats | Skin | Anchors | Animation clips |
|---|---|---|---|---|---|---|---|---|
| B05 USB-C receptacle | 56.3 KB | 5,636 | 65 | 34 | 11 | – | **30** | `ANIM_B05_EXPLODE` (33 ch) |
| B10+B11 IFC assembly | 89.5 KB | 9,524 | 57 | 37 | 8 | **1** | 7 | `ANIM_B10_PEEL` (30 ch)<br>`ANIM_B11_FLAP_OPEN`<br>`ANIM_B11_FLAP_CLOSE` |
| B40 Solder joint states | 10.4 KB | 1,168 | 8 | 8 | 5 | – | – | state-swap, no clips needed |
| B02 Mainboard | 133.3 KB | 10,284 | 433 | 84 | 10 | – | 6 | state-swap + 4 zone plates |
| B28 Hot air station | 56.1 KB | 8,564 | 39 | 30 | 9 | – | 7 | `ANIM_B28_LIFT_TO_STAND` |

### **345.7 KB total — 1.35% of your 25 MB budget.** 35,176 triangles. 5 clips. 50 anchors.

Size is a non-issue for these five. Parametric hard-surface geometry plus Draco compresses extremely hard, and B02 instances 433 nodes off just 84 unique meshes. Your budget pressure will come from textures later, not meshes.

---

## THE RIG GATE PASSED — the one real technical risk is cleared

This was the thing that could have cost three days. Blender cloth and sim caches do **not** survive a glTF round trip, so the Fix 3 ribbon peel had to be a baked bone chain — and that had to be proven, not assumed.

`gate_check.py` opens the GLB the way three.js will see it, with nothing from the source .blend, and measures actual vertex travel:

```
skin_binding      max travel 40.65 mm   2323 verts sampled   PASS
ANIM_B10_PEEL     30 bone channels, all pose.bones[...] paths PASS (9.86 mm)
ANIM_B11_FLAP_*   4 fcurves, slot OBB11_FLAP, targets the flap PASS
```

The gate is in the delivered scripts. Run it against any future GLB.

---

## What each asset gives the runtime

**B05 — USB-C receptacle.** Correct obround (stadium) cross-section. 24 individually named contacts, 12 per row, Row B mirrored so `B05_PIN_A01` and `B05_PIN_B12` share an X position — the reversibility lesson is in the geometry, not a caption. Six pin-group material slots (GND / VBUS / CC / D± / SBU / SS) so a whole signal group lights in one call. **30 anchors, including one per pin**, for callout leader lines. One reversible explode clip.

**B10+B11 — IFC assembly.** The highest-teaching-value asset. Four states: `LATCHED`, `UNLATCHED`, `HALF_CLOSED`, `SOLDER_CRACKED`. **HALF_CLOSED is the one that matters** — ~15° proud with a visible hinge gap, which is your "charges only if you hold the cable at just the right angle" fault. Verified readable in under 2 seconds beside LATCHED. Socket body is a real shell so the 12 sprung gold fingers are visible through the mouth. Anchoring solder fillets are separate objects because cracked anchors are a named fault.

**B40 — Solder joint states.** Five states built as **real meniscus geometry**, not a roughness swap: GOOD uses a concave ellipse centred *outside* the solder so the surface hollows inward; COLD uses a convex ellipse centred *in the corner* so it balls up with bare gold pad showing beyond. All five share one pad, one camera, one exposure — coverage measured identical at 21.1%, so the learner compares the joint, not the scene.

**B02 — Mainboard.** Irregular outline with battery notch, laminated edge, ~200 plated vias and 150 passives instanced off shared meshes, 3 shield cans (PMIC removable for Fix 4/5), silkscreen as real geometry, 7×7 BGA field, and pad footprints at all four zones that survive with the part removed — so the bare-pad vs cleaned-pad pair for Fix 2 step 5 works. Four `B02_ZONE_*` plates ship visible for the runtime to toggle, plus `B02_ANCHOR_PORT/IFC/PMIC/BATTCONN`.

**B28 — Hot air station.** Blank display — **no digits baked**, the runtime draws temp/airflow. Three swappable nozzles (3/5/8 mm), heat-discoloured straw-to-blue tip that reads as HOT without a label, gradient-alpha airflow cone parented to `B28_ANCHOR_TIP`, and a toggleable `B28_STANDOFF_5MM` guide ring for the safe-distance beat.

---

## Bugs found and fixed along the way

Each of these was silently wrong and would have surfaced during integration:

1. **33 fragmented clips.** Blender's default `export_animation_mode='ACTIONS'` writes one clip *per object* — B05 exported as 33 separate clips. Fixed with NLA tracks: one track name → one clip.
2. **Every empty silently dropped.** Selecting only MESH objects killed B28's animation (it lives on the handpiece empty) and **all 50 anchor nodes**. Fixed by walking the parent chain and exporting anchors on purpose.
3. **Coplanar z-fighting.** B02's solder mask and FR4 core sat at identical Z, mottling the whole board tan/green.
4. **Black renders.** At mm unit scale Blender's light falloff still treats units as metres. Added auto-exposure that renders small, measures luminance, and corrects in stops.
5. **Camera framing.** Solved off the bounding *sphere* (over-estimates badly for flat wide parts), then the iterative fix read `matrix_world`, which Blender caches until a depsgraph update, so it diverged. Now closed-form.
6. **Metals rendering as black blobs** — nothing in the world to reflect. Added a gradient studio world and camera-invisible reflector cards.
7. **NLA tracks destroyed.** `animation_data_clear()` wipes tracks too, so each new clip erased the previous one.
8. **Blender 5.x API changes** — `action.fcurves` replaced by slotted actions; slotted actions need the *slot* assigned or they evaluate to nothing; `--python` scripts run in a restricted context with no `active_object` that the glTF exporter reads unconditionally; collections reject stepped slices (`vertices[::4]`).

---

## Known remaining defects — honest list

- **B05 dimensions are USB-C spec nominal, not datasheet-verified.** Proportion accuracy matters more here than on any other asset because learners will hold the real part in tweezers and compare. Worth an hour with a real receptacle datasheet.
- **B02 zone legibility is still the weak point.** The four zone plates now ship and toggle, but on the board render they read faintly. It gets properly solved by parenting B05 into `B02_ZONE_PORT` and B11 into `B02_ZONE_IFC` — a scene-assembly step, and both assets now exist for it.
- **B10 contact fingers don't read as *sprung*.** The curve is modelled but at this scale it doesn't communicate "zero insertion force, only lock".
- **No LOD1/LOD2 generated yet.** Everything is LOD0. Given the total is 345 KB, this is not urgent, but bench-wide shots will want the 40% tier.
- **B40 has no assembled-on-board variant.** The five states live in isolation; attaching them to the B02 pad footprints would let the same states appear in real board context.

## Two decisions still open

- **Tool-only, no hands.** Everything assumes this. Cheap now, costly to reverse.
- **Molten solder method.** B40's geometry is done, but the *melt* in Fixes 2/3/6 still needs a call: baked vertex animation + animated shader, or a pre-rendered video for that one beat. A Blender fluid sim will not export — the same trap the rig gate exists to catch.
