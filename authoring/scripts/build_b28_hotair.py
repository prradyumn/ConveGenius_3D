# =====================================================================
# B28_HOTAIR - hot air rework station, handpiece, aimable nozzle
# ConveGenius Mobile Charging Repair Simulation
#
# Teaching job: Fixes 2, 3, 4, 5 and 6 ALL begin with hot air. The learner is
# not just identifying this tool - they are learning to AIM it, at a stated
# temperature, at a stated distance, without cooking the parts next door.
#
# THE ONE THING THAT MUST BE UNMISTAKABLE: where the heat goes. The nozzle is
# a separate aimable child with an explicit airflow axis, and the cone of
# effect is visible - which is what makes the Kapton tape shielding in
# Fixes 4/5/6 read as necessary rather than fussy.
#
# NO DIGITS BAKED INTO THE DISPLAY. 380 C and 450 C are different steps of
# different procedures; the runtime draws the number (U02).
# =====================================================================
import bpy, bmesh, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cg_lib as C

BW, BH, BD = 150.0, 132.0, 196.0      # station body  (X, Z, Y-depth)
HP_R, HP_L = 16.0, 148.0              # handpiece radius / length
NOZ = {"3mm": 1.5, "5mm": 2.5, "8mm": 4.0}

C.setup_scene("B28_HOTAIR")
M = C.house_materials()
M["ESD_BODY"]  = C.mat("MAT_ESD_BODY",  "#41454B", 0.0, 0.56)
M["ESD_DARK"]  = C.mat("MAT_ESD_DARK",  "#292D31", 0.0, 0.50)
M["LCD_GLASS"] = C.mat("MAT_LCD_GLASS", "#0A1512", 0.0, 0.14, coat=0.9,
                       coat_rough=0.05)
M["KNOB"]      = C.mat("MAT_KNOB",      "#15171A", 0.0, 0.42)
M["KNOB_RING"] = C.mat("MAT_KNOB_RING", "#B9BDC2", 1.0, 0.30)
M["NOZZLE"]    = C.mat("MAT_NOZZLE_HOT", "#9CA0A4", 1.0, 0.33)
M["HOSE"]      = C.mat("MAT_HOSE",      "#191A1C", 0.0, 0.72)
M["HANDGRIP"]  = C.mat("MAT_HANDGRIP",  "#2A2D31", 0.0, 0.66)
M["LABEL"]     = C.mat("MAT_SILK_LABEL", "#D8DADC", 0.0, 0.60)

# heat-discoloured stainless: straw -> blue toward the tip.
C.gradient_along(M["NOZZLE"], axis="Y", c0="#A9ADB1", c1="#4A5C86",
                 lo=-2.0, hi=30.0, rough0=0.30, rough1=0.46)

root = C.empty("B28_HOTAIR", (0, 0, 0), size=30.0)
parts = []
def child(o, m, parent=None, bevel=0.7, seg=2, angle=32.0):
    C.assign(o, m)
    C.finish(o, bevel=bevel, segments=seg, angle=angle)
    o.parent = parent or root
    parts.append(o)
    return o

# ------------------------------------------------------------------ base
body = C.solid("B28_BASE", C.rounded_rect(BW, BH, 9.0, caps=9), 0.0, BD)
child(body, M["ESD_BODY"], bevel=0.35, seg=2, angle=48.0)

# sloped front control panel, recessed
panel = C.solid("B28_PANEL", C.rounded_rect(BW - 16.0, 54.0, 4.0, caps=4),
                -3.0, 2.0)
panel.location = (0.0, 0.0, BH / 2 - 36.0)
child(panel, M["ESD_DARK"], bevel=0.6)

# display - SEPARATE material slot, blank on purpose
disp = C.box("B28_DISPLAY", 62.0, 1.6, 27.0, (0.0, -4.2, BH / 2 - 36.0))
child(disp, M["LCD_GLASS"], bevel=0.35)
bez = C.box("B28_DISPLAY_BEZEL", 70.0, 1.2, 34.0, (0.0, -3.4, BH / 2 - 36.0))
child(bez, M["ESD_DARK"], bevel=0.5)

# two knobs, each with its origin ON its own rotation axis
for nm, x in (("TEMP", -46.0), ("AIR", 46.0)):
    k = C.lathe("B28_KNOB_" + nm,
                [(0.0, 0.0), (10.5, 0.0), (11.5, -1.6), (11.5, -8.0),
                 (10.0, -9.4), (0.0, -9.4)], seg=20)
    k.location = (x, -1.0, BH / 2 - 74.0)
    child(k, M["KNOB"], bevel=0.25)
    r = C.pipe("B28_KNOB_RING_" + nm, 12.4, 11.4, -1.2, 0.4, seg=20)
    r.location = (x, -1.0, BH / 2 - 74.0)
    child(r, M["KNOB_RING"], bevel=0.12)
    C.empty("B28_ANCHOR_KNOB_" + nm, (x, -12.0, BH / 2 - 74.0), size=3.0).parent = root

# rear vent slats
for i in range(9):
    v = C.box("B28_VENT_%02d" % i, BW - 40.0, 1.4, 3.0,
              (0.0, BD - 1.0, -BH / 2 + 22.0 + i * 7.0))
    child(v, M["ESD_DARK"], bevel=0.15)

# feet
for sx in (-1.0, 1.0):
    for sy in (0.0, 1.0):
        f = C.cyl("B28_FOOT_%d_%d" % (int(sx), int(sy)), 7.0,
                  -BH / 2 - 4.0, -BH / 2 + 0.5, seg=10)
        f.rotation_euler = (math.radians(90), 0, 0)
        f.location = (sx * (BW / 2 - 18.0), 24.0 + sy * (BD - 48.0), 0.0)
        child(f, M["ESD_DARK"], bevel=0.4)

# cradle - the handpiece has a visible home, which is the safety beat
cr = C.solid("B28_CRADLE", C.rounded_rect(30.0, 46.0, 6.0, caps=4), 0.0, 62.0)
cr.location = (BW / 2 + 22.0, 40.0, -BH / 2 + 26.0)
child(cr, M["ESD_DARK"], bevel=0.8)
cru = C.pipe("B28_CRADLE_YOKE", 21.0, 17.5, 0.0, 26.0, seg=18)
cru.rotation_euler = (0.0, math.radians(90), 0.0)
cru.location = (BW / 2 + 8.0, 62.0, -BH / 2 + 60.0)
child(cru, M["ESD_DARK"], bevel=0.5)
C.empty("B28_ANCHOR_CRADLE", (BW / 2 + 22.0, 62.0, -BH / 2 + 74.0),
        size=4.0).parent = root

# ------------------------------------------------------------------ handpiece
# origin at the GRIP POINT, because the runtime moves this object
hp = C.empty("B28_HANDPIECE", (0.0, 0.0, 0.0), size=14.0)
hp.parent = root
hpp = []
def hchild(o, m, bevel=0.5):
    C.assign(o, m)
    C.finish(o, bevel=bevel, segments=2, angle=34.0)
    o.parent = hp
    parts.append(o); hpp.append(o)
    return o

hchild(C.lathe("B28_HP_BODY",
               [(0.0, -HP_L * 0.42), (HP_R - 3.0, -HP_L * 0.42),
                (HP_R, -HP_L * 0.36), (HP_R, HP_L * 0.10),
                (HP_R - 1.2, HP_L * 0.16), (HP_R - 1.2, HP_L * 0.30),
                (HP_R - 4.5, HP_L * 0.40), (HP_R - 6.0, HP_L * 0.46),
                (0.0, HP_L * 0.46)], seg=22), M["ESD_BODY"], bevel=0.6)
hchild(C.pipe("B28_HP_GRIP", HP_R + 0.9, HP_R - 0.4,
              -HP_L * 0.30, -HP_L * 0.02, seg=36), M["HANDGRIP"], bevel=0.35)
hchild(C.frustum("B28_HP_NOSE", HP_R - 6.0, 6.2,
                 HP_L * 0.46, HP_L * 0.60, seg=20), M["NOZZLE"], bevel=0.3)
hchild(C.pipe("B28_NOZZLE_COLLAR", 7.4, 5.6,
              HP_L * 0.58, HP_L * 0.66, seg=20), M["NOZZLE"], bevel=0.2)

# NOZZLE - separate child, swappable. This is what the learner aims.
noz_objs = {}
for nm, r in NOZ.items():
    o = C.lathe("B28_NOZZLE_" + nm,
                [(5.4, HP_L * 0.64), (5.4, HP_L * 0.70),
                 (r + 1.1, HP_L * 0.80), (r + 0.9, HP_L * 0.855),
                 (r, HP_L * 0.86), (r, HP_L * 0.855),
                 (r + 0.5, HP_L * 0.80), (4.6, HP_L * 0.70),
                 (4.6, HP_L * 0.64)], seg=18)
    hchild(o, M["NOZZLE"], bevel=0.12)
    noz_objs[nm] = o
    if nm != "5mm":
        o.hide_render = True
        o.hide_viewport = True

TIPY = HP_L * 0.865
tip = C.empty("B28_ANCHOR_TIP", (0.0, TIPY, 0.0), size=6.0)
tip.parent = hp

# emissive throat - intensity is driven by set temperature
throat = C.cyl("B28_NOZZLE_GLOW", NOZ["5mm"] - 0.35, TIPY - 5.0, TIPY - 0.4, seg=16)
gm = C.mat("MAT_NOZZLE_GLOW", "#FF7A2A", 0.0, 0.5,
           emission="#FF7A2A", emission_strength=14.0)
hchild(throat, gm, bevel=0.06)

# airflow cone: a gradient-alpha mesh, NOT a particle sim
cone = C.alpha_cone("B28_AIRFLOW", NOZ["5mm"] + 0.3, 8.6, 34.0, seg=18)
cone.location = (0.0, TIPY, 0.0)
cone.parent = hp
parts.append(cone)

# the 5 mm standoff guide the runtime toggles during the safe-distance beat
ring = C.pipe("B28_STANDOFF_5MM", 8.0, 6.6, 4.7, 5.3, seg=18)
ring.location = (0.0, TIPY, 0.0)
C.assign(ring, C.mat("MAT_STANDOFF", "#5CE08A", 0.0, 0.4,
                     emission="#5CE08A", emission_strength=4.0))
ring.parent = hp
ring.hide_render = True
ring.hide_viewport = True
parts.append(ring)

# pose the handpiece as the learner will see it working
hp.rotation_euler = (math.radians(34.0), 0.0, math.radians(202.0))
hp.location = (86.0, -74.0, 16.0)

# ------------------------------------------------------------------ hose
hose_pts = [(-46.0, 26.0, -BH / 2 + 12.0), (-6.0, -34.0, -BH / 2 + 8.0),
            (16.0, -96.0, -BH / 2 + 34.0), (26.0, -118.0, -BH / 2 + 74.0)]
cu = bpy.data.curves.new("B28_HOSE_CRV", "CURVE")
cu.dimensions = "3D"
cu.bevel_depth = 5.2
cu.bevel_resolution = 3
cu.resolution_u = 5
sp = cu.splines.new("BEZIER")
sp.bezier_points.add(len(hose_pts) - 1)
for i, p in enumerate(hose_pts):
    bp = sp.bezier_points[i]
    bp.co = p
    bp.handle_left_type = bp.handle_right_type = "AUTO"
hose = bpy.data.objects.new("B28_HOSE", cu)
bpy.context.scene.collection.objects.link(hose)
C.assign(hose, M["HOSE"])
hose.parent = root
parts.append(hose)

for nm, loc in (("DISPLAY", (0.0, -22.0, BH / 2 - 20.0)),
                ("BASE", (-BW / 2 - 14.0, 60.0, 0.0)),
                ("NOZZLE", (30.0, -150.0, -BH / 2 + 60.0))):
    C.empty("B28_ANCHOR_" + nm, loc, size=5.0).parent = root

# ------------------------------------------------------------------ states
def state(name):
    on = (name != "OFF")
    ready = (name == "READY")
    gm.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"] \
        .default_value = (0.0 if not on else (16.0 if ready else 6.0))
    cone.hide_render = not ready
    cone.hide_viewport = not ready
    C.log("state " + name)

# ANIM_B28_LIFT_TO_STAND - plays at the start and end of every rework
# procedure. It is the safety habit being drilled, not decoration.
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 45
stand = (BW / 2 + 20.0, 62.0, -BH / 2 + 74.0)
work = tuple(hp.location)
hp.location = stand
hp.rotation_euler = (math.radians(-64.0), 0.0, math.radians(184.0))
hp.keyframe_insert("location", frame=1)
hp.keyframe_insert("rotation_euler", frame=1)
hp.location = work
hp.rotation_euler = (math.radians(34.0), 0.0, math.radians(202.0))
hp.keyframe_insert("location", frame=45)
hp.keyframe_insert("rotation_euler", frame=45)
C.ease_out([hp])
C.push_nla([hp], "ANIM_B28_LIFT_TO_STAND", start=1)
sc.frame_set(45)

# ------------------------------------------------------------------ shots
C.lighting_rig(scale=210.0, k=30.0, cavity=False)
C.studio_world(strength=0.95)
C.reflector_cards(scale=210.0, strength=7.0)
C.set_look()
C.fix_clipping()

state("READY")
solid_parts = [o for o in parts if o.type == "MESH" and o is not cone
               and not o.hide_render]
cam = C.camera("B28_cam", (-150.0, -230.0, 130.0), (0, 20, 0), focal=95)
C.frame_camera(cam, solid_parts, margin=1.10, target=None, res=(1600, 1200))
C.auto_expose(cam, target=0.21)

tris = C.tri_count([o for o in parts if o.type == "MESH"])
C.log("LOD0 tris = %d  (budget 10000 - hose curve inflates this)" % tris)
C.viewport_setup(focus_size=200.0)
C.save_blend(os.path.join(C.OUT, "B28_HOTAIR.blend"))

SHOTS = [
 ("B28_shot1_hero",    (-150.0, -230.0, 130.0), None,  95, 1.10, "all",   "READY"),
 ("B28_shot2_handpiece", (-90.0, -150.0, 70.0), None, 105, 1.15, "hp",    "READY"),
 ("B28_shot3_nozzle",   (-38.0, -60.0, 26.0),   None, 125, 1.30, "nozzle","READY"),
 ("B28_shot4_display",  (-30.0, -160.0, 60.0),  None, 130, 1.18, "disp",  "OFF"),
 ("B28_shot5_standoff", (-70.0, -110.0, 40.0),  None, 120, 1.45, "nozzle","READY"),
]
def subj(key):
    if key == "hp":
        return [o for o in hpp if not o.hide_render]
    if key == "nozzle":
        return [noz_objs["5mm"], bpy.data.objects["B28_NOZZLE_COLLAR"],
                bpy.data.objects["B28_HP_NOSE"]]
    if key == "disp":
        return [disp, bez]
    return solid_parts

for nm, loc, tgt, f, mg, sk, st in SHOTS:
    state(st)
    if nm == "B28_shot5_standoff":
        ring.hide_render = False
        ring.hide_viewport = False
    cm = C.camera(nm + "_cam", loc, (0, 0, 0), focal=f)
    C.frame_camera(cm, subj(sk), margin=mg, target=tgt, res=(1600, 1200))
    C.render(cm, os.path.join(C.REN, nm + ".png"), res=(1600, 1200), samples=72)
    if nm == "B28_shot5_standoff":
        ring.hide_render = True
        ring.hide_viewport = True

state("READY")
glb = C.export_glb(os.path.join(C.GLB, "B28_HOTAIR_LOD0.glb"),
                   objects=[o for o in parts if o.type == "MESH"], draco=True)

C.report("B28_HOTAIR", {
 "asset": "B28_HOTAIR", "tris_lod0": tris, "tri_budget": 10000,
 "within_budget": tris <= 10000,
 "objects": len([o for o in parts if o.type == "MESH"]),
 "glb_kb": round(glb / 1024.0, 1),
 "exposure": round(bpy.context.scene.view_settings.exposure, 3),
 "nozzles": sorted(NOZ.keys()),
 "states": ["OFF", "HEATING", "READY"],
 "anim": ["ANIM_B28_LIFT_TO_STAND f1-45"],
 "display": "BLANK - no digits baked. Runtime draws temp/airflow (U02).",
 "airflow": "gradient-alpha cone mesh parented to B28_ANCHOR_TIP, not a sim",
 "standoff_guide": "B28_STANDOFF_5MM, hidden by default, runtime toggles",
 "renders": [s[0] for s in SHOTS],
})
print("[CG] B28 BUILD COMPLETE")
