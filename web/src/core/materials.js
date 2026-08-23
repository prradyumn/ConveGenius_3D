import * as THREE from 'three';
import { SELECT_COLOR, HOVER_COLOR } from './config.js';

/**
 * Highlighting.
 *
 * Materials in these assets are SHARED DATABLOCKS: MAT_PIN_GND is one material
 * on four pins. That is a feature for signal-group teaching - setting
 * MAT_PIN_VBUS.emissive lights all four VBUS pins at once, which is exactly
 * what you want.
 *
 * But it is a trap for per-item highlighting: touching the shared material
 * lights the whole group by accident. So per-object highlight ALWAYS clones
 * first, and we keep the original to restore on deselect.
 *
 * We use an emissive bump rather than OutlinePass: on a low-end phone the
 * post-processing pass is not worth the frame budget.
 */
export class Highlighter {
  constructor() {
    /** Object3D -> { original: Material|Material[], clone: Material|Material[] } */
    this.active = new Map();
    this.groupTints = new Map(); // shared material -> saved emissive state
  }

  _cloneFor(mesh) {
    const src = mesh.material;
    if (Array.isArray(src)) {
      const clones = src.map((m) => m.clone());
      return clones;
    }
    return src.clone();
  }

  /** Emissive bump on a CLONED material, so siblings sharing the datablock are untouched. */
  add(object3d, color, intensity = 0.9) {
    object3d.traverse((o) => {
      if (!(o.isMesh || o.isSkinnedMesh) || !o.material) return;
      if (this.active.has(o)) {
        this._applyEmissive(o.material, color, intensity);
        return;
      }
      const original = o.material;
      const clone = this._cloneFor(o);
      o.material = clone;
      this.active.set(o, { original, clone });
      this._applyEmissive(clone, color, intensity);
    });
  }

  _applyEmissive(mat, color, intensity) {
    const list = Array.isArray(mat) ? mat : [mat];
    for (const m of list) {
      if (!m || !m.emissive) continue;
      m.emissive.setHex(color);
      m.emissiveIntensity = intensity;
      m.needsUpdate = true;
    }
  }

  /** Restore the shared originals and dispose the clones. */
  clear(object3d) {
    const targets = [];
    if (object3d) {
      object3d.traverse((o) => { if (this.active.has(o)) targets.push(o); });
    } else {
      targets.push(...this.active.keys());
    }
    for (const o of targets) {
      const rec = this.active.get(o);
      if (!rec) continue;
      o.material = rec.original;
      const clones = Array.isArray(rec.clone) ? rec.clone : [rec.clone];
      for (const c of clones) c.dispose();
      this.active.delete(o);
    }
  }

  // Kept deliberately low. An emissive of ~1.0 on a large part like the shell
  // blows out the whole surface and destroys the metal read, which is the one
  // thing that makes shape legible at this scale.
  select(object3d) { this.add(object3d, SELECT_COLOR, 0.32); }
  hover(object3d) { this.add(object3d, HOVER_COLOR, 0.14); }

  /**
   * Group highlight by SHARED material - deliberately lights every pin that
   * shares the datablock. This is the signal-group teaching mechanic.
   */
  tintSharedMaterial(root, materialName, color, intensity = 1.4) {
    root.traverse((o) => {
      if (!(o.isMesh || o.isSkinnedMesh) || !o.material) return;
      const list = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of list) {
        if (m?.name !== materialName || this.groupTints.has(m)) continue;
        this.groupTints.set(m, {
          emissive: m.emissive ? m.emissive.getHex() : null,
          intensity: m.emissiveIntensity,
        });
        if (m.emissive) {
          m.emissive.setHex(color);
          m.emissiveIntensity = intensity;
          m.needsUpdate = true;
        }
      }
    });
  }

  clearSharedTints() {
    for (const [m, saved] of this.groupTints) {
      if (m.emissive && saved.emissive !== null) m.emissive.setHex(saved.emissive);
      m.emissiveIntensity = saved.intensity ?? 1;
      m.needsUpdate = true;
    }
    this.groupTints.clear();
  }

  disposeAll() {
    this.clear(null);
    this.clearSharedTints();
  }
}

/** Find every material instance with a given name (shared datablocks included). */
export function findMaterials(root, name) {
  const found = new Set();
  root.traverse((o) => {
    if (!o.material) return;
    const list = Array.isArray(o.material) ? o.material : [o.material];
    for (const m of list) if (m?.name === name) found.add(m);
  });
  return [...found];
}
