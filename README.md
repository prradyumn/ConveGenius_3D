# ConveGenius — Mobile Charging Repair Simulator

Interactive three.js training simulation for the BC.1 / BC.2 / BC.3 Mobile
Charging Repair course. The deployable Vite application now lives at the
repository root, so Vercel can detect and build it without a custom Root
Directory setting.

```bash
npm ci
npm run dev        # http://localhost:5290   (dev server, HMR)
npm run build      # -> dist/
npm run preview    # http://localhost:4290   (serves the production build)
npm run optimize   # optional KTX2 texture pass (see below)
```

## Repository layout

```text
src/          application source
public/       runtime GLBs, component data, and Draco decoder
tools/        web asset optimization
authoring/    Blender sources, scripts, LODs, renders, textures, and reports
```

Only `src/`, `public/`, and the root build files are needed for deployment.
`authoring/` keeps the useful source assets in one place and is excluded from
Vercel uploads by `.vercelignore`.

## Deploying to Vercel

Import this repository with the project root set to the repository root. The
checked-in `vercel.json` explicitly selects Vite, runs `npm ci` followed by
`npm run build`, and serves `dist/`. No framework override or nested `web/`
Root Directory is required.

**Ports are pinned with `strictPort`, on purpose.** This machine already runs
other Vite projects on the default `5173` and `4173`. Without `strictPort`, Vite
prints the port you asked for, quietly binds a different one, and the *other*
project answers on the URL you open — which looks exactly like this app hanging
on "Loading…". It now fails loudly instead.

**Do not open `dist/index.html` from the filesystem.** `fetch()` is blocked on
`file://`, so `components.json` never arrives and the loader sits there. Use
`npm run preview`. The app now detects this case and says so on screen.

Runtime assets live in `public/assets/`. To refresh them from the canonical
authoring files:

```bash
cp authoring/glb/*_LOD0.glb public/assets/glb/
```

The labelled component manifest is maintained at
`public/assets/data/components.json`.

---

## What is built

| Area | State |
|---|---|
| Loader + Draco + scene + environment | done |
| `components.json` → picking → labels → closed-form zoom | done (the core loop) |
| All 6 animation clips, incl. reversible explode | done |
| State toggling: 5 joints, 3 latch states, damage variants, zone plates | done |
| Morph-target solder melt + runtime emissive glow | done |
| Procedure gating: Fix 3 and Fix 2, order-critical steps hard-fail | done |
| `InstancedMesh` collapse with instance-aware picking | done (opt-in toggle) |
| Assessment quiz with response timing | done |
| In-app contract checks against the loaded binary | done |
| KTX2 pass | script provided, **not yet applied** |
| Multimeter canvas readout, VO sync, language switcher | not started |

### Layout

```
src/core/config.js      all tuning constants, asset table, latch angles
src/core/scene.js       renderer, camera, lights, environment map
src/core/loader.js      GLTFLoader + DRACOLoader, teardown
src/core/registry.js    components.json <-> glTF nodes; the label API
src/core/picking.js     raycast -> nearest registered ancestor (instance-aware)
src/core/framing.js     closed-form zoom solve + adaptive depth range
src/core/labels.js      CSS2D callouts + SVG leader lines + occlusion
src/core/materials.js   highlighting; shared-datablock vs cloned
src/core/anim.js        mixer, morph melt, runtime-driven glow
src/core/states.js      visibility/transform state machine
src/core/instancing.js  via/passive/BGA collapse, keeps clickability
src/procedures/engine.js  step gating, nozzle aim/distance check
src/procedures/fixes.js   Fix 3 and Fix 2 as data
src/ui/                 state panel, quiz, contract checks
```

---

## Decisions worth knowing

**Camera near plane is adaptive, not constant.** The brief specifies
`near = 0.01`, and that is correct — the default `0.1` clips straight through a
9 mm connector. But pairing it with `far = 20000` is a depth ratio of 2,000,000,
which a 24-bit depth buffer cannot carry: the solder mask and board core z-fight
into visible stripes across B02. `updateDepthRange()` therefore derives near/far
each frame from the viewing distance and the scene's bounding sphere. Macro zoom
still works; the striping is gone.

**The frame rate is capped at 30 fps** and rendering stops when the page is
hidden (`TARGET_FPS` in `config.js`). Rendering flat out pinned the main thread
hard enough to make the UI unresponsive — on a sub-₹12,000 Android that is heat,
throttling and battery for a scene that is static most of the time.

**Highlight emissive is deliberately low (0.32 select / 0.14 hover).** At ~1.0 a
large part like `B05_SHELL` blows out completely and the metal read — the thing
that makes shape legible at this scale — disappears.

**The quiz never runs on mount.** It sets the scene to a random state, and
mounting happens during asset load, so auto-asking silently overrode the manifest
default (B40 opened on a random joint instead of `B40_STATE_GOOD`). It fires only
when the Assess tab is opened.

**Instancing is opt-in and picking-safe.** Collapsing the via/passive/BGA
families takes B02_MAINBOARD from **442 to 98 draw calls**. Every one of those
nodes is a registered component, so hits on an `InstancedMesh` resolve through
`instanceId` back to the source node and stay clickable and labellable.
Selection uses a proxy mesh, because you cannot set an emissive on one instance
of a shared material.

**Per-asset opening view.** `ASSETS[key].view` in `config.js`. A 120 mm board
framed from a generic three-quarter angle arrives almost edge-on and reads as a
green sliver. Framing preserves the learner's direction after that.

---

## Two places the shipped documentation is wrong

Both were found by measuring in the browser. The **Checks** tab re-runs these
against whatever binary is loaded, so they can be confirmed rather than trusted.

### 1. `ANIM_B10_PEEL` works. `authoring/out/GATE_CHECK.json` is wrong about it.

The shipped gate check records `max_travel_mm: 0.0`, `pass: false`, and an
overall `PARTIAL` verdict for this clip. The build brief disagrees and says it
survived export. **The brief is right.** Measured live: **26.9 mm** of peak
vertex travel, all 10 bones rotating with increasing magnitude toward the tip.

The reason a check can read zero: `B10_B11_IFC` has **21 skinned meshes** and
only the ribbon actually deforms — the socket bodies and contact fingers are
bound but static. Sample one mesh and you will probably pick a rigid one.
`measureClipTravel()` samples every skinned mesh across 12 points in the clip.

Do not rebuild the rig on the strength of that report.

### 2. `components.json` anchors are wrong for `B02_ASSEMBLY` only.

443 of its 500 entries name `B05_ANCHOR_B02`, and 18 name `B05_ANCHOR_B11`.
Those are the anchors for **USB-C pins B2 and B11**. The generator looks to have
built `"B05_ANCHOR_" + <first token of the node name>`, so every `B02_*` part got
`B05_ANCHOR_B02`.

This is worse than a missing reference, because the names *do* exist: nothing
errors, and 461 leader lines would silently converge on one point on the
connector's pin row. Measured offsets reach **113.94 mm on a 120 mm board**.

`B02_MAINBOARD` anchors correctly (`B02_ANCHOR_PMIC`, `B02_ANCHOR_IFC`, …), which
is what makes the assembly's pattern legible as a bug.

The runtime defends itself in `Registry._vetAnchorDistances()`: an anchor further
from a component's bounds than `max(2 × diagonal, 1.5 mm)` is rejected and the
centroid is used instead. **The real fix belongs in `components.json`** — the
centroid is correct but less artful than an authored callout point.

### Also worth noting

- `B05_STATE_BENT_PINS`, `B10_STATE_PADS_WORN` and `B10_STATE_TORN` are named in
  `components.json` `states` but are **not nodes in any binary**. They are
  logical groups; the real meshes are `B05_BENT_PIN_A05/06/07`,
  `B10_WORNPAD_04..08` and `B10_TEAR`. Mapped in `LOGICAL_GROUPS`
  (`core/states.js`).
- `B02_ASSEMBLY` places a handful of passives outside the board outline. Cosmetic,
  and an asset-side matter — not touched here.
- `MAT_POLYIMIDE_V2` appears in `authoring/out/GATE_CHECK.json` but the shipped binary
  has `MAT_POLYIMIDE`. The report is stale; the runtime reads the binary.

---

## Verified against the acceptance criteria

Measured in a real browser (Chromium), per asset, via the **Checks** tab:

| Criterion | Result |
|---|---|
| Every `components.json` node clickable, labels, zooms without clipping | **pass** — 39 / 44 / 49 / 442 / 35 / 500 entries bound, 0 unmatched, 0 unregistered; framing clears the near plane on all of them |
| All six clips play; explode reverses | **pass** |
| `ANIM_B10_PEEL` visibly deforms the ribbon | **pass** — 26.9 mm measured |
| `ANIM_B11_SOLDER_MELT` changes fillet shape, glow driven runtime-side | **pass** — 0.301 mm peak morph displacement |
| All five `B40_STATE_*` reachable, exactly one visible | **pass** |
| `B11_FLAP` reaches all three latch states | **pass** |
| Wrong-order actions in Fix 2 and Fix 3 **fail** with an explanation | **pass** — see below |
| Whole-course payload under 8 MB after KTX2 | **not yet** — 5.87 MB pre-KTX2, already under; run `npm run optimize` to bank the rest |

Fix 3 gating, as exercised:

| Attempt | Outcome |
|---|---|
| Apply heat before disconnecting the battery | rejected |
| Half-close the flap when asked to open it | rejected — "half open is not open" |
| Pry the part off cold | rejected — "never pry it off cold, that tears the pads" |
| Heat with a spudger (wrong tool) | rejected |
| Solder a **middle** pad first | rejected — explains the ribbon creeps out of alignment |
| Correct sequence | advances, and the run is scored with a fault breakdown |

The teaching criteria in section 10 of the brief (3-second recognition of
`HALF_CLOSED`, thumbnail-size good-vs-cold, port-vs-ribbon discrimination,
tracing the path with labels off) **must be tested on actual learners.** The quiz
records response time and flags correct-but-slow answers so that data exists, but
nothing here substitutes for the learner test.

---

## Next

1. Run `npm run optimize`, then wire `KTX2Loader` into `core/loader.js`. The
   script prints the reminder; textures will not decode without it.
2. Fix the `B02_ASSEMBLY` anchors in `components.json` and delete the runtime
   defence, or keep it as a guard.
3. Measure on a real sub-₹12,000 Android. Metal legibility and pin readability
   behave completely differently there than on a desktop monitor, and the
   `MAX_PIXEL_RATIO` / `TARGET_FPS` caps should be re-tuned against it.
4. Remaining fixes (1, 4, 5, 6), the multimeter `CanvasTexture` readout, the
   signal-flow DOM overlay, VO-driven playhead, language switcher, telemetry.
