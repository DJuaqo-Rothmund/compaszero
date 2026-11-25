import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from cz.syllables import count_line, count_line_sung
from cz.spelling import Speller, Thesaurus


def test_sinalefa():
    assert count_line("nace la idea") == 6
    assert count_line_sung("nace la idea") == 5
    assert count_line_sung("Antes del beat, nace la idea") == 10
    assert count_line_sung("todo el humo") == 4  # to-doel-hu-mo


def test_ortografia():
    sp = Speller(personal={"flow"})
    assert sp.unknown_words("Mi cancion tiene flow") == ["cancion"]
    assert sp.suggest("cancion")[0] == "canción"
    assert "calle" in sp.suggest("calel")


def test_sinonimos():
    assert "senda" in Thesaurus().synonyms("camino")
