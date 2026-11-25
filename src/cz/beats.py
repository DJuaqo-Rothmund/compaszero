"""Bases disponibles: las incluidas en la app y las que importa el usuario."""
import os
import shutil

AUDIO_EXTS = (".wav", ".ogg", ".mp3", ".m4a", ".aac", ".flac")
BUNDLED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "beats")


def user_dir(data_dir: str) -> str:
    d = os.path.join(data_dir, "beats")
    os.makedirs(d, exist_ok=True)
    return d


def list_beats(data_dir: str) -> list[tuple[str, str]]:
    """[(nombre, ruta)] — primero las incluidas, luego las importadas."""
    out = []
    for folder in (BUNDLED, user_dir(data_dir)):
        for f in sorted(os.listdir(folder)):
            if f.lower().endswith(AUDIO_EXTS):
                out.append((os.path.splitext(f)[0], os.path.join(folder, f)))
    return out


def import_beat(data_dir: str, path: str) -> str:
    dest = os.path.join(user_dir(data_dir), os.path.basename(path))
    shutil.copyfile(path, dest)
    return dest
