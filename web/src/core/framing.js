import * as THREE from 'three';
import { FLY_MS, MARGIN_COMPONENT, CAMERA_NEAR } from './config.js';

/**
 * Closed-form zoom-to-object.
 *
 * Do NOT solve this off a bounding SPHERE. A sphere massively over-estimates
 * for flat wide parts - a connector, a ribbon, a board - and frames them far
 * too loose. And do not iterate camera.position.lerp() until it looks right.
 *
 * For a camera at C = target + d*dist looking along -d, for every bounding-box
 * corner P:
 *     a = (P - target) . d           depth along the view axis
 *     u = |(P - target) . right|     lateral offset, independent of dist
 *     v = |(P - target) . up|
 * Fitting requires |u| <= tan(fovH/2)*depth and |v| <= tan(fovV/2)*depth,
 * where depth = dist - a. Solving for dist and taking the worst corner:
 *     dist = max over corners of max( a + u/tanH , a + v/tanV )  x margin
 */
export function solveFraming(camera, object, margin = MARGIN_COMPONENT) {
  const box = new THREE.Box3().setFromObject(object);
  if (box.isEmpty()) return null;

  const target = box.getCenter(new THREE.Vector3());

  const corners = [];
  for (const x of [box.min.x, box.max.x])
    for (const y of [box.min.y, box.max.y])
      for (const z of [box.min.z, box.max.z])
        corners.push(new THREE.Vector3(x, y, z));

  // Keep the current viewing direction so the learner does not lose orientation.
  const d = camera.position.clone().sub(target);
  if (d.lengthSq() < 1e-9) d.set(0, 0.4, 1);
  d.normalize();

  const tanV = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
  const tanH = tanV * camera.aspect;

  const worldUp = new THREE.Vector3(0, 1, 0);
  let right = new THREE.Vector3().crossVectors(d, worldUp);
  if (right.lengthSq() < 1e-9) right.set(1, 0, 0);
  right.normalize();
  const camUp = new THREE.Vector3().crossVectors(right, d).normalize();

  let dist = 0;
  for (const P of corners) {
    const w = P.clone().sub(target);
    const a = w.dot(d);
    dist = Math.max(
      dist,
      a + Math.abs(w.dot(right)) / tanH,
      a + Math.abs(w.dot(camUp)) / tanV,
    );
  }
  dist *= margin;

  // A degenerate (zero-size) object still needs a sane standoff.
  if (!isFinite(dist) || dist <= 0) dist = 1;

  return {
    position: target.clone().add(d.multiplyScalar(dist)),
    target,
    dist,
    radius: box.getSize(new THREE.Vector3()).length() * 0.5,
  };
}

/**
 * Keep the depth range tight around whatever we are actually looking at.
 *
 * A fixed near=0.01 / far=20000 is a depth ratio of 2,000,000, and a 24-bit
 * depth buffer cannot carry that. The symptom is z-fighting between coplanar
 * surfaces - on B02 the solder mask and the board core stripe into each other,
 * which looks like a texture artefact but is not. near must stay tiny for macro
 * zoom on a 9 mm connector, so instead of a constant we derive the range from
 * the current viewing distance and the scene's own size.
 */
export function updateDepthRange(camera, controls, sceneRadius) {
  const d = camera.position.distanceTo(controls.target);
  const r = Math.max(sceneRadius, 0.01);

  // Inside or near the object: near has to be very small. Outside it: pull near
  // up to just in front of the object, which is where the precision comes from.
  const near = Math.max(CAMERA_NEAR, (d - r * 1.25) * 0.5);
  const far = d + r * 4;

  if (Math.abs(camera.near - near) > near * 0.05 || Math.abs(camera.far - far) > far * 0.05) {
    camera.near = near;
    camera.far = Math.max(far, near * 100);
    camera.updateProjectionMatrix();
  }
}

const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);

/**
 * Tween camera position and controls.target together. Animate, never snap.
 * Returns a cancel function; a new flight supersedes the one in progress.
 */
export function flyTo(camera, controls, solved, ms = FLY_MS, onDone) {
  if (!solved) return () => {};

  const fromPos = camera.position.clone();
  const fromTarget = controls.target.clone();
  const t0 = performance.now();
  let cancelled = false;

  // Clamp so a learner cannot push the near plane through the part.
  controls.minDistance = Math.max(solved.radius * 0.35, 0.05);

  function step(now) {
    if (cancelled) return;
    const t = Math.min(1, (now - t0) / ms);
    const e = easeOutCubic(t);
    camera.position.lerpVectors(fromPos, solved.position, e);
    controls.target.lerpVectors(fromTarget, solved.target, e);
    controls.update();
    if (t < 1) requestAnimationFrame(step);
    else if (onDone) onDone();
  }
  requestAnimationFrame(step);

  return () => { cancelled = true; };
}

export function frameObject(camera, controls, object, margin, ms, onDone) {
  return flyTo(camera, controls, solveFraming(camera, object, margin), ms, onDone);
}
