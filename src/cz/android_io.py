"""Compartir texto y guardar/abrir archivos con el selector de Android (permite Google Drive).

En el PC: compartir copia al portapapeles y los archivos van a ~/CompasZero/."""
import os

from kivy.clock import Clock
from kivy.utils import platform

DESKTOP_DIR = os.path.expanduser("~/CompasZero")
_CREATE, _OPEN = 4101, 4102
_pending = {}

if platform == "android":
    from android import activity
    from jnius import autoclass, cast

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    Intent = autoclass("android.content.Intent")
    String = autoclass("java.lang.String")

    def _on_result(request, result, data):
        cb = _pending.pop(request, None)
        if cb is None:
            return
        uri = data.getData() if (data is not None and result == -1) else None
        cb(uri)

    activity.bind(on_activity_result=_on_result)


def share_text(title: str, text: str) -> str:
    if platform != "android":
        from kivy.core.clipboard import Clipboard
        Clipboard.copy(text)
        return "Copiado al portapapeles"
    intent = Intent(Intent.ACTION_SEND)
    intent.setType("text/plain")
    intent.putExtra(Intent.EXTRA_SUBJECT, String(title))
    intent.putExtra(Intent.EXTRA_TEXT, String(text))
    chooser = Intent.createChooser(intent, String("Compartir letra"))
    PythonActivity.mActivity.startActivity(chooser)
    return ""


def save_document(filename: str, content: str, mime: str, done):
    """Pide dónde guardar (Drive, Descargas...) y escribe el texto. done(mensaje)."""
    if platform != "android":
        os.makedirs(DESKTOP_DIR, exist_ok=True)
        path = os.path.join(DESKTOP_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return done(f"Guardado en {path}")

    def write(uri):
        if uri is None:
            return Clock.schedule_once(lambda dt: done("Cancelado"))
        resolver = PythonActivity.mActivity.getContentResolver()
        out = resolver.openOutputStream(uri)
        out.write(content.encode("utf-8"))
        out.close()
        Clock.schedule_once(lambda dt: done("Copia guardada"))

    intent = Intent(Intent.ACTION_CREATE_DOCUMENT)
    intent.addCategory(Intent.CATEGORY_OPENABLE)
    intent.setType(mime)
    intent.putExtra(Intent.EXTRA_TITLE, String(filename))
    _pending[_CREATE] = write
    PythonActivity.mActivity.startActivityForResult(intent, _CREATE)


def open_document(mime: str, done):
    """Pide un archivo y devuelve su texto: done(texto o None)."""
    if platform != "android":
        files = sorted(f for f in os.listdir(DESKTOP_DIR) if f.endswith(".json")) if os.path.isdir(DESKTOP_DIR) else []
        if not files:
            return done(None)
        with open(os.path.join(DESKTOP_DIR, files[-1]), encoding="utf-8") as f:
            return done(f.read())

    def read(uri):
        if uri is None:
            return Clock.schedule_once(lambda dt: done(None))
        BufferedReader = autoclass("java.io.BufferedReader")
        InputStreamReader = autoclass("java.io.InputStreamReader")
        stream = PythonActivity.mActivity.getContentResolver().openInputStream(uri)
        reader = BufferedReader(InputStreamReader(stream, "UTF-8"))
        lines = []
        line = reader.readLine()
        while line is not None:
            lines.append(line)
            line = reader.readLine()
        reader.close()
        text = "\n".join(lines)
        Clock.schedule_once(lambda dt: done(text))

    intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
    intent.addCategory(Intent.CATEGORY_OPENABLE)
    intent.setType(mime)
    _pending[_OPEN] = read
    PythonActivity.mActivity.startActivityForResult(intent, _OPEN)
