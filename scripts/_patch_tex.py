import io, os, re

p = os.path.join(os.path.expanduser("~"), "ConveGenius_3D", "scripts",
                 "texture_pass.py")
t = io.open(p, encoding="utf-8").read()

# ---------------------------------------------------------------- 1. retune
# Roughness maps tolerate box-projection seams. NORMAL maps do not - on a
# rounded profile the dominant axis flips face to face and the seam shows as a
# hard zigzag (which is exactly what appeared on the B28 body). So normals stay
# only where the UVs are clean: the ribbon's planar map, the small flat solder
# joints, and the PCB at low strength.
reps = [
 # steel: no normal, finer tile
 ('("MAT_STEEL_SHELL",  dict(rough="steel_rough", nrm="steel_nrm",\n'
  '                           tint="#8E9194", metallic=1.0, nrm_strength=0.5),\n'
  '                      ("box", 3.0)),',
  '("MAT_STEEL_SHELL",  dict(rough="steel_rough",\n'
  '                           tint="#8E9194", metallic=1.0),\n'
  '                      ("box", 1.4)),'),
 ('("MAT_STEEL_SEAM",   dict(rough="steel_rough", tint="#7E8185", metallic=1.0),\n'
  '                      ("box", 3.0)),',
  '("MAT_STEEL_SEAM",   dict(rough="steel_rough", tint="#7E8185", metallic=1.0),\n'
  '                      ("box", 1.4)),'),
 ('("MAT_SHIELD_NICKEL",dict(rough="steel_rough", nrm="steel_nrm",\n'
  '                           tint="#9DA1A6", metallic=1.0, nrm_strength=0.4),\n'
  '                      ("box", 6.0)),',
  '("MAT_SHIELD_NICKEL",dict(rough="steel_rough",\n'
  '                           tint="#9DA1A6", metallic=1.0),\n'
  '                      ("box", 2.5)),'),
 # PCB: keep the relief but far gentler
 ('("MAT_PCB_MASK*",    dict(rough="pcb_rough", nrm="pcb_nrm", tint="#0E4F3C",\n'
  '                           metallic=0.0, nrm_strength=0.8), ("box", 9.0)),',
  '("MAT_PCB_MASK*",    dict(rough="pcb_rough", nrm="pcb_nrm", tint="#0E4F3C",\n'
  '                           metallic=0.0, nrm_strength=0.28), ("box", 5.0)),'),
 # cold solder: grain is the teaching signal, but halve the relief
 ('                           tint="#A8ABAE", metallic=1.0, nrm_strength=1.1),\n'
  '                      ("box", 0.9)),',
  '                           tint="#A8ABAE", metallic=1.0, nrm_strength=0.55),\n'
  '                      ("box", 0.9)),'),
 ('                           tint="#8E9195", metallic=1.0, nrm_strength=1.0),\n'
  '                      ("box", 0.9)),',
  '                           tint="#8E9195", metallic=1.0, nrm_strength=0.5),\n'
  '                      ("box", 0.9)),'),
 # ESD plastic: normal map was the worst seam offender on the B28 body
 ('("MAT_ESD_BODY",     dict(rough="esd_rough", nrm="esd_nrm", tint="#41454B",\n'
  '                           metallic=0.0, nrm_strength=0.35), ("box", 22.0)),',
  '("MAT_ESD_BODY",     dict(rough="esd_rough", tint="#41454B",\n'
  '                           metallic=0.0), ("box", 30.0)),'),
 ('("MAT_HANDGRIP",     dict(rough="esd_rough", nrm="esd_nrm", tint="#2A2D31",\n'
  '                           metallic=0.0, nrm_strength=0.5), ("box", 14.0)),',
  '("MAT_HANDGRIP",     dict(rough="esd_rough", tint="#2A2D31",\n'
  '                           metallic=0.0), ("box", 18.0)),'),
]
n = 0
for a, b in reps:
    if a in t:
        t = t.replace(a, b); n += 1
    else:
        print("MISS:", a.split("\n")[0][:56])

# ---------------------------------------------------------------- 2. per-asset
# One global texel size cannot serve a 3.4 mm joint AND a 120 mm board. Scale
# the tile size to the physical size of the asset's parts.
old = 'ASSETS = [\n ("B05_PORT",      "B05_PORT.blend",      True),'
new = ('# tile size must track the physical size of the parts: a 3.4 mm solder\n'
       '# coupon and a 120 mm mainboard cannot share one texel scale\n'
       'TEXEL_SCALE = {"B05_PORT": 0.55, "B10_B11_IFC": 0.75,\n'
       '               "B40_JOINT": 0.15, "B02_MAINBOARD": 1.0,\n'
       '               "B28_HOTAIR": 1.0, "B02_ASSEMBLY": 1.0}\n\n'
       'ASSETS = [\n ("B05_PORT",      "B05_PORT.blend",      True),')
if old in t:
    t = t.replace(old, new); n += 1
else:
    print("MISS: ASSETS block")

old2 = '        else:\n            C.box_uv(o, param)\n            uvs["box"] += 1'
new2 = ('        else:\n'
        '            C.box_uv(o, param * TEXEL_SCALE.get(name, 1.0))\n'
        '            uvs["box"] += 1')
if old2 in t:
    t = t.replace(old2, new2); n += 1
else:
    print("MISS: box_uv scale")

old3 = '            C.box_uv(o, 8.0)          # harmless default so nothing is UV-less'
new3 = ('            C.box_uv(o, 8.0 * TEXEL_SCALE.get(name, 1.0))'
        '   # default so nothing is UV-less')
if old3 in t:
    t = t.replace(old3, new3); n += 1

io.open(p, "w", encoding="utf-8").write(t)
print("applied %d edits" % n)
print("nrm= occurrences left:", len(re.findall(r'nrm="', t)))
print("TEXEL_SCALE present:", "TEXEL_SCALE" in t)
