"""Buscar y descargar bases libres (Creative Commons) desde Jamendo y Openverse.

- Jamendo: catálogo de música CC con filtro de instrumentales. Necesita un client_id gratuito
  (developer.jamendo.com) que el usuario pega en Ajustes.
- Openverse: buscador de audio libre (Freesound, Jamendo, ccMixter…). No necesita clave.

Cada base descargada guarda al lado un .json con autor, licencia y enlace, para dar crédito.
"""
import json
import os
import re
import threading
import urllib.error
import urllib.parse
import urllib.request

STYLES = {  # estilo -> (tags de Jamendo, palabras para Openverse)
    "Boom bap": ("hiphop+boombap", "boom bap hip hop instrumental"),
    "Trap": ("hiphop+trap", "trap beat instrumental"),
    "Lo-fi": ("lofi+hiphop", "lofi hip hop beat"),
    "Drill": ("drill", "drill beat instrumental"),
    "Jazz rap": ("hiphop+jazz", "jazz hip hop instrumental"),
    "Cualquiera": ("hiphop", "hip hop instrumental beat"),
}
UA = "CompasZero/0.3 (app de escritura de rap)"


def _ssl_context():
    """En Android Python no siempre ve los certificados del sistema: usamos los de certifi si están."""
    import ssl
    try:
        import certifi
        if os.environ.get("FLET_PLATFORM") == "android" or os.path.exists("/system/build.prop"):
            return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass
    return ssl.create_default_context()


def _open(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout, context=_ssl_context())


def parse_license(code_or_url: str) -> str:
    """'http://creativecommons.org/licenses/by-nc-sa/3.0/' o 'by-nc-sa' -> 'by-nc-sa'; dominio público -> 'cc0'."""
    s = (code_or_url or "").lower()
    if "publicdomain" in s or s in ("cc0", "pdm"):
        return "cc0"
    m = re.search(r"licenses/([a-z\-]+)/", s)
    return m.group(1) if m else s.strip()


def can_publish(lic: str) -> bool:
    """¿Se puede publicar/monetizar una canción grabada sobre esta base? (sin NC ni ND)."""
    parts = lic.split("-")
    return lic == "cc0" or ("nc" not in parts and "nd" not in parts and lic.startswith("by"))


def license_label(lic: str) -> str:
    if lic == "cc0":
        return "Dominio público"
    return "CC " + lic.upper()


def _track(source, id_, title, artist, seconds, lic, stream, download, page):
    lic = parse_license(lic)
    return {"source": source, "id": str(id_), "title": title or "Sin título", "artist": artist or "Anónimo",
            "duration": int(seconds or 0), "license": lic, "publish_ok": can_publish(lic),
            "stream": stream, "download": download or stream, "page": page}


# ---------- Jamendo ----------
def jamendo_url(client_id: str, style: str, query: str = "", offset: int = 0) -> str:
    tags = STYLES.get(style, STYLES["Cualquiera"])[0]
    params = {"client_id": client_id, "format": "json", "limit": 30, "offset": offset,
              "vocalinstrumental": "instrumental", "audioformat": "mp32",
              "order": "popularity_total", "fuzzytags": tags}
    if query.strip():
        params["search"] = query.strip()
    return "https://api.jamendo.com/v3.0/tracks/?" + urllib.parse.urlencode(params)


def parse_jamendo(data: dict) -> list[dict]:
    head = data.get("headers", {})
    if head.get("status") == "failed":
        raise ValueError(head.get("error_message") or "Error de Jamendo")
    out = []
    for r in data.get("results", []):
        dl = r.get("audiodownload") if r.get("audiodownload_allowed", True) else None
        out.append(_track("Jamendo", r.get("id"), r.get("name"), r.get("artist_name"), r.get("duration"),
                          r.get("license_ccurl", ""), r.get("audio"), dl, r.get("shareurl")))
    return out


# ---------- Openverse ----------
def openverse_url(style: str, query: str = "", page: int = 1, publish_only: bool = False) -> str:
    q = (query.strip() + " " if query.strip() else "") + STYLES.get(style, STYLES["Cualquiera"])[1]
    params = {"q": q, "page_size": 20, "page": page, "category": "music"}
    if publish_only:
        params["license_type"] = "commercial,modification"
    return "https://api.openverse.org/v1/audio/?" + urllib.parse.urlencode(params)


def parse_openverse(data: dict) -> list[dict]:
    out = []
    for r in data.get("results", []):
        if not r.get("url"):
            continue
        out.append(_track("Openverse · " + (r.get("source") or "").capitalize(), r.get("id"), r.get("title"),
                          r.get("creator"), (r.get("duration") or 0) / 1000, r.get("license", ""),
                          r.get("url"), r.get("url"), r.get("foreign_landing_url")))
    return out


# ---------- red ----------
def _get_json(url: str) -> dict:
    with _open(url, 20) as r:
        return json.loads(r.read().decode("utf-8"))


def search(source: str, style: str, query: str, client_id: str, publish_only: bool, page: int, done):
    """Busca en un hilo aparte y llama done(resultados, error) al terminar."""

    def work():
        try:
            if source == "Jamendo":
                if not client_id:
                    raise ValueError("Falta tu client_id de Jamendo (pégalo en Ajustes)")
                res = parse_jamendo(_get_json(jamendo_url(client_id, style, query, (page - 1) * 30)))
            else:
                res = parse_openverse(_get_json(openverse_url(style, query, page, publish_only)))
            if publish_only:
                res = [r for r in res if r["publish_ok"]]
            done(res, None)
        except urllib.error.HTTPError as e:
            msg = ("Demasiadas búsquedas seguidas: espera un minuto" if e.code == 429 else
                   "Clave de Jamendo no válida: revísala en Ajustes" if e.code in (401, 403) else f"Error {e.code}")
            done([], msg)
        except urllib.error.URLError:
            done([], "Sin conexión a internet")
        except Exception as e:
            msg = str(e)
            done([], msg)
    threading.Thread(target=work, daemon=True).start()


def safe_name(t: dict) -> str:
    name = f"{t['artist']} - {t['title']}"
    return re.sub(r"[^\w\- .áéíóúñÁÉÍÓÚÑ]", "", name)[:80].strip() or t["id"]


def download(track: dict, folder: str, done, progress=None):
    """Descarga la base a la carpeta de bases del usuario + ficha de créditos (.json)."""

    def work():
        try:
            ext = ".mp3"
            path = os.path.join(folder, safe_name(track) + ext)
            with _open(track["download"], 60) as r, open(path + ".part", "wb") as f:
                total = int(r.headers.get("Content-Length") or 0)
                got = 0
                while True:
                    chunk = r.read(64 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    got += len(chunk)
                    if progress and total:
                        progress(got / total)
            os.replace(path + ".part", path)
            with open(os.path.splitext(path)[0] + ".json", "w", encoding="utf-8") as f:
                json.dump(track, f, ensure_ascii=False, indent=1)
            done(path, None)
        except Exception as e:
            msg = str(e)
            done(None, msg)
    threading.Thread(target=work, daemon=True).start()


def credits_for(beat_path: str) -> dict | None:
    meta = os.path.splitext(beat_path)[0] + ".json"
    if os.path.exists(meta):
        with open(meta, encoding="utf-8") as f:
            return json.load(f)
    return None


def quota(source: str, client_id: str, done):
    """Consulta cuántas búsquedas quedan. done(texto, error).
    Openverse informa su saldo en las cabeceras; Jamendo no, así que solo se valida la clave."""

    def work():
        try:
            if source == "Openverse":
                with _open("https://api.openverse.org/v1/audio/?q=beat&page_size=1", 20) as r:
                    h = r.headers
                    day = h.get("x-ratelimit-available-anon_sustained")
                    day_lim = h.get("x-ratelimit-limit-anon_sustained", "").split("/")[0]
                    minute = h.get("x-ratelimit-available-anon_burst")
                    done({"day": day, "day_limit": day_lim, "minute": minute}, None)
            else:
                if not client_id:
                    raise ValueError("Falta tu client_id de Jamendo")
                data = _get_json(f"https://api.jamendo.com/v3.0/tracks/?client_id={urllib.parse.quote(client_id)}&format=json&limit=1")
                parse_jamendo(data)  # lanza error si la clave no sirve
                done({"valid": True}, None)
        except urllib.error.HTTPError as e:
            done(None, "Sin consultas por ahora (límite alcanzado)" if e.code == 429 else
                 "Clave de Jamendo no válida" if e.code in (401, 403) else f"Error {e.code}")
        except urllib.error.URLError:
            done(None, "Sin conexión a internet")
        except Exception as e:
            done(None, str(e))
    threading.Thread(target=work, daemon=True).start()
