"""Anonymous usage stats (orkget/usage.py, orkget/consent.py, docs/usage.md): off until the operator says yes,
one answer per machine, only the events and properties `schemas/` lists for the product, each body naming
its product. Orkline's tests of its `core/usage.py` before orkGet, once for each product."""
from __future__ import annotations

import json
import re
import urllib.error

import pytest

from orkget import consent, profile, usage
from profiles import ORKBOARD, ORKLINE


def _usage(machine, sent: list, share: bool | None = True, demo: bool = False) -> usage.Usage:
    if share is not None:
        consent.share(machine, share)
    return usage.Usage(machine, demo=demo, send=lambda url, data: sent.append((url, json.loads(data))))


def _flush(u: usage.Usage) -> None:
    u.flush(wait=5)


def test_nothing_is_sent_until_the_operator_says_yes(sharing, product, machine):
    sent: list = []
    u = _usage(machine, sent, share=None)
    assert u.should_ask() and not u.enabled()
    u.track("app_closed", minutes="<5")
    _flush(u)
    assert sent == []


def test_a_yes_sends_only_the_listed_properties_and_names_the_product(sharing, product, machine):
    sent: list = []
    u = _usage(machine, sent)
    u.track("app_opened", face="gui", tools=["claude"], title="My secret project", path="/home/me")
    u.track("app_opened", tools=["claude", "../../etc"])     # not a tool: the event goes, the value not
    u.track("prompt_typed", text="hello")                  # not an event at all
    _flush(u)
    (url, body), = sent
    assert url == "https://usage.example/v1/events"
    assert [e["props"] for e in body["events"]] == [{"face": "gui", "tools": ["claude"]}, {}]
    assert body["product"] == product.product and body["app_version"] == product.version
    assert re.fullmatch(r"[0-9a-f]{32}", body["install_id"])
    assert "My secret project" not in json.dumps(body) and "/home/me" not in json.dumps(body)


def test_each_product_sends_only_its_own_events(sharing, machine):
    sent: list = []
    profile.use(ORKBOARD)
    u = _usage(machine, sent)
    u.track("building_built", type="lake")                 # Orkline's: Orkboard has no buildings
    u.track("install_step", step="uv", ok=True)            # the installer's: every product's
    _flush(u)
    assert [e["event"] for e in sent[0][1]["events"]] == ["install_step"]
    profile.use(ORKLINE)
    assert usage.clean("building_built", {"type": "lake"}) == {"type": "lake"}


def test_a_value_is_checked_as_the_proxy_checks_it():
    assert usage.clean("stage_reached", {"stage": 2}) == {"stage": 2}
    assert usage.clean("stage_reached", {"stage": True}) == {}      # True is not 1, as in JavaScript
    assert usage.clean("stage_reached", {"stage": "2"}) == {}
    too_many = ["claude"] * 7
    assert usage.clean("app_opened", {"tools": too_many}) == {}


@pytest.mark.parametrize("env", [{"DO_NOT_TRACK": "1"}, {"ORKCRAFT_NO_USAGE": "1"}, {"CI": "true"}])
def test_do_not_track_ci_and_the_switch_stop_it_whatever_was_answered(sharing, product, machine, monkeypatch, env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    sent: list = []
    u = _usage(machine, sent)
    assert consent.blocked() and not u.enabled() and not u.should_ask()
    u.track("app_closed", minutes="<5")
    _flush(u)
    assert sent == []


def test_the_demo_and_a_build_without_a_proxy_send_nothing(sharing, machine, monkeypatch):
    sent: list = []
    assert not _usage(machine, sent, demo=True).enabled()
    monkeypatch.delenv("ORKCRAFT_USAGE_URL")
    monkeypatch.setattr(usage, "ENDPOINT", "")
    u = _usage(machine, sent)
    assert not u.enabled() and not u.should_ask()


def test_the_proxy_is_the_one_every_installed_copy_has():
    assert usage.ENDPOINT == "https://orkcraft-usage.vadim-sidoryk.workers.dev/v1/events"


def test_debug_prints_the_batch_instead_of_sending_it(sharing, product, machine, monkeypatch, capsys):
    monkeypatch.setenv("ORKCRAFT_USAGE_DEBUG", "1")
    sent: list = []
    u = _usage(machine, sent)
    u.track("app_closed", minutes="5-30")
    _flush(u)
    err = capsys.readouterr().err
    assert sent == [] and err.startswith(f"{product.agent} usage: ") and '"minutes": "5-30"' in err


def test_an_unreachable_proxy_keeps_the_batch_for_later_a_refusal_drops_it(sharing, machine):
    def down(url, data):
        raise OSError("no network")

    u = _usage(machine, [])
    u._send = down
    u.track("road_laid")
    _flush(u)
    assert len(u._queue) == 1

    def refuses(url, data):
        raise urllib.error.HTTPError(url, 400, "bad", {}, None)

    u._send = refuses
    _flush(u)
    assert u._queue == []


def test_no_forgets_the_install_id_and_a_yes_from_the_installer_keeps_its_id(machine):
    assert machine.usage is None and not consent.sharing(machine)
    consent.share(machine, True)
    first = machine.install_id
    assert consent.ID.fullmatch(first) and consent.sharing(machine)
    consent.share(machine, True)
    assert machine.install_id == first                     # a second yes keeps the install
    consent.share(machine, False)
    assert machine.install_id == "" and machine.usage is False
    consent.share(machine, True, install_id="a" * 32)
    assert machine.install_id == "a" * 32
    consent.share(machine, False)
    consent.share(machine, True, install_id="not an id")
    assert consent.ID.fullmatch(machine.install_id) and machine.install_id != "not an id"


def test_counts_and_minutes_are_buckets():
    assert [usage.count(n) for n in (0, 1, 4, 9, 40)] == list(usage.COUNTS)
    assert usage.minutes(60) == "<5" and usage.minutes(3600) == "30-120"


def test_the_product_says_its_events_by_their_old_names():
    assert usage.share is consent.share and usage.blocked is consent.blocked and usage.ID is consent.ID
    assert "building_built" in usage.EVENTS and "install_step" in usage.EVENTS
    assert usage.INSTALL_STEPS == ("uv", "python", "package", "version", "window", "agents")
