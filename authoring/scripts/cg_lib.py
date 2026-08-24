# =====================================================================
# cg_lib.py - ConveGenius Mobile Repair 3D  |  HOUSE STANDARD library
# Shared by every B-series asset build script. Blender 5.x.
# =====================================================================
import bpy, bmesh, math, json, os, sys
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
REN = os.path.join(ROOT, "renders")
GLB = os.path.join(ROOT, "glb")
for _p in (OUT, REN, GLB):
    os.makedirs(_p, exist_ok=True)

LOG = []
def log(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print("[CG] " + s)

# ---------------------------------------------------------------- colour
def srgb(hexstr):
    """#RRGGBB -> linear RGBA. Blender wants linear, not sRGB."""
    h = hexstr.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i+2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (out[0], out[1], out[2], 1.0)

# ---------------------------------------------------------------- scene
def clean_scene():
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    except Exception:
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o, do_unlink=True)

def pick_engine(prefer_cycles=False):
    avail = [i.identifier for i in
             bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    if prefer_cycles and "CYCLES" in avail:
        return "CYCLES"
    for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if e in avail:
            return e
    return avail[0]

def setup_scene(name="CG", prefer_cycles=False):
    """HOUSE STANDARD: mm units, macro-safe clipping, dark neutral world."""
    clean_scene()
    sc = bpy.context.scene
    sc.name = name
    u = sc.unit_settings
    u.system = "METRIC"
    u.scale_length = 0.001          # 1 Blender unit == 1 mm
    u.length_unit = "MILLIMETERS"
    sc.render.engine = pick_engine(prefer_cycles)
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    if sc.render.engine == "CYCLES":
        try:
            sc.cycles.device = "CPU"
            sc.cycles.use_denoising = True
            sc.cycles.samples = 96
            sc.cycles.max_bounces = 8
        except Exception:
            pass
    else:
        try:
            sc.eevee.taa_render_samples = 96
        except Exception:
            pass
    w = bpy.data.worlds.new("CG_WORLD")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = srgb("#0E1420")
        bg.inputs[1].default_value = 0.30
    sc.world = w
    log("scene ready | engine " + sc.render.engine + " | units mm")
    return sc

def fix_clipping():
    """Clip start 0.01mm everywhere. The #1 macro-scale setup bug."""
    for cam in bpy.data.cameras:
        cam.clip_start = 0.01
        cam.clip_end = 100000.0
    for scr in bpy.data.screens:
        for area in scr.areas:
            if area.type == "VIEW_3D":
                for sp in area.spaces:
                    if sp.type == "VIEW_3D":
                        try:
                            sp.clip_start = 0.01
                            sp.clip_end = 100000.0
                        except Exception:
                            pass

# ---------------------------------------------------------------- material
_ALIAS = {
    "anisotropic": "Anisotropic",
    "coat": "Coat Weight",
    "coat_rough": "Coat Roughness",
    "transmission": "Transmission Weight",
    "emission": "Emission Color",
    "emission_strength": "Emission Strength",
    "subsurface": "Subsurface Weight",
    "ior": "IOR",
    "spec": "Specular IOR Level",
    "sheen": "Sheen Weight",
}

def mat(name, base="#808080", metallic=0.0, rough=0.5, **kw):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    n = m.node_tree.nodes.get("Principled BSDF")
    def S(key, val):
        if n and key in n.inputs:
            try:
                n.inputs[key].default_value = val
            except Exception:
                pass
    S("Base Color", srgb(base) if isinstance(base, str) else base)
    S("Metallic", metallic)
    S("Roughness", rough)
    for k, v in kw.items():
        if k in _ALIAS:
            S(_ALIAS[k], srgb(v) if (k == "emission" and isinstance(v, str)) else v)
    return m

def house_materials():
    """The calibrated palette. Every asset pulls from here."""
    M = {}
    M["STEEL_SHELL"]  = mat("MAT_STEEL_SHELL",  "#8E9194", 1.0, 0.30, anisotropic=0.40)
    M["GOLD_HARD"]    = mat("MAT_GOLD_HARD",    "#D9B551", 1.0, 0.18)
    M["GOLD_WORN"]    = mat("MAT_GOLD_WORN",    "#8A6A3C", 1.0, 0.52)
    M["SOLDER_GOOD"]  = mat("MAT_SOLDER_GOOD",  "#BFC4C9", 1.0, 0.32)
    M["SOLDER_COLD"]  = mat("MAT_SOLDER_COLD",  "#A8ABAE", 1.0, 0.68)
    M["PCB_MASK"]     = mat("MAT_PCB_MASK",     "#0E4F3C", 0.0, 0.38, coat=0.15, coat_rough=0.25)
    M["HOUSING_LCP"]  = mat("MAT_HOUSING_LCP",  "#1A1A1D", 0.0, 0.46)
    M["POLYIMIDE"]    = mat("MAT_POLYIMIDE",    "#C08A28", 0.0, 0.42, transmission=0.12, ior=1.62)
    M["RUBBER"]       = mat("MAT_RUBBER",       "#141416", 0.0, 0.85, subsurface=0.02)
    M["NICKEL_BRUSH"] = mat("MAT_NICKEL_BRUSH", "#9A9DA1", 1.0, 0.42, anisotropic=0.30)
    M["COPPER_BARE"]  = mat("MAT_COPPER_BARE",  "#A55A32", 1.0, 0.35)
    M["FR4_CORE"]     = mat("MAT_FR4_CORE",     "#B7A277", 0.0, 0.62)
    M["SILK_WHITE"]   = mat("MAT_SILK_WHITE",   "#E8E8E4", 0.0, 0.55)
    M["PLASTIC_ESD"]  = mat("MAT_PLASTIC_ESD",  "#3A3D40", 0.0, 0.55)
    for g in ("GND", "VBUS", "CC", "DATA", "SBU", "SS"):
        M["PIN_" + g] = mat("MAT_PIN_" + g, "#D9B551", 1.0, 0.18)
    return M

def assign(obj, m):
    obj.data.materials.clear()
    obj.data.materials.append(m)

# ---------------------------------------------------------------- profiles
def obround(w, h, caps=16):
    """USB-C's true cross-section: a stadium. Flat top/bottom, fully radiused
    ends. This shape is why the connector is recognisable."""
    r = h / 2.0
    hs = max((w - h) / 2.0, 1e-6)
    pts = []
    for i in range(caps + 1):
        a = -math.pi / 2 + math.pi * i / caps
        pts.append((hs + r * math.cos(a), r * math.sin(a)))
    for i in range(caps + 1):
        a = math.pi / 2 + math.pi * i / caps
        pts.append((-hs + r * math.cos(a), r * math.sin(a)))
    ded = [pts[0]]
    for p in pts[1:]:
        if (p[0] - ded[-1][0]) ** 2 + (p[1] - ded[-1][1]) ** 2 > 1e-9:
            ded.append(p)
    if (ded[0][0] - ded[-1][0]) ** 2 + (ded[0][1] - ded[-1][1]) ** 2 < 1e-9:
        ded.pop()
    return ded

def rounded_rect(w, h, r, caps=6):
    r = min(r, w / 2 - 1e-4, h / 2 - 1e-4)
    cx, cz = w / 2 - r, h / 2 - r
    cen = [(cx, cz), (-cx, cz), (-cx, -cz), (cx, -cz)]
    start = [0.0, math.pi / 2, math.pi, 3 * math.pi / 2]
    pts = []
    for (ox, oz), s in zip(cen, start):
        for i in range(caps + 1):
            a = s + (math.pi / 2) * i / caps
            pts.append((ox + r * math.cos(a), oz + r * math.sin(a)))
    ded = [pts[0]]
    for p in pts[1:]:
        if (p[0] - ded[-1][0]) ** 2 + (p[1] - ded[-1][1]) ** 2 > 1e-9:
            ded.append(p)
    if (ded[0][0] - ded[-1][0]) ** 2 + (ded[0][1] - ded[-1][1]) ** 2 < 1e-9:
        ded.pop()
    return ded

# ---------------------------------------------------------------- geometry
def _obj_from_bm(name, bm, coll=None):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob

def tube(name, outer, inner, y0, y1, cap_front=True, cap_back=True, coll=None):
    """Hollow shell with real wall thickness and a front rim.
    A single flat extrusion reads as cardboard - this does not."""
    assert len(outer) == len(inner), "profiles must match point count"
    n = len(outer)
    bm = bmesh.new()
    VO0 = [bm.verts.new((p[0], y0, p[1])) for p in outer]
    VI0 = [bm.verts.new((p[0], y0, p[1])) for p in inner]
    VO1 = [bm.verts.new((p[0], y1, p[1])) for p in outer]
    VI1 = [bm.verts.new((p[0], y1, p[1])) for p in inner]
    for i in range(n):
        j = (i + 1) % n
        if cap_front:
            bm.faces.new((VO0[i], VO0[j], VI0[j], VI0[i]))
        if cap_back:
            bm.faces.new((VO1[j], VO1[i], VI1[i], VI1[j]))
        bm.faces.new((VO0[j], VO0[i], VO1[i], VO1[j]))
        bm.faces.new((VI0[i], VI0[j], VI1[j], VI1[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _obj_from_bm(name, bm, coll)

def solid(name, profile, y0, y1, coll=None):
    """Solid extrusion of a closed 2D (XZ) profile along Y."""
    n = len(profile)
    bm = bmesh.new()
    V0 = [bm.verts.new((p[0], y0, p[1])) for p in profile]
    V1 = [bm.verts.new((p[0], y1, p[1])) for p in profile]
    bm.faces.new(V0[::-1])
    bm.faces.new(V1)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((V0[i], V0[j], V1[j], V1[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _obj_from_bm(name, bm, coll)

def box(name, sx, sy, sz, loc=(0, 0, 0), coll=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts[:])
    bmesh.ops.translate(bm, vec=loc, verts=bm.verts[:])
    return _obj_from_bm(name, bm, coll)

def empty(name, loc=(0, 0, 0), size=0.4, coll=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "PLAIN_AXES"
    e.empty_display_size = size
    e.location = loc
    (coll or bpy.context.scene.collection).objects.link(e)
    return e

def collection(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c

def set_origin(obj, world_loc):
    """Move the origin to a functional pivot without moving the geometry."""
    delta = Vector(world_loc) - obj.location
    obj.data.transform(__import__("mathutils").Matrix.Translation(-delta))
    obj.location = Vector(world_loc)

# ---------------------------------------------------------------- finishing
def finish(obj, bevel=0.02, segments=2, angle=30.0, smooth=True):
    """HOUSE STANDARD finishing: bevel every visible hard edge, harden normals,
    smooth by angle. An unbevelled 90-degree edge is an auto-reject."""
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    if bevel and bevel > 0:
        m = obj.modifiers.new("CG_Bevel", "BEVEL")
        m.width = bevel
        m.segments = segments
        m.limit_method = "ANGLE"
        m.angle_limit = math.radians(angle)
        try:
            m.miter_outer = "MITER_ARC"
        except Exception:
            pass
        try:
            m.harden_normals = True
        except Exception:
            pass
    try:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))
    except Exception:
        pass
    return obj

def tri_count(objs):
    total = 0
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        if o.type != "MESH":
            continue
        try:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            me.calc_loop_triangles()
            total += len(me.loop_triangles)
            ev.to_mesh_clear()
        except Exception:
            pass
    return total

# ---------------------------------------------------------------- lighting
def lighting_rig(scale=1.0):
    """One rig, reused for all five assets. The soft reflection running along a
    metal edge is what makes shape readable - that is the key light's job.
    scale is in mm: pass the rough size of the subject."""
    made = []
    def L(name, energy, size, loc, rot):
        d = bpy.data.lights.new(name, "AREA")
        d.energy = energy
        d.size = size
        d.shape = "SQUARE"
        o = bpy.data.objects.new(name, d)
        o.location = loc
        o.rotation_euler = rot
        bpy.context.scene.collection.objects.link(o)
        made.append(o)
        return o
    s = float(scale)
    # energy scales with area for consistent exposure at any subject size
    L("CG_KEY",  0.55 * s * s, 2.5 * s, (-1.4 * s, -1.8 * s, 2.0 * s),
      (math.radians(42), math.radians(-16), math.radians(-38)))
    L("CG_FILL", 0.14 * s * s, 1.6 * s, (2.0 * s, -1.4 * s, 0.6 * s),
      (math.radians(76), 0.0, math.radians(58)))
    L("CG_RIM",  0.26 * s * s, 1.4 * s, (0.4 * s, 2.2 * s, 1.6 * s),
      (math.radians(-52), 0.0, math.radians(8)))
    return made

def camera(name, loc, target=(0, 0, 0), focal=100.0, dof=False, fdist=None):
    """DOF defaults OFF. Explanatory shots must be sharp end to end - if a
    learner cannot read a pin, the render has failed."""
    cd = bpy.data.cameras.new(name)
    cd.lens = focal
    cd.clip_start = 0.01
    cd.clip_end = 100000.0
    co = bpy.data.objects.new(name, cd)
    co.location = loc
    bpy.context.scene.collection.objects.link(co)
    d = Vector(target) - Vector(loc)
    co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cd.dof.use_dof = bool(dof)
    if dof:
        cd.dof.focus_distance = fdist or d.length
        cd.dof.aperture_fstop = 4.0
    return co

def render(cam, path, res=(2048, 1536), samples=None, transparent=True):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    if samples:
        if sc.render.engine == "CYCLES":
            try: sc.cycles.samples = samples
            except Exception: pass
        else:
            try: sc.eevee.taa_render_samples = samples
            except Exception: pass
    sc.render.filepath = path
    fix_clipping()
    bpy.ops.render.render(write_still=True)
    log("rendered " + os.path.basename(path))
    return path

# ---------------------------------------------------------------- export
def export_glb(path, objects=None, draco=True):
    bpy.ops.object.select_all(action="DESELECT")
    if objects:
        for o in objects:
            try: o.select_set(True)
            except Exception: pass
    kw = dict(filepath=path, export_format="GLB", use_selection=bool(objects),
              export_yup=True, export_apply=True, export_cameras=False,
              export_lights=False)
    if draco:
        kw["export_draco_mesh_compression_enable"] = True
        kw["export_draco_mesh_compression_level"] = 6
    try:
        bpy.ops.export_scene.gltf(**kw)
    except TypeError:
        kw.pop("export_draco_mesh_compression_enable", None)
        kw.pop("export_draco_mesh_compression_level", None)
        bpy.ops.export_scene.gltf(**kw)
    sz = os.path.getsize(path) if os.path.exists(path) else 0
    log("glb " + os.path.basename(path) + " " + str(round(sz / 1024.0, 1)) + " KB")
    return sz

def save_blend(path):
    bpy.ops.wm.save_as_mainfile(filepath=path)
    log("saved " + os.path.basename(path))

def viewport_setup(focus_size=12.0):
    """Make the open Blender window immediately usable: material preview,
    framed on the asset, macro-safe clipping."""
    fix_clipping()
    for scr in bpy.data.screens:
        for area in scr.areas:
            if area.type != "VIEW_3D":
                continue
            for sp in area.spaces:
                if sp.type != "VIEW_3D":
                    continue
                try:
                    sp.shading.type = "MATERIAL"
                    sp.shading.use_scene_lights = True
                    sp.shading.use_scene_world = False
                    sp.overlay.show_floor = False
                    sp.overlay.show_axis_x = False
                    sp.overlay.show_axis_y = False
                    sp.region_3d.view_distance = focus_size * 3.0
                except Exception:
                    pass
    try:
        bpy.ops.object.select_all(action="SELECT")
        for scr in bpy.data.screens:
            for area in scr.areas:
                if area.type == "VIEW_3D":
                    with bpy.context.temp_override(area=area,
                                                   region=area.regions[-1]):
                        bpy.ops.view3d.view_selected()
        bpy.ops.object.select_all(action="DESELECT")
    except Exception:
        pass

def report(name, data):
    p = os.path.join(OUT, name + ".json")
    data["log"] = LOG
    with open(p, "w") as f:
        json.dump(data, f, indent=1)
    print("[CG] REPORT " + p)
    return p


# ---------------------------------------------------------------- compat
def fcurves(action):
    """Blender 4.4+ replaced action.fcurves with slotted actions
    (layers -> strips -> channelbags -> fcurves). Yield either shape."""
    if action is None:
        return
    legacy = getattr(action, "fcurves", None)
    if legacy is not None:
        for fc in legacy:
            yield fc
        return
    for layer in getattr(action, "layers", []):
        for strip in getattr(layer, "strips", []):
            for cbag in getattr(strip, "channelbags", []):
                for fc in getattr(cbag, "fcurves", []):
                    yield fc

def ease_out(objs, interp="BEZIER", easing="EASE_OUT"):
    """Generous ease-out on every keyframe. Mechanical linear motion reads as
    cheap 3D; real parts decelerate."""
    n = 0
    for o in objs:
        ad = getattr(o, "animation_data", None)
        if not ad or not ad.action:
            continue
        for fc in fcurves(ad.action):
            for k in fc.keyframe_points:
                k.interpolation = interp
                k.easing = easing
                n += 1
    log("eased %d keyframes" % n)
    return n


# =====================================================================
# LIGHTING v2 - overrides the earlier rig.
# At unit_scale 0.001 a Blender unit displays as 1 mm, but light falloff
# still treats units as metres. A softbox 30 units away therefore needs
# energy on the order of k*d^2, not tens of watts. This is the single
# reason a macro-scale scene renders black.
# =====================================================================
def lighting_rig(scale=10.0, k=34.0, cavity=True):
    """One rig, reused for every asset. The soft reflection running along a
    metal edge is what makes shape readable - that is the key light's job.
    scale = rough size of the subject in mm."""
    for o in list(bpy.data.objects):
        if o.type == "LIGHT" and o.name.startswith("CG_"):
            bpy.data.objects.remove(o, do_unlink=True)
    s = float(scale)
    made = []
    spec = [
        # name        rel position            size    relative power
        ("CG_KEY",   (-1.30, -1.65,  1.90),   2.60,   1.00),
        ("CG_FILL",  ( 1.85, -1.30,  0.55),   1.80,   0.28),
        ("CG_RIM",   ( 0.35,  2.05,  1.55),   1.50,   0.55),
        ("CG_BOUNCE",( 0.00, -0.60, -1.90),   2.20,   0.16),
    ]
    if cavity:
        # aimed straight into the port opening so the interior reads as a
        # metal-lined box with a tongue in it, not a black hole
        spec.append(("CG_CAVITY", (0.00, -2.40, 0.10), 0.70, 0.34))
    for name, rel, sz, rp in spec:
        loc = (rel[0] * s, rel[1] * s, rel[2] * s)
        d2 = max(loc[0] ** 2 + loc[1] ** 2 + loc[2] ** 2, 1e-6)
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = k * d2 * rp
        ld.size = sz * s
        ld.shape = "SQUARE"
        try:
            ld.spread = math.radians(150.0)
        except Exception:
            pass
        o = bpy.data.objects.new(name, ld)
        o.location = loc
        # aim at origin
        d = Vector((0.0, 0.0, 0.0)) - Vector(loc)
        o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.collection.objects.link(o)
        made.append(o)
    log("lighting v2: %d lights, k=%.0f, scale=%.1fmm" % (len(made), k, s))
    return made


def _mean_luma(path, alpha_min=0.45):
    """Read a rendered PNG back and return mean luminance over covered pixels."""
    try:
        img = bpy.data.images.load(path, check_existing=False)
        px = list(img.pixels)
        n = len(px) // 4
        tot = 0.0
        cnt = 0
        step = max(1, n // 60000)          # sample, do not walk 2M pixels
        for i in range(0, n, step):
            a = px[i * 4 + 3]
            if a < alpha_min:
                continue
            r, g, b = px[i * 4], px[i * 4 + 1], px[i * 4 + 2]
            tot += 0.2126 * r + 0.7152 * g + 0.0722 * b
            cnt += 1
        bpy.data.images.remove(img)
        return (tot / cnt) if cnt else 0.0, cnt
    except Exception as e:
        log("luma read failed: " + str(e))
        return 0.0, 0


def auto_expose(cam, target=0.20, tries=4, res=(400, 300)):
    """Render small, measure, correct. Removes all guesswork about light
    energy at macro scale. Adjusts scene exposure in stops."""
    sc = bpy.context.scene
    probe = os.path.join(OUT, "_expose_probe.png")
    for t in range(tries):
        render(cam, probe, res=res, samples=16, transparent=True)
        m, cnt = _mean_luma(probe)
        if cnt == 0:
            log("auto_expose: nothing covered - check camera framing")
            return None
        if m <= 1e-5:
            sc.view_settings.exposure += 4.0
            log("auto_expose pass %d: black, +4 stops" % (t + 1))
            continue
        stops = math.log2(target / m)
        log("auto_expose pass %d: luma %.4f -> %+.2f stops" % (t + 1, m, stops))
        if abs(stops) < 0.18:
            log("auto_expose settled at exposure %.2f" % sc.view_settings.exposure)
            return sc.view_settings.exposure
        sc.view_settings.exposure += max(-6.0, min(6.0, stops))
    log("auto_expose final exposure %.2f" % sc.view_settings.exposure)
    return sc.view_settings.exposure


def set_look(contrast="Medium Contrast"):
    """AgX/Filmic view transform with a touch of contrast. Metal edges need
    it or they read flat and plastic."""
    vs = bpy.context.scene.view_settings
    for name in (contrast, "AgX - Medium Contrast", "Medium Contrast", "None"):
        try:
            vs.look = name
            log("look = " + name)
            return name
        except Exception:
            continue
    return None


# =====================================================================
# FRAMING - never hand-guess a camera distance at macro scale again.
# =====================================================================
def bounds(objs):
    """World-space centre and bounding-sphere radius of a set of objects."""
    pts = []
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            pts.append(o.matrix_world @ Vector(c))
    if not pts:
        return Vector((0, 0, 0)), 1.0
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    ctr = (mn + mx) * 0.5
    rad = max((mx - mn).length * 0.5, 1e-4)
    return ctr, rad

def frame_camera(cam, objs, margin=1.45, target=None, res=None):
    """Push the camera back along its own view axis until the subject fits
    with margin. Uses the limiting (usually vertical) field of view."""
    sc = bpy.context.scene
    rx = res[0] if res else sc.render.resolution_x
    ry = res[1] if res else sc.render.resolution_y
    lens = cam.data.lens
    sw = cam.data.sensor_width or 36.0
    half_h = sw / 2.0
    half_v = half_h * (float(ry) / float(rx))
    fov = 2.0 * math.atan(min(half_h, half_v) / lens)
    ctr, rad = bounds(objs)
    tgt = Vector(target) if target else ctr
    dist = (rad * margin) / max(math.tan(fov / 2.0), 1e-6)
    d = (cam.location - tgt)
    if d.length < 1e-6:
        d = Vector((0.0, -1.0, 0.35))
    d.normalize()
    cam.location = tgt + d * dist
    look = tgt - cam.location
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    cam.data.clip_start = 0.01
    cam.data.clip_end = 100000.0
    log("framed %s  dist %.1f  radius %.2f  fov %.1fdeg"
        % (cam.name, dist, rad, math.degrees(fov)))
    return cam

def aim(cam, target):
    look = Vector(target) - cam.location
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    return cam

def light_aim(name, loc, target, energy_k=34.0, size_rel=1.0, scale=10.0, power=1.0):
    """Add/replace one aimed area light with distance-corrected energy."""
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    d2 = max(sum((a - b) ** 2 for a, b in zip(loc, target)), 1e-6)
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy_k * d2 * power
    ld.size = size_rel * scale
    ld.shape = "SQUARE"
    o = bpy.data.objects.new(name, ld)
    o.location = loc
    bpy.context.scene.collection.objects.link(o)
    aim(o, target)
    return o


# =====================================================================
# FRAMING v2 - projects the real bounding box into camera space and solves
# for distance. The bounding-SPHERE version over-estimates badly for flat
# wide parts like a connector, which is why v1 framed everything too loose.
# =====================================================================
def frame_camera(cam, objs, margin=1.08, target=None, res=None):
    sc = bpy.context.scene
    rx = res[0] if res else sc.render.resolution_x
    ry = res[1] if res else sc.render.resolution_y
    lens = cam.data.lens
    sw = cam.data.sensor_width or 36.0
    if rx >= ry:
        hh = sw / 2.0; hv = hh * float(ry) / float(rx)
    else:
        hv = sw / 2.0; hh = hv * float(rx) / float(ry)
    tan_h = hh / lens
    tan_v = hv / lens
    ctr, rad = bounds(objs)
    tgt = Vector(target) if target else ctr
    corners = []
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            corners.append(o.matrix_world @ Vector(c))
    if not corners:
        return cam
    d = cam.location - tgt
    if d.length < 1e-6:
        d = Vector((0.0, -1.0, 0.40))
    d.normalize()
    dist = max(rad * 3.0, 1e-3)
    for _ in range(40):
        cam.location = tgt + d * dist
        aim(cam, tgt)
        mv = cam.matrix_world.inverted()
        need = -1e18
        for c in corners:
            p = mv @ c
            z = -p.z
            need = max(need, abs(p.x) / tan_h - z, abs(p.y) / tan_v - z)
        if abs(need) < 0.002 * max(rad, 1e-3):
            break
        dist = max(dist + need, rad * 0.25)
    dist *= margin
    cam.location = tgt + d * dist
    aim(cam, tgt)
    cam.data.clip_start = 0.01
    cam.data.clip_end = 100000.0
    log("framed %s dist %.2f rad %.2f" % (cam.name, dist, rad))
    return cam


# =====================================================================
# STUDIO WORLD - metals reflect their environment. In a near-black world a
# perfectly good steel shader renders as a black blob. This is the fix, and
# it matters more than any shader tweak.
# =====================================================================
def studio_world(top="#7C8DA8", bottom="#0E1420", strength=0.85):
    w = bpy.data.worlds.get("CG_WORLD") or bpy.data.worlds.new("CG_WORLD")
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld"); out.location = (400, 0)
    bg = nt.nodes.new("ShaderNodeBackground"); bg.location = (200, 0)
    bg.inputs["Strength"].default_value = strength
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.location = (-60, 0)
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = srgb(bottom)
    ramp.color_ramp.elements[1].position = 0.78
    ramp.color_ramp.elements[1].color = srgb(top)
    grad = nt.nodes.new("ShaderNodeTexGradient"); grad.location = (-280, 0)
    grad.gradient_type = "LINEAR"
    mapn = nt.nodes.new("ShaderNodeMapping"); mapn.location = (-480, 0)
    mapn.inputs["Rotation"].default_value = (0.0, math.radians(-90.0), 0.0)
    mapn.inputs["Location"].default_value = (0.5, 0.0, 0.0)
    tc = nt.nodes.new("ShaderNodeTexCoord"); tc.location = (-680, 0)
    nt.links.new(tc.outputs["Generated"], mapn.inputs["Vector"])
    nt.links.new(mapn.outputs["Vector"], grad.inputs["Vector"])
    nt.links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bpy.context.scene.world = w
    log("studio world gradient, strength %.2f" % strength)
    return w


def reflector_cards(scale=10.0, strength=6.0):
    """Two big off-camera emissive cards. Their soft reflection running along
    a metal edge is what makes the shape readable - the single most useful
    thing you can add to a hard-surface product render."""
    made = []
    spec = [("CG_CARD_TOP",  (0.0, -0.35, 2.30), (0.0, 0.0, 0.0), 4.2, 1.00),
            ("CG_CARD_SIDE", (-2.35, -0.55, 0.30), (0.0, math.radians(90), 0.0), 3.0, 0.55)]
    for name, rel, rot, sz, p in spec:
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
        m = bpy.data.meshes.new(name)
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=sz * scale / 2.0)
        bm.to_mesh(m); bm.free()
        o = bpy.data.objects.new(name, m)
        o.location = tuple(v * scale for v in rel)
        o.rotation_euler = rot
        bpy.context.scene.collection.objects.link(o)
        mat_ = bpy.data.materials.new("MAT_" + name)
        mat_.use_nodes = True
        nt = mat_.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        e = nt.nodes.new("ShaderNodeEmission")
        e.inputs["Color"].default_value = (1.0, 0.985, 0.96, 1.0)
        e.inputs["Strength"].default_value = strength * p
        so = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(e.outputs["Emission"], so.inputs["Surface"])
        o.data.materials.append(mat_)
        o.visible_camera = False          # seen only in reflections
        o.visible_shadow = False
        made.append(o)
    log("reflector cards: %d (camera-invisible)" % len(made))
    return made


# =====================================================================
# FRAMING v3 - closed form. v2 iterated while reading cam.matrix_world,
# which Blender caches until a depsgraph update, so every pass read a stale
# matrix and the solve diverged. This builds the camera basis by hand and
# solves for the distance exactly, in one pass.
#
#   camera at  C = tgt + d*dist,  forward = -d
#   for corner P:  a = (P-tgt).d      depth = dist - a
#                  u = (P-tgt).right  v = (P-tgt).up   (both independent of dist)
#   fit needs  |u| <= tan_h*depth  and  |v| <= tan_v*depth
#   =>  dist >= a + |u|/tan_h   and   dist >= a + |v|/tan_v
# =====================================================================
def frame_camera(cam, objs, margin=1.08, target=None, res=None):
    sc = bpy.context.scene
    rx = res[0] if res else sc.render.resolution_x
    ry = res[1] if res else sc.render.resolution_y
    lens = cam.data.lens
    sw = cam.data.sensor_width or 36.0
    if rx >= ry:
        hh = sw / 2.0
        hv = hh * float(ry) / float(rx)
    else:
        hv = sw / 2.0
        hh = hv * float(rx) / float(ry)
    tan_h = hh / lens
    tan_v = hv / lens

    corners = []
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            corners.append(o.matrix_world @ Vector(c))
    if not corners:
        log("frame_camera: no geometry for " + cam.name)
        return cam

    ctr, rad = bounds(objs)
    tgt = Vector(target) if target else ctr

    d = cam.location - tgt
    if d.length < 1e-9:
        d = Vector((0.0, -1.0, 0.40))
    d = d.normalized()

    q = (-d).to_track_quat("-Z", "Y")
    right = q @ Vector((1.0, 0.0, 0.0))
    up = q @ Vector((0.0, 1.0, 0.0))

    dist = 0.0
    for P in corners:
        w = P - tgt
        a = w.dot(d)
        u = abs(w.dot(right))
        v = abs(w.dot(up))
        dist = max(dist, a + u / tan_h, a + v / tan_v)
    dist = max(dist * margin, rad * 0.15 + 1e-3)

    cam.location = tgt + d * dist
    look = tgt - cam.location
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    cam.data.clip_start = 0.01
    cam.data.clip_end = 100000.0
    try:
        bpy.context.view_layer.update()
    except Exception:
        pass
    log("framed %s dist %.2f rad %.2f margin %.2f" % (cam.name, dist, rad, margin))
    return cam


# =====================================================================
# EXPORT v2 - a script launched with --python runs in a RESTRICTED context
# where bpy.context has no active_object, and the glTF exporter reads it
# unconditionally. Build a real UI context override from the open window,
# set an active object, and never let an export failure kill the build.
# =====================================================================
def _ui_override():
    wm = getattr(bpy.context, "window_manager", None)
    if not wm:
        return {}
    for win in getattr(wm, "windows", []):
        scr = getattr(win, "screen", None)
        if not scr:
            continue
        best = None
        for area in scr.areas:
            if area.type == "VIEW_3D":
                for region in area.regions:
                    if region.type == "WINDOW":
                        return dict(window=win, screen=scr, area=area,
                                    region=region)
            if best is None:
                best = area
        if best is not None:
            return dict(window=win, screen=scr, area=best)
    return {}


def export_glb(path, objects=None, draco=True):
    objs = [o for o in (objects or []) if getattr(o, "type", None) == "MESH"]
    kw = dict(filepath=path, export_format="GLB", use_selection=bool(objs),
              export_yup=True, export_apply=True, export_cameras=False,
              export_lights=False)
    if draco:
        kw["export_draco_mesh_compression_enable"] = True
        kw["export_draco_mesh_compression_level"] = 6

    def _do():
        try:
            bpy.ops.object.select_all(action="DESELECT")
        except Exception:
            for o in bpy.data.objects:
                try: o.select_set(False)
                except Exception: pass
        for o in objs:
            try: o.select_set(True)
            except Exception: pass
        if objs:
            try:
                bpy.context.view_layer.objects.active = objs[0]
            except Exception:
                pass
        try:
            bpy.ops.export_scene.gltf(**kw)
        except TypeError:
            kw.pop("export_draco_mesh_compression_enable", None)
            kw.pop("export_draco_mesh_compression_level", None)
            bpy.ops.export_scene.gltf(**kw)

    ov = _ui_override()
    try:
        if ov:
            with bpy.context.temp_override(**ov):
                _do()
        else:
            _do()
    except Exception as e:
        log("GLB EXPORT FAILED (non-fatal): " + str(e)[:200])
        # retry once without Draco - the Draco encoder is the usual culprit
        try:
            kw.pop("export_draco_mesh_compression_enable", None)
            kw.pop("export_draco_mesh_compression_level", None)
            if ov:
                with bpy.context.temp_override(**ov):
                    _do()
            else:
                _do()
            log("GLB export succeeded on retry without Draco")
        except Exception as e2:
            log("GLB retry also failed: " + str(e2)[:200])
            return 0
    sz = os.path.getsize(path) if os.path.exists(path) else 0
    log("glb " + os.path.basename(path) + " " + str(round(sz / 1024.0, 1)) + " KB")
    return sz


def safe(fn, *a, **kw):
    """Run a step; log and continue on failure. Reports must always be written."""
    try:
        return fn(*a, **kw)
    except Exception as e:
        log("STEP FAILED (continuing): " + fn.__name__ + " -> " + str(e)[:200])
        return None


# =====================================================================
# REVOLVED PRIMITIVES - nozzles, knobs, hose segments, bottles, spools.
# All extrude along +Y to match the house orientation.
# =====================================================================
def frustum(name, r0, r1, y0, y1, seg=28, cap0=True, cap1=True, coll=None):
    bm = bmesh.new()
    def ring(r, y):
        return [bm.verts.new((r * math.cos(2 * math.pi * i / seg), y,
                              r * math.sin(2 * math.pi * i / seg)))
                for i in range(seg)]
    V0 = ring(max(r0, 1e-5), y0)
    V1 = ring(max(r1, 1e-5), y1)
    if cap0:
        bm.faces.new(V0[::-1])
    if cap1:
        bm.faces.new(V1)
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((V0[i], V0[j], V1[j], V1[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _obj_from_bm(name, bm, coll)

def cyl(name, r, y0, y1, seg=28, coll=None):
    return frustum(name, r, r, y0, y1, seg=seg, coll=coll)

def pipe(name, r_out, r_in, y0, y1, seg=28, coll=None):
    """Hollow tube - real wall thickness, open both ends."""
    bm = bmesh.new()
    def ring(r, y):
        return [bm.verts.new((r * math.cos(2 * math.pi * i / seg), y,
                              r * math.sin(2 * math.pi * i / seg)))
                for i in range(seg)]
    O0, I0 = ring(r_out, y0), ring(r_in, y0)
    O1, I1 = ring(r_out, y1), ring(r_in, y1)
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((O0[i], O0[j], I0[j], I0[i]))
        bm.faces.new((O1[j], O1[i], I1[i], I1[j]))
        bm.faces.new((O0[j], O0[i], O1[i], O1[j]))
        bm.faces.new((I0[i], I0[j], I1[j], I1[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _obj_from_bm(name, bm, coll)

def lathe(name, profile, seg=40, coll=None):
    """Revolve a 2D (radius, y) profile about the Y axis. Bottles, spools,
    knobs - the whole consumables set is this one function."""
    bm = bmesh.new()
    rings = []
    for (r, y) in profile:
        rings.append([bm.verts.new((max(r, 1e-5) * math.cos(2 * math.pi * i / seg),
                                    y,
                                    max(r, 1e-5) * math.sin(2 * math.pi * i / seg)))
                      for i in range(seg)])
    for k in range(len(rings) - 1):
        A, B = rings[k], rings[k + 1]
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((A[i], A[j], B[j], B[i]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _obj_from_bm(name, bm, coll)

def gradient_along(m, axis="Z", c0="#8E9194", c1="#3A4C7A", lo=0.25, hi=0.95,
                   rough0=0.30, rough1=0.42):
    """Heat discolouration: a straw-to-blue oxidation gradient toward the tip.
    Tells the learner this end is HOT with no label needed."""
    try:
        nt = m.node_tree
        b = nt.nodes.get("Principled BSDF")
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
        rng = nt.nodes.new("ShaderNodeMapRange")
        rng.inputs["From Min"].default_value = lo
        rng.inputs["From Max"].default_value = hi
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = srgb(c0)
        ramp.color_ramp.elements[1].color = srgb(c1)
        ramp.color_ramp.elements[0].position = 0.15
        ramp.color_ramp.elements[1].position = 0.85
        rr = nt.nodes.new("ShaderNodeMapRange")
        rr.inputs["To Min"].default_value = rough0
        rr.inputs["To Max"].default_value = rough1
        nt.links.new(sep.outputs[axis.upper()], rng.inputs["Value"])
        nt.links.new(rng.outputs["Result"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        nt.links.new(rng.outputs["Result"], rr.inputs["Value"])
        nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    except Exception as e:
        log("gradient_along fallback " + str(e))

def alpha_cone(name, r_tip, r_end, length, seg=28, coll=None):
    """Soft airflow cone. NOT a particle sim - a gradient-alpha mesh that
    exports cleanly and reads perfectly on a low-end phone."""
    o = frustum(name, r_tip, r_end, 0.0, length, seg=seg, cap0=False, cap1=False,
                coll=coll)
    m = bpy.data.materials.new("MAT_" + name)
    m.use_nodes = True
    m.blend_method = "BLEND" if hasattr(m, "blend_method") else m.blend_method
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix = nt.nodes.new("ShaderNodeMixShader")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = srgb("#FFB067")
    em.inputs["Strength"].default_value = 1.6
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    rng = nt.nodes.new("ShaderNodeMapRange")
    rng.inputs["From Min"].default_value = 0.0
    rng.inputs["From Max"].default_value = length
    rng.inputs["To Min"].default_value = 0.42
    rng.inputs["To Max"].default_value = 0.0
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.0
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Y"], rng.inputs["Value"])
    nt.links.new(rng.outputs["Result"], mul.inputs[0])
    nt.links.new(noise.outputs["Fac"], mul.inputs[1])
    nt.links.new(mul.outputs["Value"], mix.inputs["Fac"])
    nt.links.new(tr.outputs["BSDF"], mix.inputs[1])
    nt.links.new(em.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    o.data.materials.append(m)
    o.visible_shadow = False
    return o


# =====================================================================
# PATHS + RIGGING + THE glTF DEFORM GATE
# The gate exists because Blender cloth/sim deformation does NOT survive a
# glTF round trip. A ribbon that looks perfect in Blender and snaps flat on
# import costs three days if you find out after animating. Find out in two
# minutes instead.
# =====================================================================
def catmull(waypoints, n=48):
    """Resample 2D waypoints [(x,z), ...] to n+1 points with tangents.
    Returns [(x, z, tx, tz), ...] with unit tangents."""
    P = [waypoints[0]] + list(waypoints) + [waypoints[-1]]
    segs = len(P) - 3
    out = []
    for i in range(n + 1):
        u = (float(i) / n) * segs
        k = min(int(u), segs - 1)
        t = u - k
        p0, p1, p2, p3 = P[k], P[k + 1], P[k + 2], P[k + 3]
        t2, t3 = t * t, t * t * t
        def c(a, b, cc, dd):
            return 0.5 * ((2 * b) + (-a + cc) * t +
                          (2 * a - 5 * b + 4 * cc - dd) * t2 +
                          (-a + 3 * b - 3 * cc + dd) * t3)
        def dc(a, b, cc, dd):
            return 0.5 * ((-a + cc) + 2 * (2 * a - 5 * b + 4 * cc - dd) * t +
                          3 * (-a + 3 * b - 3 * cc + dd) * t2)
        x = c(p0[0], p1[0], p2[0], p3[0])
        z = c(p0[1], p1[1], p2[1], p3[1])
        tx = dc(p0[0], p1[0], p2[0], p3[0])
        tz = dc(p0[1], p1[1], p2[1], p3[1])
        L = math.hypot(tx, tz) or 1.0
        out.append((x, z, tx / L, tz / L))
    return out


def ribbon(name, samples, profile, coll=None):
    """Sweep a 2D profile (u=width along Y, v=offset along the path normal)
    down a path in the XZ plane. Returns (object, rings) where rings[i] is the
    list of vertex indices for sample i - needed for weighting."""
    bm = bmesh.new()
    rings = []
    for (px, pz, tx, tz) in samples:
        nx, nz = -tz, tx
        r = []
        for (u, v) in profile:
            r.append(bm.verts.new((px + nx * v, u, pz + nz * v)))
        rings.append(r)
    m = len(profile)
    for k in range(len(rings) - 1):
        A, B = rings[k], rings[k + 1]
        for i in range(m):
            j = (i + 1) % m
            bm.faces.new((A[i], A[j], B[j], B[i]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.verts.index_update()
    idx = [[v.index for v in r] for r in rings]
    o = _obj_from_bm(name, bm, coll)
    return o, idx


def make_armature(name, joints, coll=None):
    """Create an armature with a bone chain through `joints` (world points).
    Bone creation needs edit mode, which needs a real context - hence the
    UI override. Returns (armature_object, [bone_names])."""
    arm = bpy.data.armatures.new(name + "_DATA")
    ao = bpy.data.objects.new(name, arm)
    (coll or bpy.context.scene.collection).objects.link(ao)
    names = []
    ov = _ui_override()
    def _build():
        bpy.ops.object.select_all(action="DESELECT")
        ao.select_set(True)
        bpy.context.view_layer.objects.active = ao
        bpy.ops.object.mode_set(mode="EDIT")
        eb = arm.edit_bones
        for b in list(eb):
            eb.remove(b)
        prev = None
        for i in range(len(joints) - 1):
            bn = "%s_BONE_%02d" % (name, i + 1)
            b = eb.new(bn)
            b.head = Vector(joints[i])
            b.tail = Vector(joints[i + 1])
            if prev is not None:
                b.parent = prev
                b.use_connect = True
            prev = b
            names.append(bn)
        bpy.ops.object.mode_set(mode="OBJECT")
    try:
        if ov:
            with bpy.context.temp_override(**ov):
                _build()
        else:
            _build()
    except Exception as e:
        log("ARMATURE BUILD FAILED: " + str(e)[:200])
        return ao, names
    log("armature %s: %d bones" % (name, len(names)))
    return ao, names


def weight_chain(obj, arm_obj, bone_names, rings, coll_smooth=1):
    """Weight a swept ribbon to its bone chain by path parameter. Deterministic
    and context-free - no bpy.ops automatic weights, which needs edit mode and
    pinches at the stiffener join."""
    nb = len(bone_names)
    nr = len(rings)
    vgs = [obj.vertex_groups.new(name=bn) for bn in bone_names]
    for i, ring in enumerate(rings):
        # position of this ring along the chain, in bone units
        s = (float(i) / max(nr - 1, 1)) * nb
        b0 = min(int(s), nb - 1)
        f = s - b0
        b1 = min(b0 + 1, nb - 1)
        # smooth blend so there is no crease at a bone boundary
        w1 = f * f * (3.0 - 2.0 * f)
        w0 = 1.0 - w1
        vgs[b0].add(ring, w0, "REPLACE")
        if b1 != b0:
            vgs[b1].add(ring, w1, "REPLACE")
    m = obj.modifiers.new("CG_Armature", "ARMATURE")
    m.object = arm_obj
    obj.parent = arm_obj
    log("weighted %s to %d bones over %d rings" % (obj.name, nb, nr))
    return m


def verify_gltf_deform(objects, arm_obj, frames=(1, 60), tag="gate"):
    """THE RIG GATE. Export the rigged mesh, re-import it, and confirm the
    deformation actually moved vertices between two frames. Blender cloth and
    most sim caches fail this; a baked bone chain passes."""
    import tempfile
    sc = bpy.context.scene
    path = os.path.join(OUT, "_gate_%s.glb" % tag)
    sel = list(objects) + [arm_obj]
    sz = export_glb(path, objects=sel, draco=False)
    if not sz:
        log("GATE %s: export produced nothing" % tag)
        return {"pass": False, "reason": "export failed"}

    before = set(o.name for o in bpy.data.objects)
    try:
        bpy.ops.import_scene.gltf(filepath=path)
    except Exception as e:
        log("GATE %s: import failed %s" % (tag, str(e)[:160]))
        return {"pass": False, "reason": "import failed"}
    new = [o for o in bpy.data.objects if o.name not in before]
    meshes = [o for o in new if o.type == "MESH"]
    if not meshes:
        log("GATE %s: no mesh came back" % tag)
        for o in new:
            bpy.data.objects.remove(o, do_unlink=True)
        return {"pass": False, "reason": "no mesh imported"}

    def sample(fr):
        sc.frame_set(fr)
        try:
            bpy.context.view_layer.update()
        except Exception:
            pass
        dg = bpy.context.evaluated_depsgraph_get()
        pts = []
        for o in meshes:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            vv = me.vertices
            for _i in range(0, len(vv), 7):
                pts.append(o.matrix_world @ vv[_i].co)
            ev.to_mesh_clear()
        return pts

    a = sample(frames[0])
    b = sample(frames[1])
    n = min(len(a), len(b))
    if n == 0:
        maxd = 0.0
    else:
        maxd = max((a[i] - b[i]).length for i in range(n))
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    ok = maxd > 0.05
    log("GATE %s: max vertex travel %.4f mm across frames %s -> %s"
        % (tag, maxd, frames, "PASS" if ok else "FAIL"))
    return {"pass": bool(ok), "max_travel_mm": round(maxd, 4),
            "frames": list(frames), "verts_sampled": n,
            "glb_kb": round(sz / 1024.0, 1)}


# =====================================================================
# EXPORT v3 - THREE.JS CORRECTNESS PASS
#
# Three real defects found by parsing the pass-1 GLBs:
#
# 1. Blender's default export_animation_mode='ACTIONS' writes ONE CLIP PER
#    OBJECT. B05 came out as 33 separate clips (B05_PIN_A01Action, ...), so
#    playing the explode in three.js would mean creating and syncing 33
#    AnimationActions. What you want is ONE clip with 33 channels.
#    Fix: NLA tracks with a shared name -> one glTF clip per track name.
#
# 2. Selecting only MESH objects silently dropped every EMPTY. That killed
#    B28's ANIM_B28_LIFT_TO_STAND (the animation lives on the handpiece empty)
#    AND every B05_ANCHOR_* / B02_ANCHOR_* node - which is exactly what
#    three.js needs for getObjectByName() to attach callout leader lines.
#    Fix: always walk the parent chain, and export anchors on purpose.
#
# 3. No post-export verification, so 1 and 2 went unnoticed.
#    Fix: parse the GLB back and assert what is actually in the file.
# =====================================================================
def push_nla(objects, track_name, start=1):
    """Move each object's active action onto an NLA strip on a track called
    track_name. The glTF exporter emits one animation per track NAME, so every
    object sharing the name collapses into a single clip."""
    n = 0
    for o in objects:
        ad = getattr(o, "animation_data", None)
        if not ad or not ad.action:
            continue
        act = ad.action
        try:
            trk = ad.nla_tracks.new()
            trk.name = track_name
            st = trk.strips.new(act.name, int(start), act)
            st.name = track_name
            ad.action = None
            n += 1
        except Exception as e:
            log("push_nla failed for %s: %s" % (o.name, str(e)[:120]))
    log("NLA track '%s': %d strips -> will export as ONE clip" % (track_name, n))
    return n


def with_parents(objects, include_anchors=True):
    """Expand a selection to include every parent (empties, armatures) plus all
    anchor empties. Without this the hierarchy and animation are lost."""
    out = {}
    for o in objects:
        cur = o
        while cur is not None:
            out[cur.name] = cur
            cur = cur.parent
    if include_anchors:
        for o in bpy.data.objects:
            if o.type == "EMPTY" and "_ANCHOR_" in o.name:
                out[o.name] = o
    return list(out.values())


def glb_summary(path):
    """Parse a .glb and report what is ACTUALLY in the file. Never trust the
    exporter's silence."""
    import struct as _s
    try:
        with open(path, "rb") as f:
            data = f.read()
        magic, ver, _tot = _s.unpack("<III", data[:12])
        if magic != 0x46546C67:
            return {"error": "not a glb"}
        off, js, binlen = 12, None, 0
        while off < len(data):
            clen, ctype = _s.unpack("<II", data[off:off + 8])
            chunk = data[off + 8:off + 8 + clen]
            if ctype == 0x4E4F534A:
                js = json.loads(chunk.decode("utf-8"))
            elif ctype == 0x004E4942:
                binlen = clen
            pad = ((4 - (clen % 4)) % 4) if clen % 4 else 0
            off += 8 + clen + pad
        g = js or {}
        tris = 0
        for m in g.get("meshes", []):
            for pr in m.get("primitives", []):
                ia = pr.get("indices")
                if ia is not None:
                    tris += g["accessors"][ia]["count"] // 3
        anims = [{"name": a.get("name", "?"), "channels": len(a.get("channels", []))}
                 for a in g.get("animations", [])]
        nodes = [n.get("name", "?") for n in g.get("nodes", [])]
        return {"kb": round(len(data) / 1024.0, 1), "bin_kb": round(binlen / 1024.0, 1),
                "meshes": len(g.get("meshes", [])), "nodes": len(nodes),
                "materials": [m.get("name", "?") for m in g.get("materials", [])],
                "skins": len(g.get("skins", [])), "animations": anims,
                "tris_in_file": tris,
                "extensions": g.get("extensionsUsed", []),
                "anchors": sorted([n for n in nodes if "_ANCHOR_" in n]),
                "node_names": sorted(nodes)}
    except Exception as e:
        return {"error": str(e)[:200]}


def export_glb(path, objects=None, draco=True, anim_mode="NLA_TRACKS",
               include_anchors=True, verify=True):
    sel = with_parents([o for o in (objects or [])], include_anchors) \
        if objects else []
    kw = dict(filepath=path, export_format="GLB", use_selection=bool(sel),
              export_yup=True, export_apply=True, export_cameras=False,
              export_lights=False, export_animations=True,
              export_animation_mode=anim_mode,
              export_bake_animation=True,
              export_optimize_animation_size=True)
    if draco:
        kw["export_draco_mesh_compression_enable"] = True
        kw["export_draco_mesh_compression_level"] = 6

    def _do(kwargs):
        try:
            bpy.ops.object.select_all(action="DESELECT")
        except Exception:
            for o in bpy.data.objects:
                try: o.select_set(False)
                except Exception: pass
        for o in sel:
            try: o.select_set(True)
            except Exception: pass
        if sel:
            try:
                bpy.context.view_layer.objects.active = sel[0]
            except Exception:
                pass
        bpy.ops.export_scene.gltf(**kwargs)

    ov = _ui_override()
    attempts = [dict(kw)]
    k2 = dict(kw); k2.pop("export_animation_mode", None)
    k2.pop("export_optimize_animation_size", None)
    k2.pop("export_bake_animation", None)
    attempts.append(k2)
    k3 = dict(k2); k3.pop("export_draco_mesh_compression_enable", None)
    k3.pop("export_draco_mesh_compression_level", None)
    attempts.append(k3)

    done = False
    for i, kwa in enumerate(attempts):
        try:
            if ov:
                with bpy.context.temp_override(**ov):
                    _do(kwa)
            else:
                _do(kwa)
            done = True
            if i:
                log("glb exported on fallback attempt %d" % (i + 1))
            break
        except Exception as e:
            log("glb attempt %d failed: %s" % (i + 1, str(e)[:160]))
    if not done:
        return 0

    sz = os.path.getsize(path) if os.path.exists(path) else 0
    log("glb %s %.1f KB (%d objects selected)"
        % (os.path.basename(path), sz / 1024.0, len(sel)))
    if verify:
        s = glb_summary(path)
        if "error" in s:
            log("GLB VERIFY ERROR: " + s["error"])
        else:
            log("GLB VERIFY: %d nodes, %d meshes, %d tris, %d anchors, anims=%s"
                % (s["nodes"], s["meshes"], s["tris_in_file"], len(s["anchors"]),
                   [(a["name"], a["channels"]) for a in s["animations"]]))
    return sz


# =====================================================================
# RIG GATE v2 - v1 reported "import failed" because bpy.ops.import_scene.gltf
# hits the same restricted context the exporter did, and on failure it left
# half-imported objects behind (hence the B10_ANCHOR_*.001 duplicates).
# =====================================================================
def verify_gltf_deform(objects, arm_obj, frames=(1, 60), tag="gate"):
    """THE RIG GATE. Export the rigged mesh, re-import it, confirm the
    deformation actually moved vertices between two frames. Blender cloth and
    sim caches FAIL this; a baked bone chain passes. Run it before animating."""
    sc = bpy.context.scene
    path = os.path.join(OUT, "_gate_%s.glb" % tag)
    sel = list(objects) + [arm_obj]
    sz = export_glb(path, objects=sel, draco=False, anim_mode="SCENE",
                    include_anchors=False, verify=False)
    if not sz:
        return {"pass": False, "reason": "export produced nothing"}

    pre = set(o.name for o in bpy.data.objects)

    def _cleanup():
        for o in [x for x in bpy.data.objects if x.name not in pre]:
            try: bpy.data.objects.remove(o, do_unlink=True)
            except Exception: pass

    ov = _ui_override()
    def _imp():
        bpy.ops.import_scene.gltf(filepath=path)
    try:
        if ov:
            with bpy.context.temp_override(**ov):
                _imp()
        else:
            _imp()
    except Exception as e:
        _cleanup()
        log("GATE %s: import failed %s" % (tag, str(e)[:160]))
        return {"pass": False, "reason": "import failed: " + str(e)[:120]}

    new = [o for o in bpy.data.objects if o.name not in pre]
    meshes = [o for o in new if o.type == "MESH"]
    skinned = [o for o in meshes
               if any(m.type == "ARMATURE" for m in o.modifiers)]
    if not meshes:
        _cleanup()
        return {"pass": False, "reason": "no mesh came back"}

    def sample(fr):
        sc.frame_set(fr)
        try:
            bpy.context.view_layer.update()
        except Exception:
            pass
        dg = bpy.context.evaluated_depsgraph_get()
        pts = []
        for o in meshes:
            try:
                ev = o.evaluated_get(dg)
                me = ev.to_mesh()
                vv = me.vertices
                for _i in range(0, len(vv), 5):
                    pts.append(o.matrix_world @ vv[_i].co)
                ev.to_mesh_clear()
            except Exception:
                pass
        return pts

    a = sample(frames[0])
    b = sample(frames[1])
    n = min(len(a), len(b))
    maxd = max((a[i] - b[i]).length for i in range(n)) if n else 0.0
    _cleanup()
    sc.frame_set(frames[0])
    ok = maxd > 0.05
    log("GATE %s: %d skinned meshes, max vertex travel %.4f mm -> %s"
        % (tag, len(skinned), maxd, "PASS" if ok else "FAIL"))
    return {"pass": bool(ok), "max_travel_mm": round(maxd, 4),
            "frames": list(frames), "verts_sampled": n,
            "skinned_meshes_imported": len(skinned),
            "glb_kb": round(sz / 1024.0, 1),
            "note": "deformation survived a real glTF round trip"
                    if ok else "deformation did NOT survive export"}


# =====================================================================
# SHAPE KEYS / MORPH TARGETS  -  the correct answer to the molten-solder
# question.
#
# glTF core has NO animated material properties. Animating emission or
# roughness in Blender exports to NOTHING. What DOES export is:
#   - morph targets (shape keys) + their weight animation
#   - node TRS animation
#   - skinned deformation
# So a solder melt must be GEOMETRY (a slumped shape key), with the glow left
# to the runtime as a one-line emissive lerp. A Blender fluid sim exports
# nothing at all - which is the trap the rig gate exists to catch.
# =====================================================================
def add_shape_key(obj, name, fn):
    """Add a shape key whose points are obj-space co -> fn(co, index).
    Pure data API: no operators, no edit mode, no context needed."""
    me = obj.data
    if not me.shape_keys:
        obj.shape_key_add(name="Basis", from_mix=False)
    sk = obj.shape_key_add(name=name, from_mix=False)
    for i, p in enumerate(sk.data):
        try:
            p.co = fn(Vector(p.co), i)
        except Exception:
            pass
    sk.value = 0.0
    sk.slider_min = 0.0
    sk.slider_max = 1.0
    log("shape key '%s' on %s (%d points)" % (name, obj.name, len(sk.data)))
    return sk


def key_shape(obj, key_name, frames_values):
    """Keyframe a shape key's weight. frames_values = [(frame, value), ...]"""
    kb = obj.data.shape_keys.key_blocks.get(key_name)
    if kb is None:
        return None
    for fr, v in frames_values:
        kb.value = v
        kb.keyframe_insert("value", frame=fr)
    return obj.data.shape_keys


def melt_fn(slump=0.45, spread=1.35, centre_y=0.0):
    """Slump vertically and spread outward - what a fillet does when it wets
    out and loses surface tension. Reads unmistakably as 'it has gone liquid'."""
    def f(co, i):
        co.z *= slump
        co.y = centre_y + (co.y - centre_y) * spread
        return co
    return f


def glb_morph_report(path):
    """Confirm morph targets actually made it into the file."""
    s = glb_summary(path)
    if "error" in s:
        return s
    import struct as _s
    with open(path, "rb") as f:
        data = f.read()
    off, js = 12, None
    while off < len(data):
        cl, ct = _s.unpack("<II", data[off:off + 8])
        if ct == 0x4E4F534A:
            js = json.loads(data[off + 8:off + 8 + cl].decode("utf-8"))
        pad = ((4 - (cl % 4)) % 4) if cl % 4 else 0
        off += 8 + cl + pad
    g = js or {}
    morphed = []
    for m in g.get("meshes", []):
        tgt = 0
        for pr in m.get("primitives", []):
            tgt += len(pr.get("targets", []) or [])
        if tgt:
            morphed.append({"mesh": m.get("name", "?"), "targets": tgt,
                            "weights": len(m.get("weights", []) or [])})
    return {"meshes_with_morph_targets": morphed,
            "animations": s.get("animations", [])}


# =====================================================================
# DESTRUCTIVE BEVEL - required for any mesh that carries shape keys.
#
# The glTF exporter's "Apply Modifiers" (export_apply=True) silently DISCARDS
# shape keys. So a mesh with a Bevel modifier cannot also ship morph targets:
# the melt clip exported with 2 channels but zero targets to drive.
# Bevel the mesh data itself, add the shape key afterwards, ship no modifier.
# =====================================================================
def bevel_destructive(obj, width=0.01, segments=2, angle=32.0, smooth=True):
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    thr = math.radians(angle)
    edges = []
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        try:
            if e.calc_face_angle() >= thr:
                edges.append(e)
        except Exception:
            pass
    if edges and width > 0:
        try:
            bmesh.ops.bevel(bm, geom=edges, offset=width, segments=segments,
                            profile=0.5, affect="EDGES",
                            offset_type="OFFSET", clamp_overlap=True)
        except TypeError:
            bmesh.ops.bevel(bm, geom=edges, offset=width, segments=segments,
                            profile=0.5)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    try:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shade_smooth_by_angle(angle=thr)
    except Exception:
        pass
    log("destructive bevel on %s (%d edges, no modifier -> shape keys safe)"
        % (obj.name, len(edges)))
    return obj


def assert_morph(path, expect_meshes=1):
    """Fail loudly if morph targets are missing from a shipped GLB."""
    r = glb_morph_report(path)
    got = len(r.get("meshes_with_morph_targets", []))
    ok = got >= expect_meshes
    log("MORPH CHECK %s: %d mesh(es) with targets -> %s"
        % (os.path.basename(path), got, "PASS" if ok else "FAIL"))
    r["pass"] = ok
    r["expected_meshes"] = expect_meshes
    return r


# =====================================================================
# EXPORT v4 - the morph-target fix.
#
# export_apply=True does NOT merely apply modifiers per-object: it disables
# shape-key export for the WHOLE file. Two attempts failed before I found
# that. So an asset shipping morph targets must export with apply=False, and
# therefore must carry NO modifiers - every bevel has to be destructive.
# (Armature modifiers are exempt: glTF handles skinning separately.)
# =====================================================================
def is_rig_object(o):
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
    sel = with_parents([o for o in (objects or [])], include_anchors) \
        if objects else []
    before = len(sel)
    sel = [o for o in sel if not is_rig_object(o)]
    if before != len(sel):
        log("export: dropped %d lighting-rig object(s) from the selection"
            % (before - len(sel)))

    if not apply_modifiers:
        bad = []
        for o in sel:
            for m in getattr(o, "modifiers", []):
                if m.type != "ARMATURE":
                    bad.append("%s:%s" % (o.name, m.type))
        if bad:
            log("WARNING apply=False but %d non-armature modifier(s) present "
                "- they will NOT be baked: %s" % (len(bad), ", ".join(bad[:6])))

    kw = dict(filepath=path, export_format="GLB", use_selection=bool(sel),
              export_yup=True, export_apply=bool(apply_modifiers),
              export_cameras=False, export_lights=False,
              export_animations=True, export_animation_mode=anim_mode,
              export_bake_animation=True,
              export_optimize_animation_size=True)
    if draco:
        kw["export_draco_mesh_compression_enable"] = True
        kw["export_draco_mesh_compression_level"] = 6
    try:
        kw["export_morph"] = True
        kw["export_morph_normal"] = False
    except Exception:
        pass

    def _do(kwargs):
        try:
            bpy.ops.object.select_all(action="DESELECT")
        except Exception:
            for o in bpy.data.objects:
                try: o.select_set(False)
                except Exception: pass
        for o in sel:
            try: o.select_set(True)
            except Exception: pass
        if sel:
            try:
                bpy.context.view_layer.objects.active = sel[0]
            except Exception:
                pass
        bpy.ops.export_scene.gltf(**kwargs)

    ov = _ui_override()
    attempts = [dict(kw)]
    k2 = dict(kw)
    for k in ("export_morph", "export_morph_normal",
              "export_optimize_animation_size", "export_bake_animation"):
        k2.pop(k, None)
    attempts.append(k2)
    k3 = dict(k2)
    k3.pop("export_animation_mode", None)
    k3.pop("export_draco_mesh_compression_enable", None)
    k3.pop("export_draco_mesh_compression_level", None)
    attempts.append(k3)

    done = False
    for i, kwa in enumerate(attempts):
        try:
            if ov:
                with bpy.context.temp_override(**ov):
                    _do(kwa)
            else:
                _do(kwa)
            done = True
            if i:
                log("glb exported on fallback attempt %d" % (i + 1))
            break
        except Exception as e:
            log("glb attempt %d failed: %s" % (i + 1, str(e)[:160]))
    if not done:
        return 0

    sz = os.path.getsize(path) if os.path.exists(path) else 0
    log("glb %s %.1f KB (apply=%s, %d objects)"
        % (os.path.basename(path), sz / 1024.0, apply_modifiers, len(sel)))
    if verify:
        s = glb_summary(path)
        if "error" in s:
            log("GLB VERIFY ERROR: " + s["error"])
        else:
            log("GLB VERIFY: %d nodes, %d meshes, %d tris, %d anchors, anims=%s"
                % (s["nodes"], s["meshes"], s["tris_in_file"],
                   len(s["anchors"]),
                   [(a["name"], a["channels"]) for a in s["animations"]]))
    return sz


# =====================================================================
# UVs + TEXTURES  -  the fix for "images=0 textures=0" in every GLB.
#
# Procedural node setups (noise, wave, gradient) do NOT export to glTF. Worse,
# a linked node into Base Color or Roughness makes the exporter omit the
# FACTOR too, so the flex ribbon shipped as white and the steel shell shipped
# at roughness 1.0 (flat matte). Real image maps + real UVs are the only fix.
#
# No mesh here had UVs at all - everything was built in bmesh. These generate
# them analytically: no operators, no edit mode, deterministic.
# =====================================================================
TEX_DIR = os.path.join(ROOT, "tex")
_IMG_CACHE = {}


def tex_image(name, non_color=False):
    """Load a map once and reuse it, so 30 objects share one image datablock."""
    key = (name, non_color)
    if key in _IMG_CACHE and _IMG_CACHE[key] is not None:
        return _IMG_CACHE[key]
    path = os.path.join(TEX_DIR, name + ".png")
    if not os.path.exists(path):
        log("MISSING TEXTURE: " + path)
        _IMG_CACHE[key] = None
        return None
    img = bpy.data.images.load(path, check_existing=True)
    try:
        img.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    except Exception:
        pass
    _IMG_CACHE[key] = img
    return img


_AX = {"X": 0, "Y": 1, "Z": 2}


def box_uv(obj, texel_mm=4.0):
    """Dominant-axis planar projection at a fixed world scale. Correct for
    tileable maps on arbitrary hard-surface geometry, and it never needs an
    unwrap operator. 1 UV unit = texel_mm millimetres."""
    me = obj.data
    if not me.polygons:
        return obj
    uvl = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    s = 1.0 / max(texel_mm, 1e-6)
    mw = obj.matrix_world
    for poly in me.polygons:
        n = poly.normal
        ax = max(("X", "Y", "Z"), key=lambda k: abs(n[_AX[k]]))
        if ax == "Z":
            ia, ib = 0, 1
        elif ax == "Y":
            ia, ib = 0, 2
        else:
            ia, ib = 1, 2
        for li in poly.loop_indices:
            co = mw @ me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (co[ia] * s, co[ib] * s)
    return obj


def planar_uv(obj, u_axis="Y", v_axis="X", u_range=None, v_range=None,
              u_tile=1.0, v_tile=1.0):
    """Map one world axis to U and another to V, normalised over the object's
    own extent. This is what a DIRECTIONAL map needs: the FPC trace stripes
    must land 12-across-the-width regardless of how the ribbon curves, and the
    nozzle heat gradient must run tip-to-collar exactly once."""
    me = obj.data
    if not me.polygons:
        return obj
    uvl = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    mw = obj.matrix_world
    ia, ib = _AX[u_axis.upper()], _AX[v_axis.upper()]
    pts = [mw @ v.co for v in me.vertices]
    if u_range is None:
        u_range = (min(p[ia] for p in pts), max(p[ia] for p in pts))
    if v_range is None:
        v_range = (min(p[ib] for p in pts), max(p[ib] for p in pts))
    du = max(u_range[1] - u_range[0], 1e-6)
    dv = max(v_range[1] - v_range[0], 1e-6)
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = mw @ me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (((co[ia] - u_range[0]) / du) * u_tile,
                              ((co[ib] - v_range[0]) / dv) * v_tile)
    return obj


def tex_set(mat, base=None, rough=None, nrm=None, tint=None,
            metallic=None, nrm_strength=1.0, clear=True,
            roughness_factor=0.42):
    """Rebuild a material as Principled + image maps. Clears any procedural
    network first - leaving one attached would re-trigger the omitted-factor
    bug that shipped a white ribbon."""
    if mat is None:
        return None
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    out = None
    for n in nt.nodes:
        if n.type == "OUTPUT_MATERIAL":
            out = n
    if clear:
        keep = {bsdf, out}
        for n in list(nt.nodes):
            if n not in keep:
                nt.nodes.remove(n)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    if out is None:
        out = nt.nodes.new("ShaderNodeOutputMaterial")
    if not any(l.to_node == out for l in nt.links):
        nt.links.new(bsdf.outputs[0], out.inputs["Surface"])

    def S(key, val):
        if key in bsdf.inputs:
            try:
                bsdf.inputs[key].default_value = val
            except Exception:
                pass

    # an explicit factor is ALWAYS written, so glTF never falls back to its
    # own defaults (metallic 1.0 / roughness 1.0) the way it did before
    if tint is not None:
        S("Base Color", srgb(tint) if isinstance(tint, str) else tint)
    if metallic is not None:
        S("Metallic", metallic)
    if rough is None and roughness_factor is not None:
        S("Roughness", roughness_factor)

    x = -700
    if base:
        img = tex_image(base, non_color=False)
        if img:
            n = nt.nodes.new("ShaderNodeTexImage")
            n.image = img
            n.location = (x, 300)
            nt.links.new(n.outputs["Color"], bsdf.inputs["Base Color"])
    if rough:
        img = tex_image(rough, non_color=True)
        if img:
            n = nt.nodes.new("ShaderNodeTexImage")
            n.image = img
            n.location = (x, 0)
            nt.links.new(n.outputs["Color"], bsdf.inputs["Roughness"])
    if nrm:
        img = tex_image(nrm, non_color=True)
        if img:
            n = nt.nodes.new("ShaderNodeTexImage")
            n.image = img
            n.location = (x, -300)
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.location = (x + 250, -300)
            nm.inputs["Strength"].default_value = nrm_strength
            nt.links.new(n.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    log("tex_set %s: base=%s rough=%s nrm=%s" % (mat.name, base, rough, nrm))
    return mat


def glb_texture_report(path):
    s = glb_summary(path)
    if "error" in s:
        return s
    import struct as _s
    d = open(path, "rb").read()
    off, js = 12, None
    while off < len(d):
        cl, ct = _s.unpack("<II", d[off:off + 8])
        if ct == 0x4E4F534A:
            js = json.loads(d[off + 8:off + 8 + cl].decode("utf-8"))
        pad = ((4 - (cl % 4)) % 4) if cl % 4 else 0
        off += 8 + cl + pad
    g = js or {}
    mats = []
    for m in g.get("materials", []):
        pbr = m.get("pbrMetallicRoughness", {})
        mats.append({
            "name": m.get("name", "?"),
            "baseColorTexture": "baseColorTexture" in pbr,
            "metallicRoughnessTexture": "metallicRoughnessTexture" in pbr,
            "normalTexture": "normalTexture" in m,
            "baseColorFactor": [round(v, 3) for v in
                                pbr.get("baseColorFactor", [])[:3]] or None,
            "roughnessFactor": pbr.get("roughnessFactor"),
        })
    textured = sum(1 for m in mats if m["baseColorTexture"]
                   or m["metallicRoughnessTexture"] or m["normalTexture"])
    return {"images": len(g.get("images", [])),
            "textures": len(g.get("textures", [])),
            "materials_total": len(mats), "materials_textured": textured,
            "materials": mats, "kb": s.get("kb")}
