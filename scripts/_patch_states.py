import io, os

p = os.path.join(os.path.expanduser("~"), "ConveGenius_3D", "scripts",
                 "texture_pass.py")
t = io.open(p, encoding="utf-8").read()

old = "    C.save_blend(os.path.join(C.OUT, blend))"
new = '''    # ---- SHIP EVERY STATE VISIBLE ------------------------------------
    # glTF has no per-node visibility, and the exporter DROPS render-hidden
    # objects entirely. B40 was shipping 1 of its 5 joint states (only GOOD)
    # and every damage variant / zone plate was missing for the same reason.
    # Anything the runtime is supposed to toggle must be IN the file; the
    # runtime decides what is visible, not the exporter.
    unhidden = []
    for o in bpy.data.objects:
        if C.is_rig_object(o):
            continue
        if o.hide_render or o.hide_viewport:
            o.hide_render = False
            o.hide_viewport = False
            unhidden.append(o.name)
    for coll in bpy.data.collections:
        if coll.hide_render or coll.hide_viewport:
            coll.hide_render = False
            coll.hide_viewport = False
            unhidden.append("[coll]" + coll.name)
    if unhidden:
        C.log("unhid %d object(s)/collection(s) so the runtime can toggle "
              "them: %s" % (len(unhidden), ", ".join(unhidden[:10])))

    # ---- DEDUPE MATERIALS -------------------------------------------
    # appending B05/B11 into the assembly created MAT_GOLD_HARD.001 etc.
    # Material names are the runtime API surface, so collapse the twins.
    merged = []
    for m in list(bpy.data.materials):
        if "." not in m.name:
            continue
        base = m.name.rsplit(".", 1)[0]
        tgt = bpy.data.materials.get(base)
        if tgt is None or tgt is m:
            continue
        for ob in bpy.data.objects:
            if ob.type != "MESH":
                continue
            for slot in ob.material_slots:
                if slot.material is m:
                    slot.material = tgt
        merged.append("%s -> %s" % (m.name, base))
    if merged:
        C.log("deduped materials: " + ", ".join(merged))

    C.save_blend(os.path.join(C.OUT, blend))'''

if old in t:
    t = t.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(t)
    print("texture_pass patched: unhide-all + material dedupe")
else:
    print("ANCHOR NOT FOUND")

# record what got unhidden / merged in the report
o2 = '        "renamed": renamed,'
n2 = ('        "renamed": renamed,\n'
      '        "unhidden_for_runtime": unhidden,\n'
      '        "materials_deduped": merged,')
t2 = io.open(p, encoding="utf-8").read()
if o2 in t2 and "unhidden_for_runtime" not in t2:
    t2 = t2.replace(o2, n2)
    io.open(p, "w", encoding="utf-8").write(t2)
    print("report fields added")
