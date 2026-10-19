"""Crash reports (orkget/crashes.py, docs/crashes.md): sent only after the usage stats' yes, only where in the
product's own code it broke, each run a Sentry session of that product. Orkline's tests of its
`core/crashes.py` before orkGet, once for each product; what is a product's own (its window, its server)
stays in the product's tests."""
from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path

import pytest

from orkget import consent, crashes, profile
from profiles import ORKBOARD, ORKLINE


@pytest.fixture
def own(tmp_path, monkeypatch):
    """The product's package is a folder of this test: frames under it are the product's own."""
    root = tmp_path / "site-of-product"

    def roots():
        return [(name, root / name) for name in profile.current().in_app]
    monkeypatch.setattr(crashes, "roots", roots)
    return root


def _reporter(machine, sent: list, share: bool | None = True, demo: bool = False) -> crashes.Reporter:
    if share is not None:
        consent.share(machine, share)
    return crashes.Reporter(machine, demo=demo, send=lambda url, data: sent.append((url, json.loads(data))))


def _boom(path: str = "/home/someone/secret-project/plan.md"):
    raise FileNotFoundError(f"[Errno 2] No such file or directory: '{path}'")


def _caught() -> BaseException:
    try:
        _boom()
    except Exception as e:
        return e
    raise AssertionError


def _wait(sent: list, n: int) -> None:
    for t in threading.enumerate():
        if t.name == "crash-report":
            t.join(5)
    assert len(sent) >= n, sent


def test_nothing_is_sent_without_a_yes_but_the_traceback_stays_here(sharing, product, machine, tmp_path):
    sent: list = []
    r = _reporter(machine, sent, share=None)
    r.capture(_caught(), "command")
    r.start()
    r.close()
    assert sent == []
    (kept,) = (tmp_path / "crashes").glob("crash-*.txt")
    assert kept.name.startswith(f"crash-{product.product}-")
    text = kept.read_text()
    assert "secret-project" in text and text.startswith(f"{product.name} {product.version} · ")


def test_a_report_says_where_it_broke_and_nothing_of_the_person(sharing, product, machine):
    sent: list = []
    r = _reporter(machine, sent)
    r.capture(_caught(), "command", command="town.build")
    _wait(sent, 1)
    (url, body), = sent
    assert url == "https://usage.example/v1/crash"
    assert body["product"] == product.product and body["app_version"] == product.version
    (event,) = body["items"]
    assert event["type"] == "event" and event["where"] == "command" and event["command"] == "town.build"
    (exc,) = event["exceptions"]
    assert exc["type"] == "FileNotFoundError" and exc["value"] == "[Errno 2] No such file or directory: '…'"
    text = json.dumps(body)
    assert "secret-project" not in text and "someone" not in text and str(Path.home()) not in text
    assert all(f["file"] == "<other>" or not f["file"].startswith("/") for f in exc["frames"])
    assert body["install_id"] == r.machine.install_id


def test_the_products_frames_keep_their_path_in_its_package(product, own):
    f = crashes.frame(str(own / product.package / "core" / "town.py"), "toast", 93)
    assert f == {"file": f"{product.package}/core/town.py", "function": "toast", "line": 93, "in_app": True}
    assert crashes.frame("/home/me/project/build.py", "my_secret_function", 3) == \
        {"file": "<other>", "function": "?", "line": None, "in_app": False}
    lib = crashes.frame("/x/lib/python3.12/site-packages/websockets/server.py", "serve", 10)
    assert lib["file"] == "websockets/server.py" and not lib["in_app"]


def test_a_product_that_carries_another_counts_its_frames_as_its_own(tmp_path, monkeypatch):
    both = profile.use(profile.Profile(**{**ORKLINE.__dict__, "in_app": ("orkcraft", "orkboard")}))
    site = tmp_path / "site"
    monkeypatch.setattr(crashes, "roots", lambda: [(n, site / n) for n in both.in_app])
    f = crashes.frame(str(site / "orkboard" / "realm" / "ideas.py"), "save", 7)
    assert f["file"] == "orkboard/realm/ideas.py" and f["in_app"]


def test_the_copy_finds_the_packages_python_finds(monkeypatch):
    profile.use(profile.Profile(**{**ORKBOARD.__dict__, "in_app": ("orkget", "no_such_package_here")}))
    assert crashes.roots() == [("orkget", Path(crashes.__file__).resolve().parent)]


@pytest.mark.parametrize("raw, said", [
    ("No such file: '/Users/ann/clients/acme.txt'", "No such file: '…'"),
    ("cannot open /var/folders/x/y.json now", "cannot open <path> now"),
    ("GET https://api.example.com/v1?token=abc failed", "GET <url> failed"),
    ("mail ann@acme.io bounced", "mail <email> bounced"),
    ('KeyError: "Acme launch plan"', "KeyError: '…'"),
    ("C:\\Users\\ann\\a.txt is locked", "<path> is locked"),
    ("list index out of range", "list index out of range"),
])
def test_scrub_takes_out_what_could_be_the_persons(raw, said):
    assert crashes.scrub(raw) == said


def test_the_same_error_goes_once_and_a_run_sends_a_few_at_most(sharing, machine):
    sent: list = []
    r = _reporter(machine, sent)
    e = _caught()
    for _ in range(5):
        r.capture(e, "clock")
    _wait(sent, 1)
    assert len(sent) == 1 and r.errors == 5
    for i in range(crashes.MAX_EVENTS + 5):
        r._event([{"type": "E", "value": "", "frames": [{"file": "orkcraft/x.py", "function": "f", "line": i,
                                                          "in_app": True}]}], "python", "clock", True, False, "")
    _wait(sent, crashes.MAX_EVENTS)
    assert len(sent) == crashes.MAX_EVENTS


def _dead_pid() -> int:
    p = subprocess.Popen(["true"])
    p.wait()
    return p.pid


def _marker(folder: Path, name: str, sid: str, pid: int) -> Path:
    path = folder / name
    path.write_text(json.dumps({"sid": sid, "started": 1.0, "pid": pid}))
    return path


def test_each_run_is_a_session_and_one_that_died_ends_as_abnormal(sharing, product, machine, tmp_path):
    folder = tmp_path / "crashes"
    folder.mkdir()
    p = product.product
    _marker(folder, f"session-{p}-{'a' * 32}.json", "a" * 32, _dead_pid())
    alive = _marker(folder, f"session-{p}-{'b' * 32}.json", "b" * 32, os.getpid())   # another window, alive
    sent: list = []
    r = _reporter(machine, sent)
    r.start()
    _wait(sent, 2)
    items = [b["items"][0] for _, b in sent]
    assert [(i["sid"], i["status"], i["init"]) for i in items] == [("a" * 32, "abnormal", False), (r.sid, "ok", True)]
    assert alive.exists() and (folder / f"session-{p}-{r.sid}.json").exists()
    r.crashed = True
    r.close()
    _wait(sent, 3)
    assert sent[-1][1]["items"][0]["status"] == "crashed"
    assert not (folder / f"session-{p}-{r.sid}.json").exists()


def test_a_product_never_ends_another_products_session(sharing, machine, tmp_path):
    folder = tmp_path / "crashes"
    folder.mkdir()
    dead = _dead_pid()
    orkline = _marker(folder, f"session-orkline-{'c' * 32}.json", "c" * 32, dead)
    legacy = _marker(folder, f"session-{'d' * 32}.json", "d" * 32, dead)      # Orkline's, written before orkGet
    profile.use(ORKBOARD)
    sent: list = []
    r = _reporter(machine, sent)
    r.start()
    _wait(sent, 1)
    assert [b["items"][0]["sid"] for _, b in sent] == [r.sid]
    assert orkline.exists() and legacy.exists()
    r.close()
    profile.use(ORKLINE)                                    # Orkline ends both of its own
    sent.clear()
    r = _reporter(machine, sent)
    r.start()
    _wait(sent, 3)
    assert sorted(b["items"][0]["sid"] for _, b in sent[:2]) == ["c" * 32, "d" * 32]
    assert not orkline.exists() and not legacy.exists()
    r.close()


def test_an_error_on_a_thread_is_reported_and_the_hooks_go_with_the_reporter(sharing, machine, monkeypatch):
    sent: list = []
    r = _reporter(machine, sent)
    monkeypatch.setattr(threading, "excepthook", lambda args: None)     # the error this test raises on purpose
    before = threading.excepthook
    r.install()
    try:
        t = threading.Thread(target=_boom)
        t.start()
        t.join()
    finally:
        r.uninstall()
    assert threading.excepthook is before
    _wait(sent, 1)
    event = sent[0][1]["items"][0]
    assert event["where"] == "thread" and event["handled"] is False


def test_the_window_reports_its_errors_by_its_own_scripts(sharing, product, machine):
    sent: list = []
    r = _reporter(machine, sent)
    r.capture_window("TypeError: b.card is undefined for '/Users/ann/x'",
                     "Hut@http://127.0.0.1:5000/static/js/hut.js:120:7\n"
                     "render@http://127.0.0.1:5000/static/js/vendor/preact.js:1:9\n"
                     "evil@file:///Users/ann/x.js:1:1")
    _wait(sent, 1)
    event = sent[0][1]["items"][0]
    assert event["platform"] == "javascript" and event["where"] == "window"
    assert event["exceptions"][0]["type"] == "TypeError"
    assert event["exceptions"][0]["value"] == "b.card is undefined for '…'"
    assert [f["file"] for f in event["exceptions"][0]["frames"]] == ["static/js/vendor/preact.js", "static/js/hut.js"]
    assert "ann" not in json.dumps(sent)


def test_debug_prints_the_report_instead_of_sending_it(sharing, product, machine, monkeypatch, capsys):
    monkeypatch.setenv("ORKCRAFT_USAGE_DEBUG", "1")
    sent: list = []
    r = _reporter(machine, sent)
    r.capture(_caught(), "command")
    assert sent == [] and capsys.readouterr().err.startswith(f"{product.agent} crash: ")


def test_the_crash_address_is_beside_the_usage_stats(monkeypatch):
    assert crashes.endpoint() == "https://orkcraft-usage.vadim-sidoryk.workers.dev/v1/crash"
    monkeypatch.setenv("ORKCRAFT_CRASH_URL", "https://elsewhere.example/c")
    assert crashes.endpoint() == "https://elsewhere.example/c"
