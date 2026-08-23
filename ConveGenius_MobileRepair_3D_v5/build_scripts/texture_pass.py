# =====================================================================
# texture_pass.py - give every asset real UVs and real image maps
#
# One centralised pass instead of editing five build scripts: open each
# .blend, assign UVs per object, rebuild mapped materials as Principled +
# image textures, tidy the sloppy _V2 material names, re-export, verify.
#
# UV MODES
#   box     - dominant-axis planar projection at a fixed mm scale. Correct for
#             tileable noise (steel grain, PCB mottle, solder grain).
#   ribbon  - u across the flex WIDTH, v along its LENGTH. The 12 trace
#             stripes must land 12-across regardless of how it curves.
#   nozzle  - v runs tip-to-collar exactly once, for the heat gradient.
#
# Usage: blender-launcher.exe --python texture_pass.py
# =====================================================================
import bpy, os, sys, json, fnmatch

sys.path.insert(0, os.path.join(os.path.expanduser("~"), "ConveGenius_3D", "scripts"))
import cg_lib as C

# material name pattern -> maps + uv treatment
MAP = [
 ("MAT_STEEL_SHELL",  dict(rough="steel_rough",
                           tint="#8E9194", metallic=1.0),
                      ("box", 1.4)),
 ("MAT_STEEL_SEAM",   dict(rough="steel_rough", tint="#7E8185", metallic=1.0),
                      ("box", 1.4)),
 ("MAT_SHIELD_NICKEL",dict(tint="#9DA1A6", metallic=1.0),
                      ("box", 6.0)),
 ("MAT_NICKEL_BRUSH", dict(tint="#9A9DA1", metallic=1.0),
                      ("box", 6.0)),
 ("MAT_PIN_*",        dict(rough="gold_rough", tint="#D9B551", metallic=1.0),
                      ("box", 1.2)),
 ("MAT_GOLD_HARD*",   dict(rough="gold_rough", tint="#D9B551", metallic=1.0),
                      ("box", 1.2)),
 ("MAT_GOLD_WORN*",   dict(rough="solder_cold_rough", tint="#8A6A3C",
                           metallic=1.0), ("box", 1.0)),
 ("MAT_PCB_MASK*",    dict(rough="pcb_rough", nrm="pcb_nrm", tint="#0E4F3C",
                           metallic=0.0, nrm_strength=0.28), ("box", 5.0)),
 ("MAT_FR4_CORE*",    dict(rough="pcb_rough", tint="#B7A277", metallic=0.0),
                      ("box", 6.0)),
 ("MAT_SOLDER_GOOD*", dict(rough="solder_good_rough", tint="#BFC4C9",
                           metallic=1.0), ("box", 1.4)),
 ("MAT_SOLDER_ANCHOR",dict(rough="solder_good_rough", tint="#C0C5CA",
                           metallic=1.0), ("box", 1.4)),
 ("MAT_SOLDER_COLD*", dict(rough="solder_cold_rough", nrm="solder_cold_nrm",
                           tint="#A8ABAE", metallic=1.0, nrm_strength=0.55),
                      ("box", 0.9)),
 ("MAT_OLD_SOLDER",   dict(rough="solder_cold_rough", nrm="solder_cold_nrm",
                           tint="#8E9195", metallic=1.0, nrm_strength=0.5),
                      ("box", 0.9)),
 ("MAT_POLYIMIDE*",   dict(base="fpc_basecolor", rough="fpc_rough",
                           nrm="fpc_nrm", metallic=0.0, nrm_strength=0.6),
                      ("ribbon", 1.0)),
 ("MAT_NOZZLE_HOT",   dict(base="nozzle_heat_basecolor",
                           rough="nozzle_heat_rough", metallic=1.0),
                      ("nozzle", 1.0)),
 ("MAT_ESD_BODY",     dict(rough="esd_rough", tint="#41454B",
                           metallic=0.0), ("box", 30.0)),
 ("MAT_ESD_DARK",     dict(rough="esd_rough", tint="#292D31", metallic=0.0),
                      ("box", 22.0)),
 ("MAT_PLASTIC_ESD",  dict(rough="esd_rough", tint="#3A3D40", metallic=0.0),
                      ("box", 22.0)),
 ("MAT_HANDGRIP",     dict(rough="esd_rough", tint="#2A2D31",
                           metallic=0.0), ("box", 18.0)),
 ("MAT_HOUSING_LCP*", dict(rough="esd_rough", tint="#28282C", metallic=0.0),
                      ("box", 4.0)),
 ("MAT_ZIF_LCP",      dict(rough="esd_rough", tint="#1C1C20", metallic=0.0),
                      ("box", 4.0)),
 ("MAT_ZIF_FLAP",     dict(rough="esd_rough", tint="#26262B", metallic=0.0),
                      ("box", 4.0)),
 ("MAT_TONGUE_LCP",   dict(rough="esd_rough", tint="#A9A8A1", metallic=0.0),
                      ("box", 4.0)),
 ("MAT_CMP_CERAMIC",  dict(rough="esd_rough", tint="#2B2724", metallic=0.0),
                      ("box", 1.2)),
 ("MAT_PASSIVE_CERAMIC", dict(rough="esd_rough", tint="#2B2724",
                              metallic=0.0), ("box", 1.2)),
 ("MAT_FPC_COPPER*",  dict(rough="gold_rough", tint="#A9642F", metallic=1.0),
                      ("box", 2.0)),
 ("MAT_TRACE_HIGHLIGHT", dict(rough="gold_rough", tint="#C98A48",
                              metallic=1.0), ("box", 2.0)),
 ("MAT_COPPER_BARE",  dict(rough="gold_rough", tint="#A55A32", metallic=1.0),
                      ("box", 2.0)),
 ("MAT_TIN_CAP",      dict(rough="solder_good_rough", tint="#C8CCD0",
                           metallic=1.0), ("box", 1.2)),
]

# tidy the iteration artefacts: material names ARE the runtime API surface
RENAME = {
 "MAT_HOUSING_LCP_V2": "MAT_HOUSING_LCP",
 "MAT_PCB_MASK_V2": "MAT_PCB_MASK",
 "MAT_SOLDER_GOOD_V2": "MAT_SOLDER_GOOD",
 "MAT_SOLDER_COLD_V2": "MAT_SOLDER_COLD",
 "MAT_GOLD_WORN_V2": "MAT_GOLD_WORN",
 "MAT_POLYIMIDE_V2": "MAT_POLYIMIDE",
 "MAT_POLYIMIDE_ASM": "MAT_POLYIMIDE",
 "MAT_FPC_COPPER_ASM": "MAT_FPC_COPPER",
 "MAT_FR4_CORE_V2": "MAT_FR4_CORE",
}

# tile size must track the physical size of the parts: a 3.4 mm solder
# coupon and a 120 mm mainboard cannot share one texel scale
TEXEL_SCALE = {"B05_PORT": 0.55, "B10_B11_IFC": 0.75,
               "B40_JOINT": 0.15, "B02_MAINBOARD": 1.0,
               "B28_HOTAIR": 1.0, "B02_ASSEMBLY": 1.0}

ASSETS = [
 ("B05_PORT",      "B05_PORT.blend",      True),
 ("B10_B11_IFC",   "B10_B11_IFC.blend",   False),   # morph targets: apply=False
 ("B40_JOINT",     "B40_JOINT.blend",     True),
 ("B02_MAINBOARD", "B02_MAINBOARD.blend", True),
 ("B28_HOTAIR",    "B28_HOTAIR.blend",    True),
 # apply=True: the assembly is a hero/context scene and needs its bevels.
 # The solder melt lives in B10_B11_IFC, which is where that close-up happens.
 ("B02_ASSEMBLY",  "B02_ASSEMBLY.blend",  True),
]

report = {}

def lookup(matname):
    for pat, kw, uv in MAP:
        if fnmatch.fnmatch(matname, pat):
            return kw, uv
    return None, None

for name, blend, apply_mod in ASSETS:
    path = os.path.join(C.OUT, blend)
    if not os.path.exists(path):
        report[name] = {"error": "blend not found"}
        continue
    bpy.ops.wm.open_mainfile(filepath=path)
    C._IMG_CACHE.clear()

    # --- tidy names first so the MAP patterns hit the clean ones
    renamed = []
    for old, new in RENAME.items():
        m = bpy.data.materials.get(old)
        if m is None:
            continue
        if bpy.data.materials.get(new) is None:
            m.name = new
            renamed.append("%s -> %s" % (old, new))
        else:
            # a clean-named twin already exists: point users at it instead
            m.name = new + "_DUP"
            renamed.append("%s -> %s (dup)" % (old, new))

    # --- materials: rebuild each mapped one exactly once
    done, skipped = [], []
    for mat in bpy.data.materials:
        kw, uv = lookup(mat.name)
        if kw is None:
            skipped.append(mat.name)
            continue
        C.tex_set(mat, **kw)
        done.append(mat.name)

    # --- special case: the airflow cone. It shipped baseColor [0,0,0] (black)
    # because it is a custom emission/transparent graph. Give it something
    # glTF can actually express: emissive + alpha blend.
    af = bpy.data.materials.get("MAT_B28_AIRFLOW")
    if af:
        af.use_nodes = True
        nt = af.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        b = nt.nodes.new("ShaderNodeBsdfPrincipled")
        o = nt.nodes.new("ShaderNodeOutputMaterial")
        b.inputs["Base Color"].default_value = C.srgb("#FF8A3C")
        b.inputs["Alpha"].default_value = 0.30
        if "Emission Color" in b.inputs:
            b.inputs["Emission Color"].default_value = C.srgb("#FF8A3C")
        if "Emission Strength" in b.inputs:
            b.inputs["Emission Strength"].default_value = 2.4
        nt.links.new(b.outputs[0], o.inputs["Surface"])
        try:
            af.blend_method = "BLEND"
        except Exception:
            pass
        done.append("MAT_B28_AIRFLOW (emissive+BLEND)")

    # --- UVs, per object, chosen by its material
    uvs = {"box": 0, "ribbon": 0, "nozzle": 0, "none": 0}
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.data.polygons:
            continue
        mn = o.data.materials[0].name if o.data.materials and o.data.materials[0] else ""
        kw, uv = lookup(mn)
        if uv is None:
            C.box_uv(o, 8.0 * TEXEL_SCALE.get(name, 1.0))   # default so nothing is UV-less
            uvs["none"] += 1
            continue
        mode, param = uv
        if mode == "ribbon":
            C.planar_uv(o, u_axis="Y", v_axis="X", u_tile=1.0, v_tile=1.0)
            uvs["ribbon"] += 1
        elif mode == "nozzle":
            C.planar_uv(o, u_axis="X", v_axis="Y", u_tile=1.0, v_tile=1.0)
            uvs["nozzle"] += 1
        else:
            C.box_uv(o, param * TEXEL_SCALE.get(name, 1.0))
            uvs["box"] += 1

    # ---- SHIP EVERY STATE VISIBLE ------------------------------------
    # glTF has no per-node visibility, and the exporter DROPS render-hidden
    # objects entirely. B40 was shipping 1 of its 5 joint states (only GOOD)
    # and every damage variant / zone plate was missing for the same reason.
    # Anything the runtime is supposed to toggle must be IN the file; the
    # runtime decides what is visible, not the exporter.
    unhidden = []
    for o in bpy.data.objects:
        if C.is_rig_object(o):
            continue
        if o.hide_render or o.hide_viewport:
            o.hide_render = False
            o.hide_viewport = False
            unhidden.append(o.name)
    for coll in bpy.data.collections:
        if coll.hide_render or coll.hide_viewport:
            coll.hide_render = False
            coll.hide_viewport = False
            unhidden.append("[coll]" + coll.name)
    if unhidden:
        C.log("unhid %d object(s)/collection(s) so the runtime can toggle "
              "them: %s" % (len(unhidden), ", ".join(unhidden[:10])))

    # ---- DEDUPE MATERIALS -------------------------------------------
    # appending B05/B11 into the assembly created MAT_GOLD_HARD.001 etc.
    # Material names are the runtime API surface, so collapse the twins.
    merged = []
    for m in list(bpy.data.materials):
        if "." not in m.name:
            continue
        base = m.name.rsplit(".", 1)[0]
        tgt = bpy.data.materials.get(base)
        if tgt is None or tgt is m:
            continue
        for ob in bpy.data.objects:
            if ob.type != "MESH":
                continue
            for slot in ob.material_slots:
                if slot.material is m:
                    slot.material = tgt
        merged.append("%s -> %s" % (m.name, base))
    if merged:
        C.log("deduped materials: " + ", ".join(merged))

    C.save_blend(os.path.join(C.OUT, blend))
    out = os.path.join(C.GLB, name + "_LOD0.glb")
    sz = C.export_glb(out, objects=[x for x in bpy.data.objects
                                    if x.type in ("MESH", "ARMATURE")
                                    and not C.is_rig_object(x)],
                      draco=True, anim_mode="NLA_TRACKS",
                      apply_modifiers=apply_mod)
    tr = C.glb_texture_report(out)
    report[name] = {
        "kb": round(sz / 1024.0, 1),
        "images_in_glb": tr.get("images"),
        "textures_in_glb": tr.get("textures"),
        "materials_total": tr.get("materials_total"),
        "materials_textured": tr.get("materials_textured"),
        "uv_modes": uvs,
        "materials_mapped": sorted(done),
        "materials_left_flat": sorted(skipped),
        "renamed": renamed,
        "unhidden_for_runtime": unhidden,
        "materials_deduped": merged,
        "untextured_after": [m["name"] for m in tr.get("materials", [])
                             if not (m["baseColorTexture"]
                                     or m["metallicRoughnessTexture"]
                                     or m["normalTexture"])],
    }
    C.log("%s -> %.1f KB, %d images, %d/%d materials textured"
          % (name, sz / 1024.0, tr.get("images", 0),
             tr.get("materials_textured", 0), tr.get("materials_total", 0)))

tot = sum(v.get("kb", 0) for v in report.values() if isinstance(v, dict))
with open(os.path.join(C.OUT, "TEXTURE_REPORT.json"), "w") as f:
    json.dump({"per_asset": report, "total_kb": round(tot, 1),
               "pct_of_25mb": round(100 * tot / (25 * 1024), 3)}, f, indent=1)
print("[TEX PASS] total %.1f KB" % tot)
print(json.dumps({k: {"kb": v.get("kb"), "images": v.get("images_in_glb"),
                      "textured": v.get("materials_textured")}
                  for k, v in report.items()}, indent=1))
