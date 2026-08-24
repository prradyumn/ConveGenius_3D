# Build several assets in one headed Blender session, one after another,
# each in a fresh scene. Any failure is captured and the queue continues.
import sys, os, json, traceback, runpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
OUT = os.path.join(ROOT, "out")
os.makedirs(OUT, exist_ok=True)

QUEUE = []
for i, a in enumerate(sys.argv):
    if a == "--cg-queue" and i + 1 < len(sys.argv):
        QUEUE = [q.strip() for q in sys.argv[i + 1].split(",") if q.strip()]
if not QUEUE:
    QUEUE = ["build_b05_port.py"]

status = os.path.join(OUT, "RUN_STATUS.json")
results = []

def write(state, current=None):
    with open(status, "w") as f:
        json.dump({"state": state, "queue": QUEUE, "current": current,
                   "results": results}, f, indent=1)

write("running", QUEUE[0] if QUEUE else None)
for target in QUEUE:
    write("running", target)
    try:
        runpy.run_path(os.path.join(SCRIPTS, target), run_name="__main__")
        results.append({"target": target, "state": "ok"})
        print("[QUEUE] OK " + target)
    except Exception:
        tb = traceback.format_exc()
        with open(os.path.join(OUT, "ERR_" + target + ".txt"), "w") as f:
            f.write(tb)
        results.append({"target": target, "state": "error",
                        "tail": tb.strip().splitlines()[-5:]})
        print("[QUEUE] ERROR " + target + "\n" + tb)
    write("running", target)
write("done", None)
print("[QUEUE] ALL DONE")
