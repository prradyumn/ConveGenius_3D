# =====================================================================
# make_textures.py - generate the tileable map set
#
# WHY NOT BLENDER'S BAKE: baking is per-object, so 35 objects would mean 35
# images per asset, it needs Cycles plus a lot of operator context, and it
# needs UVs to already exist. Generating the maps directly is fewer files,
# exact control, and reproduces what the procedural nodes were doing.
#
# Everything here is TILEABLE (periodic value noise) except two directional
# maps that must not repeat: the FPC trace stripes and the nozzle heat
# gradient. Those two are the ones carrying real teaching information.
#
# Usage: blender-launcher.exe --python make_textures.py
# =====================================================================
import bpy, os, sys, math
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "tex")
os.makedirs(TEX, exist_ok=True)
rng = np.random.default_rng(20260821)


def periodic_noise(res, period, octaves=4, gain=0.5):
    """Value noise that tiles exactly, by using a periodic integer lattice."""
    out = np.zeros((res, res), dtype=np.float64)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        p = max(2, int(period * (2 ** o)))
        lat = rng.random((p, p))
        # bilinear upsample with wraparound
        ys = np.linspace(0, p, res, endpoint=False)
        xs = np.linspace(0, p, res, endpoint=False)
        y0 = np.floor(ys).astype(int) % p
        x0 = np.floor(xs).astype(int) % p
        y1 = (y0 + 1) % p
        x1 = (x0 + 1) % p
        fy = (ys - np.floor(ys))[:, None]
        fx = (xs - np.floor(xs))[None, :]
        fy = fy * fy * (3 - 2 * fy)
        fx = fx * fx * (3 - 2 * fx)
        a = lat[np.ix_(y0, x0)]
        b = lat[np.ix_(y0, x1)]
        c = lat[np.ix_(y1, x0)]
        d = lat[np.ix_(y1, x1)]
        val = (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
        out += val * amp
        tot += amp
        amp *= gain
    return out / max(tot, 1e-9)


def stretch(a, sx=1, sy=1):
    """Anisotropic smear - how a brushed / drawn finish actually looks."""
    if sy > 1:
        k = np.ones(sy) / sy
        a = np.apply_along_axis(lambda m: np.convolve(
            np.concatenate([m[-sy:], m, m[:sy]]), k, mode="same")[sy:-sy],
            0, a)
    if sx > 1:
        k = np.ones(sx) / sx
        a = np.apply_along_axis(lambda m: np.convolve(
            np.concatenate([m[-sx:], m, m[:sx]]), k, mode="same")[sx:-sx],
            1, a)
    return a


def norm01(a):
    lo, hi = a.min(), a.max()
    return (a - lo) / max(hi - lo, 1e-9)


def save_gray(name, a, remap=None):
    """Single-channel data written as a non-colour RGB image."""
    a = np.clip(a, 0.0, 1.0)
    if remap:
        a = remap[0] + a * (remap[1] - remap[0])
    res = a.shape[0]
    img = bpy.data.images.new(name, res, res, alpha=False, float_buffer=False)
    px = np.zeros((res, res, 4), dtype=np.float32)
    px[..., 0] = a
    px[..., 1] = a
    px[..., 2] = a
    px[..., 3] = 1.0
    img.pixels.foreach_set(px.reshape(-1))
    img.filepath_raw = os.path.join(TEX, name + ".png")
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    print("[TEX]", name, res, "grayscale")


def save_rgb(name, rgb, w=None, h=None):
    h_, w_ = rgb.shape[0], rgb.shape[1]
    img = bpy.data.images.new(name, w_, h_, alpha=False, float_buffer=False)
    px = np.zeros((h_, w_, 4), dtype=np.float32)
    px[..., :3] = np.clip(rgb, 0.0, 1.0)
    px[..., 3] = 1.0
    img.pixels.foreach_set(px.reshape(-1))
    img.filepath_raw = os.path.join(TEX, name + ".png")
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    print("[TEX]", name, w_, "x", h_, "rgb")


def height_to_normal(hmap, strength=1.4):
    """Tangent-space normal map from a height field, wrapping at the edges."""
    h = hmap.astype(np.float64)
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * strength
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * strength
    nz = np.ones_like(h)
    ln = np.sqrt(dx * dx + dy * dy + nz * nz)
    n = np.stack([-dx / ln, -dy / ln, nz / ln], axis=-1)
    return n * 0.5 + 0.5


def srgb_u(hexstr):
    h = hexstr.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


R = 512

# ---------------------------------------------------------------- steel
# brushed / drawn stainless: fine streaks along one axis + micro-scratches
n = periodic_noise(R, 6, octaves=5)
streak = stretch(periodic_noise(R, 3, octaves=5), sx=1, sy=26)
steel_h = norm01(0.65 * streak + 0.35 * n)
scratch = (periodic_noise(R, 40, octaves=2) > 0.86).astype(float)
scratch = stretch(scratch, sx=1, sy=9) * 0.5
save_gray("steel_rough", norm01(steel_h * 0.8 + scratch), remap=(0.22, 0.42))
save_rgb("steel_nrm", height_to_normal(steel_h * 0.5 + scratch * 0.5, 1.1))

# ---------------------------------------------------------------- gold
g = periodic_noise(R, 14, octaves=4)
save_gray("gold_rough", g, remap=(0.14, 0.27))

# ---------------------------------------------------------------- PCB mask
# a real board is not one flat green: mottling, glossier over dense copper,
# faint routed-trace relief, and flux staining
mott = periodic_noise(R, 5, octaves=5)
bands = np.zeros((R, R))
for i in range(26):
    y = int(rng.integers(0, R))
    th = int(rng.integers(2, 6))
    for k in range(th):
        bands[(y + k) % R, :] = 1.0
bands = stretch(bands, sx=3, sy=1)
tracks = np.maximum(bands, stretch(np.rot90(bands), sx=1, sy=3) * 0.7)
pcb_h = norm01(0.55 * tracks + 0.45 * mott)
save_gray("pcb_rough", norm01(mott * 0.7 + (1.0 - tracks) * 0.3),
          remap=(0.28, 0.52))
save_rgb("pcb_nrm", height_to_normal(pcb_h, 1.6))

# ---------------------------------------------------------------- solder
# COLD: coarse, grainy, wrinkled. This texture is half the reason a cold
# joint reads as bad at thumbnail size.
c = periodic_noise(R, 22, octaves=5, gain=0.62)
wrinkle = periodic_noise(R, 9, octaves=3)
cold_h = norm01(0.6 * c + 0.4 * wrinkle)
save_gray("solder_cold_rough", cold_h, remap=(0.52, 0.84))
save_rgb("solder_cold_nrm", height_to_normal(cold_h, 2.2))
# GOOD: near-specular, only the faintest variation
sg = periodic_noise(R, 10, octaves=3)
save_gray("solder_good_rough", sg, remap=(0.20, 0.31))

# ---------------------------------------------------------------- ESD plastic
e = periodic_noise(R, 30, octaves=4)
save_gray("esd_rough", e, remap=(0.46, 0.64))
save_rgb("esd_nrm", height_to_normal(e, 0.6))

# ---------------------------------------------------------------- FPC traces
# NOT tileable across U: 12 copper traces at a fixed count across the 6 mm
# ribbon width. u = across width, v = along length (see ribbon UVs).
W, H = 512, 256
u = np.linspace(0.0, 1.0, W, endpoint=False)[None, :].repeat(H, axis=0)
amber = srgb_u("#A2701F")
copper = srgb_u("#C08A3C")
dark = srgb_u("#6E4A14")
NT = 12
duty = 0.46
phase = (u * NT) % 1.0
trace = (phase < duty).astype(float)
edge = np.minimum(np.abs(phase - 0.0), np.abs(phase - duty))
soft = np.clip(edge * NT * 6.0, 0.0, 1.0)
grain = periodic_noise(256, 18, octaves=3)[:H, :W]
if grain.shape != (H, W):
    grain = np.resize(grain, (H, W))
rgbmap = (trace[..., None] * copper[None, None, :]
          + (1 - trace)[..., None] * amber[None, None, :])
rgbmap *= (0.88 + 0.24 * grain)[..., None]
rgbmap = rgbmap * (0.72 + 0.28 * soft)[..., None] \
    + dark[None, None, :] * (0.28 * (1 - soft))[..., None]
save_rgb("fpc_basecolor", rgbmap)
save_rgb("fpc_nrm", height_to_normal(np.resize(trace * 0.6 + grain * 0.4,
                                               (H, W)), 1.0))
rough = 0.30 + 0.22 * (1 - trace) + 0.08 * grain
img = bpy.data.images.new("fpc_rough", W, H, alpha=False)
px = np.zeros((H, W, 4), dtype=np.float32)
for ch in range(3):
    px[..., ch] = np.clip(rough, 0, 1)
px[..., 3] = 1.0
img.pixels.foreach_set(px.reshape(-1))
img.filepath_raw = os.path.join(TEX, "fpc_rough.png")
img.file_format = "PNG"
img.save()
bpy.data.images.remove(img)
print("[TEX] fpc_rough", W, "x", H)

# ---------------------------------------------------------------- nozzle heat
# straw -> blue oxidation toward the tip. This is the cue that tells a learner
# "this end is HOT" with no label, so it must not be lost.
W2, H2 = 64, 512
t = np.linspace(0.0, 1.0, H2)[:, None].repeat(W2, axis=1)
cool = srgb_u("#A9ADB1")
straw = srgb_u("#B9924E")
violet = srgb_u("#6E5A86")
blue = srgb_u("#41598C")
heat = np.zeros((H2, W2, 3))
for i in range(3):
    heat[..., i] = np.interp(t.ravel(), [0.0, 0.42, 0.68, 1.0],
                             [cool[i], straw[i], violet[i], blue[i]]
                             ).reshape(H2, W2)
sp = periodic_noise(64, 10, octaves=3)[:H2 % 64 or 64, :W2]
heat *= (0.95 + 0.10 * np.resize(sp, (H2, W2)))[..., None]
save_rgb("nozzle_heat_basecolor", heat)
nz_r = 0.28 + 0.20 * t
img = bpy.data.images.new("nozzle_heat_rough", W2, H2, alpha=False)
px = np.zeros((H2, W2, 4), dtype=np.float32)
for ch in range(3):
    px[..., ch] = np.clip(nz_r, 0, 1)
px[..., 3] = 1.0
img.pixels.foreach_set(px.reshape(-1))
img.filepath_raw = os.path.join(TEX, "nozzle_heat_rough.png")
img.file_format = "PNG"
img.save()
bpy.data.images.remove(img)
print("[TEX] nozzle_heat_rough", W2, "x", H2)

files = sorted(os.listdir(TEX))
total = sum(os.path.getsize(os.path.join(TEX, f)) for f in files)
print("[TEX] wrote %d files, %.1f KB total" % (len(files), total / 1024.0))
for f in files:
    print("   ", f, "%.1f KB" % (os.path.getsize(os.path.join(TEX, f)) / 1024.0))
