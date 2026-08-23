import bpy, sys, json, os, platform
out = os.path.join(os.path.expanduser("~"), "ConveGenius_3D", "out", "probe.json")
d = {"blender": bpy.app.version_string, "py": sys.version.split()[0],
     "bg": bpy.app.background, "plat": platform.platform(),
     "gltf": hasattr(bpy.ops.export_scene, "gltf")}
with open(out, "w") as f:
    json.dump(d, f, indent=1)
print("PROBE OK")
