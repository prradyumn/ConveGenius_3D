#!/usr/bin/env node
/**
 * KTX2 / Basis texture pass.
 *
 * Textures in the shipped .glb files are embedded PNG, because Blender's glTF
 * exporter cannot produce KTX2. The asset brief is explicit that this pass
 * belongs on the web side, and it is the single biggest payload win left:
 * ~5.9 MB of glb, most of it texture.
 *
 * This wraps @gltf-transform/cli rather than reimplementing it. It is a
 * deliberate opt-in step (npm run optimize), not part of `npm run build`,
 * because it needs a toolchain download and takes minutes.
 *
 * Usage:
 *   npm run optimize            # writes public/assets/glb/optimized/
 *   npm run optimize -- --apply # replaces the originals (backup kept)
 */

import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, statSync, copyFileSync, renameSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const glbDir = join(here, '..', 'public', 'assets', 'glb');
const outDir = join(glbDir, 'optimized');
const backupDir = join(glbDir, 'original');

const apply = process.argv.includes('--apply');

function kb(p) { return (statSync(p).size / 1024).toFixed(1); }

if (!existsSync(glbDir)) {
  console.error('No glb directory at ' + glbDir);
  process.exit(1);
}
mkdirSync(outDir, { recursive: true });

const files = readdirSync(glbDir).filter((f) => f.endsWith('.glb'));
if (!files.length) {
  console.error('No .glb files found in ' + glbDir);
  process.exit(1);
}

console.log(`Optimising ${files.length} asset(s) with @gltf-transform/cli.\n`);

let before = 0, after = 0, failed = 0;

for (const file of files) {
  const src = join(glbDir, file);
  const dst = join(outDir, file);

  // UASTC for normal maps (needs the precision), ETC1S for colour (much smaller).
  // Textures are resized to 1024 because these are inspected at macro zoom on a
  // 5-inch screen, not printed.
  const args = [
    '--yes', '@gltf-transform/cli', 'optimize', src, dst,
    '--texture-compress', 'ktx2',
    '--texture-size', '1024',
    '--compress', 'draco',
    '--instance', 'false',   // the runtime does its own instancing, with picking
    '--join', 'false',       // joining meshes would destroy the node names, which ARE the API
    '--weld', 'false',       // weld can shift morph-target deltas
    '--simplify', 'false',   // LODs were measured as not worth it; do not decimate
  ];

  process.stdout.write(`  ${file.padEnd(30)} ${kb(src).padStart(9)} KB -> `);
  try {
    execFileSync('npx', args, { stdio: ['ignore', 'pipe', 'pipe'], shell: process.platform === 'win32' });
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
  console.log('IMPORTANT: after applying, the runtime needs KTX2Loader wired into');
  console.log('GLTFLoader (src/core/loader.js) or the textures will not decode.');
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
console.log('Now wire KTX2Loader into src/core/loader.js before testing.');
