import * as THREE from 'three';

/**
 * Runtime-generated soft-glow textures.
 *
 * Everything here is a CanvasTexture built on the fly, the same trick
 * scene.js already uses for the background gradient - zero bytes downloaded,
 * so these are free relative to the asset budget.
 */
function makeRadialTexture(stops, size = 128) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const ctx = c.getContext('2d');
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  for (const [offset, color] of stops) g.addColorStop(offset, color);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

/**
 * A soft dark ellipse that sits under the loaded part. There is no floor in
 * this scene, so without this every asset reads as floating in the gradient
 * void - this is the single cheapest fix for that.
 *
 * The scene background is already very dark (#0e1420), so a shallow linear
 * fade (0.5 -> 0 alpha) was nearly invisible - measured under 10/255 RGB
 * difference from bare background. A denser core with a sharper falloff
 * (rather than more overall darkness) reads as a distinct contact pool
 * instead of a barely-there tint.
 */
export function createGroundShadow() {
  const tex = makeRadialTexture([
    [0, 'rgba(0,0,0,0.92)'],
    [0.35, 'rgba(0,0,0,0.75)'],
    [0.7, 'rgba(0,0,0,0.28)'],
    [1, 'rgba(0,0,0,0)'],
  ]);
  const mat = new THREE.MeshBasicMaterial({
    map: tex, transparent: true, depthWrite: false, toneMapped: false,
  });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), mat);
  mesh.rotation.x = -Math.PI / 2;
  mesh.renderOrder = -1;
  mesh.visible = false;
  mesh.matrixAutoUpdate = true;
  return mesh;
}

/** Fit the shadow ellipse under a freshly loaded asset's bounding box. */
export function fitGroundShadow(shadowMesh, box) {
  if (!shadowMesh) return;
  if (!box || box.isEmpty()) { shadowMesh.visible = false; return; }
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  // Bigger than the object's own footprint on purpose: at anything but a
  // top-down view, a shadow sized to match the object is mostly hidden
  // behind the object itself (the camera looks down at an angle, so the
  // ground plane right under the part falls behind its own silhouette).
  // The margin has to be generous enough to still peek out at the object's
  // base from a typical 30-40 degree orbit.
  const footprint = Math.max(size.x, size.z, 0.01);
  shadowMesh.scale.set(footprint * 1.9, footprint * 1.9, 1);
  shadowMesh.position.set(center.x, box.min.y - footprint * 0.01, center.z);
  shadowMesh.visible = true;
}

/**
 * Additive halo sprite: a cheap stand-in for a bloom pass on the one or two
 * runtime-emissive hotspots (nozzle tip, solder joint). Real post-processing
 * bloom was deliberately ruled out for the target device (see scene.js); this
 * is a single extra sprite draw, not a full-screen pass.
 */
export function createGlowSprite(hex = 0xffffff) {
  const tex = makeRadialTexture([[0, 'rgba(255,255,255,1)'], [1, 'rgba(255,255,255,0)']]);
  const mat = new THREE.SpriteMaterial({
    map: tex, color: hex, transparent: true, depthWrite: false, depthTest: false,
    blending: THREE.AdditiveBlending, opacity: 0, toneMapped: false,
  });
  const sprite = new THREE.Sprite(mat);
  sprite.renderOrder = 10;
  sprite.visible = false;
  return sprite;
}

/** Drive a halo sprite's visibility/size/opacity from a 0..1 intensity. */
export function setGlow(sprite, worldPos, weight, baseScale = 1) {
  if (!sprite) return;
  if (weight <= 0.001) { sprite.visible = false; return; }
  sprite.visible = true;
  sprite.position.copy(worldPos);
  sprite.material.opacity = Math.min(0.85, weight);
  const s = baseScale * (0.6 + weight * 0.9);
  sprite.scale.set(s, s, 1);
}
