import { checkNozzleAim } from './engine.js';

/**
 * The gated fixes.
 *
 * All refusal copy is written in the voiceover's own language, because the
 * learner has to recognise the phrase on the bench, not just fail a check.
 */

/** Fix 3 - replace a worn flex cable / IF connector ribbon.
 *  Chosen as the reference implementation because it exercises the peel rig,
 *  the flap states, the solder melt and the pad-wear variants together. */
export const FIX_3 = {
  id: 'FIX_3',
  title: 'Fix 3 - Replace the flex cable (IF connector ribbon)',
  asset: 'B10_B11_IFC',
  intro:
    'The pads on this ribbon are worn through to bare copper. Cleaning or resoldering will not fix physical wear - the ribbon has to come out. Work in order.',
  completion:
    'Fix complete. The new ribbon is seated, the flap is fully latched, and the anchors are sound.',
  setup(ctx) {
    // Present the fault the fix exists to answer.
    ctx.states.setOptional('B10_STATE_PADS_WORN', true);
    ctx.states.setLatch('LATCHED');
    ctx.anim.setMelt(0);
  },
  steps: [
    {
      id: 'BATTERY',
      verb: 'disconnect',
      target: 'BATTERY',
      tool: 'hands',
      prompt: 'Before anything else: disconnect the battery.',
      why: 'Every fix that applies heat starts here. Heat plus a live board is how you destroy a mainboard and hurt yourself.',
      grants: ['BATTERY_DISCONNECTED'],
      validate: (a) => a.verb === 'disconnect' && a.target === 'BATTERY'
        ? { ok: true, message: 'Battery disconnected. Now the board is safe to heat.' }
        : { ok: false, message: 'Disconnect the battery first. No heat goes near a live board.' },
    },
    {
      id: 'INSPECT',
      verb: 'inspect',
      target: 'B10_WORNPAD_04',
      tool: 'magnifier',
      prompt: 'Inspect the landing pads under magnification and confirm the wear.',
      why: 'Confirm the diagnosis before you commit. Worn plating means replace; a dirty pad means clean.',
      requires: [{
        flag: 'BATTERY_DISCONNECTED',
        message: 'Battery first. Disconnect it before you touch anything else.',
      }],
      validate: (a) => a.verb === 'inspect' && /B10_(WORNPAD|PAD)_/.test(a.target ?? '')
        ? { ok: true, message: 'Gold rubbed through to base copper. That is physical wear - it confirms Fix 3, not a clean.' }
        : { ok: false, message: 'Zoom in on the ribbon landing pads. You are looking for gold worn through to copper.' },
    },
    {
      id: 'UNLATCH',
      verb: 'set-latch',
      target: 'UNLATCHED',
      tool: 'spudger',
      prompt: 'Lift the ZIF flap fully open.',
      why: 'Zero Insertion Force: it needs no force to insert, only to lock. Forcing a closed flap breaks the hinge.',
      requires: [{
        flag: 'BATTERY_DISCONNECTED',
        message: 'Battery first. Disconnect it before you touch anything else.',
      }],
      validate: (a, ctx) => {
        if (a.verb !== 'set-latch') {
          return { ok: false, message: 'Use the spudger to lift the latch on the socket.' };
        }
        if (a.target === 'HALF_CLOSED') {
          return {
            ok: false, kind: 'order',
            message: 'Half open is not open. Lift it all the way, or the flex will drag against the contacts on the way out.',
          };
        }
        if (a.target !== 'UNLATCHED') {
          return { ok: false, message: 'Lift the flap to fully open before withdrawing the flex.' };
        }
        ctx.states.setLatch('UNLATCHED');
        return { ok: true, message: 'Flap fully open. The flex is now free.' };
      },
    },
    {
      id: 'PEEL',
      verb: 'play-clip',
      target: 'ANIM_B10_PEEL',
      tool: 'hands',
      prompt: 'Peel the old ribbon back, corner first.',
      why: 'Do not force it, and do not pull on the port end. Corner-first lets the adhesive release along one line instead of tearing the film.',
      validate: (a, ctx) => {
        if (a.verb !== 'play-clip' || a.target !== 'ANIM_B10_PEEL') {
          return { ok: false, message: 'Peel it back from a corner - do not pull it straight off the port end.' };
        }
        ctx.anim.play('ANIM_B10_PEEL');
        return { ok: true, message: 'Corner-first peel. That is the motion - slow, and never from the port end.' };
      },
    },
    {
      id: 'MELT',
      verb: 'heat',
      target: 'B11_SOLDER_L',
      tool: 'hotair',
      prompt: 'Heat the anchoring solder until it liquifies, then lift the part away.',
      why: 'Lift away once the solder liquifies - never pry it cold. Prying cold tears the pads off the board, and a torn pad is a much bigger repair.',
      wrongTool: 'This step needs hot air. A spudger against cold solder tears pads.',
      validate: (a, ctx) => {
        if (a.verb === 'pry') {
          return {
            ok: false, kind: 'safety', severity: 'danger',
            message: 'Never pry it off cold - that tears the pads. Heat it until the solder flows, then lift.',
          };
        }
        if (a.verb !== 'heat') {
          return { ok: false, message: 'Apply hot air to the anchor fillets first.' };
        }
        // Real geometric condition, not a button: is the nozzle close and aimed?
        const tip = ctx.tools?.nozzleTip ?? null;
        const target = ctx.registry.get('B11_SOLDER_L')?.node ?? null;
        if (tip && target) {
          const aim = checkNozzleAim(tip, target);
          if (!aim.ok) return { ok: false, kind: 'technique', message: aim.message };
        }
        ctx.anim.play('ANIM_B11_SOLDER_MELT');
        return { ok: true, message: 'The fillet is flowing. Now lift it away - it should come free with no force at all.' };
      },
    },
    {
      id: 'CLEAN',
      verb: 'clean',
      target: 'B11_SOLDER_L',
      tool: 'wick',
      prompt: 'Remove the old solder, wipe with IPA, clear the pads with solder wick.',
      why: 'The pad must be flat and bright before a new part goes on. Solder will not wet a dirty pad, and you will have built a cold joint before you started.',
      wrongTool: 'Use solder wick and IPA here. Adding fresh solder onto old solder just makes a bigger bad joint.',
      validate: (a) => a.verb === 'clean'
        ? { ok: true, message: 'Flat and bright. That is what a pad has to look like before the new ribbon goes down.' }
        : { ok: false, message: 'Clear the old solder off first - wick, then IPA.' },
    },
    {
      id: 'TACK_CORNER',
      verb: 'solder',
      target: 'B10_PAD_01',
      tool: 'iron',
      prompt: 'Solder ONE CORNER pad first, to hold the ribbon in alignment.',
      why: 'One corner tacked means the ribbon cannot shift while you do the rest. Start in the middle and every remaining pad fights you.',
      grants: ['CORNER_TACKED'],
      validate: (a) => {
        if (a.verb !== 'solder') {
          return { ok: false, message: 'Tack the ribbon down with the iron - one pad only.' };
        }
        // Order-critical: a corner pad, not a middle one.
        const corner = a.target === 'B10_PAD_01' || a.target === 'B10_PAD_12';
        if (!corner) {
          return {
            ok: false, kind: 'order', severity: 'danger',
            message: 'Not a middle pad - a CORNER pad first. The first joint is there to hold the ribbon straight; from the middle it will creep out of alignment and every pad after it lands off-target.',
          };
        }
        return { ok: true, message: 'Corner tacked. The ribbon is now held in alignment - check it is square before you carry on.' };
      },
    },
    {
      id: 'SOLDER_REST',
      verb: 'solder',
      target: null,
      tool: 'iron',
      repeat: 3,
      prompt: 'Now solder the remaining pads.',
      why: 'With the corner holding alignment, the rest are routine. Work across, not randomly.',
      requires: [{
        flag: 'CORNER_TACKED',
        message: 'Tack a corner pad first. Nothing else is held until you do.',
      }],
      validate: (a) => {
        if (a.verb !== 'solder') return { ok: false, message: 'Keep soldering the remaining pads.' };
        if (a.target === 'B10_PAD_01') {
          return { ok: false, kind: 'order', message: 'That corner is already done. Move on to the next pad.' };
        }
        return { ok: true };
      },
    },
    {
      id: 'RESEAT',
      verb: 'insert',
      target: 'B10_FPC_FILM',
      tool: 'hands',
      prompt: 'Insert the new ribbon fully into the socket.',
      why: 'Zero insertion force - it should slide in with no pressure. If it resists, it is misaligned, not stiff.',
      validate: (a) => a.verb === 'insert'
        ? { ok: true, message: 'Seated square and full depth. No force needed.' }
        : { ok: false, message: 'Slide the new ribbon into the socket before closing the flap.' },
    },
    {
      id: 'LATCH',
      verb: 'set-latch',
      target: 'LATCHED',
      tool: 'hands',
      prompt: 'Close the flap fully and confirm it is latched.',
      why: 'A half-closed flap looks closed. It is the "charges only if you hold the cable at just the right angle" fault, and it is one of the most misdiagnosed in the whole course.',
      validate: (a, ctx) => {
        if (a.verb !== 'set-latch') {
          return { ok: false, message: 'Close the ZIF flap to lock the ribbon.' };
        }
        if (a.target === 'HALF_CLOSED') {
          ctx.states.setLatch('HALF_CLOSED');
          return {
            ok: false, kind: 'order', severity: 'danger',
            message: 'That is the fault, not the fix. It LOOKS closed - but half closed does not clamp, and the phone will charge only at one angle. Press it fully down until it stops.',
          };
        }
        if (a.target !== 'LATCHED') {
          return { ok: false, message: 'The flap must end up fully latched.' };
        }
        ctx.states.setLatch('LATCHED');
        ctx.states.setOptional('B10_STATE_PADS_WORN', false);
        ctx.anim.setMelt(0);
        return { ok: true, message: 'Fully latched. Now retest before you close the phone.' };
      },
    },
  ],
};

/** Fix 2 - replace the charging port. Included because its order rule
 *  (ground tabs before signal pins) is the other one that must hard-fail. */
export const FIX_2 = {
  id: 'FIX_2',
  title: 'Fix 2 - Replace the charging port',
  asset: 'B05_PORT',
  intro:
    'Contacts are physically bent, not dirty - so this is a replacement, not a clean. The order of the solder joints matters here.',
  completion: 'Fix complete. Shield tabs anchored first, then the signal pins.',
  setup(ctx) {
    ctx.states.setOptional('B05_STATE_BENT_PINS', true);
  },
  steps: [
    {
      id: 'BATTERY',
      verb: 'disconnect',
      target: 'BATTERY',
      tool: 'hands',
      prompt: 'Disconnect the battery.',
      why: 'Same rule as every heat fix: the board must be dead before the hot air comes out.',
      grants: ['BATTERY_DISCONNECTED'],
      validate: (a) => a.verb === 'disconnect' && a.target === 'BATTERY'
        ? { ok: true, message: 'Battery disconnected.' }
        : { ok: false, message: 'Disconnect the battery first.' },
    },
    {
      id: 'DIAGNOSE',
      verb: 'inspect',
      target: 'B05_BENT_PIN_A05',
      tool: 'magnifier',
      prompt: 'Inspect the contacts and decide: dust, or physical damage?',
      why: 'This is the branch point between Fix 1 and Fix 2. Deflected contacts touching a neighbour cannot be cleaned straight.',
      requires: [{ flag: 'BATTERY_DISCONNECTED', message: 'Battery first.' }],
      validate: (a) => a.verb === 'inspect' && /B05_(BENT_)?PIN_/.test(a.target ?? '')
        ? { ok: true, message: 'Deflected, one touching its neighbour. That is damage - Fix 2, not Fix 1.' }
        : { ok: false, message: 'Look closely at the contact row inside the port.' },
    },
    {
      id: 'REMOVE',
      verb: 'heat',
      target: 'B05_SHELL_TAB_L',
      tool: 'hotair',
      prompt: 'Heat the port free and lift it away.',
      why: 'Never pry a cold part off - it takes the pads with it.',
      wrongTool: 'Hot air, not a lever. Prying cold tears pads off the board.',
      validate: (a) => {
        if (a.verb === 'pry') {
          return {
            ok: false, kind: 'safety', severity: 'danger',
            message: 'Never pry it off cold - that tears the pads. Heat it evenly first.',
          };
        }
        return a.verb === 'heat'
          ? { ok: true, message: 'Even heat, then lift. It should release with no force.' }
          : { ok: false, message: 'Apply hot air to the port tabs and legs.' };
      },
    },
    {
      id: 'CLEAN',
      verb: 'clean',
      target: 'B02_BAREPAD_PORT_TAB_00',
      tool: 'wick',
      prompt: 'Remove old solder, wipe with IPA, clear the footprint with wick.',
      why: 'The footprint must be flat and bright before a new port goes on.',
      grants: ['PADS_CLEAN'],
      validate: (a) => a.verb === 'clean'
        ? { ok: true, message: 'Footprint flat and bright.' }
        : { ok: false, message: 'Clear the old solder before fitting the new port.' },
    },
    {
      id: 'TABS_FIRST',
      verb: 'solder',
      target: 'B05_SHELL_TAB_L',
      tool: 'iron',
      repeat: 2,
      prompt: 'Solder the SHIELD / GROUND TABS first.',
      why: 'The tabs are what mechanically anchor the port. Anchor it before you touch the fine pins, or the whole part shifts and every signal joint lands wrong.',
      requires: [{ flag: 'PADS_CLEAN', message: 'Clean the footprint first - solder will not wet a dirty pad.' }],
      grants: ['TABS_SOLDERED'],
      validate: (a) => {
        if (a.verb !== 'solder') return { ok: false, message: 'Solder the shield tabs.' };
        const isTab = /SHELL_TAB|LEG_/.test(a.target ?? '');
        if (!isTab) {
          return {
            ok: false, kind: 'order', severity: 'danger',
            message: 'Wrong order. The shield and ground tabs are soldered FIRST - they anchor the port. Solder a signal pin now and the port is still loose, so it will shift and lift the joint you just made.',
          };
        }
        return { ok: true, message: 'Tab anchored.' };
      },
    },
    {
      id: 'PINS',
      verb: 'solder',
      target: null,
      tool: 'iron',
      repeat: 3,
      prompt: 'Now the smaller signal pins.',
      why: 'With the port anchored, the fine joints stay put.',
      requires: [{
        flag: 'TABS_SOLDERED',
        message: 'The shield tabs come first. Until they are down, the port is not anchored.',
      }],
      validate: (a) => a.verb === 'solder'
        ? { ok: true }
        : { ok: false, message: 'Solder the remaining signal pins.' },
    },
    {
      id: 'VERIFY',
      verb: 'inspect',
      target: 'B05_SHELL_TAB_L',
      tool: 'magnifier',
      prompt: 'Inspect every joint under magnification.',
      why: 'Good solder is concave and shiny; bad solder is convex and dull. That single contrast is what a technician reads across a bench in half a second.',
      validate: (a, ctx) => {
        if (a.verb !== 'inspect') return { ok: false, message: 'Inspect the finished joints.' };
        ctx.states.setOptional('B05_STATE_BENT_PINS', false);
        return { ok: true, message: 'Concave and shiny on every joint. That is the target.' };
      },
    },
  ],
};

export const PROCEDURES = { FIX_3, FIX_2 };

export const TOOLS = [
  { id: 'hands', label: 'Hands', hint: 'Insert, withdraw, disconnect' },
  { id: 'spudger', label: 'Spudger', hint: 'Lift latches, no force' },
  { id: 'magnifier', label: 'Magnifier', hint: 'Inspect under magnification' },
  { id: 'hotair', label: 'Hot air', hint: '380-450 C for Fixes 2 and 3' },
  { id: 'iron', label: 'Soldering iron', hint: 'Make the joint' },
  { id: 'wick', label: 'Wick + IPA', hint: 'Remove old solder, clean the pad' },
];
