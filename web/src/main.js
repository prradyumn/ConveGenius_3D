import * as THREE from 'three';
import {
  ASSETS, DEFAULT_ASSET, MARGIN_COMPONENT, MARGIN_OVERVIEW,
  CAMERA_FOV, MAGNIFY_FOV, SELECT_COLOR, HOVER_COLOR, TARGET_FPS,
} from './core/config.js';
import { createStage, attachResize } from './core/scene.js';
import { loadAsset, loadComponentsManifest, disposeScene } from './core/loader.js';
import { Registry } from './core/registry.js';
import { Picker } from './core/picking.js';
import { Highlighter } from './core/materials.js';
import { LabelLayer } from './core/labels.js';
import { AnimController } from './core/anim.js';
import { StateMachine, STATE_COPY } from './core/states.js';
import { InstancedFamilies } from './core/instancing.js';
import { ProcedureRunner } from './procedures/engine.js';
import { PROCEDURES, TOOLS } from './procedures/fixes.js';
import { frameObject, updateDepthRange } from './core/framing.js';
import { runContractChecks } from './ui/checks.js';
import { mountStatePanel } from './ui/statePanel.js';
import { mountQuiz } from './ui/quiz.js';

const $ = (sel) => document.querySelector(sel);
const stageEl = $('#stage');

// ---------------------------------------------------------------- app state

const app = {
  manifest: null,
  assetKey: null,
  gltf: null,
  root: null,
  registry: null,
  states: null,
  anim: null,
  instancing: new InstancedFamilies(),
  highlighter: new Highlighter(),
  labels: null,
  selection: null,
  hovered: null,
  showLabels: false,
  magnified: false,
  cancelFly: null,
  runner: null,
  tool: 'hands',
  quiz: null,
};

const stage = createStage(stageEl);
const { renderer, labelRenderer, scene, camera, controls } = stage;
attachResize(stageEl, stage);

// The checks panel measures framing against the live camera.
app.camera = camera;
app.controls = controls;
app.renderer = renderer;

app.labels = new LabelLayer(scene, camera, stageEl, renderer);

const picker = new Picker(
  renderer, camera,
  () => app.root,
  () => app.registry,
  () => (app.instancing.enabled ? app.instancing : null),
);

// ---------------------------------------------------------------- helpers

let toastTimer = null;
function toast(msg, severity = 'info', ms = 4200) {
  const el = $('#toast');
  el.textContent = msg;
  el.className = 'toast is-on' + (severity !== 'info' ? ' toast--' + severity : '');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.className = 'toast'; }, ms);
}

function setLoading(on, text, frac) {
  const el = $('#loading');
  el.classList.toggle('is-done', !on);
  if (text) $('#loading-text').textContent = text;
  if (frac != null) $('#loading-fill').style.width = Math.round(frac * 100) + '%';
}

// ---------------------------------------------------------------- selection

function clearSelection() {
  if (app.selection) {
    app.highlighter.clear(app.selection.node);
    app.labels.remove(app.selection.name);
  }
  app.instancing.clearHighlight(app.root);
  app.selection = null;
  $('#selection').classList.add('is-empty');
}

function select(entry, hit) {
  if (!entry) return;
  if (app.selection?.name === entry.name) return;
  clearSelection();
  app.selection = entry;

  // An instanced member cannot take an emissive of its own, so highlight it
  // with a proxy at that instance's transform instead.
  if (hit?.instancedMesh != null) {
    app.instancing.highlightInstance(app.root, hit.instancedMesh, hit.instanceId, SELECT_COLOR);
  } else {
    app.highlighter.select(entry.node);
  }

  const pos = app.registry.anchorPosition(entry, new THREE.Vector3());
  app.labels.add(entry, pos, { variant: 'selected', showNote: false });

  // Card content comes from components.json, never from the component.
  $('#selection').classList.remove('is-empty');
  $('#sel-label').textContent = entry.label;
  $('#sel-cat').textContent = entry.category;
  $('#sel-signal').textContent = entry.signal ?? '';
  $('#sel-node').textContent = entry.name;
  $('#sel-note').textContent = entry.note ?? '';

  app.cancelFly?.();
  app.cancelFly = frameObject(camera, controls, entry.node, entry.zoomMargin ?? MARGIN_COMPONENT);

  if (app.runner) updateActionTarget();
}

picker.onHover((hit) => {
  const entry = hit?.entry ?? null;
  if (app.hovered?.name === entry?.name) return;

  if (app.hovered && app.hovered.name !== app.selection?.name) {
    app.highlighter.clear(app.hovered.node);
    if (!app.showLabels) app.labels.remove(app.hovered.name);
  }
  app.hovered = entry;
  renderer.domElement.style.cursor = entry ? 'pointer' : 'default';

  if (entry && entry.name !== app.selection?.name && hit.instancedMesh == null) {
    app.highlighter.hover(entry.node);
    if (!app.labels.has(entry.name)) {
      const pos = app.registry.anchorPosition(entry, new THREE.Vector3());
      app.labels.add(entry, pos, { variant: 'hover' });
    }
  }
});

picker.onSelect((hit) => {
  if (!hit) { clearSelection(); return; }
  select(hit.entry, hit);
});

// ---------------------------------------------------------------- asset load

async function loadAssetByKey(key) {
  const def = ASSETS[key];
  if (!def) return;

  setLoading(true, `Loading ${def.label}…`, 0);

  // Tear down the previous asset completely.
  app.cancelFly?.();
  clearSelection();
  app.labels.clear();
  app.highlighter.disposeAll();
  if (app.anim) app.anim.dispose();
  if (app.root) {
    app.instancing.teardown(app.root);
    scene.remove(app.root);
    disposeScene(app.root);
  }
  app.runner = null;

  let gltf;
  try {
    gltf = await loadAsset(def.file, (f) => setLoading(true, `Loading ${def.label}…`, f * 0.9));
  } catch (err) {
    setLoading(true, 'Failed to load ' + def.file);
    toast('Could not load ' + def.file + ': ' + err.message, 'danger', 9000);
    return;
  }

  app.assetKey = key;
  app.gltf = gltf;
  app.root = gltf.scene;
  scene.add(app.root);
  app.root.updateMatrixWorld(true);

  // Cached for the adaptive depth range (see updateDepthRange).
  app.sceneRadius = new THREE.Box3().setFromObject(app.root)
    .getBoundingSphere(new THREE.Sphere()).radius;

  app.registry = new Registry(app.manifest, key, app.root);
  // Hide all non-default states BEFORE the first frame, or the five B40 joints
  // render on top of each other.
  app.states = new StateMachine(app.root, app.manifest, key);
  app.anim = new AnimController(app.root, gltf.animations ?? []);
  app.labels.setRoot(app.root);

  // Occlusion testing is a raycast per label per frame. On the 500-node assets
  // that is not affordable on the target device.
  app.labels.occlusionEnabled = app.registry.entries.size < 120;

  $('#asset-blurb').textContent = def.blurb;

  buildClipButtons();
  buildPinGroupButtons();
  mountStatePanel($('#states-host'), app, { toast, frameEntry: (n) => focusByName(n) });
  app.quiz = mountQuiz($('#quiz'), app, { toast });
  buildProcedureUI();
  // Defer: renderer.info.render still holds the PREVIOUS asset's last frame
  // until this one has actually been drawn, which reads as one asset behind.
  requestAnimationFrame(() => requestAnimationFrame(refreshPerf));

  // Overview framing, then let go.
  const target = def.root ? app.root.getObjectByName(def.root) ?? app.root : app.root;
  camera.fov = CAMERA_FOV;
  camera.updateProjectionMatrix();
  app.magnified = false;
  $('#btn-magnify').setAttribute('aria-pressed', 'false');

  // Put the camera on this asset's preferred axis before solving the fit, since
  // solveFraming deliberately preserves the current direction.
  applyOpeningView(def, target);
  frameObject(camera, controls, target, MARGIN_OVERVIEW, 1);

  const diag = app.registry.diagnostics();
  setLoading(false);
  console.info('[asset]', key, diag);
  if (diag.unmatchedSpec > 0) {
    console.warn(`[registry] ${diag.unmatchedSpec} components.json entries have no node in ${key}:`, diag.unmatchedSpecNames);
  }
  if (diag.missingAnchors.length) {
    console.warn(`[registry] anchors referenced by components.json but absent from ${key} (label falls back to centroid):`, diag.missingAnchors);
  }
}

/** Seat the camera on the asset's authored viewing axis, at a rough distance
 *  that solveFraming will then correct exactly. */
function applyOpeningView(def, target) {
  if (!def.view) return;
  const box = new THREE.Box3().setFromObject(target);
  if (box.isEmpty()) return;
  const centre = box.getCenter(new THREE.Vector3());
  const reach = box.getSize(new THREE.Vector3()).length() || 1;
  const dir = new THREE.Vector3(...def.view).normalize();
  camera.position.copy(centre).add(dir.multiplyScalar(reach));
  controls.target.copy(centre);
  controls.update();
}

function focusByName(name) {
  const entry = app.registry?.get(name);
  if (!entry) return false;
  select(entry, null);
  return true;
}

// ---------------------------------------------------------------- explore UI

function buildAssetSelect() {
  const sel = $('#asset-select');
  sel.innerHTML = '';
  for (const [key, def] of Object.entries(ASSETS)) {
    const o = document.createElement('option');
    o.value = key;
    o.textContent = `${def.label}  (${def.sizeKB} KB)`;
    sel.appendChild(o);
  }
  sel.value = DEFAULT_ASSET;
  sel.addEventListener('change', () => loadAssetByKey(sel.value));
}

function buildClipButtons() {
  const host = $('#clips');
  host.innerHTML = '';
  const names = app.anim.names();

  if (!names.length) {
    const p = document.createElement('p');
    p.className = 'muted';
    p.textContent = 'This asset has no animation clips.';
    host.appendChild(p);
  }

  for (const name of names) {
    const b = document.createElement('button');
    b.className = 'btn';
    b.textContent = name.replace(/^ANIM_/, '');
    b.title = `${name} - ${app.anim.duration(name).toFixed(2)}s`;
    b.addEventListener('click', () => {
      const reverse = $('#clip-reverse').checked;
      app.anim.play(name, { reverse });
      toast(`${name}${reverse ? ' (reversed)' : ''}`, 'info', 2400);
    });
    host.appendChild(b);
  }

  const stop = document.createElement('button');
  stop.className = 'btn btn--ghost';
  stop.textContent = 'Stop';
  stop.addEventListener('click', () => app.anim.stopAll());
  host.appendChild(stop);

  // The melt and nozzle sliders only exist where the rig does.
  const hasMelt = app.anim.solderMeshes.length > 0;
  $('#melt-wrap').classList.toggle('is-hidden', !hasMelt);
  const hasNozzle = app.anim.nozzleMats.length > 0;
  $('#heat-wrap').classList.toggle('is-hidden', !hasNozzle);
}

function buildPinGroupButtons() {
  const host = $('#pin-groups');
  host.innerHTML = '';
  const groups = app.manifest.pinGroups ?? {};
  let any = false;

  for (const [matName, label] of Object.entries(groups)) {
    // Only offer a group if that material is actually in this asset.
    let present = false;
    app.root.traverse((o) => {
      if (present || !o.material) return;
      const list = Array.isArray(o.material) ? o.material : [o.material];
      if (list.some((m) => m?.name === matName)) present = true;
    });
    if (!present) continue;
    any = true;

    const b = document.createElement('button');
    b.className = 'btn';
    b.textContent = label;
    b.addEventListener('click', () => {
      const on = b.classList.contains('is-on');
      app.highlighter.clearSharedTints();
      host.querySelectorAll('.btn').forEach((x) => x.classList.remove('is-on'));
      if (!on) {
        // Deliberately touches the SHARED material: this lights every pin in
        // the group at once, which is the point of group teaching.
        app.highlighter.tintSharedMaterial(app.root, matName, SELECT_COLOR, 1.6);
        b.classList.add('is-on');
        const pins = app.registry.list().filter((e) => e.group && matName.endsWith(e.group));
        toast(`${label}: ${pins.length} contacts lit from one shared material.`, 'info', 3600);
      }
    });
    host.appendChild(b);
  }

  if (!any) {
    const p = document.createElement('p');
    p.className = 'muted';
    p.textContent = 'No pin-group materials in this asset.';
    host.appendChild(p);
  }
}

function buildSearch() {
  const input = $('#search');
  const out = $('#search-results');
  input.addEventListener('input', () => {
    out.innerHTML = '';
    if (!app.registry) return;
    for (const e of app.registry.search(input.value)) {
      const li = document.createElement('li');
      const b = document.createElement('button');
      b.innerHTML = '<span></span><small></small>';
      b.querySelector('span').textContent = e.label;
      b.querySelector('small').textContent = e.name + (e.signal ? ' · ' + e.signal : '');
      b.addEventListener('click', () => { select(e, null); out.innerHTML = ''; input.value = ''; });
      li.appendChild(b);
      out.appendChild(li);
    }
  });
}

// ---------------------------------------------------------------- procedures

function buildProcedureUI() {
  const sel = $('#fix-select');
  if (!sel.options.length) {
    for (const p of Object.values(PROCEDURES)) {
      const o = document.createElement('option');
      o.value = p.id;
      o.textContent = p.title;
      sel.appendChild(o);
    }
    sel.addEventListener('change', () => startProcedure(sel.value));
    $('#fix-restart').addEventListener('click', () => app.runner && startProcedure(app.runner.procedure.id));

    const tools = $('#tools');
    for (const t of TOOLS) {
      const b = document.createElement('button');
      b.className = 'btn' + (t.id === app.tool ? ' is-on' : '');
      b.textContent = t.label;
      b.title = t.hint;
      b.dataset.tool = t.id;
      b.addEventListener('click', () => {
        app.tool = t.id;
        tools.querySelectorAll('.btn').forEach((x) => x.classList.toggle('is-on', x.dataset.tool === t.id));
        // The magnifier IS a camera state, not a model - so picking it up
        // actually narrows the FOV.
        setMagnified(t.id === 'magnifier');
      });
      tools.appendChild(b);
    }

    const verbs = [
      ['inspect', 'Inspect'], ['disconnect', 'Disconnect battery'], ['set-latch', 'Set latch'],
      ['play-clip', 'Peel back'], ['heat', 'Apply heat'], ['pry', 'Pry it off'],
      ['clean', 'Clean pad'], ['solder', 'Solder'], ['insert', 'Insert'],
    ];
    const vhost = $('#verbs');
    for (const [verb, label] of verbs) {
      const b = document.createElement('button');
      b.className = 'btn' + (verb === 'pry' ? ' btn--danger' : '');
      b.textContent = label;
      b.addEventListener('click', () => submitAction(verb));
      vhost.appendChild(b);
    }
  }

  const wanted = [...Object.values(PROCEDURES)].find((p) => p.asset === app.assetKey);
  if (wanted) { sel.value = wanted.id; startProcedure(wanted.id); }
  else {
    app.runner = null;
    $('#fix-intro').textContent = `No gated procedure targets ${ASSETS[app.assetKey].label}. Load the USB-C port for Fix 2, or the flex + IFC for Fix 3.`;
    $('#step-prompt').textContent = '';
    $('#step-why').textContent = '';
    $('#step-counter').textContent = '';
    $('#step-list').innerHTML = '';
  }
}

function startProcedure(id) {
  const proc = PROCEDURES[id];
  if (!proc) return;
  if (proc.asset !== app.assetKey) {
    toast(`${proc.title} needs the ${ASSETS[proc.asset].label} asset. Switching.`, 'warn');
    $('#asset-select').value = proc.asset;
    loadAssetByKey(proc.asset);
    return;
  }

  const ctx = {
    registry: app.registry,
    states: app.states,
    anim: app.anim,
    scene,
    tools: { nozzleTip: app.root.getObjectByName('B28_ANCHOR_TIP') ?? null },
  };
  app.runner = new ProcedureRunner(proc, ctx);
  app.runner.onChange(() => renderProcedure());
  app.runner.reset();
  $('#fix-intro').textContent = proc.intro;
  $('#fix-feedback').textContent = '';
  renderProcedure();
}

function renderProcedure() {
  const r = app.runner;
  if (!r) return;
  const step = r.step;

  $('#step-counter').textContent = r.done
    ? 'Complete'
    : `Step ${r.stepIndex + 1} of ${r.total}`;
  $('#step-prompt').textContent = r.done ? (r.procedure.completion ?? 'Done.') : (step?.prompt ?? '');
  $('#step-why').textContent = r.done ? '' : (step?.why ?? '');

  const list = $('#step-list');
  list.innerHTML = '';
  r.procedure.steps.forEach((s, i) => {
    const li = document.createElement('li');
    li.textContent = s.prompt;
    if (i < r.stepIndex) li.className = 'is-done';
    else if (i === r.stepIndex && !r.done) li.className = 'is-current';
    list.appendChild(li);
  });

  if (r.done) {
    const sc = r.score();
    $('#fix-feedback').className = 'feedback is-ok';
    $('#fix-feedback').textContent =
      sc.clean
        ? 'Passed with no wrong actions. That is the standard.'
        : `Passed with ${sc.faults} wrong action${sc.faults === 1 ? '' : 's'}. Review those before the bench test.`;
  }
  updateActionTarget();
}

function updateActionTarget() {
  const el = $('#action-target');
  if (!el) return;
  el.textContent = app.selection
    ? `Target: ${app.selection.label} (${app.selection.name})`
    : 'Target: nothing selected yet.';
}

function submitAction(verb) {
  if (!app.runner) { toast('No procedure is running for this asset.', 'warn'); return; }

  // set-latch needs a latch state as its target, not a mesh.
  let target = app.selection?.name ?? null;
  if (verb === 'set-latch') {
    target = nextLatchChoice();
  } else if (verb === 'disconnect') {
    target = 'BATTERY';
  } else if (verb === 'play-clip') {
    target = 'ANIM_B10_PEEL';
  }

  const res = app.runner.submit({ verb, target, tool: app.tool });
  const fb = $('#fix-feedback');
  fb.className = 'feedback is-' + (res.ok ? 'ok' : (res.severity === 'warn' ? 'warn' : 'danger'));
  fb.textContent = res.message;
  toast(res.message, res.ok ? 'ok' : (res.severity ?? 'danger'), res.ok ? 3200 : 7000);
  renderProcedure();
}

/** Cycle the latch so the learner can actually choose the wrong one. */
let latchCycle = ['UNLATCHED', 'HALF_CLOSED', 'LATCHED'];
let latchIdx = 0;
function nextLatchChoice() {
  const want = latchCycle[latchIdx % latchCycle.length];
  latchIdx++;
  app.states?.setLatch(want);
  return want;
}

// ---------------------------------------------------------------- HUD

function setMagnified(on) {
  app.magnified = on;
  camera.fov = on ? MAGNIFY_FOV : CAMERA_FOV;
  camera.updateProjectionMatrix();
  $('#btn-magnify').setAttribute('aria-pressed', String(on));
  if (on) toast('Magnification on. Narrow field of view - this is a camera state, not a model.', 'info', 3200);
}

function bindHud() {
  $('#btn-reset').addEventListener('click', () => {
    clearSelection();
    app.labels.clear();
    const def = ASSETS[app.assetKey];
    const target = def.root ? app.root.getObjectByName(def.root) ?? app.root : app.root;
    app.cancelFly?.();
    app.cancelFly = frameObject(camera, controls, target, MARGIN_OVERVIEW);
  });

  $('#btn-magnify').addEventListener('click', () => setMagnified(!app.magnified));

  $('#btn-labels').addEventListener('click', (e) => {
    app.showLabels = !app.showLabels;
    e.currentTarget.setAttribute('aria-pressed', String(app.showLabels));
    e.currentTarget.textContent = app.showLabels ? 'Labels on' : 'Labels off';
    app.labels.clear();
    if (app.showLabels) showKeyLabels();
    else if (app.selection) {
      const pos = app.registry.anchorPosition(app.selection, new THREE.Vector3());
      app.labels.add(app.selection, pos, { variant: 'selected' });
    }
  });

  $('#melt').addEventListener('input', (e) => {
    const w = app.anim.setMelt(e.target.value / 100);
    if (w > 0.85) toast('Liquid. Lift it away now - never pry it cold.', 'warn', 2600);
  });

  $('#heat').addEventListener('input', (e) => app.anim.setNozzleHeat(e.target.value / 100));

  $('#run-checks').addEventListener('click', () => {
    $('#checks-out').innerHTML = runContractChecks(app);
  });

  $('#toggle-instancing').addEventListener('change', (e) => {
    if (e.target.checked) {
      const stats = app.instancing.build(app.root);
      if (!stats.families) {
        toast('No instanceable families in this asset (needs 12+ identical via/passive/BGA nodes).', 'warn');
        e.target.checked = false;
      } else {
        toast(`Collapsed ${stats.collapsed} nodes into ${stats.families} InstancedMesh families. ${stats.drawCallsSaved} draw calls saved.`, 'ok', 5000);
      }
    } else {
      app.instancing.teardown(app.root);
    }
    clearSelection();
    refreshPerf();
  });

  // Tabs
  document.querySelectorAll('.tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach((t) => t.classList.toggle('is-active', t === tab));
      document.querySelectorAll('.tabpanel').forEach((p) => {
        p.classList.toggle('is-active', p.dataset.panel === tab.dataset.tab);
      });
      // The quiz sets the scene to a random state, so it only fires once the
      // learner actually opens Assess - never during asset load.
      if (tab.dataset.tab === 'assess' && app.quiz && !app.quiz.armed()) app.quiz.ask();
    });
  });

  window.addEventListener('keydown', (e) => {
    if (e.target.matches('input, select, textarea')) return;
    if (e.key === 'Escape') { clearSelection(); }
    if (e.key === 'm') setMagnified(!app.magnified);
  });
}

/** A readable subset for "labels on": the whole manifest at once is unusable. */
function showKeyLabels() {
  const priority = ['connector', 'socket', 'flex', 'state', 'zone', 'tool', 'solder'];
  const picks = [];
  for (const cat of priority) {
    for (const e of app.registry.list()) {
      if (e.category === cat) picks.push(e);
      if (picks.length >= 10) break;
    }
    if (picks.length >= 10) break;
  }
  for (const e of picks) {
    const pos = app.registry.anchorPosition(e, new THREE.Vector3());
    app.labels.add(e, pos, { variant: e.category === 'state' ? 'fault' : 'default' });
  }
}

function refreshPerf() {
  const info = renderer.info;

  // renderer.info.render describes only the LAST FRAME, so with the camera
  // zoomed into one pad it reports things like "1 draw call, 2 triangles" -
  // true, but useless as a budget figure, and it reads as one asset behind when
  // sampled right after a load. Report scene totals as the budget, and label
  // the per-view numbers as what they are.
  let nodes = 0, visible = 0, sceneTris = 0;
  app.root?.traverse((o) => {
    if (!(o.isMesh || o.isSkinnedMesh || o.isInstancedMesh)) return;
    nodes++;
    let vis = o.visible, p = o.parent;
    while (vis && p) { if (!p.visible) vis = false; p = p.parent; }
    if (!vis) return;
    visible++;
    const idx = o.geometry?.index;
    const pos = o.geometry?.attributes?.position;
    const tris = idx ? idx.count / 3 : (pos ? pos.count / 3 : 0);
    sceneTris += tris * (o.isInstancedMesh ? o.count : 1);
  });

  const s = app.instancing.stats;
  $('#perf').textContent =
    `asset             ${app.assetKey}\n` +
    `mesh nodes        ${nodes} (${visible} visible)\n` +
    `scene triangles   ${Math.round(sceneTris).toLocaleString()}\n` +
    `draw calls (view) ${info.render.calls}\n` +
    `triangles  (view) ${info.render.triangles.toLocaleString()}\n` +
    `geometries on GPU ${info.memory.geometries}\n` +
    `textures on GPU   ${info.memory.textures}\n` +
    `instanced         ${app.instancing.enabled ? `${s.families} families, ${s.collapsed} nodes, -${s.drawCallsSaved} calls` : 'off'}\n` +
    `pixel ratio       ${renderer.getPixelRatio().toFixed(2)}\n` +
    `labels            ${app.labels.labels.size} (occlusion ${app.labels.occlusionEnabled ? 'on' : 'off'})\n` +
    `\n(view figures are last-frame and camera-dependent; scene figures are the budget)`;
}

// ---------------------------------------------------------------- loop

const clock = new THREE.Clock();
let perfTick = 0;
let accumulator = 0;
const frameBudget = 1 / TARGET_FPS;

function animate() {
  requestAnimationFrame(animate);

  const dt = clock.getDelta();

  // Nothing to draw for a page nobody is looking at.
  if (document.hidden) return;

  // Cap the frame rate. Uncapped rendering pins the CPU on a low-end phone for
  // a scene that is static most of the time, and it starves the main thread -
  // which shows up as an unresponsive UI, not as a lower frame counter.
  accumulator += dt;
  if (accumulator < frameBudget) return;
  const frameDt = accumulator;
  accumulator = 0;

  controls.update();
  // Re-derive near/far from the current distance so the depth buffer keeps its
  // precision at both 9 mm macro zoom and 213 mm overview.
  if (app.sceneRadius) updateDepthRange(camera, controls, app.sceneRadius);
  if (app.anim) app.anim.update(frameDt);

  // Anchors move while a clip plays, so live labels must re-read them.
  if (app.labels.labels.size && app.anim?.playing) {
    for (const rec of app.labels.labels.values()) {
      app.labels.refreshAnchor(rec.entry.name, app.registry.anchorPosition(rec.entry, new THREE.Vector3()));
    }
  }

  renderer.render(scene, camera);
  labelRenderer.render(scene, camera);
  app.labels.update();

  if (++perfTick % 30 === 0 && document.querySelector('[data-panel="dev"]').classList.contains('is-active')) {
    refreshPerf();
  }
}

// ---------------------------------------------------------------- boot

(async function boot() {
  setLoading(true, 'Reading components.json…', 0.05);
  try {
    app.manifest = await loadComponentsManifest();
  } catch (err) {
    // The commonest cause by far is opening dist/index.html straight off disk:
    // fetch() is blocked on file:// URLs, so this hangs on "Loading…" with no
    // obvious reason. Say so, rather than leaving a blank spinner.
    const viaFile = location.protocol === 'file:';
    setLoading(
      true,
      viaFile
        ? 'This page must be served over http, not opened from disk. Run "npm run preview" and open the URL it prints.'
        : 'components.json could not be loaded, and it is the label API. Check that assets/data/components.json is being served.',
    );
    console.error('[boot] components.json failed:', err);
    return;
  }

  buildAssetSelect();
  buildSearch();
  bindHud();
  animate();
  await loadAssetByKey(DEFAULT_ASSET);
})();

// Expose for console poking during authoring.
window.__cg = app;
