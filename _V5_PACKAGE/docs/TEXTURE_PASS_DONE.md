# Texture Pass Done — Assets Ready for three.js

The blocker is cleared. Every GLB now ships real UVs and real image maps.

| Asset | Size | Images | Tris | Morph | Skin | Anchors | Clips |
|---|---|---|---|---|---|---|---|
| B05_PORT | 437 KB | 4 | 5,636 | – | – | 30 | 1 |
| B10_B11_IFC | 729 KB | 6 | 11,252 | **2** | **1** | 7 | 4 |
| B40_JOINT | 495 KB | 5 | 1,168 | – | – | – | – |
| B02_MAINBOARD | 654 KB | 5 | 10,236 | – | – | 6 | – |
| B28_HOTAIR | 252 KB | 3 | 8,564 | – | – | 7 | 1 |
| B02_ASSEMBLY | 1,181 KB | 9 | 24,940 | 2 | – | 39 | 4 |

**3,748 KB total — 14.6% of your 25 MB budget.** Up from 595 KB, which is the honest price of shipping the material detail. Every file verified for `TEXCOORD_0`, images, clips, morph targets, skin and anchors by parsing the actual binaries.

---

## Why baking was needed at all

Procedural Blender shaders — noise, wave, gradient nodes — **do not export to glTF**. Everything I'd built that way existed only in the Blender renders. Worse, a *linked* node into Base Color or Roughness makes the exporter omit the scalar **factor** too, so glTF fell back to its own defaults. Two visible consequences:

- The flex ribbon shipped **white** (no baseColorFactor at all)
- The steel shell shipped at **roughness 1.0** — flat matte plastic, not brushed steel

## How I did it — and why not Blender's bake

Blender's bake operator is per-object: 35 objects would mean 35 images per asset, plus Cycles setup, operator context wrangling, and it needs UVs to already exist. Instead I generated **15 tileable maps directly with numpy inside Blender** (`make_textures.py`) and gave every mesh analytic UVs. Fewer images, exact control, fully reproducible.

No mesh had UVs at all — everything was built in bmesh. Three UV modes, no unwrap operator needed:

- **box** — dominant-axis planar projection at a fixed mm scale. Correct for tileable noise.
- **ribbon** — u across the flex *width*, v along its *length*, so the 12 trace stripes land 12-across however the ribbon curves.
- **nozzle** — v runs tip-to-collar exactly once, for the heat gradient.

All of it lives in one centralised `texture_pass.py` keyed by material name, so no build script needed editing.

## The three teaching-critical maps, restored

- **12 FPC copper trace stripes** — the ribbon reads as a real flex circuit again
- **Nozzle heat discolouration** — steel → straw → violet → blue, which is the "this end is HOT" cue with no label
- **Cold-solder grain** — GOOD vs COLD is a shape *and* surface contrast again, not just roughness 0.26 vs 0.70

## Four bugs found and fixed during the pass

1. **Reflector cards were shipping in every single GLB.** They're meshes with `visible_camera=False`; Blender hides them from renders but glTF has no equivalent flag. Two large emissive planes were in **all six** files and would have appeared as glowing rectangles over every model in three.js. Invisible in Blender, glaring in the browser. Now guarded inside `export_glb` itself so it cannot recur.
2. **UV seams from normal maps.** Box-projecting a *directional* streak map onto a rounded profile flips the dominant axis face-to-face, producing hard zigzag seams — very visible on the B28 body. The lesson: **roughness maps tolerate box-projection seams, normal maps do not.** Normals now ship only where UVs are clean — the ribbon's planar map, the small flat solder joints, and the PCB at 0.28 strength.
3. **One texel scale cannot serve a 3.4 mm solder coupon and a 120 mm board.** Added per-asset `TEXEL_SCALE` (B40 ×0.15, B05 ×0.55, B10 ×0.75).
4. **B02_ASSEMBLY lost all its bevels** (24,940 → 11,548 tris) because I'd set `apply=False` there for morph targets. The melt belongs in B10/B11 where that close-up happens, so the assembly is back to `apply=True` and its bevels are restored.

Also tidied: the `_V2` material names from my iteration are gone. Material names are the runtime API surface, so `MAT_POLYIMIDE` not `MAT_POLYIMIDE_V2`.

---

## Verdict: yes, this can go to animation and simulation

Everything structural and visual is now in the files and verified:

- geometry, correct dimensions, six named animation clips
- one skinned rig that passed a real glTF round-trip (40.65 mm vertex travel)
- morph targets driving the solder melt
- 89 anchor nodes for callout attachment
- textures with UVs on every asset
- no rig-object leakage, no missing factors
- 14.6% of budget

## Remaining known imperfections — none are blockers

- **B05's brushed steel reads slightly cross-hatched**, because a directional streak map box-projected onto a curved shell crosshatches. A non-directional fine-grain variant would be cleaner. Cosmetic.
- **Contact pitch is spec-nominal** (0.50 mm), not datasheet-confirmed. Opening dimensions *are* confirmed.
- **No KTX2/Basis compression.** Blender's exporter can't do it natively; textures are embedded PNG. Running the GLBs through `gltf-transform` or `gltfpack` would cut the 3.7 MB substantially — worth doing on the web side, not here.
- **LODs: recommend shipping LOD0 only** (plus B28's LOD1). Measured saving was 9% for triple the file count, and B40's LODs came out *larger* than LOD0.
- **B40 has no on-board variant** — the five joint states still live in isolation. The assembly script shows the append pattern if you want them in board context.
