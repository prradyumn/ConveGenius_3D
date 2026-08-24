# Diagnostic: what is ACTUALLY inside each imported action, and does the
# armature drive its bones when the action is bound with the right slot?
import bpy, os, sys, json, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
target = os.path.join(ROOT, "glb", "B10_B11_IFC_LOD0.glb")
for i, a in enumerate(sys.argv):
    if a == "--glb" and i + 1 < len(sys.argv):
        target = sys.argv[i + 1]

def ui_override():
    wm = getattr(bpy.context, "window_manager", None)
    for win in getattr(wm, "windows", []) if wm else []:
        scr = getattr(win, "screen", None)
        if not scr:
            continue
        for area in scr.areas:
            if area.type == "VIEW_3D":
                for r in area.regions:
                    if r.type == "WINDOW":
                        return dict(window=win, screen=scr, area=area, region=r)
        if scr.areas:
            return dict(window=win, screen=scr, area=scr.areas[0])
    return {}

bpy.ops.wm.read_factory_settings(use_empty=True)
ov = ui_override()
def _imp(): bpy.ops.import_scene.gltf(filepath=target)
if ov:
    with bpy.context.temp_override(**ov): _imp()
else:
    _imp()

rep = {"actions": {}}

def fcs(act):
    """Walk fcurves across both the legacy and the slotted-action layouts."""
    out = []
    leg = getattr(act, "fcurves", None)
    if leg is not None:
        for fc in leg:
            out.append(("legacy", fc.data_path, fc.array_index))
        return out
    for lay in getattr(act, "layers", []):
        for st in getattr(lay, "strips", []):
            for cb in getattr(st, "channelbags", []):
                slot_h = getattr(cb, "slot_handle", None)
                for fc in getattr(cb, "fcurves", []):
                    out.append(("slot%s" % slot_h, fc.data_path, fc.array_index))
    return out

for act in bpy.data.actions:
    f = fcs(act)
    paths = sorted(set(p for _s, p, _i in f))
    slots = []
    for s in getattr(act, "slots", []) or []:
        slots.append({"identifier": getattr(s, "identifier", "?"),
                      "target_id_type": getattr(s, "target_id_type", "?"),
                      "handle": getattr(s, "handle", None)})
    rep["actions"][act.name] = {
        "n_fcurves": len(f),
        "unique_paths": paths[:8],
        "n_unique_paths": len(paths),
        "has_pose_bone_paths": any("pose.bones" in p for p in paths),
        "slots": slots,
        "frame_range": [round(v, 1) for v in act.frame_range],
    }

arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
rep["armature"] = arms[0].name if arms else None

def sample():
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in meshes:
        try:
            ev = o.evaluated_get(dg); mw = ev.matrix_world
            vs = ev.data.vertices; n = len(vs); st = max(1, n // 40)
            for i in range(0, n, st):
                pts.append(mw @ vs[i].co)
        except Exception:
            pass
    return pts

# bind each action to the armature, trying EVERY slot, and report per-slot
if arms:
    arm = arms[0]
    for act in bpy.data.actions:
        info = rep["actions"][act.name]
        if not info["has_pose_bone_paths"]:
            info["armature_test"] = "skipped - no pose.bones channels"
            continue
        best = 0.0; used = None
        slots = list(getattr(act, "slots", []) or [])
        if arm.animation_data is None:
            arm.animation_data_create()
        trials = slots if slots else [None]
        for s in trials:
            arm.animation_data.action = act
            if s is not None:
                try:
                    arm.animation_data.action_slot = s
                except Exception:
                    pass
            f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
            bpy.context.scene.frame_set(f0); a = sample()
            bpy.context.scene.frame_set(f1); b = sample()
            n = min(len(a), len(b))
            d = max((a[i] - b[i]).length for i in range(n)) if n else 0.0
            if d > best:
                best = d; used = getattr(s, "identifier", "none") if s else "none"
        info["armature_test"] = {"max_travel_mm": round(best, 4),
                                 "slot_used": used,
                                 "pass": bool(best > 0.05)}
        arm.animation_data.action = None
        for b_ in arm.pose.bones:
            b_.rotation_quaternion = (1, 0, 0, 0)
            b_.rotation_euler = (0, 0, 0)

with open(os.path.join(OUT, "GATE_DIAG.json"), "w") as f:
    json.dump(rep, f, indent=1)
print(json.dumps(rep, indent=1)[:4000])
