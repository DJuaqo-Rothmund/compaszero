"""Apariencia de CompásZero: temas, color de acento, texturas de fondo, fuentes e íconos.

Todo en colores hex para Flet. El rojo REC (#E5194B) de los íconos y del botón de grabar
no cambia nunca; el "acento" es el color de botones y destacados que elige el usuario.
"""
import os

REC = "#E5194B"

THEMES = {
    # nombre: fondo, superficie, superficie 2, línea, texto, texto suave, claro?
    "Negro estudio": ("#000000", "#151515", "#222222", "#2A2A2A", "#F5F5F5", "#8C8C8C", False),
    "Grafito":       ("#121212", "#1C1C1E", "#2A2A2D", "#333336", "#F2F2F2", "#9A9A9A", False),
    "Noche azul":    ("#0A0E18", "#131A29", "#1E2738", "#28324A", "#EEF1F7", "#8C95A8", False),
    "Asfalto":       ("#14110F", "#201B18", "#2C2622", "#3A322C", "#F4EFEA", "#9C9087", False),
    "Papel":         ("#F3EEE3", "#FFFCF6", "#EDE6D8", "#DDD4C2", "#191919", "#6E685E", True),
    "Concreto":      ("#E7E7E7", "#FFFFFF", "#DDDDDD", "#CFCFCF", "#121212", "#6B6B6B", True),
}

ACCENTS = {
    # nombre: (color, texto encima)
    "Rojo REC": ("#E5194B", "#FFFFFF"),
    "Dorado": ("#F2B705", "#141414"),
    "Lima": ("#9BE15D", "#141414"),
    "Cian": ("#2EC4F1", "#141414"),
    "Naranja spray": ("#FF7A1A", "#141414"),
    "Violeta": ("#8E6CFF", "#FFFFFF"),
    "Monocromo": (None, None),
}

TEXTURES = ["Liso", "Grano", "Papel", "Concreto", "Cuaderno", "Ladrillo", "Spray"]

FONTS = {
    "Poppins": "fonts/Poppins-Regular.ttf",
    "PoppinsMedium": "fonts/Poppins-Medium.ttf",
    "PoppinsSemi": "fonts/Poppins-SemiBold.ttf",
    "PoppinsBold": "fonts/Poppins-Bold.ttf",
    "Mono": "fonts/JetBrainsMono.ttf",
    "Marker": "fonts/PermanentMarker-Regular.ttf",
}

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


class Look:
    """Paleta activa (se recalcula al cambiar tema, acento o fondo)."""

    def __init__(self, theme="Negro estudio", accent="Rojo REC", texture="Grano"):
        self.set(theme, accent, texture)

    def set(self, theme=None, accent=None, texture=None):
        self.theme = theme if theme in THEMES else getattr(self, "theme", "Negro estudio")
        self.accent_name = accent if accent in ACCENTS else getattr(self, "accent_name", "Rojo REC")
        self.texture = texture if texture in TEXTURES else getattr(self, "texture", "Grano")
        (self.bg, self.surface, self.surface2, self.line,
         self.text, self.muted, self.light) = THEMES[self.theme]
        acc, on = ACCENTS[self.accent_name]
        if acc is None:
            acc, on = ("#141414", "#FFFFFF") if self.light else ("#F5F5F5", "#141414")
        self.accent, self.on_accent = acc, on
        self.accent_dark_text = on != "#FFFFFF"

    # --- recursos ---
    def icon(self, name: str, active: bool = True) -> str:
        """Ruta (relativa a assets) del ícono: blanco en temas oscuros, negro en claros."""
        if self.light:
            v = f"{name}_l" if active else f"{name}_l_off"
        else:
            v = name if active else f"{name}_off"
        if not os.path.exists(os.path.join(ASSETS, "icons", v + ".png")):
            v = name
        return f"icons/{v}.png"

    def icon_on_accent(self, name: str) -> str:
        v = f"{name}_l" if self.accent_dark_text else name
        if not os.path.exists(os.path.join(ASSETS, "icons", v + ".png")):
            v = name
        return f"icons/{v}.png"

    def wordmark(self) -> str:
        return "wordmark_l.png" if self.light else "wordmark.png"

    def texture_src(self) -> str | None:
        return None if self.texture == "Liso" else f"textures/{self.texture.lower()}.png"
