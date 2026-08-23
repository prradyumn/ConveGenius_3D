import io, os

p = os.path.join(os.path.expanduser("~"), "ConveGenius_3D", "scripts",
                 "texture_pass.py")
t = io.open(p, encoding="utf-8").read()

# Box-projecting a DIRECTIONAL streak map onto a small box crosshatches into a
# visible checker. The shield cans are ~15 mm and never the macro subject, so
# a plain roughness factor is strictly better than a badly-tiled map.
reps = [
 ('("MAT_SHIELD_NICKEL",dict(rough="steel_rough",\n'
  '                           tint="#9DA1A6", metallic=1.0),\n'
  '                      ("box", 2.5)),',
  '("MAT_SHIELD_NICKEL",dict(tint="#9DA1A6", metallic=1.0),\n'
  '                      ("box", 6.0)),'),
 ('("MAT_NICKEL_BRUSH", dict(rough="steel_rough", tint="#9A9DA1", metallic=1.0),\n'
  '                      ("box", 6.0)),',
  '("MAT_NICKEL_BRUSH", dict(tint="#9A9DA1", metallic=1.0),\n'
  '                      ("box", 6.0)),'),
]
n = 0
for a, b in reps:
    if a in t:
        t = t.replace(a, b); n += 1
    else:
        print("MISS:", a.split("\n")[0][:56])

# tex_set with no maps still needs a roughness factor written, or glTF falls
# back to 1.0 (flat matte) - the same bug that made the steel shell look like
# plastic in the very first export
old = "    if metallic is not None:\n        S(\"Metallic\", metallic)"
new = ("    if metallic is not None:\n        S(\"Metallic\", metallic)\n"
       "    if rough is None and roughness_factor is not None:\n"
       "        S(\"Roughness\", roughness_factor)")
lib = os.path.join(os.path.dirname(p), "cg_lib.py")
u = io.open(lib, encoding="utf-8").read()
if old in u and "roughness_factor" not in u:
    u = u.replace(old, new)
    u = u.replace("def tex_set(mat, base=None, rough=None, nrm=None, tint=None,\n"
                  "            metallic=None, nrm_strength=1.0, clear=True):",
                  "def tex_set(mat, base=None, rough=None, nrm=None, tint=None,\n"
                  "            metallic=None, nrm_strength=1.0, clear=True,\n"
                  "            roughness_factor=0.42):")
    io.open(lib, "w", encoding="utf-8").write(u)
    print("cg_lib: roughness_factor fallback added")
else:
    print("cg_lib: roughness_factor already present or anchor missing")

io.open(p, "w", encoding="utf-8").write(t)
print("applied %d edits to texture_pass" % n)
