import io, os, sys, re

p = os.path.join(os.path.expanduser("~"), "ConveGenius_3D", "scripts",
                 "build_b10_b11_ifc.py")
t = io.open(p, encoding="utf-8").read()
orig = t

reps = [
 # every bevel destructive: this asset ships morph targets, so it must export
 # with apply=False, which means no modifiers may remain on any object
 ("    C.finish(o, bevel=bevel, segments=seg, angle=angle)",
  "    C.bevel_destructive(o, width=bevel, segments=seg, angle=angle)"),
 ("C.finish(film, bevel=0.008, segments=2, angle=45.0)",
  "C.bevel_destructive(film, width=0.008, segments=2, angle=45.0)"),
 ("C.finish(cu, bevel=0.004, segments=1, angle=50.0)",
  "C.bevel_destructive(cu, width=0.004, segments=1, angle=50.0)"),
 ("C.finish(lip, bevel=0.02)",
  "C.bevel_destructive(lip, width=0.02, segments=2, angle=34.0)"),
 ("C.finish(t, bevel=0.004)",
  "C.bevel_destructive(t, width=0.004, segments=1, angle=34.0)"),
 ('                   draco=True, anim_mode="NLA_TRACKS")',
  '                   draco=True, anim_mode="NLA_TRACKS",\n'
  '                   apply_modifiers=False)'),
]

applied = 0
for a, b in reps:
    if a in t:
        t = t.replace(a, b)
        applied += 1
    else:
        print("MISS:", a[:60])

io.open(p, "w", encoding="utf-8").write(t)
left = len(re.findall(r"C\.finish\(", t))
print("applied %d/%d ; C.finish( remaining = %d ; changed = %s"
      % (applied, len(reps), left, t != orig))
print("apply_modifiers=False present:", "apply_modifiers=False" in t)
print("bevel_destructive count:", len(re.findall(r"bevel_destructive\(", t)))
