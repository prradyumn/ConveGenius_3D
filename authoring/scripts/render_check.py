# Render the TEXTURED .blend files so the maps can be checked visually.
# Confirms UVs landed correctly - especially the 12 FPC trace stripes and the
# nozzle heat gradient, which are directional and easy to get wrong.
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cg_lib as C

SHOTS = [
 ("B10_B11_IFC.blend", "TXV_ifc_ribbon", (-24.0, -34.0, 20.0),
  (-14.0, 0.0, 2.6), 100, 26.0, None),
 ("B10_B11_IFC.blend", "TXV_ifc_socket", (-9.0, -15.0, 9.0),
  (-0.6, 0.0, 1.0), 110, 26.0, "B11_"),
 ("B28_HOTAIR.blend", "TXV_nozzle", (-38.0, -60.0, 26.0),
  (0.0, 0.0, 0.0), 125, 210.0, "B28_NOZZLE"),
 ("B05_PORT.blend", "TXV_port_steel", (-13.0, -15.0, 9.5),
  (0.0, 2.6, 0.0), 100, 11.0, None),
 ("B40_JOINT.blend", "TXV_joint_cold", (-3.4, -6.2, 3.1),
  (0.0, 0.0, 0.25), 115, 2.3, "COLD"),
 ("B02_MAINBOARD.blend", "TXV_board", (3.0, -30.0, 104.0),
  (0.0, 0.0, 0.0), 105, 95.0, None),
]

for blend, name, loc, tgt, focal, lscale, subj_filter in SHOTS:
    p = os.path.join(C.OUT, blend)
    if not os.path.exists(p):
        C.log("missing " + blend)
        continue
    bpy.ops.wm.open_mainfile(filepath=p)
    sc = bpy.context.scene
    sc.render.engine = C.pick_engine(False)
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"

    # B40: show only the COLD state so the grain map is visible
    if subj_filter == "COLD":
        for o in bpy.data.objects:
            if o.name.startswith("B40_STATE_"):
                hide = "COLD" not in o.name
                o.hide_render = hide
                for ch in o.children:
                    ch.hide_render = hide
        for o in bpy.data.objects:
            if o.type == "MESH" and "B40_STATE_" in o.name:
                o.hide_render = "COLD" not in o.name

    C.lighting_rig(scale=lscale, k=30.0, cavity=False)
    C.studio_world(strength=0.95)
    C.reflector_cards(scale=lscale, strength=7.0)
    if "B05" in blend:
        C.light_aim("CG_CAVITY", (0.0, -26.0, 7.0), (0.0, 2.6, 0.0),
                    energy_k=34.0, size_rel=0.85, scale=11.0, power=1.10)
    C.set_look()
    C.fix_clipping()

    subj = [o for o in bpy.data.objects
            if o.type == "MESH" and not o.hide_render
            and not o.name.startswith("CG_")]
    if subj_filter and subj_filter not in ("COLD",):
        f = [o for o in subj if subj_filter in o.name]
        if f:
            subj = f
    if not subj:
        C.log("no subject for " + name)
        continue

    cam = C.camera(name + "_cam", loc, tgt, focal=focal, dof=False)
    C.frame_camera(cam, subj, margin=1.14, target=tgt, res=(1500, 1100))
    C.auto_expose(cam, target=0.22)
    C.render(cam, os.path.join(C.REN, name + ".png"),
             res=(1500, 1100), samples=72)

print("[TXV] done")
