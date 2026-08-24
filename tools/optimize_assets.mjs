#!/usr/bin/env node
/**
 * WebP texture pass.
 *
 * Textures in the shipped .glb files are embedded PNG, because Blender's glTF
 * exporter cannot produce anything smaller. This is the single biggest
 * payload win left: ~5.9 MB of glb, most of it texture.
 *
 * KTX2/Basis (the original plan here) needs the external `ktx` CLI from
 * KTX-Software, which has no Homebrew formula and is not installed on this
 * machine - and even where it is, decoding KTX2 at runtime means wiring
 * KTX2Loader + a Basis transcoder .wasm into loader.js. WebP compresses these
 * PNGs nearly as well for a fraction of the effort: three.js's GLTFLoader
 * already decodes `EXT_texture_webp` natively (see node_modules/three's
 * GLTFLoader.js), so there is zero runtime wiring - the browser's own image
 * decoder does the work, and support is universal on anything this app
 * targets (Chrome/WebView on Android has shipped WebP since forever).
 *
 * This wraps @gltf-transform/cli rather than reimplementing it - but NOT its
 * bundled `optimize` command. `optimize` always runs an unconditional `dedup`
 * pass with no off switch, and dedup does not treat `name` as significant: it
 * collapses any materials that are numerically identical after hashing. Every
 * pin-group material in these assets (MAT_PIN_GND / MAT_PIN_VBUS / ... ) is
 * exactly that - same shader values, different name, because the *name* is
 * the whole point (signal-group teaching in materials.js keys off it). One
 * `optimize` pass silently merged all five into one and the "light this
 * signal group" buttons lost 4 of 5 groups with no error anywhere. So this
 * chains the three specific transforms actually wanted (resize, webp, draco)
 * instead of the grab-bag command, and verifies material/node counts survive
 * intact before letting anything through.
 *
 * Usage:
 *   npm run optimize            # writes public/assets/glb/optimized/
 *   npm run optimize -- --apply # replaces the originals (backup kept)
 */

import { execFileSync } from 'node:child_process';
import {
  existsSync, mkdirSync, readdirSync, statSync, copyFileSync, renameSync, rmSync, readFileSync,
} from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url));
const glbDir = join(here, '..', 'public', 'assets', 'glb');
const outDir = join(glbDir, 'optimized');
const backupDir = join(glbDir, 'original');
const scratchDir = join(tmpdir(), 'cg-optimize-' + Date.now());

/** Read glTF node + material names straight out of the GLB JSON chunk, no
 *  dependency on @gltf-transform's own (ESM-only, awkward to import from a
 *  plain script) object model. */
function readNames(path) {
  const buf = readFileSync(path);
  let offset = 12, json = null;
  while (offset < buf.length) {
    const chunkLen = buf.readUInt32LE(offset);
    const chunkType = buf.readUInt32LE(offset + 4);
    if (chunkType === 0x4e4f534a) json = JSON.parse(buf.subarray(offset + 8, offset + 8 + chunkLen).toString('utf8'));
    offset += 8 + chunkLen;
  }
  return {
    nodes: (json.nodes ?? []).map((n) => n.name).filter(Boolean).sort(),
    materials: (json.materials ?? []).map((m) => m.name).filter(Boolean).sort(),
  };
}

/** The one thing this pass must never do: change which named nodes or
 *  materials exist. components.json anchors nodes by name, and the
 *  signal-group / highlight code anchors materials by name. */
function assertNamesPreserved(srcPath, dstPath, file) {
  const before = readNames(srcPath);
  const after = readNames(dstPath);
  const missingNodes = before.nodes.filter((n) => !after.nodes.includes(n));
  const missingMats = before.materials.filter((n) => !after.materials.includes(n));
  if (missingNodes.length || missingMats.length) {
    throw new Error(
      `${file}: optimize pass dropped/merged named properties - `
      + `${missingNodes.length} node(s), ${missingMats.length} material(s). `
      + `e.g. ${[...missingNodes, ...missingMats].slice(0, 5).join(', ')}`,
    );
  }
}

const apply = process.argv.includes('--apply');

function kb(p) { return (statSync(p).size / 1024).toFixed(1); }

if (!existsSync(glbDir)) {
  console.error('No glb directory at ' + glbDir);
  process.exit(1);
}
mkdirSync(outDir, { recursive: true });
mkdirSync(scratchDir, { recursive: true });

const files = readdirSync(glbDir).filter((f) => f.endsWith('.glb'));
if (!files.length) {
  console.error('No .glb files found in ' + glbDir);
  process.exit(1);
}

console.log(`Optimising ${files.length} asset(s) with @gltf-transform/cli.\n`);

let before = 0, after = 0, failed = 0;

function run(cmd, args) {
  execFileSync('npx', ['--yes', '@gltf-transform/cli', cmd, ...args], {
    stdio: ['ignore', 'pipe', 'pipe'], shell: process.platform === 'win32',
  });
}

for (const file of files) {
  const src = join(glbDir, file);
  const dst = join(outDir, file);
  const stepA = join(scratchDir, 'a-' + file);
  const stepB = join(scratchDir, 'b-' + file);

  process.stdout.write(`  ${file.padEnd(30)} ${kb(src).padStart(9)} KB -> `);
  try {
    // Three explicit, individually-safe steps - not the `optimize` grab-bag
    // command (see header comment for why). Textures are capped at 1024px
    // because these are inspected at macro zoom on a 5-inch screen, not
    // printed; draco last so it compresses the post-resize/webp geometry.
    run('resize', [src, stepA, '--width', '1024', '--height', '1024']);
    run('webp', [stepA, stepB, '--quality', '82']);
    run('draco', [stepB, dst]);
    assertNamesPreserved(src, dst, file);

    before += statSync(src).size;
    after += statSync(dst).size;
    console.log(`${kb(dst).padStart(9)} KB`);
  } catch (err) {
    failed++;
    console.log('FAILED');
    const msg = (err.stderr?.toString() || err.message || '').split('\n').slice(0, 3).join(' ');
    console.log(`    ${msg}`);
  }
}

rmSync(scratchDir, { recursive: true, force: true });

if (failed === files.length) {
  console.error('\nEvery file failed. @gltf-transform/cli could not run - check network access,');
  console.error('or install it locally:  npm i -D @gltf-transform/cli');
  process.exit(1);
}

console.log(
  `\nTotal ${(before / 1048576).toFixed(2)} MB -> ${(after / 1048576).toFixed(2)} MB ` +
  `(${(100 - (after / before) * 100).toFixed(1)}% smaller)`,
);

if (!apply) {
  console.log(`\nWrote ${outDir}`);
  console.log('Verify in the browser, then re-run with --apply to swap them in.');
  console.log('No loader changes needed - GLTFLoader decodes EXT_texture_webp natively.');
  process.exit(0);
}

// --apply: keep the originals, then swap.
mkdirSync(backupDir, { recursive: true });
for (const file of files) {
  const opt = join(outDir, file);
  if (!existsSync(opt)) continue;
  copyFileSync(join(glbDir, file), join(backupDir, file));
  renameSync(opt, join(glbDir, file));
}
console.log(`\nApplied. Originals preserved in ${backupDir}`);
