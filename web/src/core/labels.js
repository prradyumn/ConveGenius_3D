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

    const el = document.createElement('div');
    el.className = 'callout callout--' + variant;
    el.innerHTML =
      '<div class="callout__title"></div>' +
      (showNote && entry.note ? '<div class="callout__note"></div>' : '') +
      (entry.signal ? '<div class="callout__chip"></div>' : '');
    // textContent, never innerHTML, for the manifest strings.
    el.querySelector('.callout__title').textContent = entry.label;
    if (showNote && entry.note) el.querySelector('.callout__note').textContent = entry.note;
    if (entry.signal) el.querySelector('.callout__chip').textContent = entry.signal;

    const css2d = new CSS2DObject(el);
    css2d.position.copy(anchorPos);
    // Offset the box up-right of the anchor so the leader line is visible.
    css2d.center.set(0, 1);
    this.scene.add(css2d);

    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('class', 'leader leader--' + variant);
    this.svg.appendChild(line);

    this.labels.set(entry.name, { entry, css2d, el, anchorWorld: anchorPos.clone(), line });
    return el;
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
      rec.el.classList.toggle('is-hidden', hidden);
      rec.line.style.display = hidden ? 'none' : '';
      if (hidden) continue;

      // Anchor point in CSS pixels.
      const ax = (p.x * 0.5 + 0.5) * rect.width;
      const ay = (-p.y * 0.5 + 0.5) * rect.height;

      // CSS2DRenderer has already placed the box; read where it landed and
      // draw the leader to its nearest bottom corner.
      const box = rec.el.getBoundingClientRect();
      const bx = box.left - rect.left;
      const by = box.top - rect.top;
      const attachX = ax < bx + box.width / 2 ? bx + 6 : bx + box.width - 6;
      const attachY = by + box.height;

      rec.line.setAttribute('x1', ax.toFixed(1));
      rec.line.setAttribute('y1', ay.toFixed(1));
      rec.line.setAttribute('x2', attachX.toFixed(1));
      rec.line.setAttribute('y2', attachY.toFixed(1));
    }
  }
}
