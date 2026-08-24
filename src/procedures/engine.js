import * as THREE from 'three';

/**
 * Procedure gating.
 *
 * This is what makes the simulation an assessment rather than a video.
 *
 * Several BC.3 steps are ORDER-CRITICAL and the wrong order must FAIL, not
 * silently pass:
 *   - Fix 2: solder the shield/ground tabs FIRST, then the smaller signal pins
 *   - Fix 3: solder ONE CORNER PAD first to hold the ribbon, then the rest
 *   - Fixes 2/3/5/6: disconnect the battery FIRST, before any heat
 *
 * Each fix is an explicit state machine: an ordered step list, a required tool,
 * a required target node and a validator per step. On a wrong action we explain
 * WHY in the voiceover's own language, then let the learner retry.
 */

export class ProcedureRunner {
  constructor(procedure, ctx) {
    this.procedure = procedure;
    this.ctx = ctx;          // { registry, states, anim, tools, scene }
    this.stepIndex = 0;
    this.completed = [];
    this.faults = [];        // every wrong action, for telemetry / scoring
    this.done = false;
    this.flags = new Set();  // e.g. BATTERY_DISCONNECTED
    this._listeners = new Set();
  }

  onChange(fn) { this._listeners.add(fn); return () => this._listeners.delete(fn); }
  _emit(evt) { for (const fn of this._listeners) fn(evt, this); }

  get step() { return this.procedure.steps[this.stepIndex] ?? null; }
  get total() { return this.procedure.steps.length; }

  reset() {
    this.stepIndex = 0;
    this.completed = [];
    this.faults = [];
    this.done = false;
    this.flags.clear();
    if (this.procedure.setup) this.procedure.setup(this.ctx, this);
    this._emit({ type: 'reset' });
  }

  /**
   * Submit a learner action.
   * action = { verb, target, tool, value }
   * Returns { ok, message, severity }.
   */
  submit(action) {
    if (this.done) return { ok: false, message: 'This fix is already complete.', severity: 'info' };

    const step = this.step;
    if (!step) return { ok: false, message: 'No active step.', severity: 'info' };

    // 1. A hard prerequisite that is not met is always the more useful error -
    //    check it before anything about the current step.
    for (const pre of step.requires ?? []) {
      if (!this.flags.has(pre.flag)) {
        const fault = { step: step.id, action, reason: pre.message, kind: 'prerequisite' };
        this.faults.push(fault);
        this._emit({ type: 'fault', fault });
        return { ok: false, message: pre.message, severity: 'danger' };
      }
    }

    // 2. Wrong tool.
    if (step.tool && action.tool !== step.tool) {
      const msg = step.wrongTool ??
        `That is not the right tool for this step. This step needs: ${step.tool}.`;
      const fault = { step: step.id, action, reason: msg, kind: 'tool' };
      this.faults.push(fault);
      this._emit({ type: 'fault', fault });
      return { ok: false, message: msg, severity: 'warn' };
    }

    // 3. Step-specific validation - this is where order-critical rules live.
    const verdict = step.validate
      ? step.validate(action, this.ctx, this)
      : { ok: action.verb === step.verb && (!step.target || action.target === step.target) };

    if (!verdict.ok) {
      const msg = verdict.message ?? step.hint ?? 'Not quite. Look again at what this step asks for.';
      const fault = { step: step.id, action, reason: msg, kind: verdict.kind ?? 'order' };
      this.faults.push(fault);
      this._emit({ type: 'fault', fault });
      return { ok: false, message: msg, severity: verdict.severity ?? 'danger' };
    }

    // 4. Success. Some steps only complete once repeated N times (e.g. the
    //    remaining pads after the first corner is tacked).
    step._hits = (step._hits ?? 0) + 1;
    const need = step.repeat ?? 1;
    if (step._hits < need) {
      this._emit({ type: 'progress', step, hits: step._hits, need });
      return {
        ok: true,
        message: verdict.message ?? `Good. ${need - step._hits} to go on this step.`,
        severity: 'ok',
        partial: true,
      };
    }

    if (step.grants) for (const f of step.grants) this.flags.add(f);
    if (step.onComplete) step.onComplete(this.ctx, this);

    this.completed.push(step.id);
    step._hits = 0;
    this.stepIndex++;

    if (this.stepIndex >= this.total) {
      this.done = true;
      this._emit({ type: 'done' });
      return {
        ok: true,
        message: verdict.message ?? this.procedure.completion ?? 'Fix complete.',
        severity: 'ok',
        done: true,
      };
    }

    this._emit({ type: 'advance', step: this.step });
    return { ok: true, message: verdict.message ?? 'Correct.', severity: 'ok' };
  }

  /** Score: steps passed vs faults incurred. */
  score() {
    return {
      stepsCompleted: this.completed.length,
      stepsTotal: this.total,
      faults: this.faults.length,
      faultBreakdown: this.faults.reduce((acc, f) => {
        acc[f.kind] = (acc[f.kind] ?? 0) + 1;
        return acc;
      }, {}),
      clean: this.done && this.faults.length === 0,
    };
  }
}

/**
 * Geometry check for the hot air station.
 *
 * B28_ANCHOR_TIP is the airflow axis origin, so "is the nozzle within 5 mm of
 * the target and pointing at it?" is a genuine, checkable condition rather than
 * a button the learner presses.
 */
export function checkNozzleAim(tipNode, targetNode, { maxDistance = 5, maxAngleDeg = 25 } = {}) {
  if (!tipNode || !targetNode) {
    return { ok: false, message: 'The hot air handpiece is not in this scene.' };
  }
  const tip = tipNode.getWorldPosition(new THREE.Vector3());
  const box = new THREE.Box3().setFromObject(targetNode);
  const target = box.isEmpty()
    ? targetNode.getWorldPosition(new THREE.Vector3())
    : box.getCenter(new THREE.Vector3());

  const toTarget = target.clone().sub(tip);
  const distance = toTarget.length();

  // The nozzle blows along its own -Y in the authored rig.
  const axis = new THREE.Vector3(0, -1, 0)
    .applyQuaternion(tipNode.getWorldQuaternion(new THREE.Quaternion()))
    .normalize();

  const angle = THREE.MathUtils.radToDeg(axis.angleTo(toTarget.clone().normalize()));

  if (distance > maxDistance) {
    return {
      ok: false, distance, angle,
      message: `The nozzle is ${distance.toFixed(1)} mm away. Hold it within ${maxDistance} mm - further than that and the joint never reaches temperature, so you will be tempted to pry it off cold.`,
    };
  }
  if (angle > maxAngleDeg) {
    return {
      ok: false, distance, angle,
      message: `The nozzle is off-axis by ${angle.toFixed(0)}deg. Hot air affects an AREA, not a point - aim it at the joint or you will cook the neighbouring parts instead.`,
    };
  }
  return { ok: true, distance, angle, message: 'Nozzle distance and aim are good.' };
}
