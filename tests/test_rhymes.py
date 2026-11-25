import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import pytest
from cz.rhymes import keys, last_word, RhymeIndex


@pytest.mark.parametrize("a,b", [("camino", "destino"), ("noche", "coche"), ("corazón", "razón"),
                                 ("calle", "valle"), ("vida", "bebida"), ("canción", "pasión")])
def test_consonante(a, b):
    assert keys(a)["consonante"] == keys(b)["consonante"]


@pytest.mark.parametrize("a,b", [("camino", "cuchillo"), ("noche", "nombre"), ("calle", "madre"), ("amor", "dolor")])
def test_asonante(a, b):
    assert keys(a)["asonante"] == keys(b)["asonante"]


def test_multisilabica_respeta_el_acento():
    assert keys("camino")["multisilabica"] == keys("latino")["multisilabica"]
    assert keys("noche")["multisilabica"] != keys("poder")["multisilabica"]


def test_seseo_y_b_v():
    assert keys("vez")["consonante"] == keys("bes")["consonante"]


def test_indice():
    r = RhymeIndex()
    res = r.find("camino", "consonante")
    assert "destino" in res and "camino" not in res
    assert all(w not in r.find("corazón", "asonante") for w in ("los", "con", "por"))


def test_last_word():
    assert last_word("Antes del beat, nace la idea.") == "idea"
    assert last_word("") == ""
