# =====================================================================
# B10_FPC + B11_ZIF - the IFC assembly
# ConveGenius Mobile Charging Repair Simulation | HIGHEST TEACHING VALUE
#
# Your own voiceover, verbatim:
#   "If that flap isn't fully closed, or if the solder anchoring the socket to
#    the board has cracked, you get a phone that charges only if you hold the
#    cable at just the right angle - ONE OF THE MOST COMMON AND MOST
#    MISDIAGNOSED CHARGING COMPLAINTS THERE IS."
#
# THE ONE THING THAT MUST BE UNMISTAKABLE: the difference between a flap that
# is LATCHED and one that LOOKS closed but is not. HALF_CLOSED is modelled
# deliberately - ~15 deg proud, gap at the hinge, ribbon marks misaligned.
#
# SECOND: THE SHAPE RULE. B05 is a rigid metal box, B10 is a flat gold ribbon.
# Two different parts, two different fixes, and confusing them is the
# commonest error in BC.3. Contrasted deliberately: hard steel vs soft amber.
#
# RIG: bone chain, weighted by path parameter, BAKED and verified through a
# real glTF round trip before any animation work. Blender cloth does not
# survive that trip - this is the gate that stops a 3-day mistake.
# =====================================================================
import bpy, bmesh, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cg_lib as C

# ribbon runs along X. Root (port end) at x=-36, tail inserts into the socket
# at x=+0.8. Service loop in Z - a real FPC has slack, never a taut straight run.
WAY = [(-36.0, 1.70), (-30.0, 2.30), (-24.0, 3.30), (-17.0, 3.60),
       (-10.0, 2.40), (-4.0, 0.80), (0.80, 0.55)]
NS      = 52          # path samples
NBONE   = 10
FILM_W  = 6.00
FILM_T  = 0.12
NPAD    = 12
PAD_P   = 0.50
SOCK_X, SOCK_Y, SOCK_Z = 3.40, 8.60, 1.10
HINGE_X, HINGE_Z = 1.55, 0.95
FLAP_OPEN_DEG = 110.0
HALF_DEG = 15.0

C.setup_scene("B10_B11_IFC")
M = C.house_materials()
M["POLY"]   = C.mat("MAT_POLYIMIDE_V2", "#C08A28", 0.0, 0.40,
                    transmission=0.14, ior=1.62)
M["GOLD"]   = M["GOLD_HARD"]
M["WORN"]   = C.mat("MAT_GOLD_WORN_V2", "#7E5F35", 1.0, 0.58)
M["LCP"]    = C.mat("MAT_ZIF_LCP", "#1C1C20", 0.0, 0.44)
M["LCP_FL"] = C.mat("MAT_ZIF_FLAP", "#26262B", 0.0, 0.40)
M["SOLD"]   = C.mat("MAT_SOLDER_ANCHOR", "#C0C5CA", 1.0, 0.30)
M["OXIDE"]  = C.mat("MAT_OXIDE_CRACK", "#151412", 0.30, 0.88)
M["STIFF"]  = C.mat("MAT_STIFFENER", "#8C7A5C", 0.0, 0.56)
M["CU"]     = C.mat("MAT_FPC_COPPER", "#A9642F", 1.0, 0.36)


def trace_stripes(m):
    """Copper traces read THROUGH the amber film. Stripes live in the shader
    and the geometry is a single sub-surface layer - 12 separate swept trace
    objects would blow the 6k tri budget for zero extra teaching value."""
    try:
        nt = m.node_tree
        b = nt.nodes.get("Principled BSDF")
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        w = nt.nodes.new("ShaderNodeMath"); w.operation = "MULTIPLY"
        w.inputs[1].default_value = 2.0        # 12 traces across the 6 mm width
        snap = nt.nodes.new("ShaderNodeMath"); snap.operation = "FRACT"
        step = nt.nodes.new("ShaderNodeMath"); step.operation = "GREATER_THAN"
        step.inputs[1].default_value = 0.60
        mixc = nt.nodes.new("ShaderNodeMix")
        mixc.data_type = "RGBA"
        mixc.inputs[6].default_value = C.srgb("#A2701F")   # amber film between traces
        mixc.inputs[7].default_value = C.srgb("#C98A42")   # copper seen through film
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.18
        bump.inputs["Distance"].default_value = 0.01
        nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
        nt.links.new(sep.outputs["Y"], w.inputs[0])
        nt.links.new(w.outputs["Value"], snap.inputs[0])
        nt.links.new(snap.outputs["Value"], step.inputs[0])
        nt.links.new(step.outputs["Value"], mixc.inputs["Factor"])
        nt.links.new(mixc.outputs[2], b.inputs["Base Color"])
        nt.links.new(step.outputs["Value"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    except Exception as e:
        C.log("trace_stripes fallback " + str(e))

trace_stripes(M["POLY"])

root = C.empty("B10_B11_IFC", (0, 0, 0), size=8.0)
parts = []
def keep(o, m=None, bevel=0.012, seg=2, angle=34.0, parent=None):
    if m:
        C.assign(o, m)
    C.bevel_destructive(o, width=bevel, segments=seg, angle=angle)
    o.parent = parent or root
    parts.append(o)
    return o

# =====================================================================
# B10 - the flex printed circuit
# =====================================================================
samples = C.catmull(WAY, NS)
prof_film = C.rounded_rect(FILM_W, FILM_T, 0.055, caps=3)
film, rings = C.ribbon("B10_FPC_FILM", samples, prof_film)
C.assign(film, M["POLY"])
C.bevel_destructive(film, width=0.008, segments=2, angle=45.0)
parts.append(film)

# one sub-surface copper layer, slightly inside the film
prof_cu = C.rounded_rect(FILM_W - 0.9, 0.030, 0.012, caps=2)
cu, cu_rings = C.ribbon("B10_FPC_COPPER", samples, prof_cu)
C.assign(cu, M["CU"])
C.bevel_destructive(cu, width=0.004, segments=1, angle=50.0)
parts.append(cu)

# --- bone chain: root at the PORT end, tail at the pads. The storyboard says
# --- "do not force it, do not pull on the port end", so the port end is fixed
# --- and the pad end is what lifts.
joints = []
for i in range(NBONE + 1):
    s = samples[int(round(i * (NS) / float(NBONE)))]
    joints.append((s[0], 0.0, s[1]))
arm, bone_names = C.make_armature("B10_ARM", joints)
arm.parent = root

C.weight_chain(film, arm, bone_names, rings)
C.weight_chain(cu, arm, bone_names, cu_rings)

def bind_rigid(o, bone):
    """Rigid-bind a small part to one bone. Pure data API - no edit mode."""
    vg = o.vertex_groups.new(name=bone)
    vg.add([v.index for v in o.data.vertices], 1.0, "REPLACE")
    md = o.modifiers.new("CG_Armature", "ARMATURE")
    md.object = arm
    o.parent = arm
    return o

TAILB = bone_names[-1]
PREVB = bone_names[-2]

# gold landing pads at the tail - 12, 0.50 mm pitch, on the underside
pads = []
for i in range(NPAD):
    y = (i - (NPAD - 1) / 2.0) * PAD_P
    p = C.box("B10_PAD_%02d" % (i + 1), 2.60, 0.30, 0.045, (-0.55, y, 0.455))
    keep(p, M["GOLD"], bevel=0.006)
    bind_rigid(p, TAILB)
    pads.append(p)

# stiffener: the rigid strip that lets the tail insert without buckling.
# The storyboard names it, so it must be individually pointable.
stf = C.box("B10_STIFFENER", 3.60, FILM_W + 0.10, 0.20, (-0.60, 0.0, 0.36))
keep(stf, M["STIFF"], bevel=0.02)
bind_rigid(stf, TAILB)

# coverlay: where the film stops and bare pads begin
cov = C.box("B10_COVERLAY_EDGE", 0.30, FILM_W + 0.06, 0.17, (-2.45, 0.0, 0.56))
keep(cov, M["POLY"], bevel=0.02)
bind_rigid(cov, TAILB)

C.empty("B10_ANCHOR_PADS", (-0.6, 0.0, 2.2), size=0.8).parent = root
C.empty("B10_ANCHOR_STIFFENER", (-0.6, -4.6, 1.2), size=0.8).parent = root
C.empty("B10_ANCHOR_FLEXPOINT", (-33.0, 0.0, 3.6), size=0.8).parent = root

# =====================================================================
# B11 - the board-side ZIF socket
# =====================================================================
# --- socket body as a real SHELL, not a solid block. The VO says "rows of
# --- gold-plated pins make the actual contact" - if the body is solid the
# --- fingers are buried and that sentence has no picture.
plate = C.box("B11_BODY_FLOOR", SOCK_X, SOCK_Y, 0.20, (0.0, 0.0, 0.10))
keep(plate, M["LCP"], bevel=0.025)
back = C.box("B11_BODY_BACK", 0.85, SOCK_Y, SOCK_Z, (1.28, 0.0, SOCK_Z / 2))
keep(back, M["LCP"], bevel=0.03)
body = back
for tag, sy in (("L", -1.0), ("R", 1.0)):
    w = C.box("B11_BODY_END_" + tag, SOCK_X, 0.55, SOCK_Z,
              (0.0, sy * (SOCK_Y / 2 - 0.275), SOCK_Z / 2))
    keep(w, M["LCP"], bevel=0.03)
mouth = C.box("B11_MOUTH_SHADOW", 0.20, SOCK_Y - 1.2, 0.30, (-1.62, 0.0, 0.52))
keep(mouth, M["OXIDE"], bevel=0.015)

# --- THE FLAP. Origin exactly on the hinge axis. Most important pivot in the
# --- whole course: "is it fully closed?" is the diagnosis.
flap = C.box("B11_FLAP", 2.00, SOCK_Y - 0.30, 0.30, (0.0, 0.0, 0.0))
# shift geometry so the hinge line sits at the object origin
flap.data.transform(__import__("mathutils").Matrix.Translation(
    (-1.00, 0.0, 0.0)))
flap.location = (HINGE_X, 0.0, HINGE_Z + 0.15)
keep(flap, M["LCP_FL"], bevel=0.035)
# a lip on the flap's leading edge, so a 15-degree gap is visible
lip = C.box("B11_FLAP_LIP", 0.26, SOCK_Y - 0.60, 0.44, (-1.90, 0.0, -0.06))
C.assign(lip, M["LCP_FL"])
C.bevel_destructive(lip, width=0.02, segments=2, angle=34.0)
lip.parent = flap
parts.append(lip)
C.empty("B11_ANCHOR_FLAP", (HINGE_X, 4.9, 2.4), size=0.8).parent = root

# --- 12 sprung contact fingers. Flat rectangles do not communicate why
# --- insertion needs "zero force, only lock" - these visibly deflect.
fingers = []
for i in range(NPAD):
    y = (i - (NPAD - 1) / 2.0) * PAD_P
    # pronounced arch + contact crown: a leaf spring that visibly WOULD
    # deflect. Flat tabs never communicate "zero insertion force, only lock".
    fw = C.catmull([(1.34, 0.14), (0.80, 0.16), (0.22, 0.44),
                    (-0.32, 0.74), (-0.80, 0.70), (-1.26, 0.40),
                    (-1.62, 0.28)], 16)
    prof = C.rounded_rect(0.24, 0.058, 0.026, caps=2)
    f, _r = C.ribbon("B11_PIN_%02d" % (i + 1), fw, prof)
    f.location = (0.0, y, 0.0)
    keep(f, M["GOLD"], bevel=0.006, seg=1, angle=50.0)
    fingers.append(f)
C.empty("B11_ANCHOR_PINS", (-0.4, 0.0, -1.4), size=0.8).parent = root

# --- anchoring solder fillets. SEPARATE objects, because "cracked solder
# --- anchoring the socket to the board" is a named fault in the storyboard.
def fillet_yz(name, y0, spread, h, x0, x1, n=12, sign=1.0):
    """Concave solder fillet spreading outward in Y from the socket end wall
    down to the board. Cross-section in YZ, extruded along X."""
    bm = bmesh.new()
    prof = [(0.0, 0.0), (spread, 0.0)]
    for k in range(1, n + 1):
        th = math.radians(90.0 * (1.0 - k / float(n)))
        prof.append((spread * (1.0 - math.cos(th)), h * (1.0 - math.sin(th))))
    V0 = [bm.verts.new((x0, y0 + sign * p[0], p[1])) for p in prof]
    V1 = [bm.verts.new((x1, y0 + sign * p[0], p[1])) for p in prof]
    bm.faces.new(V0[::-1]); bm.faces.new(V1)
    m = len(prof)
    for i in range(m):
        j = (i + 1) % m
        bm.faces.new((V0[i], V0[j], V1[j], V1[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o

solder = {}
for tag, sy in (("L", -1.0), ("R", 1.0)):
    s = fillet_yz("B11_SOLDER_" + tag, sy * (SOCK_Y / 2), 0.62, 0.52,
                  -SOCK_X / 2 + 0.15, SOCK_X / 2 - 0.15, sign=sy)
    # destructive bevel + NO modifier: export_apply would discard the shape key
    C.assign(s, M["SOLD"])
    C.bevel_destructive(s, width=0.010, segments=2, angle=34.0)
    s.parent = root
    parts.append(s)
    solder[tag] = s
    C.empty("B11_ANCHOR_SOLDER_" + tag,
            (0.0, sy * (SOCK_Y / 2 + 1.9), 0.9), size=0.8).parent = root

# --- MOLTEN shape key on both anchors. glTF has no animated materials, so the
# --- melt has to be GEOMETRY. A slumped, spread fillet reads unmistakably as
# --- "the solder has gone liquid" - and morph targets DO survive export.
for tag in ("L", "R"):
    cy = (SOCK_Y / 2) * (-1.0 if tag == "L" else 1.0)
    C.add_shape_key(solder[tag], "MOLTEN",
                    C.melt_fn(slump=0.42, spread=1.45, centre_y=cy))

# crack in the left anchor (hidden by default)
crack = C.box("B11_SOLDER_CRACK_L", 1.70, 0.05, 0.34,
              (0.0, -(SOCK_Y / 2 + 0.32), 0.20))
keep(crack, M["OXIDE"], bevel=0.004)
crack.hide_render = True
crack.hide_viewport = True

C.log("built: film+copper swept over %d samples, %d bones, %d pads, %d fingers"
      % (NS, len(bone_names), NPAD, NPAD))

# =====================================================================
# THE RIG GATE - run this BEFORE animating. Two minutes now, three days saved.
# =====================================================================
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 180

pb = {b.name: b for b in arm.pose.bones}
for b in arm.pose.bones:
    b.rotation_mode = "XYZ"

def key_rest(frames):
    for fr in frames:
        for b in arm.pose.bones:
            b.rotation_euler = (0.0, 0.0, 0.0)
            b.keyframe_insert("rotation_euler", frame=fr)

# a provisional deform purely so the gate has something to measure
key_rest([1])
for i, bn in enumerate(bone_names[-4:]):
    pb[bn].rotation_euler = (math.radians(-16.0 - 4 * i), 0.0, 0.0)
    pb[bn].keyframe_insert("rotation_euler", frame=60)
GATE = C.verify_gltf_deform([film, cu], arm, frames=(1, 60), tag="b10_rig")
C.log("RIG GATE -> " + ("PASS" if GATE.get("pass") else "FAIL"))

# clear the provisional keys; the real clips are built below
if arm.animation_data and arm.animation_data.action:
    arm.animation_data_clear()
for b in arm.pose.bones:
    b.rotation_euler = (0.0, 0.0, 0.0)

# =====================================================================
# ANIMATION CLIPS - each on its own NLA track, so the glTF gets one clip per
# track NAME rather than one clip per object.
# =====================================================================
def clip(name, build, f0, f1):
    """Build a clip into a fresh action, then park it on its own NLA track."""
    for o in (arm, flap):
        if o.animation_data:
            o.animation_data.action = None   # keep NLA tracks alive
    build(f0, f1)
    n = C.push_nla([arm, flap], name, start=f0)
    return n

def a_flap_open(f0, f1):
    flap.rotation_euler = (0.0, 0.0, 0.0)
    flap.keyframe_insert("rotation_euler", frame=f0)
    flap.rotation_euler = (0.0, math.radians(FLAP_OPEN_DEG), 0.0)
    flap.keyframe_insert("rotation_euler", frame=f1)
    C.ease_out([flap])

def a_flap_close(f0, f1):
    flap.rotation_euler = (0.0, math.radians(FLAP_OPEN_DEG), 0.0)
    flap.keyframe_insert("rotation_euler", frame=f0)
    # tiny overshoot then settle - reads as a click
    flap.rotation_euler = (0.0, math.radians(-4.0), 0.0)
    flap.keyframe_insert("rotation_euler", frame=f1 - 4)
    flap.rotation_euler = (0.0, 0.0, 0.0)
    flap.keyframe_insert("rotation_euler", frame=f1)
    C.ease_out([flap])

def a_peel(f0, f1):
    """FIX 3'S CENTRAL BEAT. A gradual corner-first peel, not a rigid lift.
    The twist on the last bones is what makes one corner release first."""
    span = f1 - f0
    for b in arm.pose.bones:
        b.rotation_euler = (0.0, 0.0, 0.0)
        b.keyframe_insert("rotation_euler", frame=f0)
    nb = len(bone_names)
    for k, bn in enumerate(bone_names):
        depth = nb - 1 - k                      # 0 at the tail
        start = f0 + int(depth * span * 0.055)
        end = min(f1, start + int(span * 0.45))
        bend = -20.0 * math.exp(-0.42 * depth)  # tail bends most
        twist = 9.0 * math.exp(-0.9 * depth)    # corner-first release
        pb[bn].rotation_euler = (0.0, 0.0, 0.0)
        pb[bn].keyframe_insert("rotation_euler", frame=start)
        pb[bn].rotation_euler = (math.radians(bend), math.radians(twist), 0.0)
        pb[bn].keyframe_insert("rotation_euler", frame=end)
    C.ease_out([arm])

made = {}
made["ANIM_B11_FLAP_OPEN"]  = clip("ANIM_B11_FLAP_OPEN",  a_flap_open, 1, 30)
made["ANIM_B11_FLAP_CLOSE"] = clip("ANIM_B11_FLAP_CLOSE", a_flap_close, 1, 30)
made["ANIM_B10_PEEL"]       = clip("ANIM_B10_PEEL",       a_peel, 1, 120)

def a_melt(f0, f1):
    """Fix 3 step 3-4: 'lift the ribbon once the solder liquifies - never pry
    it off cold'. Morph-target driven, so it actually plays in three.js."""
    for tag in ("L", "R"):
        C.key_shape(solder[tag], "MOLTEN", [(f0, 0.0), (f1, 1.0)])

for o in (solder["L"], solder["R"]):
    if o.data.shape_keys and o.data.shape_keys.animation_data:
        o.data.shape_keys.animation_data_clear()
a_melt(1, 45)
made["ANIM_B11_SOLDER_MELT"] = C.push_nla(
    [solder["L"].data.shape_keys, solder["R"].data.shape_keys],
    "ANIM_B11_SOLDER_MELT", start=1)
C.log("clips on NLA tracks: " + ", ".join("%s(%d)" % (k, v)
                                          for k, v in made.items()))

# =====================================================================
# STATES
# =====================================================================
STATES = {
 "B11_LATCHED":        {"flap_deg": 0.0,  "note": "correct - flap flush, marks aligned"},
 "B11_UNLATCHED":      {"flap_deg": FLAP_OPEN_DEG, "note": "flap fully up, ribbon loose"},
 "B11_HALF_CLOSED":    {"flap_deg": HALF_DEG,
                        "note": "THE TEACHING STATE - looks closed, is not. "
                                "Causes 'charges only at one angle'."},
 "B11_SOLDER_CRACKED": {"flap_deg": 0.0, "crack": True,
                        "note": "hairline crack in the left anchor, socket "
                                "very slightly lifted at that end"},
}
worn = C.collection("B10_STATE_PADS_WORN")
for src in pads[3:8]:
    d = src.copy(); d.data = src.data.copy()
    d.name = src.name.replace("B10_PAD_", "B10_WORNPAD_")
    worn.objects.link(d)
    C.assign(d, M["WORN"])
    d.parent = arm
    md = d.modifiers.new("CG_Armature", "ARMATURE"); md.object = arm
worn.hide_render = True
worn.hide_viewport = True

torn = C.collection("B10_STATE_TORN")
t = C.box("B10_TEAR", 0.06, FILM_W * 0.62, 0.30, (-32.5, 1.1, 2.30))
C.assign(t, M["OXIDE"]); C.bevel_destructive(t, width=0.004, segments=1, angle=34.0)
torn.objects.link(t)
try:
    bpy.context.scene.collection.objects.unlink(t)
except Exception:
    pass
torn.hide_render = True
torn.hide_viewport = True

def set_state(key):
    st = STATES[key]
    flap.rotation_euler = (0.0, math.radians(st["flap_deg"]), 0.0)
    on = bool(st.get("crack"))
    crack.hide_render = not on
    crack.hide_viewport = not on
    solder["L"].location = (0.0, 0.0, 0.05 if on else 0.0)
    try:
        bpy.context.view_layer.update()
    except Exception:
        pass

# =====================================================================
C.lighting_rig(scale=26.0, k=30.0, cavity=False)
C.studio_world(strength=0.95)
C.reflector_cards(scale=26.0, strength=7.0)
C.light_aim("CG_SOCKET", (-14.0, -34.0, 26.0), (0.0, 0.0, 0.7),
            energy_k=30.0, size_rel=0.9, scale=26.0, power=0.9)
C.set_look()
C.fix_clipping()

SOCKET = [body, mouth, flap, lip] + fingers + [solder["L"], solder["R"]]
TAIL = pads + [stf, cov]
ALLVIS = [o for o in parts if o.type == "MESH" and not o.hide_render]

sc.frame_set(1)
set_state("B11_LATCHED")
cam = C.camera("IFC_cam", (-26.0, -44.0, 26.0), (-8.0, 0.0, 1.6), focal=95)
C.frame_camera(cam, ALLVIS, margin=1.08, res=(2000, 1200))
C.auto_expose(cam, target=0.21)

tris = C.tri_count([o for o in parts if o.type == "MESH"])
C.log("LOD0 tris = %d (budget B10 6000 + B11 14000 = 20000)" % tris)
C.viewport_setup(focus_size=40.0)
C.save_blend(os.path.join(C.OUT, "B10_B11_IFC.blend"))

# ---- shot list
def shoot(name, loc, tgt, focal, subj, margin, res=(1600, 1200), expose=False):
    cm = C.camera(name + "_cam", loc, tgt or (0, 0, 0), focal=focal)
    C.frame_camera(cm, subj, margin=margin, target=tgt, res=res)
    if expose:
        C.auto_expose(cm, target=0.22)
    C.render(cm, os.path.join(C.REN, name + ".png"), res=res, samples=80)
    return cm

set_state("B11_LATCHED")
shoot("IFC_shot1_route", (-30.0, -50.0, 30.0), (-14.0, 0.0, 2.2), 92,
      ALLVIS, 1.08, (2000, 1200))

set_state("B11_UNLATCHED")
shoot("IFC_shot2_socket_open", (-9.0, -15.0, 9.0), (-0.6, 0.0, 1.0), 110,
      SOCKET, 1.16, (1800, 1350), expose=True)

# --- shot 3: the single most important comparison image in the course
set_state("B11_LATCHED")
c3 = shoot("IFC_shot3a_latched", (-11.0, -13.0, 7.0), (-0.4, 0.0, 1.1), 118,
           SOCKET, 1.20, (1600, 1200), expose=True)
set_state("B11_HALF_CLOSED")
C.render(c3, os.path.join(C.REN, "IFC_shot3b_half_closed.png"),
         res=(1600, 1200), samples=88)

# --- shot 4: the stack at the socket mouth
set_state("B11_LATCHED")
shoot("IFC_shot4_stack", (-13.0, -7.0, 4.2), (-1.4, 0.0, 0.75), 130,
      SOCKET + TAIL, 1.30, (1800, 1200), expose=True)

# --- shot 5: good pads vs worn pads, matched camera
c5 = shoot("IFC_shot5a_pads_good", (-9.0, -11.0, 8.0), (-0.6, 0.0, 0.6), 125,
           TAIL, 1.35, (1600, 1200), expose=True)
worn.hide_render = False
for o in worn.objects:
    o.hide_render = False
C.render(c5, os.path.join(C.REN, "IFC_shot5b_pads_worn.png"),
         res=(1600, 1200), samples=88)
worn.hide_render = True
for o in worn.objects:
    o.hide_render = True

# --- shot 6: mid-peel. Pose the bones DIRECTLY - no action, no keyframes.
# --- animation_data_clear() here would wipe all three NLA tracks, which is
# --- exactly why the first export came out with zero animations.
nb = len(bone_names)
for k, bn in enumerate(bone_names):
    depth = nb - 1 - k
    prog = max(0.0, min(1.0, (0.62 - depth * 0.055) / 0.45))
    pb[bn].rotation_euler = (math.radians(-20.0 * math.exp(-0.42 * depth) * prog),
                             math.radians(9.0 * math.exp(-0.9 * depth) * prog),
                             0.0)
try:
    bpy.context.view_layer.update()
except Exception:
    pass
shoot("IFC_shot6_peel_mid", (-24.0, -34.0, 22.0), (-10.0, 0.0, 3.0), 100,
      ALLVIS, 1.12, (1800, 1200))
for b in arm.pose.bones:
    b.rotation_euler = (0.0, 0.0, 0.0)
try:
    bpy.context.view_layer.update()
except Exception:
    pass
glb = C.export_glb(os.path.join(C.GLB, "B10_B11_IFC_LOD0.glb"),
                   objects=[o for o in parts if o.type == "MESH"] + [arm],
                   draco=True, anim_mode="NLA_TRACKS",
                   apply_modifiers=False)
summary = C.glb_summary(os.path.join(C.GLB, "B10_B11_IFC_LOD0.glb"))

C.report("B10_B11_IFC", {
 "asset": "B10_FPC + B11_ZIF",
 "tris_lod0": tris, "tri_budget": 20000, "within_budget": tris <= 20000,
 "objects": len([o for o in parts if o.type == "MESH"]),
 "bones": len(bone_names), "pads": NPAD, "fingers": NPAD,
 "glb_kb": round(glb / 1024.0, 1),
 "RIG_GATE": GATE,
 "morph_targets": C.assert_morph(os.path.join(C.GLB, "B10_B11_IFC_LOD0.glb"), 2),
 "glb_verified": {k: summary.get(k) for k in
                  ("nodes", "meshes", "skins", "animations", "tris_in_file",
                   "anchors", "extensions")},
 "states": {k: v["note"] for k, v in STATES.items()},
 "b10_states": ["GOOD (default)", "PADS_WORN (5 pads)", "TORN (flex point)"],
 "anim": list(made.keys()),
 "rig_method": "bone chain, weighted by path parameter with a smoothstep "
               "blend so there is no crease at the stiffener join. NOT cloth "
               "sim - cloth does not survive glTF export.",
 "dims_used": {"film_mm": [FILM_W, FILM_T], "path_len_mm": 36.8,
               "pads": NPAD, "pad_pitch_mm": PAD_P,
               "socket_mm": [SOCK_X, SOCK_Y, SOCK_Z],
               "flap_open_deg": FLAP_OPEN_DEG, "half_closed_deg": HALF_DEG},
 "renders": ["IFC_shot1_route", "IFC_shot2_socket_open", "IFC_shot3a_latched",
             "IFC_shot3b_half_closed", "IFC_shot4_stack",
             "IFC_shot5a_pads_good", "IFC_shot5b_pads_worn",
             "IFC_shot6_peel_mid"],
})
print("[CG] B10/B11 BUILD COMPLETE")
