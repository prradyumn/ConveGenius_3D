# =====================================================================
# gate_check.py - STANDALONE glTF VERIFICATION GATE  (v3)
#
# Opens a GLB exactly the way three.js will see it - nothing from the source
# .blend - and proves that (a) skin binding survived and (b) every animation
# clip in the file actually moves geometry.
#
# Three harness bugs this version fixes, each of which produced a false FAIL:
#   1. ev.data.vertices[::4]  -> Blender collections reject stepped slices.
#   2. Blender 4.4+ slotted actions: assigning animation_data.action is not
#      enough, the action SLOT must be assigned too or the action does nothing.
#   3. Only skinned meshes were sampled, so a flap ROTATION could never
#      register as movement.
#
# Usage: blender-launcher.exe --python gate_check.py -- --glb <path>
# =====================================================================
import bpy, os, sys, json, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
os.makedirs(OUT, exist_ok=True)

target = os.path.join(ROOT, "glb", "B10_B11_IFC_LOD0.glb")
for i, a in enumerate(sys.argv):
    if a == "--glb" and i + 1 < len(sys.argv):
        target = sys.argv[i + 1]

rep = {"glb": os.path.basename(target), "exists": os.path.exists(target)}

def ui_override():
    wm = getattr(bpy.context, "window_manager", None)
    if not wm:
        return {}
    for win in getattr(wm, "windows", []):
        scr = getattr(win, "screen", None)
        if not scr:
            continue
        for area in scr.areas:
            if area.type == "VIEW_3D":
                for region in area.regions:
                    if region.type == "WINDOW":
                        return dict(window=win, screen=scr, area=area,
                                    region=region)
        if scr.areas:
            return dict(window=win, screen=scr, area=scr.areas[0])
    return {}

try:
    bpy.ops.wm.read_factory_settings(use_empty=True)
except Exception:
    pass

ov = ui_override()
def _imp():
    bpy.ops.import_scene.gltf(filepath=target)
try:
    if ov:
        with bpy.context.temp_override(**ov):
            _imp()
    else:
        _imp()
    rep["import"] = "ok"
except Exception as e:
    rep["import"] = "FAILED: " + str(e)[:200]
    with open(os.path.join(OUT, "GATE_CHECK.json"), "w") as f:
        json.dump(rep, f, indent=1)
    print("[GATE] IMPORT FAILED")
    raise SystemExit(0)

objs = list(bpy.data.objects)
meshes = [o for o in objs if o.type == "MESH"]
arms = [o for o in objs if o.type == "ARMATURE"]
skinned = [o for o in meshes if any(m.type == "ARMATURE" for m in o.modifiers)]

rep.update({
 "objects": len(objs), "meshes": len(meshes),
 "armatures": [a.name for a in arms],
 "skinned_meshes": len(skinned),
 "actions_in_file": sorted(a.name for a in bpy.data.actions),
 "anchors_in_file": sorted(o.name for o in objs
                           if o.type == "EMPTY" and "_ANCHOR_" in o.name),
 "materials_in_file": sorted(m.name for m in bpy.data.materials),
})
if arms:
    rep["bones_in_file"] = [b.name for b in arms[0].pose.bones]


def positions():
    """Sample EVERY mesh, not just skinned ones - otherwise a flap rotation
    never registers. Read evaluated .data directly; to_mesh() fails on
    imported skinned meshes."""
    try:
        bpy.context.view_layer.update()
    except Exception:
        pass
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in meshes:
        try:
            ev = o.evaluated_get(dg)
            mw = ev.matrix_world
            vs = ev.data.vertices
            n = len(vs)
            step = max(1, n // 60)
            for i in range(0, n, step):
                pts.append(mw @ vs[i].co)
        except Exception as e:
            rep.setdefault("sample_errors", []).append(str(e)[:100])
    return pts


def maxdiff(a, b):
    n = min(len(a), len(b))
    if not n:
        return 0.0, 0
    return max((a[i] - b[i]).length for i in range(n)), n


def assign(o, act):
    """Assign an action AND its slot. Without the slot, Blender 4.4+ slotted
    actions evaluate to nothing and every clip looks dead."""
    try:
        if o.animation_data is None:
            o.animation_data_create()
        o.animation_data.action = act
    except Exception:
        return False
    try:
        slots = getattr(act, "slots", None)
        if slots and len(slots):
            for s in slots:
                try:
                    o.animation_data.action_slot = s
                    break
                except Exception:
                    continue
    except Exception:
        pass
    return True


def unassign(o):
    try:
        if o.animation_data:
            o.animation_data.action = None
    except Exception:
        pass


results = {}

# ---- 1. SKIN BINDING: drive the bones by hand, confirm the skin follows.
if arms and skinned:
    arm = arms[0]
    base = positions()
    for b in arm.pose.bones:
        b.rotation_mode = "XYZ"
        b.rotation_euler = (math.radians(-14.0), 0.0, 0.0)
    d, n = maxdiff(base, positions())
    results["skin_binding"] = {"max_travel_mm": round(d, 4),
                               "verts_sampled": n, "pass": bool(d > 0.05)}
    for b in arm.pose.bones:
        b.rotation_euler = (0.0, 0.0, 0.0)
    try:
        bpy.context.view_layer.update()
    except Exception:
        pass

# ---- 2. EVERY CLIP: bind to the object its SLOT names, not a guess.
# A glTF-imported slot identifier looks like "OBB11_FLAP" -> object B11_FLAP.
# Guessing (and breaking on the first candidate that moved) previously made
# flap clips "pass" by rotating the whole armature - a false positive.
for act in list(bpy.data.actions):
    try:
        fr = act.frame_range
        f0, f1 = int(fr[0]), int(fr[1])
    except Exception:
        f0, f1 = 1, 30
    if f1 <= f0:
        f1 = f0 + 30
    slots = list(getattr(act, "slots", []) or [])
    targets = []
    for s in slots:
        ident = getattr(s, "identifier", "") or ""
        nm = ident[2:] if ident.startswith("OB") else ident
        o = bpy.data.objects.get(nm)
        if o is not None:
            targets.append((o, s))
    if not targets:
        targets = [(o, None) for o in (arms if arms else objs[:1])]
    best = {"max_travel_mm": 0.0, "verts_sampled": 0, "driven": None,
            "slot": None}
    for o, s in targets:
        if o.animation_data is None:
            try: o.animation_data_create()
            except Exception: continue
        try:
            o.animation_data.action = act
            if s is not None:
                o.animation_data.action_slot = s
        except Exception:
            continue
        bpy.context.scene.frame_set(f0); a = positions()
        bpy.context.scene.frame_set(f1); b = positions()
        d, n = maxdiff(a, b)
        if d > best["max_travel_mm"]:
            best = {"max_travel_mm": round(d, 4), "verts_sampled": n,
                    "driven": o.name,
                    "slot": getattr(s, "identifier", None) if s else None}
        unassign(o)
    best["frames"] = [f0, f1]
    best["pass"] = bool(best["max_travel_mm"] > 0.05)
    results[act.name] = best
    bpy.context.scene.frame_set(f0)

rep["results"] = results
clips = {k: v for k, v in results.items() if k != "skin_binding"}
rep["VERDICT"] = "PASS" if (results.get("skin_binding", {}).get("pass")
                            and clips and all(v["pass"] for v in clips.values())) \
    else ("PARTIAL" if any(v["pass"] for v in results.values()) else "FAIL")

with open(os.path.join(OUT, "GATE_CHECK.json"), "w") as f:
    json.dump(rep, f, indent=1)
print("[GATE] " + rep["VERDICT"])
for k, v in results.items():
    print("  %-22s travel=%8s verts=%5s driven=%-18s %s"
          % (k, v.get("max_travel_mm"), v.get("verts_sampled"),
             v.get("driven", "-"), "PASS" if v.get("pass") else "FAIL"))
