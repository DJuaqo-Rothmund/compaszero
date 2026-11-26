"""Genera la intro de CompásZero como un grafiti pintado de verdad.

En vez de calcar el contorno de cada letra, el spray recorre el ESQUELETO (centro del trazo)
a velocidad constante, como una mano; cada píxel de la letra aparece cuando la boquilla pasa
cerca. Hay tres estilos:

  trazo  – trazo a mano limpio, bordes suaves y neblina leve en la boquilla
  spray  – pintura en aerosol: capa que se va cargando, salpicaduras alrededor y chorreones
  tag    – tag rápido y enérgico, con aceleración en cada trazo y destello final del REC

Uso: python tools/graffiti_intro.py <carpeta_mascaras> <estilo> <salida.gif|.webp> [escala]
Las máscaras (PNG blanco sobre negro, 972x908) se obtienen de los trazados del logo.
"""
import sys

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.morphology import skeletonize

FPS = 25
REC = np.array([229, 25, 75], float)
REC_OFF = np.array([61, 7, 18], float)
RNG = np.random.default_rng(11)


def load(folder, name):
    return np.asarray(Image.open(f"{folder}/{name}.png").convert("L")).astype(float) / 255


def order_skeleton(mask):
    """Devuelve un mapa 'momento de aparición' (0..1) para cada píxel de la máscara."""
    m = mask > .5
    skel = skeletonize(m)
    ys, xs = np.nonzero(skel)
    if len(ys) == 0:
        return np.where(m, 0.0, np.inf), [], 1
    idx = {(y, x): i for i, (y, x) in enumerate(zip(ys, xs))}
    nbrs = [[] for _ in ys]
    for i, (y, x) in enumerate(zip(ys, xs)):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                j = idx.get((y + dy, x + dx))
                if j is not None and j != i:
                    nbrs[i].append(j)
    # componentes, de izquierda a derecha
    lab, n = ndimage.label(skel, structure=np.ones((3, 3)))
    comps = sorted(range(1, n + 1), key=lambda c: xs[lab[ys, xs] == c].min())
    order = np.full(len(ys), -1)
    path = []
    for c in comps:
        members = [i for i in range(len(ys)) if lab[ys[i], xs[i]] == c]
        ends = [i for i in members if len(nbrs[i]) == 1] or members
        start = min(ends, key=lambda i: (xs[i], ys[i]))
        stack = [start]
        while stack:  # recorrido en profundidad: sigue el trazo y vuelve en las ramas
            i = stack.pop()
            if order[i] >= 0:
                continue
            order[i] = len(path)
            path.append((ys[i], xs[i]))
            nxt = sorted((j for j in nbrs[i] if order[j] < 0), key=lambda j: -abs(xs[j] - xs[i]) - abs(ys[j] - ys[i]))
            stack.extend(nxt)
    total = max(len(path) - 1, 1)
    tmap = np.full(m.shape, np.inf)
    tmap[ys, xs] = order / total
    # cada píxel de la letra toma el momento del punto del esqueleto más cercano
    _, (iy, ix) = ndimage.distance_transform_edt(~skel, return_indices=True)
    dist = ndimage.distance_transform_edt(~skel)
    near = tmap[iy, ix]
    t = np.where(m, near + dist / (total * 3.0), np.inf)
    return t, path, len(path)


def soft_dot(shape, cy, cx, r, strength=1.0):
    y, x = np.ogrid[:shape[0], :shape[1]]
    return strength * np.exp(-((y - cy) ** 2 + (x - cx) ** 2) / (2 * r * r))


class Stroke:
    def __init__(self, mask, start, speed_px, style):
        self.mask = mask
        self.t, self.path, n = order_skeleton(mask)
        self.start = start
        self.dur = max(n / speed_px, .18)
        self.style = style
        self.drip = None
        if style == "spray" and RNG.random() < .55 and n > 0:
            ys, xs = np.nonzero(mask > .5)
            k = np.argmax(ys + RNG.random(len(ys)) * 20)  # un punto bajo de la letra
            self.drip = (ys[k], xs[k], RNG.uniform(14, 34))

    def progress(self, now):
        u = (now - self.start) / self.dur
        if self.style == "tag":  # acelera en medio del trazo
            u = np.clip(u, 0, 1)
            u = u * u * (3 - 2 * u)
        return u

    def alpha(self, now):
        u = self.progress(now)
        if u <= 0:
            return None, None
        soft = {"trazo": .035, "spray": .09, "tag": .02}[self.style]
        a = np.clip((u - self.t) / soft, 0, 1)
        if self.style == "spray":  # la pintura se va cargando: primero transparente, luego sólida
            a = np.clip(a * .55 + np.clip((u - self.t - .12) / .25, 0, 1) * .45, 0, 1)
        nozzle = None
        if 0 < u < 1 and self.path:
            nozzle = self.path[min(int(u * (len(self.path) - 1)), len(self.path) - 1)]
        return a * (self.mask > .5), nozzle


def render(folder, style, out, scale=1.0):
    letters = [load(folder, f"letter{i}") for i in range(7)]
    lines = [load(folder, "line0"), load(folder, "line1")]
    symbol, tagline, dots = load(folder, "symbol"), load(folder, "tagline"), load(folder, "dots")
    H, W = symbol.shape
    speed = {"trazo": 520, "spray": 430, "tag": 900}[style]  # píxeles de esqueleto por segundo
    t = .75
    strokes = []
    for m in letters:
        s = Stroke(m, t, speed, style)
        strokes.append(s)
        t += s.dur * (.92 if style != "tag" else .7)
    t_dots = t
    for m in lines:
        s = Stroke(m, t, speed * 2.2, style)
        strokes.append(s)
        t += s.dur * .8
    t_tag = t + .25
    end = t_tag + 1.4
    over = np.zeros((H, W))  # salpicadura acumulada alrededor de los trazos
    frames = []
    n_frames = int(end * FPS)
    for f in range(n_frames):
        now = f / FPS
        canvas = np.zeros((H, W, 3))
        # símbolo: aparece primero
        sa = np.clip(now / .6, 0, 1)
        canvas += symbol[..., None] * 245 * sa
        # punto REC que late (centro del símbolo: 243.22, 153.21 en el SVG, a escala 2x)
        cy, cx = 153.21 * H / 453.66, 243.22 * W / 486.44
        pulse = .5 + .5 * np.cos(now * 2 * np.pi / 1.6)
        col = REC_OFF + (REC - REC_OFF) * pulse
        yy, xx = np.ogrid[:H, :W]
        disc = ((yy - cy) ** 2 + (xx - cx) ** 2) <= (11.89 * H / 453.66) ** 2
        canvas[disc] = col * sa
        glow = soft_dot((H, W), cy, cx, 34, .5 * pulse * sa)
        canvas += glow[..., None] * REC
        paint = np.zeros((H, W))
        mist = np.zeros((H, W))
        for s in strokes:
            a, nozzle = s.alpha(now)
            if a is None:
                continue
            paint = np.maximum(paint, a)
            if nozzle is not None:
                ny, nx = nozzle
                r = {"trazo": 10, "spray": 20, "tag": 7}[style]
                mist += soft_dot((H, W), ny, nx, r, {"trazo": .25, "spray": .45, "tag": .2}[style])
                if style in ("spray", "trazo"):  # gotitas sueltas que quedan pegadas
                    k = 18 if style == "spray" else 5
                    py = (ny + RNG.normal(0, r * 1.3, k)).astype(int)
                    px = (nx + RNG.normal(0, r * 1.3, k)).astype(int)
                    ok = (py >= 0) & (py < H) & (px >= 0) & (px < W)
                    over[py[ok], px[ok]] = np.maximum(over[py[ok], px[ok]], RNG.uniform(.25, .7, ok.sum()))
            if s.drip and s.progress(now) > 1:  # chorreón que baja despacio
                dy, dx, ln = s.drip
                grow = np.clip((s.progress(now) - 1) * s.dur / 1.2, 0, 1) * ln
                y0 = int(dy)
                paint[y0:int(dy + grow), int(dx) - 2:int(dx) + 2] = 1
                if grow > 3:
                    paint = np.maximum(paint, soft_dot((H, W), dy + grow, dx, 3.2) > .5)
        # comillas y puntos: soplido de spray
        if now >= t_dots:
            k = np.clip((now - t_dots) / .35, 0, 1)
            paint = np.maximum(paint, dots * k)
        canvas += paint[..., None] * 245 * (1 - mist[..., None] * .2)
        canvas += np.clip(mist, 0, 1)[..., None] * 200
        if style != "tag":
            canvas += (over * (1 - paint))[..., None] * 160
        # lema
        if now >= t_tag:
            k = np.clip((now - t_tag) / .5, 0, 1)
            shift = int((1 - k) * 10)
            tl = np.roll(tagline, shift, axis=0)
            canvas += tl[..., None] * 245 * k
        if style == "tag" and t_tag - .2 < now < t_tag + .1:  # destello del REC al terminar
            canvas += soft_dot((H, W), cy, cx, 90, .6)[..., None] * REC
        img = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))
        if scale != 1:
            img = img.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
        frames.append(img)
    frames += [frames[-1]] * int(.8 * FPS)
    if out.endswith(".gif"):
        q = [fr.quantize(96, dither=Image.Dither.NONE) for fr in frames]
        q[0].save(out, save_all=True, append_images=q[1:], duration=1000 // FPS, loop=0, optimize=True)
    else:
        frames[0].save(out, save_all=True, append_images=frames[1:], duration=1000 // FPS, loop=1, quality=82, method=4)
    print(out, len(frames), "cuadros")


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]) if len(sys.argv) > 4 else 1.0)
