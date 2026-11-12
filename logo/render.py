"""Tiny physically based ray tracer for glass blueberries (numpy, vectorised).

Glass spheres with Fresnel reflection, refraction (IOR 1.5), Beer-Lambert blue
absorption, a recessed star-shaped crown (normal-perturbed, dark tinted),
trapped bubbles, and a ground plane with soft, blue-tinted shadows plus a
lens-focused caustic.
"""
import sys
import numpy as np
from PIL import Image, ImageFilter

N = int(sys.argv[1]) if len(sys.argv) > 1 else 600     # render size (square)
SS = 2                                                   # supersampling per axis
OUT = sys.argv[2] if len(sys.argv) > 2 else 'glass.png'
rng = np.random.default_rng(7)

def norm(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True)

# ---------------- scene ----------------
GROUND = np.array([0.80, 0.85, 0.845])                  # grey-teal surface
IOR = 1.5
SIGMA = np.array([0.5, 0.24, 0.075])                    # absorption per unit length (blue glass)

def tilt(v):
    return norm(np.array(v, float))

# centre, radius, crown axis (tilted toward camera), crown spin
BERRIES = [
    (np.array([-1.02, 0.98, 0.55]), 0.98, tilt([-0.15, 1.0, 0.55]), 0.3),
    (np.array([1.05, 0.92, 0.62]), 0.92, tilt([0.2, 1.0, 0.5]), 1.1),
    (np.array([0.02, 1.0, -1.05]), 1.0, tilt([0.05, 1.0, 0.45]), 2.0),
]
# bubbles: (berry index, local offset, radius)
BUBBLES = []
for bi, (c, r, ax, sp) in enumerate(BERRIES):
    for _ in range(26):
        v = rng.normal(size=3); v /= np.linalg.norm(v)
        BUBBLES.append((bi, c + v * r * rng.uniform(0.25, 0.8), r * rng.uniform(0.004, 0.014)))

LIGHT_C = np.array([-5.5, 9.0, 5.0])                    # area light centre
LIGHT_U = np.array([2.2, 0.0, 0.0]); LIGHT_V = np.array([0.0, 1.2, -1.6])
LIGHT_DIR = norm(LIGHT_C)

# ---------------- camera ----------------
eye = np.array([0.0, 5.9, 9.6]); look = np.array([0.0, 0.75, -0.15]); fov = 34
fw = norm(look - eye); rt = norm(np.cross(fw, [0, 1, 0])); up = np.cross(rt, fw)
M = N * SS
t = np.tan(np.radians(fov) / 2)
xs = (np.arange(M) + 0.5) / M * 2 - 1
X, Y = np.meshgrid(xs * t, -xs * t)
D = norm(X[..., None] * rt + Y[..., None] * up + fw).reshape(-1, 3)
O = np.broadcast_to(eye, D.shape).copy()

# ---------------- environment (studio) ----------------
def env(d):
    """Seamless studio: soft bright top, grey-teal walls, a large softbox up-left."""
    y = d[:, 1:2]
    base = np.where(y > 0, 0.86 + 0.14 * np.clip(y, 0, 1), 0.82)
    col = base * np.array([0.92, 0.96, 0.96])
    # softbox: bright window toward the light
    s = np.clip((d @ LIGHT_DIR - 0.9) / 0.03, 0, 1)[:, None]
    col = col + s * 3.6
    # a second, dimmer strip light on the right for rim highlights
    s2 = np.clip((d @ norm(np.array([6.0, 4.0, -2.0])) - 0.975) / 0.012, 0, 1)[:, None]
    return col + s2 * 1.4

# ---------------- intersections ----------------
def hit_sphere(o, d, c, r):
    oc = o - c
    b = np.einsum('ij,ij->i', oc, d)
    cc = np.einsum('ij,ij->i', oc, oc) - r * r
    disc = b * b - cc
    ok = disc > 0
    sq = np.sqrt(np.where(ok, disc, 0))
    t0 = -b - sq; t1 = -b + sq
    t = np.where(t0 > 1e-4, t0, np.where(t1 > 1e-4, t1, np.inf))
    return np.where(ok, t, np.inf)

def hit_ground(o, d):
    t = np.where(d[:, 1] < -1e-6, -o[:, 1] / np.where(d[:, 1] < -1e-6, d[:, 1], -1), np.inf)
    return np.where(t > 1e-4, t, np.inf)

def crown_info(p, bi):
    """For points p on berry bi: crown mask (0..1), hole mask, perturbed normal."""
    c, r, ax, spin = BERRIES[bi]
    n = norm(p - c)
    cosT = np.clip(n @ ax, -1, 1); th = np.arccos(cosT)
    # local frame around the crown axis
    e1 = norm(np.cross(ax, [0.0, 0.0, 1.0])); e2 = np.cross(ax, e1)
    phi = np.arctan2(n @ e2, n @ e1) + spin
    star = 0.25 * (1 + 0.16 * np.cos(5 * phi) + 0.06 * np.sin(11 * phi + 1.3) + 0.04 * np.sin(19 * phi + .4) + 0.025 * np.sin(31 * phi))
    inside = np.clip((star - th) / 0.025, 0, 1)                 # crown area, slightly soft edge
    rim = np.exp(-((th - star) / 0.03) ** 2)                     # raised lip around the crown
    hole = np.clip((0.1 - th) / 0.03, 0, 1)
    # bowl: tilt the normal inward (toward the axis) inside the crown, outward on the rim
    tang = norm(n - cosT[:, None] * ax + 1e-9)
    bowl = (inside * np.sin(np.clip(th / star, 0, 1) * np.pi * 0.5 + np.pi * 0.5) * 1.3 - rim * 0.6)[:, None]
    npert = norm(n + bowl * tang * 1.0)
    return inside, hole, rim, npert

def fresnel(cosi):
    r0 = ((1 - IOR) / (1 + IOR)) ** 2
    return r0 + (1 - r0) * (1 - cosi) ** 5

def refract(d, n, eta):
    cosi = -np.einsum('ij,ij->i', d, n)
    k = 1 - eta * eta * (1 - cosi * cosi)
    tir = k < 0
    tdir = eta * d + (eta * cosi - np.sqrt(np.where(tir, 0, k)))[:, None] * n
    return norm(tdir), tir

def first_hit(o, d, skip=None):
    tg = hit_ground(o, d)
    best = tg.copy(); obj = np.full(len(d), -1)          # -1 ground, -2 env
    obj[np.isinf(best)] = -2
    for i, (c, r, _, _) in enumerate(BERRIES):
        tt = hit_sphere(o, d, c, r)
        m = tt < best
        best[m] = tt[m]; obj[m] = i
    return best, obj

# ---------------- ground shading: soft blue shadows + caustics ----------------
LS = [LIGHT_C + LIGHT_U * a + LIGHT_V * b for a in np.linspace(-1, 1, 4) for b in np.linspace(-1, 1, 4)]

def shade_ground(p):
    col = np.zeros((len(p), 3)); n = np.array([0, 1.0, 0])
    for L in LS:
        ld = norm(L - p)
        lam = np.clip(ld[:, 1], 0, 1)[:, None]
        trans = np.ones((len(p), 3)); caus = np.zeros(len(p))
        for i, (c, r, _, _) in enumerate(BERRIES):
            tt = hit_sphere(p, ld, c, r)
            blk = np.isfinite(tt)
            # closest approach of the light ray to the centre: thick path = more tint, centre = focused light
            oc = c - p
            proj = np.einsum('ij,ij->i', oc, ld)
            dist = np.linalg.norm(oc - proj[:, None] * ld, axis=1) / r
            path = 2 * r * np.sqrt(np.clip(1 - dist ** 2, 0, 1))
            tint = np.exp(-SIGMA[None, :] * path[:, None] * 2.4) * (1 - 0.6 * dist[:, None] ** 4) * 0.85
            trans = np.where(blk[:, None], trans * tint, trans)
            caus = caus + np.where(blk, np.exp(-(dist / 0.34) ** 2) * 5.0, 0)
        col += lam * (trans * (1 + caus[:, None] * np.array([0.75, 0.92, 1.0])))
    col /= len(LS)
    # ambient occlusion under each berry
    ao = np.ones(len(p))
    for c, r, _, _ in BERRIES:
        dxz = np.hypot(p[:, 0] - c[0], p[:, 2] - c[2]) / r
        ao *= 1 - 0.55 * np.exp(-(dxz / 0.55) ** 2)
    return GROUND * (0.42 + 0.78 * col) * ao[:, None]

# ---------------- main trace ----------------
def trace(o, d):
    out = np.zeros((len(d), 3))
    thr = np.ones((len(d), 3))
    alive = np.ones(len(d), bool)
    inside = np.full(len(d), -1)                         # berry index we're inside, or -1
    for depth in range(7):
        idx = np.nonzero(alive)[0]
        if len(idx) == 0:
            break
        oo, dd = o[idx], d[idx]
        ins = inside[idx]
        tb, obj = first_hit(oo, dd)
        # rays inside a berry: next hit is that berry's exit
        m_in = ins >= 0
        if m_in.any():
            for i, (c, r, _, _) in enumerate(BERRIES):
                mm = m_in & (ins == i)
                if mm.any():
                    tt = hit_sphere(oo[mm], dd[mm], c, r)
                    tb[mm] = tt; obj[mm] = i
                    # bubbles: bright speck where the inner ray passes a bubble
                    for (bj, bc, br) in BUBBLES:
                        if bj != i:
                            continue
                        ocb = bc - oo[mm]
                        pr = np.einsum('ij,ij->i', ocb, dd[mm])
                        dist = np.linalg.norm(ocb - pr[:, None] * dd[mm], axis=1)
                        ring = np.exp(-((dist - br) / (br * 0.35)) ** 2) * (pr > 0) * (pr < tt)
                        sel = idx[mm]
                        out[sel] += thr[sel] * ring[:, None] * 0.55
        p = oo + dd * np.where(np.isfinite(tb), tb, 0)[:, None]

        # environment
        e = obj == -2
        if e.any():
            out[idx[e]] += thr[idx[e]] * env(dd[e])
            alive[idx[e]] = False
        # ground
        g = obj == -1
        if g.any():
            out[idx[g]] += thr[idx[g]] * shade_ground(p[g])
            alive[idx[g]] = False

        # glass
        for i, (c, r, _, _) in enumerate(BERRIES):
            mm = obj == i
            if not mm.any():
                continue
            sel = idx[mm]; P = p[mm]; Dd = dd[mm]
            was_in = ins[mm] >= 0
            nrm_geo = norm(P - c)
            # hand-made glass: gentle surface waviness bends the refraction
            q = (P - c) / r * 3.1 + i * 1.7
            wob = np.stack([np.sin(q[:, 1] * 2.3 + q[:, 2] * 1.1), np.sin(q[:, 2] * 2.1 + q[:, 0] * 1.4), np.sin(q[:, 0] * 2.6 + q[:, 1] * 0.9)], 1)
            wob += 0.5 * np.stack([np.sin(q[:, 2] * 5.3 + 1), np.sin(q[:, 0] * 4.7 + 2), np.sin(q[:, 1] * 5.9 + 3)], 1)
            nrm_geo = norm(nrm_geo + wob * 0.045)
            inside_c, hole, rim, npert = crown_info(P, i)
            nrm = norm(npert + (nrm_geo - norm(P - c)))
            # absorption along the path just travelled inside the glass
            if was_in.any():
                seg = tb[mm][was_in]
                thr[sel[was_in]] *= np.exp(-SIGMA[None, :] * seg[:, None])
            # entering from outside
            ent = ~was_in
            if ent.any():
                s2 = sel[ent]; n2 = nrm[ent]; d2 = Dd[ent]
                cosi = np.clip(-np.einsum('ij,ij->i', d2, n2), 0, 1)
                F = fresnel(cosi)[:, None] * (1 - 0.75 * inside_c[ent][:, None] * (1 - rim[ent][:, None]))
                rdir = norm(d2 + 2 * cosi[:, None] * n2)
                # reflection: environment or ground (cheap single bounce)
                tg = hit_ground(P[ent], rdir)
                refl = env(rdir)
                gm = np.isfinite(tg)
                if gm.any():
                    refl[gm] = shade_ground(P[ent][gm] + rdir[gm] * tg[gm][:, None]) * 0.9
                out[s2] += thr[s2] * F * refl
                # the crown: dark navy pigment, matte-ish, lit from the light
                ic = inside_c[ent][:, None]; hl = hole[ent][:, None]; rm = rim[ent][:, None]
                lamb = np.clip(n2 @ LIGHT_DIR, 0, 1)[:, None]
                depth_t = np.clip(1 - np.arccos(np.clip(n2 @ BERRIES[i][2], -1, 1))[:, None] / 0.25, 0, 1)
                crown_col = np.array([0.09, 0.15, 0.32]) * (0.3 + 1.0 * lamb) * (1 - 0.82 * depth_t) * (1 - 0.95 * hl)
                out[s2] += thr[s2] * (1 - F) * ic * crown_col
                out[s2] += thr[s2] * rm * np.array([0.6, 0.75, 0.9]) * 0.18
                thr[s2] *= (1 - F) * np.clip(1 - ic * (0.96 + 0.04 * hl), 0, 1)
                tdir, tir = refract(d2, n2, 1 / IOR)
                o[s2] = P[ent] - n2 * 1e-3
                d[s2] = tdir
                inside[s2] = i
            # exiting from inside
            if was_in.any():
                s3 = sel[was_in]; n3 = -nrm_geo[was_in]; d3 = Dd[was_in]
                tdir, tir = refract(d3, n3, IOR)
                cosi = np.clip(-np.einsum('ij,ij->i', d3, n3), 0, 1)
                F = np.where(tir, 1.0, fresnel(cosi))
                # follow the stronger branch, scale throughput
                go_out = ~tir & (F < 0.5)
                rdir = norm(d3 + 2 * cosi[:, None] * n3)
                newd = np.where(go_out[:, None], tdir, rdir)
                thr[s3] *= np.where(go_out, 1 - F, np.maximum(F, 0.6))[:, None]
                o[s3] = P[was_in] + np.where(go_out[:, None], -n3, n3) * 1e-3
                d[s3] = newd
                inside[s3] = np.where(go_out, -1, i)
    # rays still alive: fade to environment
    rest = np.nonzero(alive)[0]
    if len(rest):
        out[rest] += thr[rest] * env(d[rest])
    return out

CH = 60000
img = np.zeros((len(D), 3))
for s in range(0, len(D), CH):
    img[s:s + CH] = trace(O[s:s + CH].copy(), D[s:s + CH].copy())
    print(f'{min(100, (s + CH) * 100 // len(D))}%', end=' ', flush=True)
img = img.reshape(M, M, 3)
# tone map + gentle cool grade
img = img / (1 + img * 0.35)
img = np.clip(img * 1.12, 0, 1) ** (1 / 1.05)
im = Image.fromarray((img * 255).astype(np.uint8)).resize((N, N), Image.LANCZOS)
im.save(OUT)
print('\nsaved', OUT)
