# =====================================================================
# B40_JOINT - five solder joint condition states
# ConveGenius Mobile Charging Repair Simulation
#
# Teaching job, from the storyboard's own words:
#   "a dry or cracked solder joint here is a very common not-charging complaint"
#   "cracked or dry pads ... charges-only-in-one-position"
#   "a lot of what looks like a dead Charger IC is actually just a cold joint"
#   "inspect under magnification for solder bridges"
# Joint quality is not a detail of this course. It IS the course.
#
# THE ONE THING THAT MUST BE UNMISTAKABLE:
#   Good solder is CONCAVE and SHINY. Bad solder is CONVEX and DULL.
#   Built as real meniscus geometry, not a roughness swap:
#     concave -> ellipse centred OUTSIDE the solder (surface hollows inward,
#                low wetting angle ~25-40 deg, the solder WANTED to stick)
#     convex  -> ellipse centred INSIDE the corner (balls up, angle >90 deg)
#
# All five share ONE identical pad + component so the camera never moves
# between them. The learner compares the JOINT, not the scene.
# =====================================================================
import bpy, bmesh, math, os, sys

sys.path.insert(0, os.path.join(os.path.expanduser("~"), "ConveGenius_3D", "scripts"))
import cg_lib as C

# 0603 chip component on a phone board
BRD_X, BRD_Y, BRD_Z = 3.4, 2.4, 0.24
PAD_X, PAD_Y, PAD_Z = 0.95, 0.90, 0.035
PAD_CX             = 0.78            # pad centre offset from origin
CMP_X, CMP_Y, CMP_Z = 1.60, 0.80, 0.45
CAP_X              = 0.30            # metallised end-cap length
ZP                 = PAD_Z           # top of pad = solder start height

STATES = ["GOOD", "COLD", "CRACKED", "BRIDGED", "DRY"]

C.setup_scene("B40_JOINT")
M = C.house_materials()

M["SOLDER_GOOD"] = C.mat("MAT_SOLDER_GOOD_V2", "#C4C9CE", 1.0, 0.26)
M["SOLDER_COLD"] = C.mat("MAT_SOLDER_COLD_V2", "#9EA1A4", 1.0, 0.70)
M["OXIDE_DARK"]  = C.mat("MAT_OXIDE_DARK",     "#1B1A18", 0.35, 0.85)
M["CERAMIC"]     = C.mat("MAT_CMP_CERAMIC",    "#2A2622", 0.0, 0.52)
M["TIN_CAP"]     = C.mat("MAT_TIN_CAP",        "#C8CCD0", 1.0, 0.34)


def grainy(m, scale=1400.0, lo=0.55, hi=0.82, bump=0.55):
    """Cold solder is grainy and slightly wrinkled. That texture, not just a
    roughness number, is what makes it read as bad at thumbnail size."""
    try:
        nt = m.node_tree
        b = nt.nodes.get("Principled BSDF")
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = scale
        tex.inputs["Detail"].default_value = 8.0
        try:
            tex.inputs["Roughness"].default_value = 0.75
        except Exception:
            pass
        rng = nt.nodes.new("ShaderNodeMapRange")
        rng.inputs["To Min"].default_value = lo
        rng.inputs["To Max"].default_value = hi
        bmp = nt.nodes.new("ShaderNodeBump")
        bmp.inputs["Strength"].default_value = bump
        nt.links.new(tex.outputs["Fac"], rng.inputs["Value"])
        nt.links.new(rng.outputs["Result"], b.inputs["Roughness"])
        nt.links.new(tex.outputs["Fac"], bmp.inputs["Height"])
        nt.links.new(bmp.outputs["Normal"], b.inputs["Normal"])
    except Exception as e:
        C.log("grainy fallback " + str(e))

def silky(m, scale=600.0, lo=0.20, hi=0.30):
    try:
        nt = m.node_tree
        b = nt.nodes.get("Principled BSDF")
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = scale
        rng = nt.nodes.new("ShaderNodeMapRange")
        rng.inputs["To Min"].default_value = lo
        rng.inputs["To Max"].default_value = hi
        nt.links.new(tex.outputs["Fac"], rng.inputs["Value"])
        nt.links.new(rng.outputs["Result"], b.inputs["Roughness"])
    except Exception:
        pass

grainy(M["SOLDER_COLD"])
silky(M["SOLDER_GOOD"])


def meniscus(x0, L, h, sign=1.0, concave=True, n=16):
    """Closed XZ profile of a solder fillet.
    concave=True  -> hollow surface, low contact angle  (a GOOD joint)
    concave=False -> bulging surface, angle > 90 deg    (a COLD joint)"""
    pts = [(x0, ZP), (x0 + sign * L, ZP)]
    for i in range(1, n + 1):
        th = math.radians(90.0 * (1.0 - float(i) / n))
        if concave:
            x = x0 + sign * L * (1.0 - math.cos(th))
            z = ZP + (h - ZP) * (1.0 - math.sin(th))
        else:
            x = x0 + sign * L * math.sin(th)
            z = ZP + (h - ZP) * math.cos(th)
        pts.append((x, z))
    out = [pts[0]]
    for p in pts[1:]:
        if (p[0] - out[-1][0]) ** 2 + (p[1] - out[-1][1]) ** 2 > 1e-10:
            out.append(p)
    return out


def build_state(name, xoff):
    """One complete pad + component + joint assembly, parented to an empty."""
    rootname = "B40_STATE_" + name
    root = C.empty(rootname, (xoff, 0.0, 0.0), size=1.2)
    objs = []

    def add(o, m, bevel=0.008, seg=2, angle=32.0):
        C.assign(o, m)
        C.finish(o, bevel=bevel, segments=seg, angle=angle)
        o.parent = root
        objs.append(o)
        return o

    # --- shared base: identical in all five states ---
    add(C.box(rootname + "_BOARD", BRD_X, BRD_Y, BRD_Z, (0, 0, -BRD_Z / 2)),
        M["PCB_MASK"], bevel=0.02)
    for s, sx in (("L", -1.0), ("R", 1.0)):
        add(C.box(rootname + "_PAD_" + s, PAD_X, PAD_Y, PAD_Z,
                  (sx * PAD_CX, 0, PAD_Z / 2)), M["GOLD_HARD"], bevel=0.006)
    add(C.box(rootname + "_CMP_BODY", CMP_X - 2 * CAP_X, CMP_Y, CMP_Z,
              (0, 0, ZP + CMP_Z / 2)), M["CERAMIC"], bevel=0.012)
    for s, sx in (("L", -1.0), ("R", 1.0)):
        add(C.box(rootname + "_CMP_CAP_" + s, CAP_X, CMP_Y + 0.02, CMP_Z + 0.02,
                  (sx * (CMP_X / 2 - CAP_X / 2), 0, ZP + CMP_Z / 2)),
            M["TIN_CAP"], bevel=0.010)

    y0, y1 = -(CMP_Y / 2 + 0.06), (CMP_Y / 2 + 0.06)
    xcap = CMP_X / 2                       # outer face of the end cap

    def fillet(tag, sx, L, h, concave, mtl, xshift=0.0):
        prof = meniscus(sx * xcap + sx * xshift, L, h, sign=sx, concave=concave)
        o = C.solid(rootname + "_FILLET_" + tag, prof, y0, y1)
        return add(o, mtl, bevel=0.006, seg=2, angle=40.0)

    if name == "GOOD":
        # concave, sweeping smoothly pad-to-lead, reaching full pad width
        for s, sx in (("L", -1.0), ("R", 1.0)):
            fillet(s, sx, 0.44, 0.34, True, M["SOLDER_GOOD"])

    elif name == "COldPLACEHOLDER":
        pass

    elif name == "COLD":
        # convex, balled up, sitting ON the pad instead of flowing into it
        for s, sx in (("L", -1.0), ("R", 1.0)):
            fillet(s, sx, 0.24, 0.40, False, M["SOLDER_COLD"])

    elif name == "CRACKED":
        # GOOD geometry, but separated from the lead by a real 0.045 mm gap,
        # with oxidised faces showing inside the fissure
        for s, sx in (("L", -1.0), ("R", 1.0)):
            fillet(s, sx, 0.42, 0.32, True, M["SOLDER_GOOD"], xshift=0.045)
            add(C.box(rootname + "_CRACK_" + s, 0.045, CMP_Y + 0.06, 0.30,
                      (sx * (xcap + 0.020), 0, ZP + 0.13)),
                M["OXIDE_DARK"], bevel=0.003)

    elif name == "BRIDGED":
        # a WELL-FORMED joint in the wrong PLACE. Shiny, not dirty - that
        # distinction is what most training material misses.
        for s, sx in (("L", -1.0), ("R", 1.0)):
            fillet(s, sx, 0.40, 0.32, True, M["SOLDER_GOOD"])
        span = PAD_CX + PAD_X / 2
        prof = [(-span, ZP), (span, ZP)]
        n = 24
        for i in range(n + 1):
            t = math.pi * (1.0 - float(i) / n)
            prof.append((span * math.cos(t) * -1.0,
                         ZP + 0.20 * math.sin(math.pi * float(i) / n)))
        add(C.solid(rootname + "_BRIDGE", prof, -0.30, 0.30),
            M["SOLDER_GOOD"], bevel=0.008)

    elif name == "DRY":
        # starved. Pad left partly bare, no fillet to speak of, visible gap.
        for s, sx in (("L", -1.0), ("R", 1.0)):
            fillet(s, sx, 0.13, 0.13, False, M["SOLDER_COLD"])
        add(C.box(rootname + "_GAP", 0.05, CMP_Y * 0.55, 0.06,
                  (xcap - 0.02, 0.10, ZP + 0.02)), M["OXIDE_DARK"], bevel=0.002)

    C.log("state %-8s objects %d" % (name, len(objs)))
    return root, objs


roots, allobjs, per_state = {}, [], {}
for i, s in enumerate(STATES):
    r, o = build_state(s, 0.0)
    roots[s] = r
    per_state[s] = o
    allobjs += o

# =====================================================================
C.lighting_rig(scale=2.3, k=30.0, cavity=False)
C.studio_world(strength=0.95)
C.reflector_cards(scale=2.3, strength=7.0)
C.set_look()
C.fix_clipping()

def show_only(name):
    for s in STATES:
        hide = (s != name) if name else False
        roots[s].hide_render = hide
        roots[s].hide_viewport = hide
        for o in per_state[s]:
            o.hide_render = hide
            o.hide_viewport = hide

def joint_subj(s):
    """Frame on the JOINT, not the board. The board is context, not subject -
    solving on the whole assembly makes a 0.4 mm fillet microscopic."""
    keys = ("_FILLET_", "_CMP_", "_CRACK_", "_BRIDGE", "_GAP", "_PAD_")
    return [o for o in per_state[s] if any(k in o.name for k in keys)]

# one camera, identical for all five - this IS the deliverable
cam = C.camera("B40_cam", (-3.4, -6.2, 3.1), (0.0, 0.0, 0.25), focal=115)
show_only("GOOD")
C.frame_camera(cam, joint_subj("GOOD"), margin=1.28,
               target=(0.0, 0.0, 0.28), res=(1600, 1200))
C.auto_expose(cam, target=0.22)

tris_each = {}
for s in STATES:
    show_only(s)
    tris_each[s] = C.tri_count(per_state[s])

show_only("GOOD")
C.viewport_setup(focus_size=5.0)
C.save_blend(os.path.join(C.OUT, "B40_JOINT.blend"))

# shots 1-5: matched camera, matched light. The core assessment image set.
for i, s in enumerate(STATES, start=1):
    show_only(s)
    C.render(cam, os.path.join(C.REN, "B40_shot%d_%s.png" % (i, s.lower())),
             res=(1600, 1200), samples=96)

# shot 6: all five in a row, for the wall-chart reference card
show_only(None)
for i, s in enumerate(STATES):
    roots[s].location = ((i - 2) * 4.3, 0.0, 0.0)
try:
    bpy.context.view_layer.update()
except Exception:
    pass
rowcam = C.camera("B40_rowcam", (0.0, -20.0, 9.0), (0.0, 0.0, 0.25), focal=90)
C.frame_camera(rowcam, sum([joint_subj(s) for s in STATES], []), margin=1.06, target=(0.0, 0.0, 0.3),
               res=(2400, 900))
C.render(rowcam, os.path.join(C.REN, "B40_shot6_row.png"),
         res=(2400, 900), samples=96)

for s in STATES:
    roots[s].location = (0.0, 0.0, 0.0)
show_only("GOOD")

glb = C.export_glb(os.path.join(C.GLB, "B40_JOINT_LOD0.glb"),
                   objects=allobjs, draco=True)

C.report("B40_JOINT", {
 "asset": "B40_JOINT",
 "states": STATES,
 "tris_per_state": tris_each,
 "tri_budget_per_state": 3000,
 "within_budget": all(v <= 3000 for v in tris_each.values()),
 "glb_kb": round(glb / 1024.0, 1),
 "exposure": round(bpy.context.scene.view_settings.exposure, 3),
 "method": "real meniscus geometry - concave ellipse centred outside the "
           "solder for GOOD, convex ellipse centred in the corner for COLD. "
           "Not a roughness swap.",
 "dims_used": {"component": "0603 chip, 1.60 x 0.80 x 0.45 mm",
               "pad_mm": [PAD_X, PAD_Y, PAD_Z], "pad_centres_mm": PAD_CX * 2,
               "crack_gap_mm": 0.045},
 "renders": ["B40_shot%d_%s" % (i, s.lower()) for i, s in enumerate(STATES, 1)]
            + ["B40_shot6_row"],
})
print("[CG] B40 BUILD COMPLETE")
