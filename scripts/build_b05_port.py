# =====================================================================
# B05_PORT - USB-C female receptacle, exploded-capable
# ConveGenius Mobile Charging Repair Simulation | HERO ASSET
#
# Teaching job: BC.1 scene 2 names NINE components inside a part 8 mm wide.
# "The charging port looks like a simple slot - but inside, there's a small
# city of pins." This asset is how that sentence lands.
#
# DIMENSIONS (opening + depth confirmed against USB-C spec / Wikipedia USB-C;
#   shell outer      8.94 x 3.16 mm, depth 7.10 mm
#   cavity opening   8.34 x 2.56 mm, 6.20 mm deep  (DATASHEET-CONFIRMED)
#   tongue           6.60 x 0.70 mm, length 4.75 mm
#   contacts         24, 12 per row, 0.30 mm wide, 0.50 mm pitch
# Cross-section is an OBROUND (stadium), not a rounded rectangle.
#
# The tongue is LIGHT plastic on purpose - real USB-C tongues are white so the
# gold contacts stand out. That is both accurate and the whole teaching point.
# =====================================================================
import bpy, bmesh, math, os, sys

sys.path.insert(0, os.path.join(os.path.expanduser("~"), "ConveGenius_3D", "scripts"))
import cg_lib as C

SH_W, SH_H, SH_D = 8.94, 3.16, 7.10
CV_W, CV_H       = 8.34, 2.56
TG_W, TG_T       = 6.60, 0.70
TG_Y0, TG_Y1     = 1.50, 6.25
PIN_W, PIN_PITCH = 0.30, 0.50
PIN_Y0, PIN_Y1   = 1.85, 5.80
PIN_T            = 0.10
HOUS_Y0          = 6.20
CAPS             = 20

GRP_A = ["GND","SS","SS","VBUS","CC","DATA","DATA","SBU","VBUS","SS","SS","GND"]
LBL_A = ["GND","TX1+","TX1-","VBUS","CC1","D+","D-","SBU1","VBUS","RX2-","RX2+","GND"]
LBL_B = ["GND","TX2+","TX2-","VBUS","CC2","D+","D-","SBU2","VBUS","RX1-","RX1+","GND"]

# =====================================================================
C.setup_scene("B05_PORT")
M = C.house_materials()

# tongue: light LCP so the contacts read. Slight warm grey, not pure white.
M["TONGUE_LCP"] = C.mat("MAT_TONGUE_LCP", "#A9A8A1", 0.0, 0.46)
# housing lifted off pure black so the cavity is not a void
M["HOUSING_LCP"] = C.mat("MAT_HOUSING_LCP_V2", "#28282C", 0.0, 0.47)

def brush_steel(m):
    """Micro-scratches and a drawn-shell grain. This port has had a cable
    pushed into it a thousand times, and that wear is a teaching detail."""
    try:
        nt = m.node_tree
        bsdf = nt.nodes.get("Principled BSDF")
        coord = nt.nodes.new("ShaderNodeTexCoord"); coord.location = (-1200, -200)
        mp = nt.nodes.new("ShaderNodeMapping"); mp.location = (-1000, -200)
        mp.inputs["Scale"].default_value = (1.0, 26.0, 1.0)     # stretch = brushed
        tex = nt.nodes.new("ShaderNodeTexNoise"); tex.location = (-800, -200)
        tex.inputs["Scale"].default_value = 45.0
        tex.inputs["Detail"].default_value = 6.0
        rng = nt.nodes.new("ShaderNodeMapRange"); rng.location = (-560, -200)
        rng.inputs["To Min"].default_value = 0.22
        rng.inputs["To Max"].default_value = 0.40
        bump = nt.nodes.new("ShaderNodeBump"); bump.location = (-560, -460)
        bump.inputs["Strength"].default_value = 0.15
        nt.links.new(coord.outputs["Object"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Fac"], rng.inputs["Value"])
        nt.links.new(rng.outputs["Result"], bsdf.inputs["Roughness"])
        nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        C.log("steel: brushed grain + micro-scratch bump")
    except Exception as e:
        C.log("steel shader fallback: " + str(e))

def gold_variation(m):
    """Hard gold over nickel. Pale, never uniform."""
    try:
        nt = m.node_tree
        bsdf = nt.nodes.get("Principled BSDF")
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 700.0
        tex.inputs["Detail"].default_value = 4.0
        rng = nt.nodes.new("ShaderNodeMapRange")
        rng.inputs["To Min"].default_value = 0.23
        rng.inputs["To Max"].default_value = 0.35
        nt.links.new(tex.outputs["Fac"], rng.inputs["Value"])
        nt.links.new(rng.outputs["Result"], bsdf.inputs["Roughness"])
    except Exception:
        pass

brush_steel(M["STEEL_SHELL"])
for g in ("GND", "VBUS", "CC", "DATA", "SBU", "SS"):
    gold_variation(M["PIN_" + g])

# ------------------------------------------------------------------ build
root = C.empty("B05_PORT", (0, 0, 0), size=2.0)
parts = []

def child(o, m, bevel=0.02, seg=2, angle=30.0):
    C.assign(o, m)
    C.finish(o, bevel=bevel, segments=seg, angle=angle)
    o.parent = root
    parts.append(o)
    return o

outer = C.obround(SH_W, SH_H, CAPS)
inner = C.obround(CV_W, CV_H, CAPS)
shell = C.tube("B05_SHELL", outer, inner, 0.0, SH_D, True, True)
child(shell, M["STEEL_SHELL"], bevel=0.040, seg=3, angle=22.0)

# folded-shell seam. A real stamped shell has a visible draw line; without it
# the top face is a big featureless gradient and reads as untextured 3D.
seam = C.box("B05_SHELL_SEAM", 0.05, SH_D - 0.30, 0.022,
             loc=(0.0, SH_D / 2.0, SH_H / 2 - 0.018))
child(seam, C.mat("MAT_STEEL_SEAM", "#7E8185", 1.0, 0.42), bevel=0.006)

for side, sx in (("L", -1.0), ("R", 1.0)):
    t = C.box("B05_SHELL_TAB_" + side, 0.40, 1.00, 0.28,
              loc=(sx * (SH_W / 2 + 0.05), 5.40, -SH_H / 2 + 0.05))
    child(t, M["STEEL_SHELL"], bevel=0.03)

hous = C.solid("B05_HOUSING", C.obround(CV_W - 0.05, CV_H - 0.05, CAPS),
               HOUS_Y0, SH_D - 0.05)
child(hous, M["HOUSING_LCP"], bevel=0.03)

tongue = C.solid("B05_TONGUE", C.rounded_rect(TG_W, TG_T, 0.15, caps=6),
                 TG_Y0, TG_Y1)
child(tongue, M["TONGUE_LCP"], bevel=0.028, seg=3)

# ---- 24 SEPARATE pin objects. "Each pin lights up sequentially" needs it.
x0 = -(PIN_PITCH * 11) / 2.0
pin_objs = {}
for i in range(12):
    xa = x0 + i * PIN_PITCH
    xb = -xa                      # Row B mirrored: A1 and B12 share an X.
    for row, x, lbl in (("A", xa, LBL_A[i]), ("B", xb, LBL_B[i])):
        grp = GRP_A[i]
        # proud of the tongue face by 0.05 so it catches the key light
        z = (TG_T / 2 + PIN_T / 2 - 0.05) * (1.0 if row == "A" else -1.0)
        nm = "B05_PIN_%s%02d" % (row, i + 1)
        p = C.box(nm, PIN_W, PIN_Y1 - PIN_Y0, PIN_T,
                  loc=(x, (PIN_Y0 + PIN_Y1) / 2.0, z))
        child(p, M["PIN_" + grp], bevel=0.018, seg=2, angle=38.0)
        p["cg_signal"] = lbl
        p["cg_group"] = grp
        pin_objs[nm] = p
        C.empty("B05_ANCHOR_%s%02d" % (row, i + 1),
                (x, PIN_Y0 + 0.4, z + (1.0 if row == "A" else -1.0)),
                size=0.12).parent = root
C.log("pins built: %d" % len(pin_objs))

for side, sx in (("L", -1.0), ("R", 1.0)):
    leg = C.box("B05_LEG_" + side, 0.50, 1.40, 0.85,
                loc=(sx * 2.60, 2.20, -1.90))
    child(leg, M["STEEL_SHELL"], bevel=0.03)
    pad = C.box("B05_LEGPAD_" + side, 0.72, 1.00, 0.09,
                loc=(sx * 2.60, 2.20, -2.38))
    child(pad, M["SOLDER_GOOD"], bevel=0.025)

gk = C.tube("B05_GASKET", C.obround(SH_W + 0.70, SH_H + 0.70, CAPS),
            C.obround(SH_W + 0.02, SH_H + 0.02, CAPS), -0.38, 0.0)
child(gk, M["RUBBER"], bevel=0.05)
gk.hide_render = True            # storyboard: "on water-resistant models"
gk.hide_viewport = True

for nm, loc in (("SHELL", (SH_W / 2 + 1.2, 1.0, SH_H / 2 + 0.6)),
                ("HOUSING", (0.0, SH_D - 0.4, SH_H / 2 + 1.2)),
                ("TONGUE", (0.0, TG_Y0 + 0.6, 0.0)),
                ("LEGS", (SH_W / 2 + 0.6, 2.2, -SH_H / 2 - 1.4)),
                ("GASKET", (-SH_W / 2 - 1.2, -0.2, 0.0)),
                ("TABS", (SH_W / 2 + 1.4, 5.55, -SH_H / 2 - 0.5))):
    C.empty("B05_ANCHOR_" + nm, loc, size=0.25).parent = root

# =====================================================================
# ANIM_B05_EXPLODE  f1-90, reversible (play backwards to assemble)
# =====================================================================
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 90
EXPL = {"B05_SHELL": (0.0, -3.4, 6.0), "B05_SHELL_TAB_L": (-2.4, -3.4, 6.0),
        "B05_SHELL_TAB_R": (2.4, -3.4, 6.0), "B05_HOUSING": (0.0, 5.6, 0.0),
        "B05_LEG_L": (-3.2, 0.0, -2.4), "B05_LEG_R": (3.2, 0.0, -2.4),
        "B05_LEGPAD_L": (-3.9, 0.0, -3.2), "B05_LEGPAD_R": (3.9, 0.0, -3.2)}
def kf(o, f, loc):
    o.location = loc
    o.keyframe_insert("location", frame=f)
for name, off in EXPL.items():
    o = bpy.data.objects.get(name)
    if not o:
        continue
    r = tuple(o.location)
    kf(o, 1, r); kf(o, 28, r)
    kf(o, 90, (r[0] + off[0], r[1] + off[1], r[2] + off[2]))
for o in list(pin_objs.values()) + [bpy.data.objects["B05_TONGUE"]]:
    r = tuple(o.location)
    kf(o, 1, r); kf(o, 44, r)
    kf(o, 90, (r[0], r[1] - 1.6, r[2] - 3.8))
C.ease_out(parts)
# one NLA track name => ONE glTF clip. Default ACTIONS mode gave 33 separate
# clips (one per object), which three.js would have to sync by hand.
C.push_nla(parts, "ANIM_B05_EXPLODE", start=1)
C.log("ANIM_B05_EXPLODE 1-90 keyed")

# =====================================================================
# STATE_BENT_PINS - Fix 1 vs Fix 2 branches on "dust or physical damage?"
# =====================================================================
bent = C.collection("B05_STATE_BENT_PINS")
for tag, dz, dx, rot in (("A05", 0.17, 0.07, 15.0),
                         ("A06", 0.24, -0.11, -21.0),
                         ("A07", 0.10, 0.15, 9.0)):
    src = pin_objs["B05_PIN_" + tag]
    d = src.copy(); d.data = src.data.copy()
    d.name = "B05_BENT_PIN_" + tag
    bent.objects.link(d)
    d.location = (src.location.x + dx, src.location.y, src.location.z + dz)
    d.rotation_euler = (0.0, math.radians(rot), math.radians(rot * 0.4))
    d.parent = root
bent.hide_render = True
bent.hide_viewport = True
C.log("STATE_BENT_PINS: 3 deflected contacts")

# =====================================================================
# lighting + shot list
# =====================================================================
C.lighting_rig(scale=11.0, k=30.0, cavity=False)
C.studio_world(strength=0.95); C.reflector_cards(scale=11.0, strength=7.0); C.set_look()
# dedicated cavity light: front, slightly high, aimed at the tongue so the
# interior reads as a metal-lined box with a blade in it, not a black hole
C.light_aim("CG_CAVITY", (0.0, -26.0, 7.0), (0.0, 2.6, 0.0),
            energy_k=34.0, size_rel=0.85, scale=11.0, power=1.10)
C.light_aim("CG_PINGRAZE", (-4.0, -16.0, 9.5), (0.0, 2.9, 0.40),
            energy_k=34.0, size_rel=0.55, scale=11.0, power=1.25)
C.fix_clipping()

PINS_AND_TONGUE = list(pin_objs.values()) + [bpy.data.objects["B05_TONGUE"]]

CAMS = {
 "B05_shot1_hero":     dict(dir=(-1.00, -1.35, 0.72), f=100, frame=1,
                            subj="all",   margin=1.10, tgt=(0, 2.6, 0)),
 "B05_shot2_cavity":   dict(dir=(0.00, -1.00, 0.52), f=115, frame=1,
                            subj="pins",  margin=1.32, tgt=(0, 2.6, 0)),
 "B05_shot3_exploded": dict(dir=(-0.85, -1.25, 0.80), f=85,  frame=90,
                            subj="all",   margin=1.08, tgt=None),
 "B05_shot4_pinrow":   dict(dir=(-0.38, -1.00, 0.60), f=120, frame=1,
                            subj="pins",  margin=1.55, tgt=None),
 "B05_shot5_topdown":  dict(dir=(0.02, -0.14, 1.00), f=105, frame=1,
                            subj="all",   margin=1.08, tgt=(0, 3.0, 0)),
 "B05_shot6_shell":    dict(dir=(-0.95, -1.20, 0.62), f=105, frame=60,
                            subj="all",   margin=1.10, tgt=None),
}
cams = {}
for nm, d in CAMS.items():
    loc = tuple(v * 30.0 for v in d["dir"])
    cams[nm] = C.camera(nm, loc, (0, 2.6, 0), focal=d["f"], dof=False)

def subject(key):
    if key == "shell":
        return [bpy.data.objects["B05_SHELL"]]
    if key == "pins":
        return PINS_AND_TONGUE
    return [o for o in parts if not o.hide_render]

# frame + auto-expose on the hero, then render the set
sc.frame_set(1)
C.frame_camera(cams["B05_shot1_hero"], subject("all"),
               margin=1.10, target=(0, 2.6, 0), res=(1600, 1200))
C.auto_expose(cams["B05_shot1_hero"], target=0.21)

tris = C.tri_count(parts)
C.log("LOD0 tris = %d  (budget 30000)" % tris)
C.viewport_setup(focus_size=10.0)
C.save_blend(os.path.join(C.OUT, "B05_PORT.blend"))

for nm, d in CAMS.items():
    sc.frame_set(d["frame"])
    C.frame_camera(cams[nm], subject(d["subj"]), margin=d["margin"],
                   target=d["tgt"], res=(1600, 1200))
    C.render(cams[nm], os.path.join(C.REN, nm + ".png"),
             res=(1600, 1200), samples=80)

sc.frame_set(1)
glb = C.export_glb(os.path.join(C.GLB, "B05_PORT_LOD0.glb"),
                   objects=parts, draco=True)

C.report("B05_PORT", {
 "asset": "B05_PORT",
 "tris_lod0": tris, "tri_budget": 30000, "within_budget": tris <= 30000,
 "objects": len(parts), "pins": len(pin_objs),
 "glb_bytes": glb, "glb_kb": round(glb / 1024.0, 1),
 "exposure": round(bpy.context.scene.view_settings.exposure, 3),
 "dims_used": {"shell_outer_mm": [SH_W, SH_H, SH_D], "cavity_mm": [CV_W, CV_H],
               "wall_mm": round((SH_W - CV_W) / 2, 3),
               "tongue_mm": [TG_W, TG_T, TG_Y1 - TG_Y0],
               "contacts": 24, "pitch_mm": PIN_PITCH, "contact_w_mm": PIN_W,
               "source": "opening 8.34x2.56x6.20mm CONFIRMED vs USB-C spec; "
                         "0.50mm pitch is spec-nominal, not datasheet-verified"},
 "states": ["GOOD (default)", "BENT_PINS"],
 "anim": ["ANIM_B05_EXPLODE f1-90 reversible"],
 "renders": sorted(CAMS.keys()),
})
print("[CG] B05 BUILD COMPLETE")
