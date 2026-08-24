# Polish Pass — Done

All five polish items closed, plus the molten-solder effect decision resolved with a working implementation.

---

## 1. B05 dimensions — datasheet-verified ✅

Checked against the USB Type-C spec. The receptacle opening is **8.34 × 2.56 mm, 6.20 mm deep**.

- Width and height were already **exact**.
- **Depth was wrong** — my cavity was 4.90 mm. Corrected to 6.20 mm, shell to 7.10 mm, tongue and contact spans moved to match.
- Bonus: the deeper cavity genuinely improves the "small city of pins" read — there is more depth to look into.

Contact pitch stays at 0.50 mm, which is spec-nominal. Neither source I checked states it explicitly, so it is **not** datasheet-confirmed and is flagged as such in the build script's dimension note. Worth one look at a real handset receptacle datasheet if you want it nailed down.

## 2. B02 zone legibility — solved properly ✅

Tinted plates were only half a fix. `build_b02_assembly.py` now appends the **real B05 receptacle** (70 objects) and the **real B11 socket** (25 objects) into their board footprints, and generates a fresh flex at the **true 14.8 mm board gap**.

The standalone B10 keeps its 36 mm service loop for Fix 3 close-ups — a phone's flex really is longer than the straight-line distance, but dropping a 36 mm ribbon onto a 15 mm gap hangs it off the board edge.

Result: **port → flex → IFC socket is physically continuous and traceable with a finger**, which was B02's whole teaching job. `B02_ASSEMBLY_LOD0.glb` carries **39 anchors** (all 4 zone anchors + all 24 B05 pin anchors) and **4 animation clips**.

## 3. B10 contact fingers — now read as sprung ✅

Reprofiled to a pronounced arch with a contact crown, 16 path samples, thinner section (0.058 mm). They now visibly look like leaf springs that *would* deflect — which is what makes "zero insertion force, only lock" land.

## 4. Molten solder — decision made and implemented ✅

**The finding that settled it: glTF has no animated material properties.** Animating emission or roughness in Blender exports to *nothing*. What does export is morph targets, node TRS, and skinned deformation.

So the melt is **geometry**: a `MOLTEN` shape key that slumps the fillet (z × 0.42) and spreads it outward (y × 1.45), driven by `ANIM_B11_SOLDER_MELT`. The glow is left to the runtime as a one-line emissive lerp.

Getting this to actually ship took two failed attempts and one real discovery:

> `export_apply=True` does not merely apply modifiers per-object — **it disables shape-key export for the entire file.**

So B10/B11 now exports with `apply=False` and every bevel on it is destructive (baked into mesh data, no modifier left). Verified in the file:

```
B11_SOLDER_L  targets=1 weights=1
B11_SOLDER_R  targets=1 weights=1
ANIM_B11_SOLDER_MELT  2 channels     assert_morph -> PASS
```

## 5. LODs — generated, measured, and I recommend dropping them ⚠️

This is a negative result, and it's the honest answer:

| Tier | Total | % of 25 MB |
|---|---|---|
| LOD0 | 351.4 KB | 1.37% |
| LOD1 (40%) | 330.5 KB | 1.29% |
| LOD2 (15%) | 319.6 KB | 1.25% |

**A 9% saving for triple the file count.** Worse in detail:

- **B40 LOD1/LOD2 are *larger* than LOD0** (12.4 KB vs 10.4 KB). All 46 of its meshes are under 60 verts so nothing was decimated, and the triangulation change hurt Draco's compression.
- **B02 barely moved** (136 → 135 KB). Its cost is 433 node transforms, materials and JSON overhead, not vertex data.
- **B28 is the only real win** (57 → 41 KB, 28%) because it has genuinely dense revolved geometry.

**Recommendation: ship LOD0 only, plus B28's LOD1.** Revisit if any single asset passes ~500 KB. `polish_lods.py` is in the zip if you want to regenerate.

---

## Final verified GLB set

| File | Size | Tris | Morph | Anchors | Skin | Clips |
|---|---|---|---|---|---|---|
| B02_ASSEMBLY | 242.1 KB | 24,992 | 2 | **39** | – | 4 |
| B02_MAINBOARD | 133.3 KB | 10,284 | – | 6 | – | – |
| B10_B11_IFC | 97.2 KB | 11,252 | **2** | 7 | **1** | 4 |
| B05_PORT | 56.3 KB | 5,636 | – | 30 | – | 1 |
| B28_HOTAIR | 56.1 KB | 8,564 | – | 7 | – | 1 |
| B40_JOINT | 10.4 KB | 1,168 | – | – | – | – |

**595.5 KB for the whole set including the combined assembly — 2.33% of budget.**

Animation clips, all verified present in-file:
`ANIM_B05_EXPLODE` (33 ch) · `ANIM_B10_PEEL` (30 ch) · `ANIM_B11_FLAP_OPEN` · `ANIM_B11_FLAP_CLOSE` · `ANIM_B11_SOLDER_MELT` (2 ch) · `ANIM_B28_LIFT_TO_STAND`

---

## What's genuinely still open

- **Contact pitch** is spec-nominal, not datasheet-confirmed (see item 1).
- **B40 has no on-board variant.** The five joint states still live in isolation. Attaching them to B02's pad footprints is now easy — the assembly script shows the append pattern.
- **The in-build rig gate reports an implausible magnitude** (10,341 mm on a 40 mm asset). It correctly detects *that* deformation happened, but its number is junk. `gate_check.py`, run standalone, is the authoritative one — it reported 40.65 mm across 2,323 verts. Use that; ignore the in-build figure.
- **B02_ASSEMBLY is 39,084 evaluated tris** against no formal budget. Fine as a hero scene, but it should not be the always-loaded default.
