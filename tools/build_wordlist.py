"""Genera src/assets/rimas_es.tsv con las palabras más usadas del español y sus claves de rima.
Datos: wordfreq (CC BY-SA 4.0, https://github.com/rspeer/wordfreq). Uso: pip install wordfreq; python tools/build_wordlist.py"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wordfreq import top_n_list
from cz.rhymes import keys, TYPES

ALLOWED = set("abcdefghijklmnñopqrstuvwxyzáéíóúü")
n = 0
with open(ROOT / "src/assets/rimas_es.tsv", "w", encoding="utf-8") as f:
    for w in top_n_list("es", 60000):
        if len(w) < 2 or not set(w) <= ALLOWED:
            continue
        k = keys(w)
        if not k:
            continue
        f.write("\t".join([w] + [k[t] for t in TYPES]) + "\n")
        n += 1
print(n, "palabras")
