import * as THREE from 'three';
import { solveFraming } from '../core/framing.js';
import { CAMERA_NEAR } from '../core/config.js';

/**
 * Acceptance checks, run against the LOADED BINARY rather than the docs.
 *
 * This exists because the shipped reports and the build brief disagree in
 * places - the asset gate check recorded ANIM_B10_PEEL at 0.0 mm of travel and
 * a PARTIAL verdict, while the brief states it survived the export. So the
 * runtime measures it itself.
 */
export function runContractChecks(app) {
  const lines = [];
  const pass = (m) => lines.push(`<span class="pass">PASS</span>  ${esc(m)}`);
  const fail = (m) => lines.push(`<span class="fail">FAIL</span>  ${esc(m)}`);
  const warn = (m) => lines.push(`<span class="warn">WARN</span>  ${esc(m)}`);
  const note = (m) => lines.push(`      ${esc(m)}`);

  if (!app.root) return 'No asset loaded.';

  lines.push(`asset: ${app.assetKey}`);
  lines.push('');

  // --- 1. Every components.json entry is bound, clickable and framable ---
  const diag = app.registry.diagnostics();
  if (diag.unmatchedSpec === 0) {
    pass(`all ${diag.bound} components.json entries bound to a node`);
  } else {
    fail(`${diag.unmatchedSpec} of ${diag.specEntries} components.json entries have no node here`);
    note('first few: ' + diag.unmatchedSpecNames.join(', '));
  }

  if (diag.missingAnchors.length) {
    warn(`${diag.missingAnchors.length} anchor name(s) referenced by components.json are absent from this binary`);
    note(diag.missingAnchors.join(', '));
    note('labels fall back to the node centroid, so nothing is lost visually');
  } else {
    pass('every anchor referenced by components.json exists');
  }

  if (diag.suspectAnchors) {
    warn(`${diag.suspectAnchors} component(s) name an anchor that is nowhere near them - centroid used instead`);
    for (const g of diag.suspectAnchorGroups.slice(0, 4)) {
      note(`${g.anchor} is claimed by ${g.count} component(s), up to ${g.maxDistance} mm away`);
    }
    note('these anchor names EXIST, so nothing errors - the labels would just all');
    note('converge on one wrong point. Looks like components.json was generated as');
    note('"B05_ANCHOR_" + the node name prefix, so every B02_* part got B05_ANCHOR_B02.');
    note('B02_MAINBOARD anchors correctly to B02_ANCHOR_*, so the fix belongs in the manifest.');
  } else {
    pass('every authored anchor sits on or near the component it labels');
  }

  if (diag.unregisteredMeshes) {
    warn(`${diag.unregisteredMeshes} renderable node(s) have no components.json entry (not clickable)`);
    note('first few: ' + diag.unregisteredMeshNames.join(', '));
  } else {
    pass('no unregistered renderable nodes');
  }

  // --- 2. Framing produces a non-clipping camera distance for every entry ---
  let clipRisk = 0, degenerate = 0, worstNear = Infinity, worstName = '';
  for (const e of app.registry.list()) {
    const solved = solveFraming(app.camera ?? cameraFallback(), e.node, e.zoomMargin);
    if (!solved) { degenerate++; continue; }
    const nearGap = solved.dist - solved.radius;
    if (nearGap < worstNear) { worstNear = nearGap; worstName = e.name; }
    if (nearGap <= CAMERA_NEAR) clipRisk++;
  }
  if (clipRisk === 0) {
    pass(`framing clears the near plane for all ${app.registry.entries.size} entries`);
    if (isFinite(worstNear)) {
      note(`tightest: ${worstName} at ${worstNear.toFixed(3)} mm of clearance (near = ${CAMERA_NEAR})`);
    }
  } else {
    fail(`${clipRisk} entries frame closer than the near plane`);
  }
  if (degenerate) warn(`${degenerate} entries have an empty bounding box`);

  // --- 3. Clips ---
  const clips = app.anim.names();
  if (clips.length) {
    pass(`${clips.length} clip(s) present: ${clips.join(', ')}`);
  } else {
    note('this asset carries no clips (expected for B40 and B02_MAINBOARD)');
  }

  // Measure real vertex travel for the skinned peel, rather than trusting either doc.
  if (clips.includes('ANIM_B10_PEEL')) {
    const m = measureClipTravel(app, 'ANIM_B10_PEEL');
    if (m == null) {
      warn('ANIM_B10_PEEL: could not sample a skinned mesh to measure');
    } else if (m.max > 1) {
      pass(`ANIM_B10_PEEL deforms the ribbon: ${m.max.toFixed(2)} mm peak vertex travel, at t=${m.atT.toFixed(2)}`);
      note(`measured across ${m.meshCount} skinned meshes; the deforming one is ${m.worstMesh}`);
      note('the shipped GATE_CHECK.json records 0.0 mm and a PARTIAL verdict for this clip. That');
      note('report is wrong: most of the skinned meshes here are rigidly bound and never move, so');
      note('a measurement that samples only one of them reads zero on a rig that works. Do not');
      note('rebuild the asset on the strength of that report.');
    } else {
      fail(`ANIM_B10_PEEL peaks at only ${m.max.toFixed(3)} mm - the rig is not deforming`);
    }
  }

  // --- 4. Morph-target melt changes SHAPE, not just colour ---
  if (app.anim.solderMeshes.length) {
    const mesh = app.anim.solderMeshes[0];
    const influences = mesh.morphTargetInfluences?.length ?? 0;

    // Box3.setFromObject reads geometry.boundingBox, which IGNORES morph
    // influences - so it reports an identical size at weight 0 and weight 1 on
    // a morph that is working. Measure the morph delta attribute instead.
    const shift = measureMorphShift(mesh);

    if (influences > 0 && shift > 0.0005) {
      pass(`solder melt drives ${influences} morph target(s) on ${mesh.name}`);
      note(`peak vertex displacement at full weight: ${shift.toFixed(3)} mm - the fillet changes SHAPE`);
      note('the glow is NOT in the file - it is a runtime emissive lerp driven alongside the weight');
    } else if (influences > 0) {
      fail(`${mesh.name} has ${influences} morph target(s) but zero positional delta`);
    } else {
      fail('no morph target influences on the solder meshes');
    }
  }

  // --- 5. States: exactly one exclusive member visible ---
  for (const g of app.states.availableExclusiveGroups()) {
    const members = app.manifest.states[g].group.filter((m) => app.root.getObjectByName(m));
    const visible = members.filter((m) => app.root.getObjectByName(m).visible);
    if (visible.length === 1) {
      pass(`${g}: exactly one of ${members.length} visible (${visible[0]})`);
      note('all five ship visible in the file; the runtime hides the rest on load');
    } else {
      fail(`${g}: ${visible.length} visible, expected exactly 1 - they will render on top of each other`);
    }
  }

  // --- 6. Latch reaches all three states ---
  if (app.states.hasLatch()) {
    const before = app.states.latchState();
    const reached = ['LATCHED', 'HALF_CLOSED', 'UNLATCHED'].filter((s) => app.states.setLatch(s));
    app.states.setLatch(before);
    if (reached.length === 3) pass('B11_FLAP reaches all three latch states');
    else fail(`B11_FLAP reached only ${reached.length} of 3 latch states`);
  }

  // --- 7. Shared-material trap ---
  const shared = countSharedMaterials(app.root);
  if (shared.length) {
    pass(`${shared.length} shared material datablock(s) drive more than one mesh`);
    note(shared.slice(0, 4).map((s) => `${s.name} x${s.count}`).join(', '));
    note('group highlight is free; per-item highlight clones first, or it lights the whole group');
  }

  // --- 8. Scale sanity ---
  const size = new THREE.Box3().setFromObject(app.root).getSize(new THREE.Vector3());
  const span = Math.max(size.x, size.y, size.z);
  if (span > 0.5 && span < 5000) {
    pass(`asset spans ${span.toFixed(2)} world units - consistent with 1 unit = 1 mm`);
  } else {
    warn(`asset spans ${span.toFixed(2)} units - check the millimetre-scale assumption`);
  }

  return lines.join('\n');
}

function cameraFallback() {
  const c = new THREE.PerspectiveCamera(45, 16 / 9, CAMERA_NEAR, 20000);
  c.position.set(0, 0.4, 1);
  return c;
}

/**
 * Peak deformation across a whole clip, over every skinned mesh.
 *
 * The trap that produced the shipped PARTIAL verdict: sample one skinned mesh
 * and you will probably pick a rigidly-bound one. B10_B11_IFC has 21 skinned
 * meshes and only the ribbon actually deforms - the socket bodies and contact
 * fingers are bound but static. Measuring the first mesh found reports 0.0 mm
 * on a rig that moves 26.9 mm.
 */
function measureClipTravel(app, clipName, steps = 12) {
  // Sample EVERY skinned mesh, not just the first one found. Most of the 21
  // skinned meshes in this asset are rigidly bound (socket bodies, pins) and
  // never deform; only the ribbon does. Picking the first one alphabetically
  // lands on B10_COVERLAY_EDGE and measures a flat zero on a working rig.
  const meshes = [];
  app.root.traverse((o) => { if (o.isSkinnedMesh) meshes.push(o); });
  if (!meshes.length) return null;

  // Keep each mesh's samples in its own bucket so we can name the mesh that
  // actually deforms, instead of just asserting that something did.
  const sample = () => meshes.map((m) => {
    m.skeleton?.update();
    const pos = m.geometry.attributes.position;
    const v = new THREE.Vector3();
    const out = [];
    const step = Math.max(1, Math.floor(pos.count / 60));
    for (let i = 0; i < pos.count; i += step) {
      v.fromBufferAttribute(pos, i);
      // applyBoneTransform gives the DEFORMED position - the whole point here.
      if (m.applyBoneTransform) m.applyBoneTransform(i, v);
      out.push(v.clone().applyMatrix4(m.matrixWorld));
    }
    return out;
  });

  /** Per-mesh peak deviation between two frames. */
  const deviation = (A, B) => A.map((pts, mi) => {
    let m = 0;
    const other = B[mi] ?? [];
    for (let i = 0; i < Math.min(pts.length, other.length); i++) {
      m = Math.max(m, pts[i].distanceTo(other[i]));
    }
    return m;
  });

  const prevPlaying = app.anim.playing;

  app.anim.scrub(clipName, 0);
  app.root.updateMatrixWorld(true);
  const base = sample();

  let max = 0, atT = 0, endpoints = 0, worstIdx = 0;
  for (let s = 1; s <= steps; s++) {
    const t = s / steps;
    app.anim.scrub(clipName, t);
    app.root.updateMatrixWorld(true);
    const per = deviation(base, sample());
    const frameMax = Math.max(...per);
    if (frameMax > max) { max = frameMax; atT = t; worstIdx = per.indexOf(frameMax); }
    if (s === steps) endpoints = frameMax;
  }

  app.anim.stopAll();
  if (prevPlaying) app.anim.play(prevPlaying);
  else app.anim.scrub(clipName, 0);

  return {
    max, atT, endpoints,
    meshCount: meshes.length,
    worstMesh: meshes[worstIdx]?.name ?? '(unknown)',
  };
}

/** Largest vertex displacement the morph target applies at full weight. */
function measureMorphShift(mesh) {
  const rel = mesh.geometry?.morphAttributes?.position;
  if (!rel || !rel.length) return 0;
  const delta = rel[0];
  // glTF morph targets are relative offsets, so the attribute IS the shift.
  const absolute = mesh.geometry.morphTargetsRelative !== false;
  const basePos = mesh.geometry.attributes.position;
  let max = 0;
  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  for (let i = 0; i < delta.count; i++) {
    a.fromBufferAttribute(delta, i);
    if (absolute) {
      max = Math.max(max, a.length());
    } else {
      b.fromBufferAttribute(basePos, i);
      max = Math.max(max, a.distanceTo(b));
    }
  }
  return max;
}

function countSharedMaterials(root) {
  const counts = new Map();
  root.traverse((o) => {
    if (!o.material) return;
    const list = Array.isArray(o.material) ? o.material : [o.material];
    for (const m of list) {
      if (!m) continue;
      counts.set(m, (counts.get(m) ?? 0) + 1);
    }
  });
  return [...counts.entries()]
    .filter(([, c]) => c > 1)
    .map(([m, c]) => ({ name: m.name || '(unnamed)', count: c }))
    .sort((x, y) => y.count - x.count);
}

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
