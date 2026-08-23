import * as THREE from 'three';
import { isIgnorable } from './loader.js';

/**
 * The registry binds components.json (the label API) to the loaded glTF nodes.
 *
 * Rule: labels and teaching notes ALWAYS come from components.json. Never
 * hard-code a label in a component, and never invent one at runtime.
 */
export class Registry {
  constructor(manifest, assetKey, root) {
    this.assetKey = assetKey;
    this.root = root;
    this.asset = manifest.assets?.[assetKey] ?? { components: {} };
    this.spec = this.asset.components ?? {};
    this.statesSpec = manifest.states ?? {};
    this.pinGroups = manifest.pinGroups ?? {};

    /** name -> { name, node, label, category, zoomMargin, note, anchor, row, index, signal, group } */
    this.entries = new Map();
    /** Object3D -> entry, for fast raycast resolution */
    this.byObject = new Map();

    this.anchors = new Map();
    this.missingAnchors = new Set();
    this.suspectAnchors = [];
    this.unmatchedSpec = [];
    this.unregisteredMeshes = [];

    this._index();
  }

  _index() {
    const nodesByName = new Map();
    this.root.traverse((o) => {
      if (o.name) {
        // glTF node names are unique per file in these assets; first wins if not.
        if (!nodesByName.has(o.name)) nodesByName.set(o.name, o);
        if (o.name.includes('_ANCHOR_')) this.anchors.set(o.name, o);
      }
    });

    for (const [name, meta] of Object.entries(this.spec)) {
      const node = nodesByName.get(name);
      if (!node) {
        this.unmatchedSpec.push(name);
        continue;
      }

      let anchorNode = null;
      if (meta.anchor) {
        anchorNode = this.anchors.get(meta.anchor) ?? null;
        if (!anchorNode) this.missingAnchors.add(meta.anchor);
      }

      const entry = {
        name,
        node,
        label: meta.label ?? name,
        category: meta.category ?? 'other',
        zoomMargin: meta.zoomMargin ?? 1.15,
        note: meta.note ?? '',
        anchorName: meta.anchor ?? null,
        anchorNode,
        anchorRejected: null,
        row: meta.row ?? null,
        index: meta.index ?? null,
        signal: meta.signal ?? null,
        group: meta.group ?? null,
      };

      this.entries.set(name, entry);

      // Map this node and all of its descendants to the entry, so a click on an
      // unregistered child mesh resolves to its nearest registered ancestor.
      node.traverse((o) => {
        if (!this.byObject.has(o)) this.byObject.set(o, entry);
      });
    }

    // Anything renderable with no registered ancestor: worth reporting, because
    // acceptance requires every node in components.json to be clickable.
    this.root.traverse((o) => {
      if ((o.isMesh || o.isSkinnedMesh) && !this.byObject.has(o) && !isIgnorable(o.name)) {
        this.unregisteredMeshes.push(o.name || '(unnamed)');
      }
    });

    this._vetAnchorDistances();
  }

  /**
   * Reject anchors that are nowhere near the part they label.
   *
   * B02_ASSEMBLY needs this. Its components.json anchors 443 of 500 entries to
   * B05_ANCHOR_B02 and 18 to B05_ANCHOR_B11 - which are the anchors for USB-C
   * pins B2 and B11. The generator looks to have built "B05_ANCHOR_" + the first
   * token of the node name, so every B02_* part got B05_ANCHOR_B02. Because
   * those names collide with real pin anchors they resolve silently, and every
   * leader line would converge on one spot on the connector's pin row instead of
   * pointing at its part. B02_MAINBOARD, by contrast, anchors correctly to
   * B02_ANCHOR_*.
   *
   * A missing anchor is loud; a wrong one is silent. So measure it: if the
   * anchor sits far outside the component's own bounds, drop it and use the
   * centroid, which is always correct if less artful.
   */
  _vetAnchorDistances() {
    const box = new THREE.Box3();
    const center = new THREE.Vector3();
    const anchorPos = new THREE.Vector3();

    for (const entry of this.entries.values()) {
      if (!entry.anchorNode) continue;

      box.setFromObject(entry.node);
      if (box.isEmpty()) continue;
      box.getCenter(center);

      const diagonal = box.getSize(new THREE.Vector3()).length();
      entry.anchorNode.getWorldPosition(anchorPos);

      // Distance from the box itself, so a legitimately offset callout anchor
      // sitting just outside a small part is not punished.
      const surfaceDistance = box.distanceToPoint(anchorPos);
      const tolerance = Math.max(diagonal * 2, 1.5); // mm

      if (surfaceDistance > tolerance) {
        this.suspectAnchors.push({
          component: entry.name,
          anchor: entry.anchorName,
          distance: +surfaceDistance.toFixed(2),
          tolerance: +tolerance.toFixed(2),
        });
        entry.anchorRejected = entry.anchorName;
        entry.anchorNode = null; // anchorPosition() now falls back to centroid
      }
    }
  }

  get(name) { return this.entries.get(name) ?? null; }

  /** Resolve a raycast hit to the nearest REGISTERED ancestor. */
  resolve(object) {
    let o = object;
    while (o) {
      const hit = this.byObject.get(o);
      if (hit) return hit;
      o = o.parent;
    }
    return null;
  }

  list() { return [...this.entries.values()]; }

  byCategory() {
    const map = new Map();
    for (const e of this.entries.values()) {
      if (!map.has(e.category)) map.set(e.category, []);
      map.get(e.category).push(e);
    }
    for (const arr of map.values()) arr.sort((a, b) => a.label.localeCompare(b.label));
    return map;
  }

  /** Search by label, node name or signal - drives the component finder. */
  search(query) {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    const out = [];
    for (const e of this.entries.values()) {
      if (
        e.label.toLowerCase().includes(q) ||
        e.name.toLowerCase().includes(q) ||
        (e.signal && e.signal.toLowerCase().includes(q))
      ) out.push(e);
    }
    return out.slice(0, 40);
  }

  /**
   * Where a leader line should attach. Prefer the authored anchor empty;
   * fall back to the node's own world-space centroid.
   */
  anchorPosition(entry, out = new THREE.Vector3()) {
    if (entry.anchorNode) return entry.anchorNode.getWorldPosition(out);
    const box = new THREE.Box3().setFromObject(entry.node);
    if (box.isEmpty()) return entry.node.getWorldPosition(out);
    return box.getCenter(out);
  }

  /** Every pin in a signal group (GND, VBUS, CC, DATA, SBU, SS). */
  pinsInGroup(group) {
    return this.list().filter((e) => e.group === group);
  }

  diagnostics() {
    // Group the rejected anchors by anchor name - the interesting signal is
    // "one anchor is being used by 443 unrelated components", not the list.
    const byAnchor = new Map();
    for (const s of this.suspectAnchors) {
      if (!byAnchor.has(s.anchor)) byAnchor.set(s.anchor, { anchor: s.anchor, count: 0, maxDistance: 0 });
      const rec = byAnchor.get(s.anchor);
      rec.count++;
      rec.maxDistance = Math.max(rec.maxDistance, s.distance);
    }

    return {
      asset: this.assetKey,
      specEntries: Object.keys(this.spec).length,
      bound: this.entries.size,
      unmatchedSpec: this.unmatchedSpec.length,
      unmatchedSpecNames: this.unmatchedSpec.slice(0, 12),
      missingAnchors: [...this.missingAnchors],
      suspectAnchors: this.suspectAnchors.length,
      suspectAnchorGroups: [...byAnchor.values()].sort((a, b) => b.count - a.count),
      unregisteredMeshes: this.unregisteredMeshes.length,
      unregisteredMeshNames: this.unregisteredMeshes.slice(0, 12),
    };
  }
}
