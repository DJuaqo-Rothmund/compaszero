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


def test_estado_busqueda_versiones(tmp_path):
    nb = Notebook(str(tmp_path / "v.db"))
    sid = nb.create_song("Calle")
    nb.set_song(sid, status="En progreso", tags="#barrio #noche", bpm=92)
    nb.add_bar("primera barra", sid, "Verso")
    s = nb.song(sid)
    assert (s.status, s.tags, s.bpm, s.bars) == ("En progreso", "#barrio #noche", 92, 1)
    assert [x.id for x in nb.search("barrio")] == [sid]
    assert [x.id for x in nb.search("primera")] == [sid]
    assert nb.search("nada") == []
    assert nb.snapshot(sid) and not nb.snapshot(sid)   # solo guarda si cambió
    nb.add_bar("segunda", sid, "Coro")
    v_old = nb.versions(sid)[0]
    nb.restore(v_old.id)
    assert [b.text for b in nb.bars(sid)] == ["primera barra"]
    assert len(nb.versions(sid)) == 2                  # la letra con "segunda" quedó guardada
    assert "[Verso]" in nb.song_text(sid)


def test_racha_diccionario_respaldo(tmp_path):
    import datetime, time
    nb = Notebook(str(tmp_path / "r.db"))
    nb.add_bar("hoy")
    assert nb.streak() == 1
    nb.add_word("Flow")
    assert nb.personal_words() == {"flow"}
    data = nb.export_json()
    nb2 = Notebook(str(tmp_path / "r2.db"))
    nb2.import_json(data)
    assert [b.text for b in nb2.ideas()] == ["hoy"] and nb2.personal_words() == {"flow"}


def test_tomas(tmp_path):
    nb = Notebook(str(tmp_path / "t.db"))
    sid = nb.create_song("x")
    f = tmp_path / "a.m4a"; f.write_bytes(b"x")
    tid = nb.add_take(str(f), 12.5, sid, "Verso", "Toma 1")
    nota = nb.add_take(str(f), 3, name="Nota")
    assert [t.name for t in nb.takes(sid)] == ["Toma 1"] and [t.id for t in nb.voice_notes()] == [nota]
    nb.delete_take(tid)
    assert nb.takes(sid) == [] and not f.exists()
