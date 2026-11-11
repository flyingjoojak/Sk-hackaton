import json
import threading
import urllib.error
import urllib.request

import pytest

from app.server import make_server


@pytest.fixture(scope="module")
def base_url():
    srv = make_server(port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def test_health(base_url):
    with urllib.request.urlopen(base_url + "/api/health") as r:
        assert json.load(r) == {"ok": True}


def test_index_served(base_url):
    with urllib.request.urlopen(base_url + "/") as r:
        assert "업무 도구" in r.read().decode("utf-8")


def test_path_traversal_blocked(base_url):
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(base_url + "/../server.py")
    assert e.value.code == 404
