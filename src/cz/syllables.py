"""Contador de sílabas para español.

Cuenta núcleos vocálicos: los diptongos y triptongos (vocal débil i/u + otra vocal)
forman una sola sílaba; dos vocales fuertes juntas (a, e, o, o débiles acentuadas í/ú)
forman hiato y cuentan como dos. La "u" muda de que/qui/gue/gui no cuenta y la "h"
intercalada no rompe el diptongo. No aplica sinalefa entre palabras.
"""
import re

STRONG = set("aeoáéóíú")
WEAK = set("iuüy")
_WORD = re.compile(r"[^\W\d_]+")


def words(line: str) -> list[str]:
    return _WORD.findall(line.lower())


def count_line(line: str) -> int:
    return sum(count_word(w) for w in words(line))


def _is_vowel(w: str, i: int) -> bool:
    c = w[i]
    if c == "y":  # vocal sola, al final o antes de consonante (rey, muy, y)
        nxt = w[i + 1] if i + 1 < len(w) else None
        return nxt is None or not (nxt in STRONG or nxt in WEAK)
    return c in STRONG or c in WEAK


def _is_silent_u(w: str, i: int) -> bool:
    return (w[i] == "u" and i > 0 and w[i - 1] in "qg"
            and i + 1 < len(w) and w[i + 1] in "eiéí")


def count_word(raw: str) -> int:
    w = "".join(c for c in raw.lower() if c.isalpha())
    if not w:
        return 0
    count, prev = 0, None  # prev: última vocal del núcleo actual
    for i, c in enumerate(w):
        if c == "h":
            continue
        if _is_silent_u(w, i):
            prev = None
        elif _is_vowel(w, i):
            if prev is None or (prev in STRONG and c in STRONG):
                count += 1
            prev = c
        else:
            prev = None
    return max(count, 1)
