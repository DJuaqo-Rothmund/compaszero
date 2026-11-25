"""Une los cuadros renderizados (tools/render_intro.js) en:
- docs/brand/intro.gif  (vista previa, en bucle)
- src/assets/intro.zip  (cuadros JPG que la app Kivy reproduce una vez)
Uso: python tools/frames_to_media.py <cuadros_1x> <cuadros_2x>"""
import glob, io, sys, zipfile
from PIL import Image, ImageDraw


def load(d):
    for f in sorted(glob.glob(f"{d}/*.png")):
        im = Image.open(f).convert("RGB")
        ImageDraw.Draw(im).rectangle([0, 0, im.width - 1, im.height - 1], outline="black", width=6)  # borde limpio
        yield im


g = [f.quantize(64, dither=Image.Dither.NONE) for f in load(sys.argv[1])]
g[0].save("docs/brand/intro.gif", save_all=True, append_images=g[1:], duration=40, loop=0, optimize=True)
with zipfile.ZipFile("src/assets/intro.zip", "w", zipfile.ZIP_STORED) as z:
    for i, im in enumerate(load(sys.argv[2])):
        b = io.BytesIO()
        im.crop((180, 100, 792, 820)).save(b, "JPEG", quality=82)  # solo el área del logo: carga más rápido
        z.writestr(f"{i:03d}.jpg", b.getvalue())
