"""Genera src/assets/sinonimos_es.tsv desde el tesauro de LibreOffice (OpenThesaurus-es, LGPL 2.1).
Uso: curl -LO https://raw.githubusercontent.com/LibreOffice/dictionaries/master/es/th_es_v2.dat
     python tools/build_thesaurus.py th_es_v2.dat"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
lines = open(sys.argv[1], encoding="latin-1").read().splitlines()[1:]
syn: dict[str, list[str]] = {}
i = 0
while i < len(lines):
    head, n = lines[i].rsplit("|", 1)
    word = head.lower()
    for j in range(int(n)):
        for s in lines[i + 1 + j].split("|")[1:]:
            s = s.strip()
            lst = syn.setdefault(word, [])
            if s and s.lower() != word and s not in lst:
                lst.append(s)
    i += 1 + int(n)
with open(ROOT / "src/assets/sinonimos_es.tsv", "w", encoding="utf-8") as f:
    for w in sorted(syn):
        if syn[w]:
            f.write(w + "\t" + "|".join(syn[w][:30]) + "\n")
print(len(syn), "entradas")
