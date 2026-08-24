# =====================================================================
# B02_ASSEMBLY - the mainboard with REAL parts in its footprints
#
# B02's whole teaching job is that the four zones read as a traceable path:
#   charging port (board EDGE) -> IFC socket -> Charger IC -> battery connector
# Tinted zone plates only half-solved that. Dropping the actual B05 receptacle
# and B11 socket into their footprints solves it properly, because now the
# learner sees the parts they will meet on a real bench, in the right places.
#
# The flex between them is generated fresh at the true 16 mm board distance.
# The standalone B10 keeps its full 36 mm service loop for the Fix 3 close-ups
# - a phone's flex really is longer than the straight-line gap, but a 36 mm
# ribbon dropped onto a 16 mm gap would hang off the board edge.
#
# Usage: blender-launcher.exe --python build_b02_assembly.py
# =====================================================================
import bpy, bmesh, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cg_lib as C

BASE = os.path.join(C.OUT, "B02_MAINBOARD.blend")
SRC_PORT = os.path.join(C.OUT, "B05_PORT.blend")
SRC_IFC = os.path.join(C.OUT, "B10_B11_IFC.blend")

try:
    bpy.ops.wm.open_mainfile(filepath=BASE)
except Exception as e:
    raise SystemExit("cannot open B02: " + str(e))

sc = bpy.context.scene
ZTOP = 0.90 + 0.031
ZONES = {"PORT": (-54.0, 0.0), "IFC": (-38.0, 5.0),
         "PMIC": (-4.0, -3.0), "BATTCONN": (32.0, 7.0)}
C.log("opened B02 with %d objects" % len(bpy.data.objects))


def append_objects(blend, predicate, tag):
    """Pure data API - bpy.data.libraries.load needs no operator context."""
    got = []
    try:
        with bpy.data.libraries.load(blend, link=False) as (src, dst):
            dst.objects = [n for n in src.objects if predicate(n)]
    except Exception as e:
        C.log("append failed from %s: %s" % (os.path.basename(blend), str(e)[:140]))
        return got
    for o in dst.objects:
        if o is None:
            continue
        sc.collection.objects.link(o)
        got.append(o)
    C.log("appended %d objects (%s)" % (len(got), tag))
    return got


# ------------------------------------------------------------------ B05 port
# B05 is built with the cavity facing -Y and depth running +Y. Rotating -90
# about Z maps depth to +X, so the opening faces -X = out of the board edge.
port_objs = append_objects(
    SRC_PORT,
    lambda n: n.startswith("B05_") and "BENT" not in n and "GASKET" not in n,
    "B05 port")
port_root = C.empty("ASM_PORT_ROOT", (0, 0, 0), size=3.0)
px, py = ZONES["PORT"]
for o in port_objs:
    if o.parent is None or o.parent.name not in [x.name for x in port_objs]:
        o.parent = port_root
port_root.rotation_euler = (0.0, 0.0, math.radians(-90.0))
port_root.location = (px - 4.4, py, ZTOP + 1.58)

# ------------------------------------------------------------------ B11 socket
# socket only - the standalone ribbon is the wrong length for this gap
sock_objs = append_objects(
    SRC_IFC,
    lambda n: n.startswith("B11_") and "SOLDER_CRACK" not in n,
    "B11 socket")
sock_root = C.empty("ASM_IFC_ROOT", (0, 0, 0), size=3.0)
for o in sock_objs:
    if o.parent is None or o.parent.name not in [x.name for x in sock_objs]:
        o.parent = sock_root
ix, iy = ZONES["IFC"]
sock_root.location = (ix, iy, ZTOP)

# ------------------------------------------------------------------ the flex
# generated at the real board distance, with a service loop that stays on board
gap0 = px - 1.0            # leaves the port
gap1 = ix - 2.2            # enters the socket mouth
WAY = [(gap0, ZTOP + 1.35), (gap0 + 3.0, ZTOP + 2.90),
       (0.5 * (gap0 + gap1), ZTOP + 3.30),
       (gap1 - 3.0, ZTOP + 1.70), (gap1, ZTOP + 0.62)]
samples = C.catmull(WAY, 40)
prof = C.rounded_rect(6.0, 0.12, 0.055, caps=3)
flex, _rings = C.ribbon("ASM_FLEX_FILM", samples, prof)
flex.location = (0.0, iy, 0.0)
poly = C.mat("MAT_POLYIMIDE_ASM", "#B57F26", 0.0, 0.42,
             transmission=0.12, ior=1.62)
C.assign(flex, poly)
C.finish(flex, bevel=0.008, segments=2, angle=45.0)
cu_prof = C.rounded_rect(5.1, 0.03, 0.012, caps=2)
flexcu, _r2 = C.ribbon("ASM_FLEX_COPPER", samples, cu_prof)
flexcu.location = (0.0, iy, 0.0)
C.assign(flexcu, C.mat("MAT_FPC_COPPER_ASM", "#A9642F", 1.0, 0.36))
C.finish(flexcu, bevel=0.004, segments=1, angle=50.0)
C.log("generated %0.1f mm flex across the real board gap" % abs(gap1 - gap0))

# ------------------------------------------------------------------ shot list
zone_plates = [o for o in bpy.data.objects if o.name.startswith("B02_ZONE_")]
for z in zone_plates:
    z.hide_render = True
    z.hide_viewport = True

C.lighting_rig(scale=95.0, k=30.0, cavity=False)
C.studio_world(strength=0.92)
C.reflector_cards(scale=95.0, strength=6.0)
C.light_aim("CG_OVERHEAD", (14.0, -28.0, 190.0), (0.0, 0.0, 0.0),
            energy_k=30.0, size_rel=1.9, scale=95.0, power=1.15)
C.set_look()
C.fix_clipping()

# exclude the CG_ lighting rig: the reflector cards are MESHES, and letting
# them into the framing bounds blew the wide shot out to 0.6% coverage
vis = [o for o in bpy.data.objects
       if o.type in ("MESH", "FONT") and not o.hide_render
       and not o.name.startswith("CG_")]
path_parts = port_objs + sock_objs + [flex, flexcu]
path_parts = [o for o in path_parts if o.type == "MESH" and not o.hide_render]

def shoot(name, loc, tgt, focal, subj, margin, res, expose=True, samples_=64):
    cm = C.camera(name + "_cam", loc, tgt or (0, 0, 0), focal=focal)
    C.frame_camera(cm, subj, margin=margin, target=tgt, res=res)
    if expose:
        C.auto_expose(cm, target=0.21)
    C.render(cm, os.path.join(C.REN, name + ".png"), res=res, samples=samples_)
    return cm

tris = C.tri_count([o for o in bpy.data.objects if o.type == "MESH"])
C.log("assembly LOD0 tris = %d" % tris)
C.viewport_setup(focus_size=110.0)
C.save_blend(os.path.join(C.OUT, "B02_ASSEMBLY.blend"))

shoot("ASM_shot1_board_populated", (6.0, -60.0, 108.0), (-14.0, 2.0, 2.0),
      100, vis, 1.05, (2200, 1200))
shoot("ASM_shot2_path_closeup", (-58.0, -46.0, 34.0), (-46.0, 3.0, 3.0),
      110, path_parts, 1.12, (2000, 1200))
shoot("ASM_shot3_port_in_situ", (-78.0, -30.0, 20.0), (-52.0, 0.0, 2.2),
      120, port_objs + [flex], 1.20, (1800, 1200))

for z in zone_plates:
    z.hide_render = False
    z.hide_viewport = False
shoot("ASM_shot4_zones_lit", (6.0, -60.0, 108.0), (-14.0, 2.0, 2.0),
      100, vis, 1.05, (2200, 1200))
for z in zone_plates:
    z.hide_render = False   # ship visible; runtime toggles

glb = C.export_glb(os.path.join(C.GLB, "B02_ASSEMBLY_LOD0.glb"),
                   objects=[o for o in bpy.data.objects
                            if o.type in ("MESH", "ARMATURE")],
                   draco=True, anim_mode="NLA_TRACKS")
s = C.glb_summary(os.path.join(C.GLB, "B02_ASSEMBLY_LOD0.glb"))

C.report("B02_ASSEMBLY", {
 "asset": "B02_ASSEMBLY - board with real parts seated",
 "tris_lod0": tris, "glb_kb": round(glb / 1024.0, 1),
 "appended": {"B05_port_objects": len(port_objs),
              "B11_socket_objects": len(sock_objs)},
 "generated_flex_mm": round(abs(gap1 - gap0), 1),
 "zones_populated": ["PORT (B05 seated at the board edge)",
                     "IFC (B11 socket seated)",
                     "PMIC (BGA field + removable shield, no B13 yet)",
                     "BATTCONN (pads only, no B15/B16 yet)"],
 "glb_verified": {k: s.get(k) for k in
                  ("nodes", "meshes", "tris_in_file", "animations", "anchors")},
 "note": "flex regenerated at the true 16 mm board gap. Standalone B10 keeps "
         "its 36 mm service loop for Fix 3 close-ups.",
 "renders": ["ASM_shot1_board_populated", "ASM_shot2_path_closeup",
             "ASM_shot3_port_in_situ", "ASM_shot4_zones_lit"],
})
print("[CG] B02 ASSEMBLY COMPLETE")
