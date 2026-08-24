import { STATE_COPY } from '../core/states.js';
import { LATCH_STATES } from '../core/config.js';

/**
 * State-toggle panel.
 *
 * Only renders controls for states that actually exist in the loaded asset -
 * three of the groups named in components.json (B05_STATE_BENT_PINS,
 * B10_STATE_PADS_WORN, B10_STATE_TORN) are logical, not nodes, and are resolved
 * to their member meshes by the state machine.
 */
export function mountStatePanel(host, app, { toast, frameEntry }) {
  host.innerHTML = '';
  const states = app.states;
  let rendered = 0;

  // --- Exclusive groups (B40's five joints: show exactly one) ---
  for (const groupName of states.availableExclusiveGroups()) {
    const def = app.manifest.states[groupName];
    const members = def.group.filter((m) => app.root.getObjectByName(m));
    if (!members.length) continue;
    rendered++;

    const wrap = document.createElement('div');
    wrap.className = 'state-group card';
    const title = document.createElement('h3');
    title.className = 'card__title';
    title.textContent = 'Joint condition';
    wrap.appendChild(title);

    const hint = document.createElement('p');
    hint.className = 'muted';
    hint.textContent = 'All five ship visible in the file. Exactly one is shown - same origin, same camera, same exposure, so the learner compares the JOINT, not the scene.';
    wrap.appendChild(hint);

    const row = document.createElement('div');
    row.className = 'btnrow';
    const teach = document.createElement('p');
    teach.className = 'state-teach';

    for (const m of members) {
      const b = document.createElement('button');
      b.className = 'btn' + (states.currentExclusive(groupName) === m ? ' is-on' : '');
      b.textContent = STATE_COPY[m]?.label ?? m.replace(/^B40_STATE_/, '');
      b.addEventListener('click', () => {
        states.setExclusive(groupName, m);
        row.querySelectorAll('.btn').forEach((x) => x.classList.remove('is-on'));
        b.classList.add('is-on');
        teach.textContent = STATE_COPY[m]?.teaching ?? '';
        frameEntry?.(m);
      });
      row.appendChild(b);
    }
    wrap.appendChild(row);

    const cur = states.currentExclusive(groupName);
    teach.textContent = STATE_COPY[cur]?.teaching ?? '';
    wrap.appendChild(teach);
    host.appendChild(wrap);
  }

  // --- ZIF latch: a TRANSFORM, not separate meshes ---
  if (states.hasLatch()) {
    rendered++;
    const wrap = document.createElement('div');
    wrap.className = 'state-group card';
    wrap.innerHTML = '<h3 class="card__title">ZIF latch</h3>';

    const hint = document.createElement('p');
    hint.className = 'muted';
    hint.textContent = 'These are rotations of B11_FLAP, not separate meshes.';
    wrap.appendChild(hint);

    const row = document.createElement('div');
    row.className = 'btnrow';
    const teach = document.createElement('p');
    teach.className = 'state-teach';

    for (const name of Object.keys(LATCH_STATES)) {
      const b = document.createElement('button');
      const isFault = name === 'HALF_CLOSED';
      b.className = 'btn' + (isFault ? ' btn--danger' : '') + (states.latchState() === name ? ' is-on' : '');
      b.textContent = STATE_COPY[name]?.label ?? name;
      b.addEventListener('click', () => {
        states.setLatch(name);
        row.querySelectorAll('.btn').forEach((x) => x.classList.remove('is-on'));
        b.classList.add('is-on');
        teach.textContent = STATE_COPY[name]?.teaching ?? '';
        const flapEntry = app.registry.get('B11_FLAP');
        if (flapEntry) frameEntry?.('B11_FLAP');
      });
      row.appendChild(b);
    }
    wrap.appendChild(row);
    teach.textContent = STATE_COPY[states.latchState()]?.teaching ?? '';
    wrap.appendChild(teach);
    host.appendChild(wrap);
  }

  // --- Optional overlays and damage variants ---
  const optional = states.availableOptional();
  if (optional.length) {
    rendered++;
    const wrap = document.createElement('div');
    wrap.className = 'state-group card';
    wrap.innerHTML = '<h3 class="card__title">Fault states &amp; overlays</h3>';

    const hint = document.createElement('p');
    hint.className = 'muted';
    hint.textContent = 'Off by default. glTF has no per-node visibility, so the runtime owns this.';
    wrap.appendChild(hint);

    const row = document.createElement('div');
    row.className = 'btnrow';
    const teach = document.createElement('p');
    teach.className = 'state-teach';

    for (const name of optional) {
      const b = document.createElement('button');
      const isZone = name.includes('_ZONE_');
      b.className = 'btn' + (!isZone ? ' btn--danger' : '') + (states.isOn(name) ? ' is-on' : '');
      b.textContent = STATE_COPY[name]?.label
        ?? name.replace(/^B\d+_(STATE_|ZONE_)?/, '').replace(/_/g, ' ').toLowerCase();
      b.title = name;
      b.addEventListener('click', () => {
        const on = states.toggleOptional(name);
        b.classList.toggle('is-on', states.isOn(name));
        teach.textContent = STATE_COPY[name]?.teaching ?? '';
        if (states.isOn(name)) toast?.(`${b.textContent} shown.`, 'info', 2200);
      });
      row.appendChild(b);
    }
    wrap.appendChild(row);
    wrap.appendChild(teach);
    host.appendChild(wrap);
  }

  if (!rendered) {
    const p = document.createElement('p');
    p.className = 'muted';
    p.textContent = 'This asset has no toggleable states. Load the solder joints, the flex + IFC, the port or the mainboard.';
    host.appendChild(p);
  }
}
