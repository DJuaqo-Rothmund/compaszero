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


def test_freestyle(tmp_path):
    nb = Notebook(str(tmp_path / "f.db"))
    sid = nb.start_session("Boom bap 90 BPM")
    nb.add_line(sid, 4.2, "rimo con el alma")
    lid = nb.add_line(sid, 1.0, "antes del beat")
    nb.end_session(sid, 30)
    assert [l.text for l in nb.lines(sid)] == ["antes del beat", "rimo con el alma"]
    nb.update_line(lid, "antes del beat nace la idea")
    assert nb.sessions()[0].lines == 2 and nb.session(sid).duration == 30
    nb.delete_session(sid)
    assert nb.sessions() == [] and nb.lines(sid) == []
