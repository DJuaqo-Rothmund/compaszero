"""Revisión ortográfica sencilla con la lista de palabras de la app + diccionario personal.

No reemplaza al autocorrector del teclado: sirve para marcar palabras dudosas en las barras
ya escritas y sugerir la forma correcta (sobre todo tildes: "cancion" -> "canción")."""
import os
import unicodedata

from cz.syllables import words

ALPHABET = "abcdefghijklmnñopqrstuvwxyzáéíóúü"


def _plain(w: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", w) if unicodedata.category(c) != "Mn" or c == "̃")


class Speller:
    def __init__(self, path: str | None = None, personal: set[str] | None = None):
        path = path or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "rimas_es.tsv")
        self.rank: dict[str, int] = {}
        self.by_plain: dict[str, str] = {}
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                w = line.split("\t", 1)[0]
                self.rank[w] = i
                self.by_plain.setdefault(unicodedata.normalize("NFC", _plain(w)), w)
        self.personal = personal if personal is not None else set()

    def known(self, word: str) -> bool:
        w = word.lower()
        if len(w) < 2 or w in self.personal:
            return True
        if w not in self.rank:
            return False
        # palabras frecuentes escritas sin tilde ("cancion"): la forma con tilde es mucho más común
        alt = self.by_plain.get(unicodedata.normalize("NFC", _plain(w)))
        return not (alt and alt != w and self.rank[w] > 300 and self.rank[alt] * 5 < self.rank[w])

    def unknown_words(self, text: str) -> list[str]:
        out = []
        for w in words(text):
            if not self.known(w) and w not in out:
                out.append(w)
        return out

    def suggest(self, word: str, n: int = 6) -> list[str]:
        w = word.lower()
        cands = set()
        accent = self.by_plain.get(unicodedata.normalize("NFC", _plain(w)))
        if accent and accent != w:
            cands.add(accent)
        splits = [(w[:i], w[i:]) for i in range(len(w) + 1)]
        edits = {a + b[1:] for a, b in splits if b}
        edits |= {a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1}
        edits |= {a + c + b[1:] for a, b in splits if b for c in ALPHABET}
        edits |= {a + c + b for a, b in splits for c in ALPHABET}
        cands |= {e for e in edits if e in self.rank}
        cands.discard(w)
        ordered = sorted(cands, key=lambda c: (c != accent, self.rank.get(c, 1e9)))
        return ordered[:n]


class Thesaurus:
    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sinonimos_es.tsv")
        self._data = None

    def _load(self):
        self._data = {}
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                w, syns = line.rstrip("\n").split("\t")
                self._data[w] = syns.split("|")

    def synonyms(self, word: str) -> list[str]:
        if self._data is None:
            self._load()
        w = word.lower()
        return self._data.get(w) or self._data.get(w.rstrip("s")) or []
