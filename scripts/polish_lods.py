# =====================================================================
# polish_lods.py - generate LOD1 / LOD2 for every finished asset
#
# LOD0 = full detail, used only when the part is the macro / inspection subject
# LOD1 = 40%, bench-wide shots
# LOD2 = 15%, icons and thumbnails
#
# Skinned meshes and anything carrying morph targets are NOT decimated -
# Decimate destroys vertex groups and shape keys, which would break the rig
# and the solder melt. Those keep full density; everything else shrinks.
#
# Usage: blender-launcher.exe --python polish_lods.py
# =====================================================================
import bpy, os, sys, json

sys.path.insert(0, os.path.join(os.path.expanduser("~"), "ConveGenius_3D", "scripts"))
import cg_lib as C

ASSETS = [
    ("B05_PORT",     "B05_PORT.blend"),
    ("B10_B11_IFC",  "B10_B11_IFC.blend"),
    ("B40_JOINT",    "B40_JOINT.blend"),
    ("B02_MAINBOARD","B02_MAINBOARD.blend"),
    ("B28_HOTAIR",   "B28_HOTAIR.blend"),
]
LODS = [("LOD1", 0.40), ("LOD2", 0.15)]

report = {}

def protected(o):
    """Never decimate a skinned mesh or one with shape keys."""
    if any(m.type == "ARMATURE" for m in o.modifiers):
        return True
    if o.data and getattr(o.data, "shape_keys", None):
        return True
    if len(o.data.vertices) < 60:
        return True
    return False

for name, blend in ASSETS:
    path = os.path.join(C.OUT, blend)
    if not os.path.exists(path):
        report[name] = {"error": "blend not found"}
        continue
    entry = {}
    for lod, ratio in LODS:
        try:
            bpy.ops.wm.open_mainfile(filepath=path)
        except Exception as e:
            entry[lod] = {"error": "open failed: " + str(e)[:120]}
            continue
        meshes = [o for o in bpy.data.objects if o.type == "MESH"]
        dec = kept = 0
        for o in meshes:
            if protected(o):
                kept += 1
                continue
            m = o.modifiers.new("CG_LOD", "DECIMATE")
            m.decimate_type = "COLLAPSE"
            m.ratio = ratio
            m.use_collapse_triangulate = True
            dec += 1
        tris = C.tri_count(meshes)
        out = os.path.join(C.GLB, "%s_%s.glb" % (name, lod))
        sz = C.export_glb(out, objects=[o for o in bpy.data.objects
                                        if o.type in ("MESH", "ARMATURE")],
                          draco=True, anim_mode="NLA_TRACKS")
        s = C.glb_summary(out)
        entry[lod] = {"ratio": ratio, "decimated": dec, "protected": kept,
                      "tris_eval": tris, "kb": round(sz / 1024.0, 1),
                      "tris_in_file": s.get("tris_in_file"),
                      "clips": [a["name"] for a in s.get("animations", [])],
                      "anchors": len(s.get("anchors", []))}
        C.log("%s %s -> %.1f KB, %d tris in file"
              % (name, lod, sz / 1024.0, s.get("tris_in_file", 0)))
    report[name] = entry

# roll-up: what a scene actually costs at each tier
tot = {"LOD0": 0.0, "LOD1": 0.0, "LOD2": 0.0}
for name, _b in ASSETS:
    p0 = os.path.join(C.GLB, name + "_LOD0.glb")
    if os.path.exists(p0):
        tot["LOD0"] += os.path.getsize(p0) / 1024.0
    for lod, _r in LODS:
        p = os.path.join(C.GLB, "%s_%s.glb" % (name, lod))
        if os.path.exists(p):
            tot[lod] += os.path.getsize(p) / 1024.0

with open(os.path.join(C.OUT, "LOD_REPORT.json"), "w") as f:
    json.dump({"per_asset": report,
               "totals_kb": {k: round(v, 1) for k, v in tot.items()},
               "budget_mb": 25,
               "pct_of_budget": {k: round(100 * v / (25 * 1024), 3)
                                 for k, v in tot.items()},
               "policy": "LOD0 macro/inspection only; LOD1 bench-wide; "
                         "LOD2 icons. Skinned + morph-target meshes are never "
                         "decimated (Decimate destroys vertex groups and "
                         "shape keys)."}, f, indent=1)
print("[LOD] done")
print(json.dumps(tot, indent=1))
