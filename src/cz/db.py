"""Cuaderno guardado en SQLite (en el almacenamiento privado de la app)."""
import datetime
import json
import os
import sqlite3
import time
from dataclasses import asdict, dataclass

SECTIONS = ["Intro", "Verso", "Coro", "Puente", "Outro"]
STATUSES = ["Idea", "En progreso", "Lista", "Grabada"]


@dataclass
class Song:
    id: int
    title: str
    updated_at: float
    bars: int = 0
    status: str = "Idea"
    tags: str = ""
    beat: str = ""   # ruta de la base vinculada
    bpm: int = 90


@dataclass
class Take:
    id: int
    song_id: int | None  # None = nota de voz suelta
    section: str
    path: str
    created_at: float
    duration: float
    name: str


@dataclass
class Version:
    id: int
    song_id: int
    created_at: float
    content: str  # JSON [[sección, texto], ...]


@dataclass
class Session:
    id: int
    beat: str
    created_at: float
    duration: float
    lines: int = 0


@dataclass
class Line:
    id: int
    session_id: int
    t: float  # segundos desde que empezó la base
    text: str


@dataclass
class Bar:
    id: int
    song_id: int | None  # None = idea suelta
    section: str
    text: str
    created_at: float


def default_path() -> str:
    base = os.getenv("FLET_APP_STORAGE_DATA") or os.path.expanduser("~/.compaszero")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "cuaderno.db")


class Notebook:
    def __init__(self, path: str | None = None):
        self.conn = sqlite3.connect(path or default_path(), check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS song (
                id INTEGER PRIMARY KEY, title TEXT NOT NULL, updated_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS bar (
                id INTEGER PRIMARY KEY,
                song_id INTEGER REFERENCES song(id) ON DELETE CASCADE,
                section TEXT NOT NULL DEFAULT '', text TEXT NOT NULL, created_at REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS bar_song ON bar(song_id);
            CREATE TABLE IF NOT EXISTS freestyle (
                id INTEGER PRIMARY KEY, beat TEXT NOT NULL, created_at REAL NOT NULL,
                duration REAL NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS freestyle_line (
                id INTEGER PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES freestyle(id) ON DELETE CASCADE,
                t REAL NOT NULL, text TEXT NOT NULL);
        """)
        self._migrate()

    def _migrate(self):
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(song)")}
        for name, ddl in [("status", "TEXT NOT NULL DEFAULT 'Idea'"), ("tags", "TEXT NOT NULL DEFAULT ''"),
                          ("beat", "TEXT NOT NULL DEFAULT ''"), ("bpm", "INTEGER NOT NULL DEFAULT 90")]:
            if name not in cols:
                self.conn.execute(f"ALTER TABLE song ADD COLUMN {name} {ddl}")
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS take (
                id INTEGER PRIMARY KEY,
                song_id INTEGER REFERENCES song(id) ON DELETE CASCADE,
                section TEXT NOT NULL DEFAULT '', path TEXT NOT NULL, created_at REAL NOT NULL,
                duration REAL NOT NULL DEFAULT 0, name TEXT NOT NULL DEFAULT '');
            CREATE TABLE IF NOT EXISTS version (
                id INTEGER PRIMARY KEY,
                song_id INTEGER NOT NULL REFERENCES song(id) ON DELETE CASCADE,
                created_at REAL NOT NULL, content TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS word (word TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS setting (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        self.conn.commit()

    _SONG_COLS = "s.id, s.title, s.updated_at, COUNT(b.id), s.status, s.tags, s.beat, s.bpm"

    # canciones
    def songs(self) -> list[Song]:
        rows = self.conn.execute(f"""
            SELECT {self._SONG_COLS} FROM song s
            LEFT JOIN bar b ON b.song_id = s.id GROUP BY s.id ORDER BY s.updated_at DESC""")
        return [Song(*r) for r in rows]

    def search(self, q: str) -> list[Song]:
        """Canciones cuyo título, etiquetas o alguna barra contienen el texto."""
        like = f"%{q.strip().lower()}%"
        rows = self.conn.execute(f"""
            SELECT {self._SONG_COLS} FROM song s LEFT JOIN bar b ON b.song_id = s.id
            WHERE s.id IN (SELECT s2.id FROM song s2 LEFT JOIN bar b2 ON b2.song_id = s2.id
                           WHERE lower(s2.title) LIKE ? OR lower(s2.tags) LIKE ? OR lower(b2.text) LIKE ?)
            GROUP BY s.id ORDER BY s.updated_at DESC""", (like, like, like))
        return [Song(*r) for r in rows]

    def song(self, song_id: int) -> Song | None:
        r = self.conn.execute(f"""SELECT {self._SONG_COLS} FROM song s LEFT JOIN bar b ON b.song_id = s.id
                                  WHERE s.id = ? GROUP BY s.id""", (song_id,)).fetchone()
        return Song(*r) if r else None

    def set_song(self, song_id: int, **fields):
        """Actualiza status, tags, beat o bpm."""
        allowed = {k: v for k, v in fields.items() if k in ("status", "tags", "beat", "bpm", "title")}
        if allowed:
            sets = ", ".join(f"{k} = ?" for k in allowed)
            with self.conn:
                self.conn.execute(f"UPDATE song SET {sets}, updated_at = ? WHERE id = ?",
                                  (*allowed.values(), time.time(), song_id))

    def create_song(self, title: str) -> int:
        with self.conn:
            cur = self.conn.execute("INSERT INTO song (title, updated_at) VALUES (?, ?)",
                                    (title.strip() or "Sin título", time.time()))
        return cur.lastrowid

    def rename_song(self, song_id: int, title: str):
        with self.conn:
            self.conn.execute("UPDATE song SET title = ?, updated_at = ? WHERE id = ?",
                              (title.strip() or "Sin título", time.time(), song_id))

    def delete_song(self, song_id: int):
        with self.conn:
            self.conn.execute("DELETE FROM song WHERE id = ?", (song_id,))

    # barras
    def bars(self, song_id: int) -> list[Bar]:
        rows = self.conn.execute("SELECT * FROM bar WHERE song_id = ? ORDER BY created_at, id", (song_id,))
        return [Bar(*r) for r in rows]

    def ideas(self) -> list[Bar]:
        rows = self.conn.execute("SELECT * FROM bar WHERE song_id IS NULL ORDER BY created_at DESC, id DESC")
        return [Bar(*r) for r in rows]

    def add_bar(self, text: str, song_id: int | None = None, section: str = "") -> int | None:
        if not text.strip():
            return None
        with self.conn:
            cur = self.conn.execute("INSERT INTO bar (song_id, section, text, created_at) VALUES (?, ?, ?, ?)",
                                    (song_id, section, text.strip(), time.time()))
            self._touch(song_id)
        return cur.lastrowid

    def update_bar(self, bar_id: int, text: str):
        with self.conn:
            self.conn.execute("UPDATE bar SET text = ? WHERE id = ?", (text.strip(), bar_id))

    def move_idea(self, bar_id: int, song_id: int, section: str):
        with self.conn:
            self.conn.execute("UPDATE bar SET song_id = ?, section = ?, created_at = ? WHERE id = ?",
                              (song_id, section, time.time(), bar_id))
            self._touch(song_id)

    def delete_bar(self, bar_id: int):
        with self.conn:
            self.conn.execute("DELETE FROM bar WHERE id = ?", (bar_id,))

    def _touch(self, song_id: int | None):
        if song_id is not None:
            self.conn.execute("UPDATE song SET updated_at = ? WHERE id = ?", (time.time(), song_id))

    # freestyle
    def start_session(self, beat: str) -> int:
        with self.conn:
            return self.conn.execute("INSERT INTO freestyle (beat, created_at) VALUES (?, ?)",
                                     (beat, time.time())).lastrowid

    def end_session(self, session_id: int, duration: float):
        with self.conn:
            self.conn.execute("UPDATE freestyle SET duration = ? WHERE id = ?", (duration, session_id))

    def add_line(self, session_id: int, t: float, text: str) -> int:
        with self.conn:
            return self.conn.execute("INSERT INTO freestyle_line (session_id, t, text) VALUES (?, ?, ?)",
                                     (session_id, t, text.strip())).lastrowid

    def sessions(self) -> list[Session]:
        rows = self.conn.execute("""
            SELECT f.id, f.beat, f.created_at, f.duration, COUNT(l.id) FROM freestyle f
            LEFT JOIN freestyle_line l ON l.session_id = f.id GROUP BY f.id ORDER BY f.created_at DESC""")
        return [Session(*r) for r in rows]

    def session(self, session_id: int) -> Session | None:
        r = self.conn.execute("SELECT id, beat, created_at, duration FROM freestyle WHERE id = ?",
                              (session_id,)).fetchone()
        return Session(*r) if r else None

    def lines(self, session_id: int) -> list[Line]:
        rows = self.conn.execute("SELECT * FROM freestyle_line WHERE session_id = ? ORDER BY t, id", (session_id,))
        return [Line(*r) for r in rows]

    def update_line(self, line_id: int, text: str):
        with self.conn:
            self.conn.execute("UPDATE freestyle_line SET text = ? WHERE id = ?", (text.strip(), line_id))

    def delete_line(self, line_id: int):
        with self.conn:
            self.conn.execute("DELETE FROM freestyle_line WHERE id = ?", (line_id,))

    def delete_session(self, session_id: int):
        with self.conn:
            self.conn.execute("DELETE FROM freestyle WHERE id = ?", (session_id,))

    # tomas grabadas y notas de voz
    def add_take(self, path: str, duration: float, song_id: int | None = None, section: str = "", name: str = "") -> int:
        with self.conn:
            return self.conn.execute(
                "INSERT INTO take (song_id, section, path, created_at, duration, name) VALUES (?, ?, ?, ?, ?, ?)",
                (song_id, section, path, time.time(), duration, name)).lastrowid

    def takes(self, song_id: int) -> list[Take]:
        return [Take(*r) for r in self.conn.execute(
            "SELECT * FROM take WHERE song_id = ? ORDER BY created_at DESC", (song_id,))]

    def voice_notes(self) -> list[Take]:
        return [Take(*r) for r in self.conn.execute(
            "SELECT * FROM take WHERE song_id IS NULL ORDER BY created_at DESC")]

    def delete_take(self, take_id: int):
        r = self.conn.execute("SELECT path FROM take WHERE id = ?", (take_id,)).fetchone()
        with self.conn:
            self.conn.execute("DELETE FROM take WHERE id = ?", (take_id,))
        if r and os.path.exists(r[0]):
            os.remove(r[0])

    # historial de versiones
    def _content(self, song_id: int) -> str:
        return json.dumps([[b.section, b.text] for b in self.bars(song_id)], ensure_ascii=False)

    def snapshot(self, song_id: int) -> bool:
        """Guarda una versión si la letra cambió desde la última. Devuelve True si guardó."""
        content = self._content(song_id)
        last = self.conn.execute("SELECT content FROM version WHERE song_id = ? ORDER BY created_at DESC, id DESC LIMIT 1",
                                 (song_id,)).fetchone()
        if content == "[]" or (last and last[0] == content):
            return False
        with self.conn:
            self.conn.execute("INSERT INTO version (song_id, created_at, content) VALUES (?, ?, ?)",
                              (song_id, time.time(), content))
        return True

    def versions(self, song_id: int) -> list[Version]:
        return [Version(*r) for r in self.conn.execute(
            "SELECT * FROM version WHERE song_id = ? ORDER BY created_at DESC, id DESC", (song_id,))]

    def restore(self, version_id: int):
        v = Version(*self.conn.execute("SELECT * FROM version WHERE id = ?", (version_id,)).fetchone())
        self.snapshot(v.song_id)  # no perder la letra actual
        with self.conn:
            self.conn.execute("DELETE FROM bar WHERE song_id = ?", (v.song_id,))
            for i, (section, text) in enumerate(json.loads(v.content)):
                self.conn.execute("INSERT INTO bar (song_id, section, text, created_at) VALUES (?, ?, ?, ?)",
                                  (v.song_id, section, text, time.time() + i * 1e-3))
            self._touch(v.song_id)

    # ajustes
    def get_setting(self, key: str, default: str = "") -> str:
        r = self.conn.execute("SELECT value FROM setting WHERE key = ?", (key,)).fetchone()
        return r[0] if r else default

    def set_setting(self, key: str, value: str):
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO setting VALUES (?, ?)", (key, value))

    def count_request(self, source: str):
        """Lleva la cuenta de búsquedas por día y por mes (Jamendo no informa su saldo)."""
        import datetime
        today = datetime.date.today()
        for key in (f"req_{source}_{today:%Y%m%d}", f"req_{source}_{today:%Y%m}"):
            self.set_setting(key, str(int(self.get_setting(key, "0")) + 1))

    def requests_used(self, source: str) -> tuple[int, int]:
        import datetime
        today = datetime.date.today()
        return (int(self.get_setting(f"req_{source}_{today:%Y%m%d}", "0")),
                int(self.get_setting(f"req_{source}_{today:%Y%m}", "0")))

    # diccionario personal
    def personal_words(self) -> set[str]:
        return {r[0] for r in self.conn.execute("SELECT word FROM word")}

    def add_word(self, word: str):
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO word VALUES (?)", (word.lower(),))

    # racha de escritura: días seguidos (hasta hoy o ayer) con al menos una barra
    def streak(self, today: datetime.date | None = None) -> int:
        today = today or datetime.date.today()
        days = {datetime.date.fromtimestamp(r[0]) for r in self.conn.execute("SELECT created_at FROM bar")}
        d = today if today in days else today - datetime.timedelta(days=1)
        n = 0
        while d in days:
            n += 1
            d -= datetime.timedelta(days=1)
        return n

    # texto para compartir
    def song_text(self, song_id: int) -> str:
        song = self.song(song_id)
        out, current = [song.title.upper(), ""], None
        for b in self.bars(song_id):
            if b.section != current:
                current = b.section
                out += ["", f"[{current or 'Sin sección'}]"]
            out.append(b.text)
        return "\n".join(out).strip() + "\n"

    # copia de seguridad (todo el cuaderno en JSON; los audios no se incluyen)
    def export_json(self) -> str:
        def rows(sql):
            cur = self.conn.execute(sql)
            names = [c[0] for c in cur.description]
            return [dict(zip(names, r)) for r in cur]
        data = {t: rows(f"SELECT * FROM {t}") for t in ("song", "bar", "freestyle", "freestyle_line", "version", "word", "setting")}
        data["app"], data["format"] = "CompásZero", 1
        return json.dumps(data, ensure_ascii=False)

    def import_json(self, text: str):
        """Reemplaza el cuaderno por el de la copia."""
        data = json.loads(text)
        if data.get("app") != "CompásZero":
            raise ValueError("No es una copia de CompásZero")
        with self.conn:
            for t in ("version", "freestyle_line", "freestyle", "bar", "take", "song", "word"):
                self.conn.execute(f"DELETE FROM {t}")
            for t in ("song", "bar", "freestyle", "freestyle_line", "version", "word", "setting"):
                for row in data.get(t, []):
                    cols = ", ".join(row)
                    verb = "INSERT OR REPLACE" if t == "setting" else "INSERT"
                    self.conn.execute(f"{verb} INTO {t} ({cols}) VALUES ({', '.join('?' * len(row))})", tuple(row.values()))
