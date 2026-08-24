import * as THREE from 'three';
import { CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js';

/**
 * Callout labels.
 *
 * HTML overlays (CSS2D) rather than 3D/sprite text: sprite text is illegible at
 * 720p on a 5-inch screen, and HTML gives free multilingual text, screen-reader
 * access and reflow.
 *
 * A leader line is drawn in a single SVG layer: we project the anchor to screen
 * space each frame and hide the label when it is occluded or off-screen.
 */
export class LabelLayer {
  constructor(scene, camera, container, renderer) {
    this.scene = scene;
    this.camera = camera;
    this.container = container;
    this.renderer = renderer;

    this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    this.svg.classList.add('leader-layer');
    container.appendChild(this.svg);

    /** name -> { entry, css2d, el, anchorWorld, line } */
    this.labels = new Map();
    this.occlusionEnabled = true;
    this._ray = new THREE.Raycaster();
    this._v = new THREE.Vector3();
    this._root = null;
  }

  setRoot(root) { this._root = root; }

  /** Add a callout for a registry entry. anchorPos is a world-space Vector3. */
  add(entry, anchorPos, { variant = 'default', showNote = false } = {}) {
    this.remove(entry.name);

    // The CSS2DObject element (`el`) is a bare positional anchor: CSS2DRenderer
    // fully overwrites its `transform` every frame, so it cannot also carry our
    // own declutter offset. `inner` holds the actual visible box and is where
    // update() applies a corrective translateY when callouts would overlap.
    const el = document.createElement('div');
    const inner = document.createElement('div');
    inner.className = 'callout callout--' + variant;
    inner.innerHTML =
      '<div class="callout__title"></div>' +
      (showNote && entry.note ? '<div class="callout__note"></div>' : '') +
      (entry.signal ? '<div class="callout__chip"></div>' : '');
    // textContent, never innerHTML, for the manifest strings.
    inner.querySelector('.callout__title').textContent = entry.label;
    if (showNote && entry.note) inner.querySelector('.callout__note').textContent = entry.note;
    if (entry.signal) inner.querySelector('.callout__chip').textContent = entry.signal;
    el.appendChild(inner);

    const css2d = new CSS2DObject(el);
    css2d.position.copy(anchorPos);
    // Offset the box up-right of the anchor so the leader line is visible.
    css2d.center.set(0, 1);
    this.scene.add(css2d);

    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('class', 'leader leader--' + variant);
    this.svg.appendChild(line);

    this.labels.set(entry.name, {
      entry, css2d, el, inner, anchorWorld: anchorPos.clone(), line, declutterY: 0,
    });
    return inner;
  }

  remove(name) {
    const rec = this.labels.get(name);
    if (!rec) return;
    this.scene.remove(rec.css2d);
    rec.el.remove();
    rec.line.remove();
    this.labels.delete(name);
  }

  clear() {
    for (const name of [...this.labels.keys()]) this.remove(name);
  }

  has(name) { return this.labels.has(name); }

  /** Re-read anchor world positions (needed while a clip is playing). */
  refreshAnchor(name, pos) {
    const rec = this.labels.get(name);
    if (rec) { rec.anchorWorld.copy(pos); rec.css2d.position.copy(pos); }
  }

  /** Called every frame after controls.update(). */
  update() {
    const rect = this.renderer.domElement.getBoundingClientRect();
    if (this.svg.getAttribute('width') !== String(rect.width)) {
      this.svg.setAttribute('width', rect.width);
      this.svg.setAttribute('height', rect.height);
      this.svg.setAttribute('viewBox', `0 0 ${rect.width} ${rect.height}`);
    }

    const camPos = this.camera.position;
    const visible = [];

    for (const rec of this.labels.values()) {
      const p = this._v.copy(rec.anchorWorld).project(this.camera);
      const offScreen = p.z > 1 || p.x < -1.05 || p.x > 1.05 || p.y < -1.05 || p.y > 1.05;

      let occluded = false;
      if (!offScreen && this.occlusionEnabled && this._root) {
        // Cast from camera toward the anchor; if something solid is hit
        // meaningfully in front of it, the anchor is behind geometry.
        const dir = rec.anchorWorld.clone().sub(camPos);
        const dist = dir.length();
        dir.normalize();
        this._ray.set(camPos, dir);
        this._ray.far = dist * 0.985;
        const hits = this._ray.intersectObjects(this._root.children, true);
        occluded = hits.some((h) => h.object.visible && h.distance < dist * 0.985);
      }

      const hidden = offScreen || occluded;
      rec.inner.classList.toggle('is-hidden', hidden);
      rec.line.style.display = hidden ? 'none' : '';
      // Undo any previous declutter shift before re-measuring: CSS2DRenderer
      // repositions `el` fresh every frame, so `inner`'s natural (unshifted)
      // box is what we want to test for overlaps below.
      rec.inner.style.transform = '';
      if (hidden) continue;

      const ax = (p.x * 0.5 + 0.5) * rect.width;
      const ay = (-p.y * 0.5 + 0.5) * rect.height;
      visible.push({ rec, ax, ay });
    }

    // Declutter: several anchors close together in screen space (e.g. a
    // cluster of fault pins after an explode) otherwise land their callouts
    // exactly on top of each other, illegible. Greedily stack collisions
    // downward instead of leaving them to overlap. Cheap: at most a handful
    // of labels are ever visible at once (occlusion caps the rest).
    visible.sort((a, b) => a.ay - b.ay);
    const placed = [];
    for (const { rec, ax, ay } of visible) {
      const natural = rec.inner.getBoundingClientRect();
      const box = {
        left: natural.left - rect.left,
        top: natural.top - rect.top,
        right: natural.right - rect.left,
        bottom: natural.bottom - rect.top,
      };
      const height = box.bottom - box.top;
      const step = height + 6;
      let dy = 0;
      let guard = 0;
      while (
        placed.some((p) => box.left < p.right && box.right > p.left
          && box.top + dy < p.bottom && box.bottom + dy > p.top)
        && guard++ < 16
      ) {
        dy += step;
      }
      if (dy !== 0) rec.inner.style.transform = `translateY(${dy}px)`;
      placed.push({ left: box.left, right: box.right, top: box.top + dy, bottom: box.bottom + dy });

      // Draw the leader to the callout's actual (post-shift) nearest corner.
      const bx = box.left;
      const by = box.top + dy;
      const bw = box.right - box.left;
      const attachX = ax < bx + bw / 2 ? bx + 6 : bx + bw - 6;
      const attachY = by + height;

      rec.line.setAttribute('x1', ax.toFixed(1));
      rec.line.setAttribute('y1', ay.toFixed(1));
      rec.line.setAttribute('x2', attachX.toFixed(1));
      rec.line.setAttribute('y2', attachY.toFixed(1));
    }
  }
}
