"""Texturas de fondo (mosaicos de 256 px que se repiten sin costuras).
Son blancas con transparencia: la app las pinta claras sobre temas oscuros y oscuras sobre temas claros.
Uso: python tools/make_textures.py"""
import pathlib
import numpy as np
from PIL import Image, ImageFilter

OUT = pathlib.Path(__file__).resolve().parents[1] / "src/assets/textures"
N = 256
rng = np.random.default_rng(3)


def smooth_noise(scale):
    """Ruido suave y repetible (se envuelve en los bordes)."""
    g = rng.random((N // scale, N // scale))
    img = Image.fromarray((g * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC)
    a = np.asarray(img).astype(float) / 255
    return (a + np.roll(a, N // 2, 0) + np.roll(a, N // 2, 1) + np.roll(np.roll(a, N // 2, 0), N // 2, 1)) / 4


def save(name, alpha):
    alpha = np.clip(alpha, 0, 1)
    rgba = np.dstack([np.full((N, N), 255)] * 3 + [alpha * 255]).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(OUT / f"{name}.png")


grain = rng.random((N, N))
save("grano", (grain > .5) * grain * .35)

fib = smooth_noise(4) * .5 + smooth_noise(16) * .5
streak = np.asarray(Image.fromarray((rng.random((N, N)) * 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(0))).astype(float) / 255
save("papel", (fib - .45).clip(0) * .9 + (streak > .985) * .25)

blot = smooth_noise(8) * .6 + smooth_noise(32) * .4
pits = (rng.random((N, N)) > .992) * .7
save("concreto", (blot - .4).clip(0) * 1.0 + pits + grain * .06)

lines = np.zeros((N, N))
for y in range(0, N, 32):
    lines[y:y + 1, :] = .35
lines[:, 40:41] = np.maximum(lines[:, 40:41], .0)  # (el margen se dibuja aparte para no repetirse)
save("cuaderno", lines + grain * .04)

brick = np.zeros((N, N))
h, w = 32, 64
for row in range(N // h):
    y = row * h
    brick[y:y + 2, :] = .45
    off = 0 if row % 2 == 0 else w // 2
    for x in range(off, N + w, w):
        brick[y:y + h, x % N:(x % N) + 2] = .45
save("ladrillo", brick * (.6 + smooth_noise(8) * .6) + grain * .05)

spray = np.zeros((N, N))
for _ in range(9):
    cx, cy, r = rng.integers(0, N, 2).tolist() + [int(rng.integers(20, 60))]
    yy, xx = np.mgrid[0:N, 0:N]
    dx, dy = np.minimum(abs(xx - cx), N - abs(xx - cx)), np.minimum(abs(yy - cy), N - abs(yy - cy))
    d = np.sqrt(dx ** 2 + dy ** 2) / r
    spray += (rng.random((N, N)) < np.exp(-d ** 2) * .25) * .8
save("spray", spray + grain * .03)
print(sorted(p.name for p in OUT.iterdir()))
