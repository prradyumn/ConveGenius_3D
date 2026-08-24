import fs from 'fs';
import path from 'path';

const dir = process.argv[2] || 'authoring/glb';
const files = fs.readdirSync(dir).filter(f => f.endsWith('_LOD0.glb')).sort();

function readGltfJson(file) {
  const buf = fs.readFileSync(file);
  if (buf.readUInt32LE(0) !== 0x46546C67) throw new Error('not glb');
  let off = 12;
  while (off < buf.length) {
    const len = buf.readUInt32LE(off);
    const type = buf.readUInt32LE(off + 4);
    const data = buf.subarray(off + 8, off + 8 + len);
    if (type === 0x4E4F534A) return JSON.parse(data.toString('utf8'));
    off += 8 + len + ((4 - (len % 4)) % 4 === 0 ? 0 : 0);
    off += (4 - (len % 4)) % 4;
  }
  throw new Error('no json chunk');
}

const out = {};
for (const f of files) {
  const full = path.join(dir, f);
  const g = readGltfJson(full);
  const nodes = (g.nodes || []).map(n => n.name);
  const meshNodes = (g.nodes || []).filter(n => n.mesh !== undefined).map(n => n.name);
  const emptyNodes = (g.nodes || []).filter(n => n.mesh === undefined && n.skin === undefined && n.camera === undefined).map(n => n.name);
  const morphMeshes = (g.meshes || []).filter(m => (m.primitives || []).some(p => p.targets)).map(m => m.name);
  out[f] = {
    sizeKB: +(fs.statSync(full).size / 1024).toFixed(1),
    nodeCount: nodes.length,
    meshNodeCount: meshNodes.length,
    animations: (g.animations || []).map(a => a.name),
    materials: (g.materials || []).map(m => m.name),
    skins: (g.skins || []).length,
    morphMeshes,
    extensionsRequired: g.extensionsRequired || [],
    images: (g.images || []).length,
    anchors: nodes.filter(n => n && n.includes('ANCHOR')),
    emptyNonAnchor: emptyNodes.filter(n => n && !n.includes('ANCHOR')),
    allNodes: nodes,
  };
}
fs.writeFileSync('authoring/tools/glb_inspect.json', JSON.stringify(out, null, 1));

for (const [f, v] of Object.entries(out)) {
  console.log('\n===== ' + f + ' (' + v.sizeKB + ' KB) =====');
  console.log('nodes:', v.nodeCount, '| meshNodes:', v.meshNodeCount, '| images:', v.images, '| skins:', v.skins);
  console.log('extensionsRequired:', JSON.stringify(v.extensionsRequired));
  console.log('animations:', JSON.stringify(v.animations));
  console.log('morphMeshes:', JSON.stringify(v.morphMeshes));
  console.log('materials:', JSON.stringify(v.materials));
  console.log('anchors(' + v.anchors.length + ')');
  console.log('emptyNonAnchor:', JSON.stringify(v.emptyNonAnchor));
}
