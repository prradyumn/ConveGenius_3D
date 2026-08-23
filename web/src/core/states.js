import * as THREE from 'three';
import { LATCH_STATES } from './config.js';

/**
 * State toggling.
 *
 * Every state ships VISIBLE in the file, because glTF has no per-node
 * visibility and the Blender exporter DROPS render-hidden objects. So the
 * runtime owns visibility, and must hide all but the default on load - or all
 * five B40 solder joints render on top of each other.
 *
 * Note on the manifest: components.json names three state groups that are NOT
 * nodes in any binary - B05_STATE_BENT_PINS, B10_STATE_PADS_WORN and
 * B10_STATE_TORN. They are logical groups. The real meshes are listed below,
 * verified against the glb node lists.
 */
const LOGICAL_GROUPS = {
  B05_STATE_BENT_PINS: ['B05_BENT_PIN_A05', 'B05_BENT_PIN_A06', 'B05_BENT_PIN_A07'],
  B10_STATE_PADS_WORN: [
    'B10_WORNPAD_04', 'B10_WORNPAD_05', 'B10_WORNPAD_06',
    'B10_WORNPAD_07', 'B10_WORNPAD_08',
  ],
  B10_STATE_TORN: ['B10_TEAR'],
};

/** Human copy for the assessment UI. */
export const STATE_COPY = {
  B40_STATE_GOOD: {
    label: 'Good',
    teaching: 'Concave and shiny, the fillet sweeping smoothly from pad to lead, reaching full pad width. The solder WANTED to stick.',
  },
  B40_STATE_COLD: {
    label: 'Cold',
    teaching: 'Convex and dull - balled up ON the pad instead of flowing into it. A lot of what looks like a dead Charger IC is just a cold joint underneath.',
  },
  B40_STATE_CRACKED: {
    label: 'Cracked',
    teaching: 'A hairline fracture between fillet and lead. This is the "charges only at one angle" fault.',
  },
  B40_STATE_BRIDGED: {
    label: 'Bridged',
    teaching: 'A well-formed joint in the WRONG PLACE, shorting two pads. A bridge is not a bad-looking joint - it is a good joint somewhere it should not be.',
  },
  B40_STATE_DRY: {
    label: 'Dry / starved',
    teaching: 'Not enough solder, pad partly bare, no fillet. What an unwicked or under-soldered repair looks like.',
  },
  LATCHED: { label: 'Latched', teaching: 'Correct. The flap is fully down and clamping the flex.' },
  HALF_CLOSED: {
    label: 'Half closed',
    teaching: 'THE TEACHING STATE. It looks closed but it is not. This is "charges only if you hold the cable at just the right angle" - one of the most misdiagnosed faults in the course.',
  },
  UNLATCHED: { label: 'Unlatched', teaching: 'Fully open. The flex can be inserted or withdrawn with zero force.' },
  B05_GASKET: { label: 'Waterproof gasket', teaching: 'Water-resistant models only. Rubber seal keeping moisture off the pins.' },
  B05_STATE_BENT_PINS: {
    label: 'Bent contacts',
    teaching: 'Contacts visibly deflected, one touching a neighbour. This is what makes Fix 1 vs Fix 2 branch: dust, or physical damage?',
  },
  B10_STATE_PADS_WORN: {
    label: 'Worn pads',
    teaching: 'Gold plating rubbed through to base copper. Cleaning or resoldering will NOT fix physical wear - this is Fix 3\'s trigger.',
  },
  B10_STATE_TORN: {
    label: 'Torn film',
    teaching: 'The polyimide cracked at the high-flex point near the port. Repeated bending there is a common failure point.',
  },
  B11_SOLDER_CRACK_L: {
    label: 'Cracked anchor',
    teaching: 'A hairline crack in the left anchor, socket slightly lifted at that end.',
  },
};

export class StateMachine {
  constructor(root, manifest, assetKey) {
    this.root = root;
    this.assetKey = assetKey;
    this.spec = manifest.states ?? {};

    this.exclusiveGroups = new Map(); // groupName -> { members[], current }
    this.optionalFlags = new Map();   // stateName -> bool
    this.latch = 'LATCHED';
    this.flap = root.getObjectByName('B11_FLAP');

    this._applyDefaults();
  }

  _nodesFor(stateName) {
    if (LOGICAL_GROUPS[stateName]) {
      return LOGICAL_GROUPS[stateName]
        .map((n) => this.root.getObjectByName(n))
        .filter(Boolean);
    }
    const o = this.root.getObjectByName(stateName);
    return o ? [o] : [];
  }

  _setVisible(stateName, visible) {
    const nodes = this._nodesFor(stateName);
    for (const n of nodes) n.visible = visible;
    return nodes.length > 0;
  }

  _applyDefaults() {
    for (const [groupName, def] of Object.entries(this.spec)) {
      // Exclusive group (B40's five joints): show exactly one.
      if (Array.isArray(def.group)) {
        const members = def.group.filter((m) => this._nodesFor(m).length > 0);
        if (!members.length) continue;
        for (const m of members) this._setVisible(m, false);
        const initial = members.includes(def.default) ? def.default : members[0];
        this._setVisible(initial, true);
        this.exclusiveGroups.set(groupName, { members, current: initial });
        continue;
      }

      // Optional overlays and damage variants: default to off unless listed.
      if (Array.isArray(def.optional)) {
        const on = new Set(def.default ?? []);
        for (const m of def.optional) {
          if (!this._nodesFor(m).length) continue;
          const want = on.has(m);
          this._setVisible(m, want);
          this.optionalFlags.set(m, want);
        }
        continue;
      }

      // Transform-driven state (the ZIF latch).
      if (def.node && def.property && def.values) {
        const initial = def.default in def.values ? def.default : Object.keys(def.values)[0];
        this.setLatch(initial);
      }
    }

    // Logical damage groups that components.json lists but whose group node
    // does not exist: make sure their member meshes start hidden.
    for (const g of Object.keys(LOGICAL_GROUPS)) {
      if (!this.optionalFlags.has(g) && this._nodesFor(g).length) {
        this._setVisible(g, false);
        this.optionalFlags.set(g, false);
      }
    }
  }

  /** Exclusive: show one member of a group, hide the rest. */
  setExclusive(groupName, member) {
    const g = this.exclusiveGroups.get(groupName);
    if (!g || !g.members.includes(member)) return false;
    for (const m of g.members) this._setVisible(m, m === member);
    g.current = member;
    return true;
  }

  currentExclusive(groupName) {
    return this.exclusiveGroups.get(groupName)?.current ?? null;
  }

  setOptional(stateName, on) {
    if (!this._nodesFor(stateName).length) return false;
    this._setVisible(stateName, !!on);
    this.optionalFlags.set(stateName, !!on);
    return true;
  }

  toggleOptional(stateName) {
    return this.setOptional(stateName, !this.optionalFlags.get(stateName));
  }

  isOn(stateName) { return !!this.optionalFlags.get(stateName); }

  /** ZIF latch: a TRANSFORM, not a separate mesh. */
  setLatch(stateName) {
    if (!this.flap || !(stateName in LATCH_STATES)) return false;
    this.flap.rotation.y = LATCH_STATES[stateName];
    this.latch = stateName;
    return true;
  }

  latchState() { return this.latch; }

  availableExclusiveGroups() { return [...this.exclusiveGroups.keys()]; }
  availableOptional() { return [...this.optionalFlags.keys()]; }
  hasLatch() { return !!this.flap; }
}
