# ConveGenius — Mobile Charging Repair Simulator · 3D Asset Package v5

**Everything for the three.js build.** Assets finished, textured, verified. 21 August 2026.

Start with **`docs/THREEJS_BUILD_PROMPT.md`** and the runtime manifest at
**`../public/assets/data/components.json`**.

---

## What's in here

```
glb/                                   LOD0 deliverables plus retained LOD1/LOD2 files
tex/                 15 files, 1.9 MB   source texture maps (already embedded in the glb)
scripts/             Blender generators, checks, and maintenance tools
out/                 Blender working files and generated reports
renders/             42 files,  57 MB   shot list, 1500–2400px transparent PNG
docs/                                   status docs, the original asset register, contact sheets
../public/assets/data/components.json   1,109 labelled components — the runtime's label API
docs/THREEJS_BUILD_PROMPT.md            the implementation brief
```

## The six assets

| File | Size | Nodes | Tris | Images | Skin | Morph | Anchors | Clips |
|---|---|---|---|---|---|---|---|---|
| `B05_PORT_LOD0.glb` | 448 KB | 69 | 6,968 | 4 | – | – | 30 | 1 |
| `B10_B11_IFC_LOD0.glb` | 915 KB | 64 | 11,944 | 7 | **1** | **2** | 7 | 4 |
| `B40_JOINT_LOD0.glb` | 1,201 KB | 49 | 6,548 | 7 | – | – | – | – |
| `B02_MAINBOARD_LOD0.glb` | 1,326 KB | 450 | 12,120 | 7 | – | – | 6 | – |
| `B28_HOTAIR_LOD0.glb` | 262 KB | 42 | 9,924 | 3 | – | – | 7 | 1 |
| `B02_ASSEMBLY_LOD0.glb` | 1,854 KB | 543 | 26,824 | 11 | – | 2 | 39 | 4 |

**5.87 MB total — 23.5% of the 25 MB course budget.** Every figure above was read out of the actual binaries, not assumed.

Run all six through **`gltf-transform`** or **`gltfpack`** for KTX2/Basis before shipping. Blender's exporter can't produce it, so textures are currently embedded PNG. That pass should roughly halve the total.

## Six animation clips

| Clip | Target | What it teaches |
|---|---|---|
| `ANIM_B05_EXPLODE` | 33 nodes | The port is an assembly, not a hole. Reversible. |
| `ANIM_B11_FLAP_OPEN` / `_CLOSE` | `B11_FLAP` | ZIF latch, with a click-like settle on close |
| `ANIM_B10_PEEL` | 10 bones | Fix 3's central beat — corner-first peel |
| `ANIM_B11_SOLDER_MELT` | morph weights | "Lift away once the solder liquifies" |
| `ANIM_B28_LIFT_TO_STAND` | handpiece | The safety habit being drilled |

## Rebuild anything

```
blender-launcher.exe --python authoring/scripts/run_all.py -- --cg-queue build_b05_port.py,build_b10_b11_ifc.py,build_b40_joints.py,build_b02_mainboard.py,build_b28_hotair.py,build_b02_assembly.py,texture_pass.py
```

`make_textures.py` regenerates the 15 maps. `gate_check.py` re-verifies any glb's skin and clips. Nothing was hand-modelled — the scripts are the source of truth, so every change is diffable and every rebuild is identical.

---

## Four things that will save you time

1. **Camera near plane.** Assets are at true millimetre scale: 1 world unit = 1 mm. Three.js's default `near = 0.1` clips straight through a 9 mm connector. Use `0.01`.
2. **Every state ships visible.** glTF has no per-node visibility and the exporter *drops* render-hidden objects. So all five `B40_STATE_*` joints, every damage variant and every zone plate are in the file and visible. **Hide all but the default on load** or the five solder joints render on top of each other.
3. **glTF carries no animated material properties.** The solder melt geometry is real (morph targets), but the *glow* is not in the file — drive emissive runtime-side alongside the clip. Same for the nozzle heat ramp.
4. **Materials are shared datablocks.** Changing `MAT_PIN_VBUS` lights all four VBUS pins at once — correct for signal-group teaching. Per-pin highlighting needs `material.clone()` first.

## Known imperfections — none block the build

- **No KTX2 compression** (see above). Do it on the web side.
- **B05's brushed steel reads slightly cross-hatched** — a directional streak map box-projected onto a curved shell. Cosmetic.
- **Contact pitch (0.50 mm) is spec-nominal, not datasheet-confirmed.** The opening dimensions (8.34 × 2.56 × 6.20 mm) *are* confirmed. Don't state the pitch as fact in learner-facing copy.
- **LODs: ship LOD0 only.** Measured saving was 9% for triple the file count, and B40's LODs came out *larger* than LOD0. `polish_lods.py` is included if you disagree.
- **B02 has 450 nodes off ~90 unique meshes.** Convert the via/passive/BGA-ball families to `InstancedMesh` — biggest single perf win available.

## Two decisions already made, for the record

- **Tool-only — no hands modelled.** Saved ~15–20 days and constant clipping problems; it's also what teardown videos do.
- **Molten solder is morph-target geometry, not a fluid sim.** A Blender fluid sim exports nothing at all.
