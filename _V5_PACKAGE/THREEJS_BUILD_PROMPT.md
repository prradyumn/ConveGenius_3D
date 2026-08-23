# Build Prompt — ConveGenius Mobile Charging Repair Simulator (three.js)

Hand this to whoever builds the runtime, human or AI. It is written to be usable verbatim.

---

## 0. What you are building

An interactive 3D teaching simulation for the **Mobile Charging Repair** course (modules BC.1 / BC.2 / BC.3), delivered in a browser with **three.js**. Learners are 17–25 year olds in Indian ITI / TVET programmes, many of whom have never opened a phone, on **sub-₹12,000 Android devices over 3G**. Every technical decision is judged against one question:

> Can a first-timer point at this on screen and then find the same thing on a real bench?

Three interaction pillars, in priority order:

1. **Click a component → it labels itself and the camera zooms to it.**
2. **Play a named animation clip** to demonstrate a procedure step.
3. **Swap a component's state** (good / cold / cracked / worn / half-closed) so the learner can be *assessed* on telling them apart.

The 3D assets are finished and shipped as glTF 2.0 binary (`.glb`). **Do not remodel anything.** Read the asset contract below — the node names, clip names, material names and anchor names ARE the API.

---

## 1. Asset contract

Six `.glb` files. Every name below was verified by parsing the actual binaries, not assumed.

| File | Size | Tris | Images | Skin | Morph | Anchors | Clips |
|---|---|---|---|---|---|---|---|
| `B05_PORT_LOD0.glb` | 437 KB | 5,636 | 4 | – | – | 30 | 1 |
| `B10_B11_IFC_LOD0.glb` | 729 KB | 11,252 | 6 | 1 | 2 | 7 | 4 |
| `B40_JOINT_LOD0.glb` | ~500 KB | ~5,900 | 5 | – | – | – | – |
| `B02_MAINBOARD_LOD0.glb` | 654 KB | 10,236 | 5 | – | – | 6 | – |
| `B28_HOTAIR_LOD0.glb` | 252 KB | 8,564 | 3 | – | – | 7 | 1 |
| `B02_ASSEMBLY_LOD0.glb` | 1,181 KB | 24,940 | 9 | – | 2 | 39 | 4 |

`components.json` ships alongside and maps every addressable node to a human label, a category, and its teaching note. **Drive the UI from that file — never hard-code a label in a component.**

### Animation clips

| Clip | Target | Frames | What it teaches |
|---|---|---|---|
| `ANIM_B05_EXPLODE` | 33 nodes (shell, housing, tongue, 24 pins, legs, tabs) | 1–90 | The port is an ASSEMBLY, not a hole. Reversible — play backwards to assemble. |
| `ANIM_B11_FLAP_OPEN` | `B11_FLAP` | 1–30 | ZIF latch lifting |
| `ANIM_B11_FLAP_CLOSE` | `B11_FLAP` | 1–30 | Closing + a small overshoot that reads as a click |
| `ANIM_B10_PEEL` | 10 bones of `B10_ARM` | 1–112 | **Fix 3's central beat.** Corner-first peel. "Do not force it, do not pull on the port end." |
| `ANIM_B11_SOLDER_MELT` | morph weights on `B11_SOLDER_L/R` | 1–45 | "Lift away once the solder liquifies — never pry it cold." |
| `ANIM_B28_LIFT_TO_STAND` | `B28_HANDPIECE` | 1–45 | Safety habit: the iron always returns to its stand |

### Runtime-toggleable states

Every state ships **visible** in the file, because glTF has no per-node visibility and the exporter drops render-hidden objects. **The runtime owns visibility.** On load, hide all but the default state.

- `B40_STATE_GOOD` / `_COLD` / `_CRACKED` / `_BRIDGED` / `_DRY` — five joint conditions, all at the same origin, one camera, one exposure. Show exactly one.
- `B05_STATE_BENT_PINS`, `B05_GASKET` (optional, water-resistant models only)
- `B10_STATE_PADS_WORN`, `B10_STATE_TORN`
- `B11_SOLDER_CRACK_L` (hidden unless demonstrating a cracked anchor)
- `B02_ZONE_PORT` / `_IFC` / `_PMIC` / `_BATTCONN` — tinted zone overlays

`B11` latch states are **transforms**, not separate meshes — set `B11_FLAP.rotation.y`:

| State | rotation.y | Note |
|---|---|---|
| `LATCHED` | `0` | correct |
| `HALF_CLOSED` | `15°` | **the teaching state.** Looks closed, is not. Causes "charges only at one angle". |
| `UNLATCHED` | `110°` | fully open |

### Material groups

Materials are **shared datablocks**. `MAT_PIN_GND` is one material on four pins.

- `MAT_PIN_GND` · `MAT_PIN_VBUS` · `MAT_PIN_CC` · `MAT_PIN_DATA` · `MAT_PIN_SBU` · `MAT_PIN_SS`
- `MAT_TRACE_HIGHLIGHT` — the five charging-path traces on B02, on their own slot so you can light the path in sequence

**Gotcha:** because they're shared, changing `MAT_PIN_VBUS.emissive` lights *all four* VBUS pins at once. That is exactly what you want for signal-group teaching. But **per-pin** highlighting requires `material.clone()` first, or you will light the whole group by accident.

### The reversibility fact worth building a lesson on

`B05_PIN_A01` and `B05_PIN_B12` occupy the **same X position** — Row B is mirrored, which is *why* USB-C is reversible. Highlight Row A, then flip and highlight Row B: the learner sees GND land on GND.

---

## 2. Scene setup — get this right first

The assets are modelled at **true real-world millimetre scale**. One three.js world unit = 1 mm. The USB-C port is ~9 units across; the mainboard is ~120 units.

```js
// Default near = 0.1 CLIPS STRAIGHT THROUGH a 9mm connector at macro zoom.
// This is the single most common setup mistake at this scale — it cost me
// hours on the Blender side too.
const camera = new THREE.PerspectiveCamera(45, w / h, 0.01, 20000);
```

- `renderer.outputColorSpace = THREE.SRGBColorSpace`
- `renderer.toneMapping = THREE.ACESFilmicToneMapping`, `toneMappingExposure ≈ 1.0`
- **Metals need something to reflect.** In a black environment a correct steel shader renders as a black blob. Ship a small studio-gradient environment map (or a `RoomEnvironment` from `PMREMGenerator`) — this matters more than any material tweak.
- Background: dark neutral `#0E1420` → `#16213A` to match the existing ConveGenius sim.
- Lights: one large key + fill + rim. The soft reflection running along a metal edge is what makes shape readable.

---

## 3. Click-to-select

```js
const raycaster = new THREE.Raycaster();
// pointerdown → normalised device coords → intersectObjects(root.children, true)
// walk up parent chain until you hit a node present in components.json
```

Rules:

- Ignore anchors (`*_ANCHOR_*`) and any node whose name starts with `CG_`.
- Resolve to the nearest **registered** ancestor, so clicking `B05_SHELL_TAB_L` can resolve to `B05_SHELL` if you've grouped tabs under the shell.
- On hover: outline + label tooltip. Use `OutlinePass`, or a cheaper emissive bump on a cloned material — on a low-end phone prefer the clone.
- On click: select → show the label card → **zoom to it** (next section).
- Provide a persistent "back / show whole part" control. Learners get lost after two zooms.

---

## 4. Zoom-to-component — use the closed-form solve

Do **not** iterate `camera.position.lerp()` until it looks right, and do not solve off a bounding *sphere* — a sphere massively over-estimates for flat wide parts like a connector or a board, and you will end up framed far too loose. I hit exactly this and had to replace it.

Solve it analytically. For a camera at `C = target + d·dist` looking along `-d`, for every bounding-box corner `P`:

```
a = (P − target) · d          // depth along the view axis
u = |(P − target) · right|    // lateral offset, independent of dist
v = |(P − target) · up|
```

Fitting requires `|u| ≤ tan(fovH/2)·depth` and `|v| ≤ tan(fovV/2)·depth`, where `depth = dist − a`. So:

```
dist = max over corners of  max( a + u/tanH , a + v/tanV )   ×  margin
```

```js
function frameObject(camera, object, controls, margin = 1.15) {
  const box = new THREE.Box3().setFromObject(object);
  const target = box.getCenter(new THREE.Vector3());
  const corners = [];
  for (const x of [box.min.x, box.max.x])
    for (const y of [box.min.y, box.max.y])
      for (const z of [box.min.z, box.max.z])
        corners.push(new THREE.Vector3(x, y, z));

  const d = camera.position.clone().sub(target);
  if (d.lengthSq() < 1e-9) d.set(0, 0.4, 1);
  d.normalize();

  const tanV = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
  const tanH = tanV * camera.aspect;

  const up = new THREE.Vector3(0, 1, 0);
  const right = new THREE.Vector3().crossVectors(d, up).normalize();
  if (right.lengthSq() < 1e-9) right.set(1, 0, 0);
  const camUp = new THREE.Vector3().crossVectors(right, d).normalize();

  let dist = 0;
  for (const P of corners) {
    const w = P.clone().sub(target);
    const a = w.dot(d);
    dist = Math.max(dist,
      a + Math.abs(w.dot(right)) / tanH,
      a + Math.abs(w.dot(camUp))  / tanV);
  }
  dist *= margin;

  // animate, do not snap — a hard cut loses the learner's spatial context
  return { position: target.clone().add(d.multiplyScalar(dist)), target };
}
```

Tween position and `controls.target` together over ~600 ms with an ease-out. Clamp `controls.minDistance` so a learner cannot push the near plane through the part.

**Margins that work:** `1.15` for a single component, `1.06` for a whole-asset overview, `1.35` when you need surrounding context (e.g. a pad on a board).

---

## 5. Labels and callouts

Every asset ships **anchor nodes** — empties positioned where a leader line should attach. They arrive as `THREE.Object3D` with no geometry.

```js
const anchor = root.getObjectByName('B05_ANCHOR_A05'); // CC1 pin
```

- 30 anchors on B05, including **one per pin** (`B05_ANCHOR_A01`…`B12`)
- 7 on B10/B11 (`B11_ANCHOR_FLAP`, `B11_ANCHOR_PINS`, `B11_ANCHOR_SOLDER_L/R`, `B10_ANCHOR_PADS`, `_STIFFENER`, `_FLEXPOINT`)
- 7 on B28 (`B28_ANCHOR_TIP` is the airflow axis origin — use it for aim and range checks)
- 4 zone anchors on B02, 39 total on the assembly

Render labels as **CSS2DRenderer / CSS3DRenderer overlays**, not 3D text. Sprite text is illegible at 720p on a 5-inch screen, and HTML labels give you free multilingual text, screen-reader access and reflow. Project the anchor to screen space each frame, draw an SVG leader line to the label box, and hide the label when the anchor is occluded or off-screen.

**Label text and teaching notes come from `components.json`.** Do not write them into components.

---

## 6. Animation control

```js
const mixer = new THREE.AnimationMixer(root);
const clips = {};
gltf.animations.forEach(c => clips[c.name] = mixer.clipAction(c));

// one-shot, hold the last frame
const a = clips['ANIM_B11_FLAP_OPEN'];
a.setLoop(THREE.LoopOnce); a.clampWhenFinished = true; a.reset().play();
```

- `ANIM_B05_EXPLODE` is **reversible** — set `timeScale = -1` and start from the end to assemble.
- `ANIM_B10_PEEL` drives a **skinned armature** (`B10_ARM`, 10 bones). It was verified through a real glTF round trip: 40.65 mm of vertex travel survived export. It will play; do not rebuild it.
- `ANIM_B11_SOLDER_MELT` drives **morph target weights**, not transforms:

```js
const solder = root.getObjectByName('B11_SOLDER_L');
solder.morphTargetInfluences[0] = 0..1;  // 0 = solid fillet, 1 = molten
```

**Important:** glTF has **no animated material properties**. The melt geometry is real, but the *glow* is not in the file and must be a runtime emissive lerp:

```js
// drive alongside the morph weight
mat.emissive.setHex(0xff6a1e);
mat.emissiveIntensity = THREE.MathUtils.lerp(0, 2.5, weight);
```

Same applies to the `B28_NOZZLE_GLOW` heat-up ramp.

---

## 7. Procedure gating — the core mechanic of BC.3

This is what makes the simulation an assessment rather than a video, and it deserves real engineering time.

Several BC.3 steps are **order-critical** and the wrong order must *fail*, not silently pass:

- Fix 2: solder the **shield/ground tabs first**, then the smaller signal pins
- Fix 3: solder **one corner pad first** to hold the ribbon, then the rest
- Fixes 2/3/5/6: **disconnect the battery FIRST**, before any heat

Model each fix as an explicit state machine: an ordered step list, a required tool per step, a required target node per step, and a validator. On a wrong action, show *why* it is wrong in the voiceover's own language ("never pry it off cold — that tears the pads"), then let them retry.

The tool set is real geometry: `B28_HANDPIECE` is aimable and `B28_ANCHOR_TIP` gives you the airflow axis, so "is the nozzle within 5 mm of the target and pointing at it?" is a genuine, checkable condition. `B28_STANDOFF_5MM` is a ring marker you can toggle on to teach the distance.

---

## 8. Things that are NOT in the assets and must be built in the runtime

| Need | Why it isn't in the glb | Build as |
|---|---|---|
| Multimeter / power-meter digits | `B28_DISPLAY` is deliberately blank; the number must respond to *where* the probe is placed | `CanvasTexture` on the display material, redrawn on change |
| Solder / nozzle glow | glTF has no animated material properties | emissive lerp driven alongside the clip |
| Magnification mode | "inspect under magnification" recurs in 5 of 6 fixes; it's a camera state, not a model | narrow FOV + tighter clamp + optional vignette |
| Zone highlighting | plates ship but are inert | toggle `B02_ZONE_*` visibility + emissive pulse |
| Signal-flow overlays (VBUS / GND / CC / D± / SBU) | these are **invisible electrical paths** with no geometry — modelling them would have cost weeks and taught less | 2D SVG/DOM overlay on top of the canvas, plus `MAT_TRACE_HIGHLIGHT` for the board traces |
| Language switcher + VO sync | — | VO timing should **drive** the clip playhead, not run alongside it |

---

## 9. Performance rules for the target device

- **Convert instanced families to `InstancedMesh`.** B02 has 429 nodes off only 84 unique meshes — 167 vias, 133 passives, 49 BGA balls. `GLTFLoader` creates 429 separate `Mesh` objects sharing geometry, which is 429 draw calls. Merging the via/passive/ball families is the single biggest win available.
- **Textures are embedded PNG. There is no KTX2/Basis** — Blender's exporter cannot produce it. Run every `.glb` through `gltf-transform` or `gltfpack` to get KTX2 + resize. This will cut the 3.7 MB total substantially and is the right place to do it.
- **Ship LOD0 only** (plus B28's LOD1 if you want it). LOD1/LOD2 were generated and measured: only a **9%** total saving for triple the file count, and B40's LODs came out *larger* than LOD0 because its meshes are tiny and re-triangulation hurt Draco. Not worth the pipeline complexity here.
- Draco is already applied — include `DRACOLoader` and point it at the decoder.
- Cap `devicePixelRatio` at ~1.5. Prefer a lower resolution over dropped frames.
- Shadows: one directional shadow map at most, or none. Contact shadows via a baked blob are cheaper and read fine.
- Test on a real sub-₹12,000 Android before signing off. Metal legibility and pin readability behave completely differently there than on a desktop monitor.

---

## 10. Acceptance criteria

Functional:

- [ ] Every node in `components.json` is clickable, labels correctly, and zooms without clipping.
- [ ] All six clips play, and `ANIM_B05_EXPLODE` reverses cleanly.
- [ ] `ANIM_B10_PEEL` visibly deforms the ribbon in the browser (it survived the export gate — if it looks rigid, the bug is in your mixer setup, not the asset).
- [ ] `ANIM_B11_SOLDER_MELT` changes the fillet **shape**, with the glow lerped in runtime-side.
- [ ] All five `B40_STATE_*` joints are reachable and only one is visible at a time.
- [ ] `B11_FLAP` reaches all three latch states.
- [ ] Wrong-order actions in Fix 2 and Fix 3 **fail** with an explanation.
- [ ] Whole-course asset payload under 8 MB after KTX2.

Teaching (test these on actual learners, not on yourselves):

- [ ] Shown `LATCHED` and `HALF_CLOSED` side by side, an untrained learner picks the faulty one in **under 3 seconds**.
- [ ] Shown `B40_STATE_GOOD` and `_COLD` at thumbnail size, they pick the good joint correctly.
- [ ] Shown B05 and B10 together, they can say which is "the rigid metal box" and which is "the flat gold ribbon" — **this distinction is the commonest error in BC.3**, and Fix 2 vs Fix 3 depends on it.
- [ ] After the B02 assembly scene, they can trace port → flex → IFC socket with a finger, labels off.

---

## 11. Gotchas found while producing the assets — these will bite you too

1. **Camera near plane.** Default `0.1` clips through a 9 mm part. Use `0.01`.
2. **Bounding-sphere framing over-estimates badly** for flat wide parts. Use the closed-form solve in section 4.
3. **Metals need an environment map** or they render black regardless of how good the material is.
4. **Shared materials mean group highlighting is free but per-item highlighting needs `.clone()`.**
5. **glTF has no per-node visibility.** Every state ships visible; the runtime must hide the ones it doesn't want on load. If you forget, all five solder joints render on top of each other.
6. **glTF has no animated material properties.** Any glow, colour change or roughness change over time is yours to drive.
7. **Row B is mirrored, not offset.** `B05_PIN_A01` and `B05_PIN_B12` share an X. Don't "fix" it.
8. `neutral_bone` in `B10_B11_IFC` is an exporter artefact, not a real bone. Ignore it.
9. **Contact pitch (0.50 mm) is spec-nominal, not datasheet-confirmed.** The opening dimensions (8.34 × 2.56 × 6.20 mm) *are* confirmed. Don't quote the pitch as fact in learner-facing copy.
10. **B02_ASSEMBLY's flex is 14.8 mm** — regenerated at the true board gap. The standalone B10 keeps a 36 mm service loop for Fix 3 close-ups. They are deliberately different; don't reconcile them.

---

## 12. Suggested build order

1. Loader + scene + correct near plane + environment map. Render `B05_PORT` and confirm it looks like the reference stills.
2. `components.json` → raycast picking → label overlay → closed-form zoom. **This is the core loop; get it right before anything else.**
3. Animation mixer + a clip playback panel for testing all six.
4. State toggling, starting with `B40` (five joints) and `B11_FLAP` (three latch states) — the two highest-value assessment mechanics.
5. Morph target melt + runtime emissive.
6. Step gating for one fix end-to-end (recommend **Fix 3**, since it exercises the rig, the flap states, the melt and the pad-wear variants together).
7. `InstancedMesh` conversion and the KTX2 pass, then measure on a real target device.
8. Remaining fixes, multimeter canvas readout, language switcher, telemetry.
