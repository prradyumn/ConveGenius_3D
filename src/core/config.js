/**
 * Central tuning constants.
 *
 * Assets are modelled at TRUE MILLIMETRE SCALE: 1 three.js world unit = 1 mm.
 * The USB-C port is ~9 units across; the mainboard is ~120 units.
 */

// Camera near plane. three.js's default of 0.1 clips straight THROUGH a 9 mm
// connector at macro zoom. This is the single most common setup mistake at
// this scale. Do not raise it.
export const CAMERA_NEAR = 0.01;
export const CAMERA_FAR = 20000;
export const CAMERA_FOV = 45;

// Narrow FOV used by "inspect under magnification", which recurs in 5 of the
// 6 fixes. Magnification is a camera state, not a model.
export const MAGNIFY_FOV = 16;

// Framing margins measured against the real assets (see framing.js).
export const MARGIN_COMPONENT = 1.15; // a single component
export const MARGIN_OVERVIEW = 1.06;  // a whole asset
export const MARGIN_CONTEXT = 1.35;   // a pad on a board: keep surroundings

// Camera flight. A hard cut loses the learner's spatial context.
export const FLY_MS = 600;

// Cap device pixel ratio. On the target device (sub-Rs.12,000 Android over 3G)
// a lower resolution always beats dropped frames.
export const MAX_PIXEL_RATIO = 1.5;

// Frame-rate cap. Rendering as fast as the device will allow pins the CPU/GPU,
// which on a cheap Android means heat, throttling and a flat battery - for a
// scene that is usually static. 30 fps is indistinguishable here and leaves the
// main thread free for the UI. Rendering also stops entirely when the page is
// hidden.
export const TARGET_FPS = 30;

export const BG_TOP = 0x16213a;
export const BG_BOTTOM = 0x0e1420;

export const SELECT_COLOR = 0x39d0ff;
export const HOVER_COLOR = 0xffc65c;
export const FAULT_COLOR = 0xff5470;

// ZIF latch states are TRANSFORMS, not separate meshes.
// HALF_CLOSED is the teaching state: it looks closed but is not, and it is the
// "charges only at one angle" fault - one of the most misdiagnosed in the course.
export const LATCH_STATES = {
  LATCHED: 0,
  HALF_CLOSED: 0.2618, // 15 degrees
  UNLATCHED: 1.9199,   // 110 degrees
};

// Assets. Every figure here was read out of the actual binaries.
//
// `view` is the direction the camera looks FROM on first load, normalised at
// use. It matters more than it sounds: a 120 mm board framed from the default
// three-quarter angle arrives almost edge-on and reads as a green sliver, while
// a 9 mm connector wants a lower, more frontal view so you can see into the
// cavity. Framing then preserves whatever direction the learner orbits to.
export const ASSETS = {
  B05_PORT: {
    file: 'B05_PORT_LOD0.glb',
    label: 'USB-C Charging Port',
    blurb: 'The rigid metal box at the board edge. 24 contacts on a tongue.',
    root: 'B05_PORT',
    view: [0.55, 0.42, 0.72],
    sizeKB: 448,
  },
  B10_B11_IFC: {
    file: 'B10_B11_IFC_LOD0.glb',
    label: 'Flex Cable + IF Connector',
    blurb: 'The flat gold ribbon and the socket it plugs into. Fix 3 lives here.',
    root: 'B10_B11_IFC',
    view: [0.35, 0.62, 0.70],
    sizeKB: 915,
  },
  B40_JOINT: {
    file: 'B40_JOINT_LOD0.glb',
    label: 'Solder Joint States',
    blurb: 'Good / cold / cracked / bridged / dry. One camera, one exposure.',
    root: null,
    view: [0.30, 0.55, 0.78],
    sizeKB: 1201,
  },
  B02_MAINBOARD: {
    file: 'B02_MAINBOARD_LOD0.glb',
    label: 'Mainboard',
    blurb: 'Port at the edge, then IFC, then Charger IC, then battery connector.',
    root: 'B02_MAINBOARD',
    view: [0.30, 0.88, 0.38],
    sizeKB: 1326,
  },
  B28_HOTAIR: {
    file: 'B28_HOTAIR_LOD0.glb',
    label: 'Hot Air Rework Station',
    blurb: 'Aimable handpiece. The airflow axis is a real, checkable condition.',
    root: 'B28_HOTAIR',
    view: [0.62, 0.40, 0.68],
    sizeKB: 262,
  },
  B02_ASSEMBLY: {
    file: 'B02_ASSEMBLY_LOD0.glb',
    label: 'Full Assembly',
    blurb: 'Port -> flex -> IFC socket, in situ on the board. 14.8 mm flex span.',
    root: null,
    view: [0.32, 0.86, 0.40],
    sizeKB: 1854,
  },
};

export const DEFAULT_ASSET = 'B05_PORT';
