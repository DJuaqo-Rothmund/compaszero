import os

import kivy
from kivy.utils import get_color_from_hex as hexc

MONO = os.path.join(os.path.dirname(kivy.__file__), "data", "fonts", "RobotoMono-Regular.ttf")


THEMES = {
    # nombre: (fondo, superficie, superficie 2, línea, campo, texto, texto suave, claro?)
    "Negro estudio": ("#000000", "#1A1A1A", "#2A2A2A", "#2E2E2E", "#121212", "#F5F5F5", "#8A8A8A", False),
    "Grafito":       ("#121212", "#1E1E1E", "#2C2C2C", "#353535", "#181818", "#F2F2F2", "#9A9A9A", False),
    "Noche azul":    ("#0A0E18", "#141A28", "#1F2738", "#28324A", "#0F1420", "#EEF1F7", "#8C95A8", False),
    "Asfalto":       ("#13110F", "#211C19", "#2D2723", "#3A322C", "#1A1613", "#F4EFEA", "#9C9087", False),
    "Papel":         ("#F3EFE6", "#FFFDF8", "#EAE4D6", "#DCD4C3", "#FFFFFF", "#141414", "#6E6A62", True),
    "Concreto":      ("#E9E9E9", "#FFFFFF", "#DCDCDC", "#CFCFCF", "#FFFFFF", "#111111", "#6B6B6B", True),
}


ACCENTS = {
    # nombre: (color, texto encima)
    "Rojo REC": ("#E5194B", "#FFFFFF"),
    "Dorado": ("#F2B705", "#111111"),
    "Lima": ("#9BE15D", "#111111"),
    "Cian": ("#2EC4F1", "#111111"),
    "Naranja spray": ("#FF7A1A", "#111111"),
    "Violeta": ("#8E6CFF", "#FFFFFF"),
    "Monocromo": (None, None),  # blanco en temas oscuros, negro en temas claros
}

TEXTURES = ["Liso", "Grano", "Papel", "Concreto", "Cuaderno", "Ladrillo", "Spray"]


class C:
    rec = hexc("#E5194B")       # el rojo REC no cambia en ningún tema
    rec_off = hexc("#3D0712")
    on_rec = hexc("#FFFFFF")    # texto sobre botones rojos
    light = False


def apply_theme(name: str):
    ink, g1, g2, line, field, chalk, muted, light = THEMES.get(name, THEMES["Negro estudio"])
    C.ink, C.graphite, C.graphite2, C.line, C.field = map(hexc, (ink, g1, g2, line, field))
    C.chalk, C.muted, C.light = hexc(chalk), hexc(muted), light
    C.rec_off = hexc("#F2B3C3") if light else hexc("#3D0712")
    C.name = name if name in THEMES else "Negro estudio"


def apply_accent(name: str):
    color, on = ACCENTS.get(name, ACCENTS["Rojo REC"])
    if color is None:  # monocromo
        color, on = ("#141414", "#FFFFFF") if C.light else ("#F5F5F5", "#111111")
    C.accent, C.on_accent = hexc(color), hexc(on)
    C.accent_hex = color.lstrip("#")
    C.accent_dark_text = on != "#FFFFFF"
    C.accent_name = name if name in ACCENTS else "Rojo REC"


def apply_texture(name: str):
    C.texture = name if name in TEXTURES else "Liso"


apply_theme(os.getenv("CZ_THEME", "Negro estudio"))
apply_accent(os.getenv("CZ_ACCENT", "Rojo REC"))
apply_texture(os.getenv("CZ_TEXTURE", "Liso"))


ICONS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icons")


def icon(name: str) -> str:
    """Ícono según el tema: blanco en temas oscuros, negro en temas claros (el rojo siempre igual)."""
    if C.light:
        base, off = (name[:-4], True) if name.endswith("_off") else (name, False)
        lname = base + ("_l_off" if off else "_l")
        if os.path.exists(os.path.join(ICONS, lname + ".png")):
            name = lname
    return os.path.join(ICONS, name + ".png")


def icon_raw(name: str) -> str:
    """Ícono para dibujar sobre un botón del color de acento (blanco u oscuro según el contraste)."""
    if getattr(C, "accent_dark_text", False) and os.path.exists(os.path.join(ICONS, name + "_l.png")):
        return os.path.join(ICONS, name + "_l.png")
    return os.path.join(ICONS, name + ".png")


def texture_path() -> str | None:
    if C.texture == "Liso":
        return None
    return os.path.join(os.path.dirname(ICONS), "textures", C.texture.lower() + ".png")
