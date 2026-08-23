import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';

const GLB_BASE = 'assets/glb/';
const DATA_BASE = 'assets/data/';

let gltfLoader = null;
let dracoLoader = null;

function getLoader() {
  if (gltfLoader) return gltfLoader;
  // Draco is already applied to every asset (KHR_draco_mesh_compression is in
  // extensionsRequired), so the decoder is mandatory, not optional.
  dracoLoader = new DRACOLoader();
  dracoLoader.setDecoderPath('draco/gltf/');
  dracoLoader.setDecoderConfig({ type: 'wasm' });
  gltfLoader = new GLTFLoader();
  gltfLoader.setDRACOLoader(dracoLoader);
  return gltfLoader;
}

export function disposeLoaders() {
  if (dracoLoader) dracoLoader.dispose();
  dracoLoader = null;
  gltfLoader = null;
}

export async function loadComponentsManifest() {
  const res = await fetch(DATA_BASE + 'components.json');
  if (!res.ok) throw new Error('components.json failed to load: ' + res.status);
  return res.json();
}

export function loadAsset(file, onProgress) {
  return new Promise((resolve, reject) => {
    getLoader().load(
      GLB_BASE + file,
      (gltf) => resolve(gltf),
      (evt) => {
        if (onProgress && evt.total) onProgress(evt.loaded / evt.total);
      },
      (err) => reject(err),
    );
  });
}

/**
 * Anchors arrive as THREE.Object3D with no geometry. They must never be
 * raycast-pickable and must never be framed as if they had size.
 */
export function isAnchor(name) {
  return !!name && name.includes('_ANCHOR_');
}

export function isIgnorable(name) {
  if (!name) return true;
  if (isAnchor(name)) return true;
  if (name.startsWith('CG_')) return true;
  // neutral_bone is a Blender glTF exporter artefact, not a real bone.
  if (name === 'neutral_bone') return true;
  return false;
}

/** Collect every anchor empty in the loaded scene, by name. */
export function collectAnchors(root) {
  const anchors = new Map();
  root.traverse((o) => {
    if (isAnchor(o.name)) anchors.set(o.name, o);
  });
  return anchors;
}

/** Free GPU memory when switching assets. */
export function disposeScene(root) {
  if (!root) return;
  root.traverse((o) => {
    if (o.isMesh || o.isSkinnedMesh) {
      o.geometry?.dispose();
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of mats) {
        if (!m) continue;
        for (const key of Object.keys(m)) {
          const v = m[key];
          if (v && v.isTexture) v.dispose();
        }
        m.dispose();
      }
    }
  });
}
