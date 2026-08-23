import { STATE_COPY } from '../core/states.js';
import { LATCH_STATES } from '../core/config.js';

/**
 * "Spot the fault" - the state-swap mechanic used as assessment rather than demo.
 *
 * The two questions the acceptance criteria name explicitly:
 *   - shown LATCHED vs HALF_CLOSED, an untrained learner should pick the faulty
 *     one in under 3 seconds
 *   - shown GOOD vs COLD at thumbnail size, they should pick the good joint
 *
 * So we time the answer and report it: a correct answer that took 11 seconds is
 * a different result from a correct answer that took 2.
 */
export function mountQuiz(host, app, { toast }) {
  const promptEl = host.querySelector('#quiz-prompt');
  const optionsEl = host.querySelector('#quiz-options');
  const feedbackEl = host.querySelector('#quiz-feedback');
  const scoreEl = host.querySelector('#quiz-score');
  const newBtn = host.querySelector('#quiz-new');

  const stats = { asked: 0, right: 0, times: [] };
  let current = null;
  let shownAt = 0;

  function pool() {
    const out = [];
    const joints = app.states.availableExclusiveGroups()
      .flatMap((g) => app.manifest.states[g].group ?? [])
      .filter((m) => app.root.getObjectByName(m));

    if (joints.length >= 2) {
      out.push({
        kind: 'joint',
        prompt: 'What condition is this joint in?',
        show: (answer) => app.states.setExclusive('B40_JOINT', answer),
        options: joints,
        labelOf: (m) => STATE_COPY[m]?.label ?? m,
      });
    }

    if (app.states.hasLatch()) {
      out.push({
        kind: 'latch',
        prompt: 'Is this flap correctly latched?',
        show: (answer) => app.states.setLatch(answer),
        options: Object.keys(LATCH_STATES),
        labelOf: (m) => STATE_COPY[m]?.label ?? m,
      });
    }
    return out;
  }

  function ask() {
    const qs = pool();
    if (!qs.length) {
      promptEl.textContent = 'No state-based question is available for this asset. Load the solder joints or the flex + IFC.';
      optionsEl.innerHTML = '';
      feedbackEl.textContent = '';
      current = null;
      return;
    }

    const q = qs[Math.floor(Math.random() * qs.length)];
    const answer = q.options[Math.floor(Math.random() * q.options.length)];
    current = { q, answer };

    // Set the scene to the answer, then ask. The learner reads the model, not the UI.
    q.show(answer);

    promptEl.textContent = q.prompt;
    feedbackEl.textContent = '';
    feedbackEl.className = 'feedback';
    optionsEl.innerHTML = '';

    for (const opt of q.options) {
      const b = document.createElement('button');
      b.className = 'btn';
      b.textContent = q.labelOf(opt);
      b.addEventListener('click', () => answerWith(opt, b));
      optionsEl.appendChild(b);
    }
    shownAt = performance.now();
  }

  function answerWith(choice, btn) {
    if (!current) return;
    const elapsed = (performance.now() - shownAt) / 1000;
    const correct = choice === current.answer;

    stats.asked++;
    if (correct) { stats.right++; stats.times.push(elapsed); }

    optionsEl.querySelectorAll('.btn').forEach((b) => { b.disabled = true; });
    btn.classList.add('is-on');

    const teaching = STATE_COPY[current.answer]?.teaching ?? '';
    feedbackEl.className = 'feedback is-' + (correct ? 'ok' : 'danger');
    feedbackEl.textContent = correct
      ? `Correct in ${elapsed.toFixed(1)}s. ${teaching}`
      : `No - that was ${STATE_COPY[current.answer]?.label ?? current.answer}. ${teaching}`;

    const median = stats.times.length
      ? [...stats.times].sort((a, b) => a - b)[Math.floor(stats.times.length / 2)]
      : 0;
    scoreEl.textContent = `${stats.right}/${stats.asked} correct` +
      (median ? ` · median ${median.toFixed(1)}s` : '');

    // The acceptance bar is a 3-second recognition, so say when it is missed.
    if (correct && elapsed > 3) {
      toast?.('Right, but slower than 3 seconds. The visual difference should be instant - look again at what gives it away.', 'warn', 5200);
    }

    current = null;
  }

  newBtn.addEventListener('click', ask);

  // Deliberately NOT asking on mount. ask() sets the scene to a random state,
  // and mounting happens during asset load - so auto-asking would silently
  // override the manifest default (B40 would open on a random joint instead of
  // B40_STATE_GOOD) before the learner has even opened this tab.
  function armed() { return !!current; }

  return { ask, stats, armed };
}
