import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import pytest
from cz.syllables import count_word, count_line


@pytest.mark.parametrize("word,n", [
    ("casa", 2), ("rap", 1), ("micrófono", 4), ("compás", 2),          # simples
    ("ciudad", 2), ("bueno", 2), ("aire", 2), ("cuidado", 3),        # diptongos
    ("poeta", 3), ("día", 2), ("país", 2), ("leer", 2), ("baúl", 2),  # hiatos
    ("que", 1), ("guitarra", 3), ("pingüino", 3), ("ahumado", 3),    # u muda, h
    ("rey", 1), ("muy", 1), ("yo", 1), ("ayer", 2), ("y", 1),        # y
])
def test_word(word, n):
    assert count_word(word) == n


def test_line():
    assert count_line("Antes del beat, nace la idea.") == 11
