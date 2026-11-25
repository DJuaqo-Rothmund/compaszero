import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from cz.db import Notebook


def test_flujo_cuaderno(tmp_path):
    nb = Notebook(str(tmp_path / "t.db"))
    idea = nb.add_bar("Antes del beat")
    assert [b.text for b in nb.ideas()] == ["Antes del beat"]
    sid = nb.create_song("Primera")
    nb.move_idea(idea, sid, "Coro")
    assert nb.ideas() == []
    assert [(b.section, b.text) for b in nb.bars(sid)] == [("Coro", "Antes del beat")]
    assert nb.songs()[0].bars == 1
    nb.delete_song(sid)
    assert nb.songs() == [] and nb.bars(sid) == []
