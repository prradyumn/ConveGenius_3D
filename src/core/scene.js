import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { CSS2DRenderer } from 'three/examples/jsm/renderers/CSS2DRenderer.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import {
  CAMERA_NEAR, CAMERA_FAR, CAMERA_FOV, MAX_PIXEL_RATIO, BG_TOP, BG_BOTTOM,
} from './config.js';
import { createGroundShadow } from './glow.js';

/**
 * Renderer / camera / lights / environment.
 *
 * The two things that matter most here:
 *  - near = 0.01, because these assets are millimetre-scale (config.js).
 *  - a real environment map, because METALS NEED SOMETHING TO REFLECT. In a
 *    black environment a physically correct steel shader renders as a black
 *    blob, and no amount of material tweaking fixes it.
 */
export function createStage(container) {
  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    powerPreference: 'high-performance',
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, MAX_PIXEL_RATIO));
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  // One directional shadow map at most. On the target device, none is often better.
  renderer.shadowMap.enabled = false;
  container.appendChild(renderer.domElement);

  // CSS2D overlay for labels. HTML labels, not sprite text: sprite text is
  // illegible at 720p on a 5-inch screen, and HTML gives us free multilingual
  // text, screen-reader access and reflow.
  const labelRenderer = new CSS2DRenderer();
  labelRenderer.setSize(container.clientWidth, container.clientHeight);
  labelRenderer.domElement.className = 'label-layer';
  container.appendChild(labelRenderer.domElement);

  const scene = new THREE.Scene();
  scene.background = makeGradientBackground();

  const camera = new THREE.PerspectiveCamera(
    CAMERA_FOV,
    container.clientWidth / container.clientHeight,
    CAMERA_NEAR,
    CAMERA_FAR,
  );
  camera.position.set(18, 14, 26);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.rotateSpeed = 0.75;
  controls.zoomSpeed = 0.9;
  controls.panSpeed = 0.7;
  controls.minDistance = 0.05;
  controls.maxDistance = 4000;

  // Environment: RoomEnvironment through PMREM. Small, procedural, no download,
  // and it gives the steel and gold something to catch.
  const pmrem = new THREE.PMREMGenerator(renderer);
  pmrem.compileEquirectangularShader();
  const envRT = pmrem.fromScene(new RoomEnvironment(), 0.04);
  scene.environment = envRT.texture;
  pmrem.dispose();

  addLights(scene);

  // A soft dark ellipse under the part - the only grounding cue in a scene
  // with no floor. See glow.js.
  const groundShadow = createGroundShadow();
  scene.add(groundShadow);

  return {
    renderer, labelRenderer, scene, camera, controls, groundShadow,
  };
}

/** One large key + fill + rim. The soft reflection running along a metal edge
 *  is what makes shape readable at this scale. */
function addLights(scene) {
  const key = new THREE.DirectionalLight(0xffffff, 2.1);
  key.position.set(40, 60, 35);
  scene.add(key);

  const fill = new THREE.DirectionalLight(0xbfd4ff, 0.75);
  fill.position.set(-45, 18, 25);
  scene.add(fill);

  // Rim from behind: separates the part from the dark background.
  const rim = new THREE.DirectionalLight(0xffe6bf, 1.0);
  rim.position.set(-12, 22, -48);
  scene.add(rim);

  scene.add(new THREE.HemisphereLight(0x8fb2ff, 0x141a26, 0.45));
  scene.add(new THREE.AmbientLight(0xffffff, 0.18));
}

function makeGradientBackground() {
  const c = document.createElement('canvas');
  c.width = 4;
  c.height = 256;
  const ctx = c.getContext('2d');
  const g = ctx.createLinearGradient(0, 0, 0, 256);
  g.addColorStop(0, '#' + BG_TOP.toString(16).padStart(6, '0'));
  g.addColorStop(1, '#' + BG_BOTTOM.toString(16).padStart(6, '0'));
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 4, 256);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

export function attachResize(container, { renderer, labelRenderer, camera }) {
  const onResize = () => {
    const w = container.clientWidth;
    const h = container.clientHeight;
    if (!w || !h) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, MAX_PIXEL_RATIO));
    renderer.setSize(w, h);
    labelRenderer.setSize(w, h);
  };
  window.addEventListener('resize', onResize);
  return onResize;
}
