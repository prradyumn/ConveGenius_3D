# =====================================================================
# B02_MAINBOARD - smartphone printed board assembly
# ConveGenius Mobile Charging Repair Simulation | HIGHEST-REUSE ASSET (7/18)
#
# Teaching job: this is not scenery, it is the MAP. Every fix in BC.3 begins
# with the learner locating a part ON this board. If the board is generic
# mush, "the IFC socket sits a short distance in from the port" is a sentence
# with no picture attached.
#
# THE ONE THING THAT MUST BE UNMISTAKABLE - four zones, in this order:
#   charging port (at the board EDGE) -> IFC socket (a short way in)
#   -> Charger IC / PMIC (mid-board, under a shield) -> battery connector
# A learner should be able to trace that path with a finger, labels off.
#
# Pad footprints survive with the part REMOVED, because Fix 2 and Fix 3 both
# show a bare cleaned pad and that shot only works if the pads exist alone.
# =====================================================================
import bpy, bmesh, math, os, sys, random

sys.path.insert(0, os.path.join(os.path.expanduser("~"), "ConveGenius_3D", "scripts"))
import cg_lib as C

random.seed(20260821)                 # deterministic rebuild

BZ = 0.90                             # board thickness
MASK = 0.022                          # solder-mask lip
ZONES = {"PORT": (-54.0, 0.0), "IFC": (-38.0, 5.0),
         "PMIC": (-4.0, -3.0), "BATTCONN": (32.0, 7.0)}

C.setup_scene("B02_MAINBOARD")
M = C.house_materials()
M["MASK"]   = C.mat("MAT_PCB_MASK_V2", "#0D4A38", 0.0, 0.40, coat=0.22, coat_rough=0.22)
M["CORE"]   = C.mat("MAT_FR4_CORE_V2", "#BBA579", 0.0, 0.66)
M["SILK"]   = C.mat("MAT_SILK_V2", "#E4E6E2", 0.0, 0.58)
M["TRACE"]  = C.mat("MAT_TRACE_HIGHLIGHT", "#C98A48", 1.0, 0.34)
M["SHIELD"] = C.mat("MAT_SHIELD_NICKEL", "#9DA1A6", 1.0, 0.44, anisotropic=0.30)
M["CERAM"]  = C.mat("MAT_PASSIVE_CERAMIC", "#2B2724", 0.0, 0.50)
M["CAPTAN"] = C.mat("MAT_PASSIVE_TAN", "#8A6A45", 0.0, 0.46)
M["OLDSOL"] = C.mat("MAT_OLD_SOLDER", "#8E9195", 1.0, 0.72)


def mask_detail(m):
    """A real board is not one flat green: mottling, a glossier finish over
    dense copper, faint flux staining near the connectors, and trace relief.
    A flat green texture is an auto-reject."""
    try:
        nt = m.node_tree
        b = nt.nodes.get("Principled BSDF")
        tc = nt.nodes.new("ShaderNodeTexCoord")
        # trace relief - directional, so it reads as routing not noise
        w = nt.nodes.new("ShaderNodeTexWave")
        w.wave_type = "BANDS"
        w.bands_direction = "X"
        w.inputs["Scale"].default_value = 26.0
        w.inputs["Distortion"].default_value = 12.0
        w.inputs["Detail"].default_value = 4.0
        n2 = nt.nodes.new("ShaderNodeTexNoise")
        n2.inputs["Scale"].default_value = 9.0
        n2.inputs["Detail"].default_value = 7.0
        mixn = nt.nodes.new("ShaderNodeMix")
        mixn.data_type = "FLOAT"
        mixn.inputs["Factor"].default_value = 0.45
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.32
        bump.inputs["Distance"].default_value = 0.02
        rr = nt.nodes.new("ShaderNodeMapRange")
        rr.inputs["To Min"].default_value = 0.30
        rr.inputs["To Max"].default_value = 0.50
        nt.links.new(tc.outputs["Object"], w.inputs["Vector"])
        nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
        nt.links.new(w.outputs["Fac"], mixn.inputs[2])
        nt.links.new(n2.outputs["Fac"], mixn.inputs[3])
        nt.links.new(mixn.outputs[0], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
        nt.links.new(n2.outputs["Fac"], rr.inputs["Value"])
        nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    except Exception as e:
        C.log("mask_detail fallback " + str(e))

mask_detail(M["MASK"])

root = C.empty("B02_MAINBOARD", (0, 0, 0), size=20.0)
parts = []
def child(o, m, bevel=0.06, seg=2, angle=32.0, parent=None):
    C.assign(o, m)
    C.finish(o, bevel=bevel, segments=seg, angle=angle)
    o.parent = parent or root
    parts.append(o)
    return o


def plate(name, poly, z0, z1):
    """Extrude an XY outline along Z. A real phone board has an irregular
    outline with notches - a plain rectangle reads as a placeholder."""
    bm = bmesh.new()
    V0 = [bm.verts.new((p[0], p[1], z0)) for p in poly]
    V1 = [bm.verts.new((p[0], p[1], z1)) for p in poly]
    bm.faces.new(V0[::-1]); bm.faces.new(V1)
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((V0[i], V0[j], V1[j], V1[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o

# irregular board outline: battery notch on the lower edge, chamfered corners
OUTLINE = [(-60, -22), (-56, -25), (18, -25), (22, -21), (22, -8),
           (46, -8), (52, -14), (58, -14), (60, -10), (60, 20),
           (56, 25), (-52, 25), (-60, 18)]

# laminated edge: FR4 core with a thin mask lip top and bottom
core = plate("B02_BOARD_CORE", OUTLINE, 0.0, BZ)
child(core, M["CORE"], bevel=0.10, seg=2)
for tag, z in (("TOP", BZ + 0.007 + MASK), ("BOT", -0.007)):
    lip = plate("B02_BOARD_MASK_" + tag, OUTLINE,
                z - (MASK if tag == "TOP" else 0.0),
                z + (0.0 if tag == "TOP" else -MASK))
    lip.scale = (0.9985, 0.9962, 1.0)
    child(lip, M["MASK"], bevel=0.05, seg=2)

ZTOP = BZ + 0.031

# ------------------------------------------------------------------ vias
# real plated holes, not painted dots. Shared mesh data = cheap instancing.
via_src = C.pipe("B02_VIA_SRC", 0.155, 0.085, -0.02, BZ + 0.02, seg=8)
C.assign(via_src, M["COPPER_BARE"])
C.finish(via_src, bevel=0.012)
via_src.parent = root
parts.append(via_src)
vias = 0
for gx in range(-26, 27):
    for gy in range(-5, 6):
        if random.random() > 0.30:
            continue
        x, y = gx * 2.15 + random.uniform(-.3, .3), gy * 2.15 + random.uniform(-.3, .3)
        if not (-57 < x < 57 and -21 < y < 22):
            continue
        if abs(x - ZONES["PMIC"][0]) < 7 and abs(y - ZONES["PMIC"][1]) < 6:
            continue
        o = bpy.data.objects.new("B02_VIA_%03d" % vias, via_src.data)
        bpy.context.scene.collection.objects.link(o)
        o.location = (x, y, 0.0)
        o.parent = root
        parts.append(o)
        vias += 1
C.log("vias %d (shared mesh)" % vias)

# ------------------------------------------------------------------ passives
p0402 = C.box("B02_P0402_SRC", 1.00, 0.50, 0.35, (0, 0, ZTOP + 0.175))
C.assign(p0402, M["CERAM"]); C.finish(p0402, bevel=0.03)
p0402.parent = root; parts.append(p0402)
p0201 = C.box("B02_P0201_SRC", 0.60, 0.30, 0.25, (0, 0, ZTOP + 0.125))
C.assign(p0201, M["CAPTAN"]); C.finish(p0201, bevel=0.02)
p0201.parent = root; parts.append(p0201)
np_ = 0
for i in range(150):
    x = random.uniform(-56, 57); y = random.uniform(-21, 22)
    if abs(x - ZONES["PMIC"][0]) < 8 and abs(y - ZONES["PMIC"][1]) < 7:
        continue
    if abs(x - ZONES["PORT"][0]) < 6:
        continue
    src = p0402 if random.random() < 0.55 else p0201
    o = bpy.data.objects.new("B02_PASSIVE_%03d" % np_, src.data)
    bpy.context.scene.collection.objects.link(o)
    o.location = (x, y, 0.0)
    o.rotation_euler = (0, 0, math.radians(random.choice([0, 0, 0, 90])))
    o.parent = root; parts.append(o); np_ += 1
C.log("passives %d (2 shared meshes)" % np_)

# ------------------------------------------------------------------ zones
def pad_row(tag, cx, cy, n, pitch, sx, sy, rot=0.0, mtl=None, z=ZTOP):
    made = []
    for i in range(n):
        off = (i - (n - 1) / 2.0) * pitch
        px, py = (cx + off, cy) if rot == 0.0 else (cx, cy + off)
        o = C.box("B02_PAD_%s_%02d" % (tag, i), sx, sy, 0.035,
                  (px, py, z + 0.0175))
        child(o, mtl or M["GOLD_HARD"], bevel=0.008)
        made.append(o)
    return made

def bga_field(tag, cx, cy, nx, ny, pitch, r, mtl):
    made = []
    src = None
    for iy in range(ny):
        for ix in range(nx):
            x = cx + (ix - (nx - 1) / 2.0) * pitch
            y = cy + (iy - (ny - 1) / 2.0) * pitch
            if src is None:
                src = C.cyl("B02_%s_BALL_SRC" % tag, r, 0.0, 0.10, seg=10)
                C.assign(src, mtl); C.finish(src, bevel=0.012)
                src.rotation_euler = (math.radians(90), 0, 0)
                src.location = (x, y, ZTOP + 0.02)
                src.parent = root; parts.append(src); made.append(src)
                continue
            o = bpy.data.objects.new("B02_%s_BALL_%02d_%02d" % (tag, ix, iy), src.data)
            bpy.context.scene.collection.objects.link(o)
            o.rotation_euler = (math.radians(90), 0, 0)
            o.location = (x, y, ZTOP + 0.02)
            o.parent = root; parts.append(o); made.append(o)
    return made

# PORT zone: matches B05's leg pads + shield tabs so B05 drops straight in
px, py = ZONES["PORT"]
port_pads = pad_row("PORT_LEG", px + 2.0, py, 2, 5.2, 0.95, 1.30)
port_pads += pad_row("PORT_TAB", px + 5.6, py, 2, 9.1, 0.55, 1.10)
# IFC zone: 12 landing pads, 0.5 mm pitch, matching B10's flex tail
ix, iy = ZONES["IFC"]
ifc_pads = pad_row("IFC", ix, iy, 12, 0.50, 0.30, 1.10)
ifc_anchor = pad_row("IFC_ANCHOR", ix, iy, 2, 7.4, 0.80, 0.80)
# PMIC zone: BGA ball field under the Charger IC (Fix 4 works on these)
mx, my = ZONES["PMIC"]
pmic_balls = bga_field("PMIC", mx, my, 7, 7, 0.42, 0.14, M["SOLDER_GOOD"])
# battery connector zone
bx, by = ZONES["BATTCONN"]
bc_pads = pad_row("BATTCONN", bx, by, 6, 0.90, 0.55, 1.40)

# test points
for i in range(18):
    x = random.uniform(-50, 55); y = random.uniform(-19, 21)
    o = C.cyl("B02_TESTPAD_%02d" % i, 0.42, 0.0, 0.03, seg=12)
    o.rotation_euler = (math.radians(90), 0, 0)
    o.location = (x, y, ZTOP + 0.015)
    child(o, M["GOLD_HARD"], bevel=0.008)

# ------------------------------------------------------------------ shields
shields = {}
for tag, cx, cy, sx, sy, h in (("PMIC", mx, my, 15.0, 13.0, 1.05),
                               ("RF", 24.0, -12.0, 17.0, 9.0, 0.95),
                               ("AUX", -22.0, -14.0, 12.0, 8.0, 0.85)):
    can = C.box("B02_SHIELD_" + tag, sx, sy, h, (cx, cy, ZTOP + h / 2))
    child(can, M["SHIELD"], bevel=0.10, seg=2)
    shields[tag] = can
shields["PMIC"].hide_render = True      # Fix 4 and 5 work underneath it
shields["PMIC"].hide_viewport = True

# ------------------------------------------------------------------ charging path
# five highlight traces on their own material slot, so the runtime can light
# them in sequence for the I04 signal overlay
for i in range(5):
    yo = (i - 2) * 0.55
    seg_pts = [(px + 7.0, py + yo), (ix - 2.0, iy + yo * 0.8),
               (ix + 3.0, iy + yo * 0.8), (mx - 8.0, my + yo),
               (mx + 8.0, my + yo), (bx - 4.0, by + yo)]
    for k in range(len(seg_pts) - 1):
        a, b = seg_pts[k], seg_pts[k + 1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 0.2:
            continue
        o = C.box("B02_TRACE_%d_%d" % (i, k), L, 0.22, 0.030,
                  ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, ZTOP + 0.012))
        o.rotation_euler = (0, 0, math.atan2(dy, dx))
        child(o, M["TRACE"], bevel=0.006)

# ------------------------------------------------------------------ silkscreen
def silk(txt, x, y, size=1.15, rot=0.0):
    try:
        cu = bpy.data.curves.new("B02_SILK_" + txt, "FONT")
        cu.body = txt
        cu.size = size
        cu.align_x = "CENTER"
        cu.align_y = "CENTER"
        cu.extrude = 0.004
        o = bpy.data.objects.new("B02_SILK_" + txt, cu)
        bpy.context.scene.collection.objects.link(o)
        o.location = (x, y, ZTOP + 0.012)
        o.rotation_euler = (0, 0, rot)
        C.assign(o, M["SILK"])
        o.parent = root
        parts.append(o)
        return o
    except Exception as e:
        C.log("silk skipped " + str(e))
        return None

for txt, x, y in (("J1", px + 2.0, py - 4.2), ("IFC", ix, iy - 3.2),
                  ("U301", mx, my + 9.2), ("BAT", bx, by - 3.6),
                  ("C118", -14.0, 12.0), ("R204", 8.0, 18.0),
                  ("CG-MB-REV-A", 40.0, 21.0)):
    silk(txt, x, y, size=1.5 if len(txt) < 5 else 1.1)

# ------------------------------------------------------------------ anchors
# B02's "one thing that must be unmistakable" is the four zones reading as a
# traceable path. Real sized zone plates on their own material slot, hidden by
# default, so the runtime (or a callout render) can light them in sequence.
M["ZONE"] = C.mat("MAT_ZONE_TINT", "#2FA8FF", 0.0, 0.42,
                  emission="#2FA8FF", emission_strength=1.4)
ZONE_SIZE = {"PORT": (11.0, 7.0), "IFC": (8.5, 4.5),
             "PMIC": (16.5, 14.5), "BATTCONN": (7.5, 4.5)}
zone_plates = {}
for tag, (x, y) in ZONES.items():
    C.empty("B02_ANCHOR_" + tag, (x, y, ZTOP + 4.5), size=1.6).parent = root
    sx, sy = ZONE_SIZE[tag]
    z = C.box("B02_ZONE_" + tag, sx, sy, 0.02, (x, y, ZTOP + 0.055))
    C.assign(z, M["ZONE"])
    z.parent = root
    z.hide_render = True
    z.hide_viewport = True
    zone_plates[tag] = z
    parts.append(z)

# ------------------------------------------------------------------ states
# PAD_BARE vs PAD_CLEANED - this pair IS the lesson of Fix 2 step 5
bare = C.collection("B02_STATE_PAD_BARE")
for src in ifc_pads + port_pads:
    d = src.copy(); d.data = src.data.copy()
    d.name = src.name.replace("B02_PAD_", "B02_BAREPAD_")
    bare.objects.link(d)
    d.scale = (1.0, 1.0, random.uniform(2.6, 5.4))
    d.location = (src.location.x + random.uniform(-.03, .03),
                  src.location.y, src.location.z + 0.03)
    C.assign(d, M["OLDSOL"])
    d.parent = root
bare.hide_render = True
bare.hide_viewport = True

dusty = C.collection("B02_STATE_DUSTY")
dusty.hide_render = True
dusty.hide_viewport = True

C.log("zones wired: " + ", ".join(sorted(ZONES.keys())))

# ------------------------------------------------------------------ shots
C.lighting_rig(scale=95.0, k=30.0, cavity=False)
C.studio_world(strength=0.90)
C.reflector_cards(scale=95.0, strength=6.0)
# a board is a flat subject: it needs a genuinely overhead source or the whole
# top face sits in grazing light and renders near-black
C.light_aim("CG_OVERHEAD", (14.0, -28.0, 190.0), (0.0, 0.0, 0.0),
            energy_k=30.0, size_rel=1.9, scale=95.0, power=1.15)
C.set_look()
C.fix_clipping()

vis = [o for o in parts if o.type in ("MESH", "FONT") and not o.hide_render
       and not o.name.startswith("CG_")]
edge_subj = [o for o in parts if "PORT" in o.name or "TRACE_2" in o.name]

cam = C.camera("B02_cam", (-30.0, -90.0, 70.0), (0, 0, 0), focal=90)
C.frame_camera(cam, vis, margin=1.06, res=(2000, 1200))
C.auto_expose(cam, target=0.21)

tris = C.tri_count([o for o in parts if o.type == "MESH"])
C.log("LOD0 tris = %d  (budget 45000)" % tris)
C.viewport_setup(focus_size=100.0)
C.save_blend(os.path.join(C.OUT, "B02_MAINBOARD.blend"))

SHOTS = [
 ("B02_shot1_topdown",  (3.0, -30.0, 104.0), 105, 1.05, "all",  (2000, 1100)),
 ("B02_shot3_hero",     (-40.0, -95.0, 62.0), 88, 1.06, "all",  (2000, 1200)),
 ("B02_shot4_edge",     (-70.0, -34.0, 16.0), 120, 1.35, "edge", (1800, 1200)),
 ("B02_shot6_shield",   (-24.0, -46.0, 34.0), 105, 1.20, "pmic", (1800, 1200)),
]
def subj(k):
    if k == "edge":
        return edge_subj or vis
    if k == "pmic":
        return [shields["PMIC"]] + pmic_balls
    return vis

for nm, loc, f, mg, sk, res in SHOTS:
    if sk == "pmic":
        shields["PMIC"].hide_render = False
        shields["PMIC"].hide_viewport = False
    cm = C.camera(nm + "_cam", loc, (0, 0, 0), focal=f)
    C.frame_camera(cm, subj(sk), margin=mg, res=res)
    C.auto_expose(cm, target=0.21)
    C.render(cm, os.path.join(C.REN, nm + ".png"), res=res, samples=64)
    if sk == "pmic":
        shields["PMIC"].hide_render = True
        shields["PMIC"].hide_viewport = True

# shot 2: the four zones lit, so the port -> IFC -> PMIC -> battery path is
# traceable with a finger. This is the graphic BC.1 scene 1 actually needs.
for z in zone_plates.values():
    z.hide_render = False
    z.hide_viewport = False
cm = C.camera("B02_shot2_zones_cam", (4.0, -34.0, 104.0), (0, 0, 0), focal=105)
C.frame_camera(cm, vis, margin=1.05, res=(2000, 1100))
C.auto_expose(cm, target=0.21)
C.render(cm, os.path.join(C.REN, "B02_shot2_zones.png"),
         res=(2000, 1100), samples=64)
for z in zone_plates.values():
    z.hide_render = True
    z.hide_viewport = True

# shot 5: bare pad vs cleaned pad, matched camera
cm = C.camera("B02_shot5_cam", (-44.0, -22.0, 13.0), (ix, iy, ZTOP), focal=135)
C.frame_camera(cm, ifc_pads, margin=1.9, target=(ix, iy, ZTOP + 0.2),
               res=(1600, 1200))
C.auto_expose(cm, target=0.22)
C.render(cm, os.path.join(C.REN, "B02_shot5b_pad_cleaned.png"),
         res=(1600, 1200), samples=72)
bare.hide_render = False
bare.hide_viewport = False
for o in bare.objects:
    o.hide_render = False
    o.hide_viewport = False
C.render(cm, os.path.join(C.REN, "B02_shot5a_pad_bare.png"),
         res=(1600, 1200), samples=72)
bare.hide_render = True
for o in bare.objects:
    o.hide_render = True

# glTF core has no per-node visibility, and the exporter drops render-hidden
# objects entirely. Ship the zone plates VISIBLE and let the runtime hide them
# - that is how a toggleable overlay is supposed to work.
for z in zone_plates.values():
    z.hide_render = False
    z.hide_viewport = False

glb = C.export_glb(os.path.join(C.GLB, "B02_MAINBOARD_LOD0.glb"),
                   objects=[o for o in parts if o.type == "MESH"], draco=True)

C.report("B02_MAINBOARD", {
 "asset": "B02_MAINBOARD", "tris_lod0": tris, "tri_budget": 45000,
 "within_budget": tris <= 45000,
 "objects": len(parts), "vias": vias, "passives": np_,
 "glb_kb": round(glb / 1024.0, 1),
 "exposure": round(bpy.context.scene.view_settings.exposure, 3),
 "zones": ZONES,
 "footprints": {"PORT": len(port_pads), "IFC": len(ifc_pads),
                "PMIC_balls": len(pmic_balls), "BATTCONN": len(bc_pads)},
 "states": ["CLEAN (default)", "PAD_BARE", "PAD_CLEANED", "DUSTY (stub)"],
 "trace_material": "MAT_TRACE_HIGHLIGHT - own slot for the I04 signal overlay",
 "dims_used": {"board_mm": "irregular outline, ~120 x 50 x 0.90, "
                           "battery notch on the lower edge",
               "via_dia_mm": 0.31, "passives": "0402 + 0201"},
 "renders": [s[0] for s in SHOTS] + ["B02_shot5a_pad_bare",
                                     "B02_shot5b_pad_cleaned"],
})
print("[CG] B02 BUILD COMPLETE")
