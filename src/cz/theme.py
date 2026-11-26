import os

import kivy
from kivy.utils import get_color_from_hex as hexc

MONO = os.path.join(os.path.dirname(kivy.__file__), "data", "fonts", "RobotoMono-Regular.ttf")


class C:
    ink = hexc("#000000")
    chalk = hexc("#F5F5F5")
    rec = hexc("#E5194B")
    rec_off = hexc("#3D0712")
    graphite = hexc("#1A1A1A")
    graphite2 = hexc("#2A2A2A")
    muted = hexc("#8A8A8A")
    line = hexc("#2E2E2E")
    field = hexc("#121212")


ICONS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icons")


def icon(name: str) -> str:
    return os.path.join(ICONS, name + ".png")
