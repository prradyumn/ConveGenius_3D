import io, os

lib = os.path.join(os.path.expanduser("~"), "ConveGenius_3D", "scripts",
                   "cg_lib.py")
u = io.open(lib, encoding="utf-8").read()

# The reflector cards are MESHES with visible_camera=False. Blender renders hide
# them; glTF has no such concept, so they shipped in EVERY GLB as two large
# emissive planes. Guard it inside export_glb so it can never recur.
old = """def export_glb(path, objects=None, draco=True, anim_mode="NLA_TRACKS",
               include_anchors=True, verify=True, apply_modifiers=True):
    sel = with_parents([o for o in (objects or [])], include_anchors) \\
        if objects else []
"""
new = '''def is_rig_object(o):
    """Lighting-rig helpers must never ship. The reflector cards are MESHES
    with visible_camera=False - Blender hides them from renders, but glTF has
    no equivalent flag, so they exported into every GLB as two big emissive
    planes. Invisible in Blender, glaring in three.js."""
    n = getattr(o, "name", "") or ""
    if n.startswith("CG_"):
        return True
    if getattr(o, "type", None) in ("LIGHT", "CAMERA"):
        return True
    return False


def export_glb(path, objects=None, draco=True, anim_mode="NLA_TRACKS",
               include_anchors=True, verify=True, apply_modifiers=True):
    sel = with_parents([o for o in (objects or [])], include_anchors) \\
        if objects else []
    before = len(sel)
    sel = [o for o in sel if not is_rig_object(o)]
    if before != len(sel):
        log("export: dropped %d lighting-rig object(s) from the selection"
            % (before - len(sel)))
'''
if old in u:
    u = u.replace(old, new)
    io.open(lib, "w", encoding="utf-8").write(u)
    print("cg_lib patched: rig objects excluded from export")
else:
    print("ANCHOR NOT FOUND")

# also stop the cards being included by the callers' own object lists
tp = os.path.join(os.path.dirname(lib), "texture_pass.py")
t = io.open(tp, encoding="utf-8").read()
o2 = ('    sz = C.export_glb(out, objects=[x for x in bpy.data.objects\n'
      '                                    if x.type in ("MESH", "ARMATURE")],')
n2 = ('    sz = C.export_glb(out, objects=[x for x in bpy.data.objects\n'
      '                                    if x.type in ("MESH", "ARMATURE")\n'
      '                                    and not C.is_rig_object(x)],')
if o2 in t:
    t = t.replace(o2, n2)
    io.open(tp, "w", encoding="utf-8").write(t)
    print("texture_pass patched")
else:
    print("texture_pass anchor not found (guard in export_glb still covers it)")
