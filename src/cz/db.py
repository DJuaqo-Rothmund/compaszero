"""Cuaderno guardado en SQLite (en el almacenamiento privado de la app)."""
import os
import sqlite3
import time
from dataclasses import dataclass

SECTIONS = ["Intro", "Verso", "Coro", "Puente", "Outro"]


@dataclass
class Song:
    id: int
    title: str
    updated_at: float
    bars: int = 0


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
        """)

    # canciones
    def songs(self) -> list[Song]:
        rows = self.conn.execute("""
            SELECT s.id, s.title, s.updated_at, COUNT(b.id) FROM song s
            LEFT JOIN bar b ON b.song_id = s.id GROUP BY s.id ORDER BY s.updated_at DESC""")
        return [Song(*r) for r in rows]

    def song(self, song_id: int) -> Song | None:
        r = self.conn.execute("SELECT id, title, updated_at FROM song WHERE id = ?", (song_id,)).fetchone()
        return Song(*r) if r else None

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
