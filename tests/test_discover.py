import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from cz.discover import parse_license, can_publish, parse_jamendo, parse_openverse, jamendo_url, openverse_url


def test_licencias():
    assert parse_license("http://creativecommons.org/licenses/by-nc-sa/3.0/") == "by-nc-sa"
    assert parse_license("https://creativecommons.org/publicdomain/zero/1.0/") == "cc0"
    assert can_publish("by") and can_publish("by-sa") and can_publish("cc0")
    assert not can_publish("by-nc") and not can_publish("by-nd") and not can_publish("by-nc-sa")


def test_jamendo():
    data = {"headers": {"status": "success"}, "results": [{
        "id": "123", "name": "Calle", "artist_name": "DJ X", "duration": 180,
        "license_ccurl": "http://creativecommons.org/licenses/by-sa/3.0/",
        "audio": "https://x/stream.mp3", "audiodownload": "https://x/dl.mp3", "audiodownload_allowed": True,
        "shareurl": "https://jamendo.com/track/123"}]}
    t = parse_jamendo(data)[0]
    assert (t["title"], t["artist"], t["license"], t["publish_ok"], t["download"]) == ("Calle", "DJ X", "by-sa", True, "https://x/dl.mp3")
    assert "vocalinstrumental=instrumental" in jamendo_url("abc", "Trap")


def test_jamendo_error():
    import pytest
    with pytest.raises(ValueError):
        parse_jamendo({"headers": {"status": "failed", "error_message": "Invalid Client Id"}, "results": []})


def test_openverse():
    data = {"results": [{"id": "a", "title": "Jazzy beat", "creator": "v", "license": "by", "url": "https://c/x.mp3",
                         "duration": 79217, "source": "freesound", "foreign_landing_url": "https://f/1"}]}
    t = parse_openverse(data)[0]
    assert t["duration"] == 79 and t["publish_ok"] and t["source"] == "Openverse · Freesound"
    assert "license_type=commercial%2Cmodification" in openverse_url("Lo-fi", "", 1, True)
