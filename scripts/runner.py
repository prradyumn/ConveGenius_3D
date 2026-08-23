# Wrapper: runs a build script and captures any traceback to disk, so a
# failure in a headed Blender session is still diagnosable.
import sys, os, traceback, json, runpy

ROOT = os.path.join(os.path.expanduser("~"), "ConveGenius_3D")
SCRIPTS = os.path.join(ROOT, "scripts")
OUT = os.path.join(ROOT, "out")
os.makedirs(OUT, exist_ok=True)

target = None
for i, a in enumerate(sys.argv):
    if a == "--cg-build" and i + 1 < len(sys.argv):
        target = sys.argv[i + 1]
if not target:
    target = os.environ.get("CG_BUILD", "build_b05_port.py")

status = os.path.join(OUT, "RUN_STATUS.json")
with open(status, "w") as f:
    json.dump({"state": "running", "target": target}, f)

path = os.path.join(SCRIPTS, target)
try:
    runpy.run_path(path, run_name="__main__")
    with open(status, "w") as f:
        json.dump({"state": "ok", "target": target}, f)
    print("[RUNNER] OK " + target)
except Exception:
    tb = traceback.format_exc()
    with open(os.path.join(OUT, "RUN_ERROR.txt"), "w") as f:
        f.write(tb)
    with open(status, "w") as f:
        json.dump({"state": "error", "target": target,
                   "tail": tb.strip().splitlines()[-6:]}, f, indent=1)
    print("[RUNNER] ERROR\n" + tb)
