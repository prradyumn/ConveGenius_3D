import * as THREE from 'three';

/**
 * InstancedMesh conversion - the single biggest perf win available on B02.
 *
 * B02_MAINBOARD has ~445 mesh nodes off ~90 unique meshes: 167 vias, 133
 * passives, 49 BGA balls. GLTFLoader creates a separate THREE.Mesh for each,
 * which is one draw call each even though they share geometry.
 *
 * The catch, and why this is not a one-liner: every one of those nodes is a
 * registered component in components.json and MUST stay clickable and
 * labellable. So we keep a (InstancedMesh, instanceId) -> source node map and
 * teach the picker to resolve through it. Selection highlight uses a cheap
 * proxy mesh placed at the instance's transform, because you cannot set an
 * emissive on one instance of a shared material.
 */

const FAMILY_PATTERNS = [
  /_VIA_\d+$/,
  /_PASSIVE_\d+$/,
  /_PMIC_BALL_\d+_\d+$/,
];

const MIN_FAMILY_SIZE = 12;

function familyKey(mesh) {
  if (!FAMILY_PATTERNS.some((re) => re.test(mesh.name))) return null;
  const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  if (mats.length !== 1) return null;
  // Same geometry + same material = safely instanceable.
  return mesh.geometry.uuid + '|' + mats[0].uuid;
}

export class InstancedFamilies {
  constructor() {
    this.enabled = false;
    /** InstancedMesh -> Object3D[] indexed by instanceId */
    this.sources = new Map();
    this.instanced = [];
    this.originals = [];
    this.proxy = null;
    this.stats = { families: 0, collapsed: 0, drawCallsSaved: 0 };
  }

  /** Build InstancedMesh for each qualifying family. Non-destructive: the
   *  original nodes stay in the graph, just made invisible. */
  build(root) {
    if (this.enabled) return this.stats;

    const families = new Map();
    root.traverse((o) => {
      if (!o.isMesh || o.isSkinnedMesh || o.isInstancedMesh) return;
      const key = familyKey(o);
      if (!key) return;
      if (!families.has(key)) families.set(key, []);
      families.get(key).push(o);
    });

    root.updateWorldMatrix(true, true);

    for (const [, members] of families) {
      if (members.length < MIN_FAMILY_SIZE) continue;

      const proto = members[0];
      const mat = Array.isArray(proto.material) ? proto.material[0] : proto.material;
      const inst = new THREE.InstancedMesh(proto.geometry, mat, members.length);
      inst.name = 'CG_INSTANCED_' + (proto.name || 'family');
      inst.frustumCulled = true;
      inst.instanceMatrix.setUsage(THREE.DynamicDrawUsage);

      const m = new THREE.Matrix4();
      members.forEach((src, i) => {
        // Bake world transform: the InstancedMesh is parented at the root, so
        // instance matrices must be in root space.
        m.copy(src.matrixWorld);
        inst.setMatrixAt(i, m);
        src.visible = false;
        this.originals.push(src);
      });
      inst.instanceMatrix.needsUpdate = true;
      inst.computeBoundingSphere();

      root.add(inst);
      this.sources.set(inst, members);
      this.instanced.push(inst);
      this.stats.families++;
      this.stats.collapsed += members.length;
      this.stats.drawCallsSaved += members.length - 1;
    }

    this.enabled = this.instanced.length > 0;
    return this.stats;
  }

  /** Put the individual meshes back and drop the instanced copies. */
  teardown(root) {
    if (!this.enabled) return;
    for (const inst of this.instanced) {
      root.remove(inst);
      inst.dispose();
    }
    for (const src of this.originals) src.visible = true;
    this.instanced = [];
    this.originals = [];
    this.sources.clear();
    this.clearHighlight(root);
    this.enabled = false;
    this.stats = { families: 0, collapsed: 0, drawCallsSaved: 0 };
  }

  /** Resolve a raycast hit on an InstancedMesh back to the real source node. */
  resolveHit(object, instanceId) {
    if (instanceId == null) return null;
    const members = this.sources.get(object);
    if (!members) return null;
    return members[instanceId] ?? null;
  }

  isInstanced(object) { return this.sources.has(object); }

  /**
   * Highlight one instance with a proxy mesh. You cannot bump the emissive on a
   * single instance of a shared material, so we draw a slightly inflated copy
   * at that instance's transform instead.
   */
  highlightInstance(root, instancedMesh, instanceId, color) {
    this.clearHighlight(root);
    const members = this.sources.get(instancedMesh);
    if (!members || !members[instanceId]) return null;

    const m = new THREE.Matrix4();
    instancedMesh.getMatrixAt(instanceId, m);

    const mat = new THREE.MeshBasicMaterial({
      color, transparent: true, opacity: 0.55, depthWrite: false,
      side: THREE.DoubleSide,
    });
    const proxy = new THREE.Mesh(instancedMesh.geometry, mat);
    proxy.name = 'CG_INSTANCE_HIGHLIGHT';
    proxy.applyMatrix4(m);
    proxy.scale.multiplyScalar(1.18);
    proxy.renderOrder = 999;
    root.add(proxy);
    this.proxy = proxy;
    return members[instanceId];
  }

  clearHighlight(root) {
    if (!this.proxy) return;
    root.remove(this.proxy);
    this.proxy.material.dispose();
    this.proxy = null;
  }

  /** Hide/show a single instance by collapsing its matrix. */
  setInstanceVisible(instancedMesh, instanceId, visible) {
    const members = this.sources.get(instancedMesh);
    if (!members) return false;
    const m = new THREE.Matrix4();
    if (visible) {
      m.copy(members[instanceId].matrixWorld);
    } else {
      m.makeScale(0, 0, 0);
    }
    instancedMesh.setMatrixAt(instanceId, m);
    instancedMesh.instanceMatrix.needsUpdate = true;
    return true;
  }
}
