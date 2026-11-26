"""Motor de rimas en español.

Tipos de rima (todos se miden desde la vocal tónica hasta el final):
- consonante:   coinciden vocales y consonantes            camino / destino
- asonante:     coinciden solo las vocales                 camino / cuchillo
- multisilabica: asonante que además coincide la vocal de
                la sílaba anterior a la tónica              camino / latino / palito

Se compara por cómo suena en español latinoamericano (b=v, s=z=c(e,i), ll=y, h muda).
"""
import os

STRONG = set("aeoáéó")
ACCENTED = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u"}
VOWELS = set("aeiouáéíóúü")
# palabras gramaticales que no aportan como rima
STOP = set("""a al algo alguien ante aquel aquella así aun aunque cada como con contra cual cuando de del desde
donde dos el ella ellas ello ellos en entre era eran es esa esas ese eso esos esta estas este esto estos fue fueron
ha han hasta hay la las le les lo los me mi mis muy nada nadie ni no nos nosotros o os otra otro para pero poco por
porque pues que quien se sea ser si sin sino sobre son su sus también tan tanto te ti tu tus un una uno unos unas y ya yo
qué cómo cuándo dónde quién él tú sí más mí está están estar estoy soy eres somos fue sido hace hizo""".split())

TYPES = {"consonante": "Consonante", "asonante": "Asonante", "multisilabica": "Multisilábica"}


def _plain(c: str) -> str:
    return ACCENTED.get(c, c)


def _letters(word: str) -> str:
    return "".join(c for c in word.lower() if c.isalpha())


def _nuclei(w: str) -> list[list[int]]:
    """Grupos vocálicos (índices) separados en hiato cuando hay dos vocales fuertes."""
    groups, cur, prev = [], None, None
    for i, c in enumerate(w):
        if c == "h" and cur is not None:
            continue
        silent_u = c == "u" and i > 0 and w[i - 1] in "qg" and i + 1 < len(w) and w[i + 1] in "eiéí"
        is_v = c in VOWELS or (c == "y" and (i + 1 == len(w) or w[i + 1] not in VOWELS) and i > 0)
        if silent_u or not is_v:
            cur, prev = None, None
            continue
        strong = c in STRONG or c in "íú"
        if cur is None or (prev and strong):
            cur = [i]
            groups.append(cur)
        else:
            cur.append(i)
        prev = strong
    return groups


def _main_vowel(w: str, group: list[int], stressed: bool) -> int:
    for i in group:  # tilde manda
        if w[i] in "áéíóú":
            return i
    for i in group:
        if w[i] in "aeo":
            return i
    return group[-1] if stressed else group[0]


def analyze(word: str):
    """Devuelve (índice de la vocal tónica, lista de vocales principales por sílaba, palabra en minúsculas)."""
    w = _letters(word)
    groups = _nuclei(w)
    if not groups:
        return None
    k = next((n for n, g in enumerate(groups) if any(w[i] in "áéíóú" for i in g)), None)
    if k is None:
        last = w[-1]
        k = len(groups) - 2 if (len(groups) >= 2 and (last in VOWELS or last in "ns")) else len(groups) - 1
    mains = [_main_vowel(w, g, n == k) for n, g in enumerate(groups)]
    return k, mains, w


def _sound(s: str) -> str:
    s = "".join(_plain(c) for c in s)
    out, i = [], 0
    while i < len(s):
        c, nxt = s[i], s[i + 1] if i + 1 < len(s) else ""
        if c == "h":
            pass
        elif c == "v":
            out.append("b")
        elif c == "z":
            out.append("s")
        elif c == "c" and nxt == "h":
            out.append("ch"); i += 1
        elif c == "c":
            out.append("s" if nxt in "ei" else "k")
        elif c == "q":
            out.append("k"); i += 1 if nxt == "u" else 0
        elif c == "l" and nxt == "l":
            out.append("y"); i += 1
        elif c == "g" and nxt in "ei":
            out.append("j")
        elif c == "g" and nxt == "u" and i + 2 < len(s) and s[i + 2] in "ei":
            out.append("g"); i += 1
        elif c == "y" and i + 1 == len(s):
            out.append("i")
        elif c == "x":
            out.append("ks")
        else:
            out.append(c)
        i += 1
    return "".join(out)


def keys(word: str) -> dict[str, str] | None:
    a = analyze(word)
    if a is None:
        return None
    k, mains, w = a
    tail = mains[k:]
    ason = "".join(_plain(w[i]) for i in tail)
    # al menos dos sílabas seguidas: si la tónica es la última, suma la anterior
    # (la barra marca dónde cae el acento, para que "noche" no rime con "poder")
    pre = _plain(w[mains[k - 1]]) if k >= 1 else ""
    multi = f"{pre}|{ason}" if len(mains) >= 2 else ""
    return {
        "consonante": _sound(w[mains[k]:]),
        "asonante": ason,
        "multisilabica": multi,
    }


class RhymeIndex:
    """Índice de palabras precalculado (assets/rimas_es.tsv: palabra, consonante, asonante, multisílaba)."""

    def __init__(self, path: str | None = None):
        path = path or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "rimas_es.tsv")
        self.index = {t: {} for t in TYPES}
        with open(path, encoding="utf-8") as f:
            for line in f:
                word, *ks = line.rstrip("\n").split("\t")
                for t, key in zip(TYPES, ks):
                    if key:
                        self.index[t].setdefault(key, []).append(word)

    def find(self, word: str, kind: str = "consonante", limit: int = 40) -> list[str]:
        ks = keys(word)
        if not ks or not ks[kind]:
            return []
        base = _letters(word)
        out = []
        for cand in self.index[kind].get(ks[kind], []):
            # fuera la misma palabra y las que solo le agregan algo delante (amor / desamor)
            if cand == base or cand in STOP or cand.endswith(base) or base.endswith(cand):
                continue
            out.append(cand)
            if len(out) >= limit:
                break
        return out


def last_word(text: str) -> str:
    ws = [w for w in "".join(c if c.isalpha() else " " for c in text).split()]
    return ws[-1] if ws else ""


STRESS_NAMES = {1: "aguda", 2: "llana", 3: "esdrújula"}


def stress_info(word: str):
    """Dónde cae el acento: (índice de la vocal tónica en la palabra en minúsculas, tipo, palabra).
    tipo: aguda (última sílaba), llana (penúltima), esdrújula (antepenúltima) o sobresdrújula."""
    a = analyze(word)
    if a is None:
        return None
    k, mains, w = a
    from_end = len(mains) - k
    return mains[k], STRESS_NAMES.get(from_end, "sobresdrújula"), w
