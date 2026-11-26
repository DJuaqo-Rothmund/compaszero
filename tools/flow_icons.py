"""Convierte los íconos generados con Google Flow (fondo negro) en PNG transparentes,
versión activa (blanco + rojo) e inactiva (gris + rojo oscuro) para la app.
Uso: python tools/flow_icons.py"""
import pathlib
import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "docs/brand/icons/flow", ROOT / "src/assets/icons"
VARIANTS = {"": ((245, 245, 245), (229, 25, 75)), "_off": ((138, 138, 138), (122, 18, 41))}


def convert(path, name, size=144, inset=0):
    img = Image.open(path).convert("RGB")
    if inset:  # quitar un marco
        img = img.crop((inset, inset, img.width - inset, img.height - inset))
    a = np.asarray(img).astype(float) / 255
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    white = np.clip((np.minimum(np.minimum(r, g), b) - .12) / .7, 0, 1)
    red = np.clip((r - np.maximum(g, b) - .15) / .5, 0, 1)
    alpha = np.maximum(white, red)
    ys, xs = np.nonzero(alpha > .2)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    side = int(max(y1 - y0, x1 - x0) * 1.08)
    cy, cx = (y0 + y1) // 2, (x0 + x1) // 2
    box = (cx - side // 2, cy - side // 2, cx - side // 2 + side, cy - side // 2 + side)
    is_red = red > white
    for suffix, (wc, rc) in VARIANTS.items():
        rgb = np.where(is_red[..., None], np.array(rc), np.array(wc))
        img = np.dstack([rgb, alpha * 255]).astype(np.uint8)
        im = Image.fromarray(img, "RGBA").crop(box).resize((size, size), Image.LANCZOS)
        im.save(OUT / f"{name}{suffix}.png")


NAMES = ["ideas", "ideas_cuaderno", "descargar", "canciones", "gear", "back", "voz", "plus", "stop", "play",
         "enviar", "importar", "mas", "freestyle", "descubrir"]
for n in NAMES:
    convert(SRC / f"{n}.jpg", n)
convert(SRC / "buscar.jpg", "buscar", inset=80)

# ícono de la app: fondo negro completo (se quita el borde blanco del círculo)
im = Image.open(SRC / "app.jpg").convert("RGB")
w, h = im.size
mask = Image.new("L", im.size, 0)
from PIL import ImageDraw
ImageDraw.Draw(mask).ellipse((40, 40, w - 40, h - 40), fill=255)
black = Image.new("RGB", im.size, (0, 0, 0))
Image.composite(im, black, mask).resize((1024, 1024), Image.LANCZOS).save(ROOT / "src/assets/icon.png")
print("ok")
