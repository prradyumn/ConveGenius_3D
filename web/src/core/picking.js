import * as THREE from 'three';
import { isAnchor } from './loader.js';

/**
 * Raycast picking, resolved through the registry to the nearest REGISTERED
 * ancestor - so clicking a tab can resolve to the shell it is grouped under.
 *
 * Anchors are Object3D with no geometry so they never intersect, but we filter
 * defensively anyway.
 */
export class Picker {
  constructor(renderer, camera, getRoot, getRegistry, getInstancing) {
    this.renderer = renderer;
    this.camera = camera;
    this.getRoot = getRoot;
    this.getRegistry = getRegistry;
    // Optional: lets a hit on an InstancedMesh resolve back to its source node.
    this.getInstancing = getInstancing ?? (() => null);

    this.raycaster = new THREE.Raycaster();
    // Millimetre scale: keep the ray's own near/far sane for macro zoom.
    this.raycaster.near = 0;
    this.raycaster.far = Infinity;

    this.pointer = new THREE.Vector2();
    this.enabled = true;

    this._onHover = null;
    this._onSelect = null;
    this._downXY = null;

    const el = renderer.domElement;
    el.addEventListener('pointermove', this._move = (e) => this._handleMove(e));
    el.addEventListener('pointerdown', this._down = (e) => {
      this._downXY = { x: e.clientX, y: e.clientY };
    });
    el.addEventListener('pointerup', this._up = (e) => this._handleUp(e));
    el.addEventListener('pointerleave', this._leave = () => {
      if (this._onHover) this._onHover(null);
    });
  }

  onHover(fn) { this._onHover = fn; return this; }
  onSelect(fn) { this._onSelect = fn; return this; }

  _ndc(event) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    return this.pointer;
  }

  /** Nearest registered entry under the pointer, or null. */
  pick(event) {
    const root = this.getRoot();
    const registry = this.getRegistry();
    if (!root || !registry) return null;

    this.raycaster.setFromCamera(this._ndc(event), this.camera);
    const hits = this.raycaster.intersectObjects(root.children, true);

    const instancing = this.getInstancing();

    for (const hit of hits) {
      const o = hit.object;
      if (!o.visible || isAnchor(o.name)) continue;
      // Skip anything hidden by an invisible ancestor (state variants we turned off).
      let p = o.parent, hiddenAncestor = false;
      while (p) { if (!p.visible) { hiddenAncestor = true; break; } p = p.parent; }
      if (hiddenAncestor) continue;
      // Our own selection proxy must never be pickable.
      if (o.name === 'CG_INSTANCE_HIGHLIGHT') continue;

      // A hit on a collapsed family resolves through the instanceId back to the
      // real node, so instanced components stay clickable and labellable.
      if (instancing && instancing.isInstanced(o)) {
        const src = instancing.resolveHit(o, hit.instanceId);
        const iEntry = src ? registry.resolve(src) : null;
        if (iEntry) {
          return {
            entry: iEntry, point: hit.point, distance: hit.distance,
            object: src, instancedMesh: o, instanceId: hit.instanceId,
          };
        }
        continue;
      }

      const entry = registry.resolve(o);
      if (entry) return { entry, point: hit.point, distance: hit.distance, object: o };
    }
    return null;
  }

  _handleMove(event) {
    if (!this.enabled || !this._onHover) return;
    const hit = this.pick(event);
    this._onHover(hit, event);
  }

  _handleUp(event) {
    if (!this.enabled || !this._onSelect) return;
    // Ignore drags: an orbit gesture must not select. 5px slop.
    if (this._downXY) {
      const dx = event.clientX - this._downXY.x;
      const dy = event.clientY - this._downXY.y;
      if (Math.hypot(dx, dy) > 5) { this._downXY = null; return; }
    }
    this._downXY = null;
    const hit = this.pick(event);
    this._onSelect(hit, event);
  }

  dispose() {
    const el = this.renderer.domElement;
    el.removeEventListener('pointermove', this._move);
    el.removeEventListener('pointerdown', this._down);
    el.removeEventListener('pointerup', this._up);
    el.removeEventListener('pointerleave', this._leave);
  }
}
