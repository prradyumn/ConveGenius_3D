import * as THREE from 'three';
import { findMaterials } from './materials.js';

/**
 * Clip playback.
 *
 * Two things glTF does NOT carry, which the runtime therefore owns:
 *  1. Animated material properties. The solder MELT GEOMETRY is real (morph
 *     targets) but the GLOW is not in the file - it must be an emissive lerp
 *     driven alongside the clip. Same for the B28 nozzle heat ramp.
 *  2. Per-node visibility (see states.js).
 */
export class AnimController {
  constructor(root, clips) {
    this.root = root;
    this.mixer = new THREE.AnimationMixer(root);
    this.actions = new Map();
    this.clipInfo = new Map();
    this.playing = null;
    this._onFinish = null;

    for (const clip of clips) {
      const action = this.mixer.clipAction(clip);
      action.setLoop(THREE.LoopOnce, 1);
      // Hold the last frame - a step demo must not snap back.
      action.clampWhenFinished = true;
      this.actions.set(clip.name, action);
      this.clipInfo.set(clip.name, { duration: clip.duration, tracks: clip.tracks.length });
    }

    this.mixer.addEventListener('finished', (e) => {
      const name = [...this.actions.entries()].find(([, a]) => a === e.action)?.[0];
      if (this.playing === name) this.playing = null;
      if (this._onFinish) this._onFinish(name);
    });

    // Runtime-driven glow rigs, resolved lazily per asset.
    this.solderMats = [
      ...findMaterials(root, 'MAT_SOLDER_ANCHOR'),
      ...findMaterials(root, 'MAT_SOLDER_GOOD'),
    ];
    this.nozzleMats = findMaterials(root, 'MAT_NOZZLE_GLOW');
    this._solderBase = this.solderMats.map((m) => ({
      m, hex: m.emissive ? m.emissive.getHex() : 0x000000, i: m.emissiveIntensity ?? 1,
    }));
    this._nozzleBase = this.nozzleMats.map((m) => ({
      m, hex: m.emissive ? m.emissive.getHex() : 0x000000, i: m.emissiveIntensity ?? 1,
    }));

    this.solderMeshes = ['B11_SOLDER_L', 'B11_SOLDER_R']
      .map((n) => root.getObjectByName(n))
      .filter((o) => o && o.morphTargetInfluences);
  }

  onFinish(fn) { this._onFinish = fn; return this; }

  names() { return [...this.actions.keys()]; }
  duration(name) { return this.clipInfo.get(name)?.duration ?? 0; }

  /** Play forward from the start. reverse=true plays backward from the end -
   *  which is how ANIM_B05_EXPLODE assembles the port again. */
  play(name, { reverse = false, speed = 1 } = {}) {
    const action = this.actions.get(name);
    if (!action) return false;
    this.stopAll();
    action.reset();
    action.timeScale = reverse ? -Math.abs(speed) : Math.abs(speed);
    action.time = reverse ? action.getClip().duration : 0;
    action.paused = false;
    action.play();
    this.playing = name;
    return true;
  }

  pause() { if (this.playing) this.actions.get(this.playing).paused = true; }
  resume() { if (this.playing) this.actions.get(this.playing).paused = false; }

  stopAll() {
    for (const a of this.actions.values()) a.stop();
    this.playing = null;
  }

  /** Scrub a clip to a normalised 0..1 position - this is how VO timing DRIVES
   *  the playhead rather than running alongside it. */
  scrub(name, t01) {
    const action = this.actions.get(name);
    if (!action) return;
    this.stopAll();
    action.reset();
    action.play();
    action.paused = true;
    action.time = THREE.MathUtils.clamp(t01, 0, 1) * action.getClip().duration;
    this.playing = null;
    this.mixer.update(0);
    this._syncRuntimeGlow();
  }

  progress() {
    if (!this.playing) return 0;
    const a = this.actions.get(this.playing);
    const d = a.getClip().duration || 1;
    return THREE.MathUtils.clamp(a.time / d, 0, 1);
  }

  /** Directly set the melt without a clip: 0 = solid fillet, 1 = molten. */
  setMelt(weight) {
    const w = THREE.MathUtils.clamp(weight, 0, 1);
    for (const mesh of this.solderMeshes) {
      for (let i = 0; i < mesh.morphTargetInfluences.length; i++) {
        mesh.morphTargetInfluences[i] = w;
      }
    }
    this._applySolderGlow(w);
    return w;
  }

  /** Nozzle heat ramp: also runtime-side, for the same reason. */
  setNozzleHeat(t) {
    const w = THREE.MathUtils.clamp(t, 0, 1);
    for (const { m, hex, i } of this._nozzleBase) {
      if (!m.emissive) continue;
      m.emissive.setHex(w > 0 ? 0xff5a1e : hex);
      m.emissiveIntensity = THREE.MathUtils.lerp(i, 3.2, w);
      m.needsUpdate = true;
    }
    return w;
  }

  _applySolderGlow(w) {
    for (const { m, hex, i } of this._solderBase) {
      if (!m.emissive) continue;
      if (w <= 0.001) {
        m.emissive.setHex(hex);
        m.emissiveIntensity = i;
      } else {
        m.emissive.setHex(0xff6a1e);
        m.emissiveIntensity = THREE.MathUtils.lerp(0, 2.5, w);
      }
      m.needsUpdate = true;
    }
  }

  /** Keep the runtime glow in step with whatever the mixer just wrote. */
  _syncRuntimeGlow() {
    if (this.solderMeshes.length) {
      const w = this.solderMeshes[0].morphTargetInfluences?.[0] ?? 0;
      this._applySolderGlow(w);
    }
  }

  update(dt) {
    this.mixer.update(dt);
    // The melt clip drives morph weights; the emissive must follow them every
    // frame because the file cannot carry it.
    if (this.playing === 'ANIM_B11_SOLDER_MELT' || this.solderMeshes.length) {
      this._syncRuntimeGlow();
    }
  }

  dispose() {
    this.stopAll();
    this.mixer.uncacheRoot(this.root);
  }
}
