"""The proxy (proxy/worker.js, docs/usage.md, docs/crashes.md), run in Node: today's bodies from every copy
released before orkGet get today's answers and requests (Orkline's, with `product` added); Orkboard's go to
its own Sentry project, as Orkmine's go to its own; anything not a product's is refused. Skipped without Node."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKER = (ROOT / "proxy" / "worker.js").as_uri()

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

HELPERS = """
const worker = (await import(process.argv[2])).default;
const calls = [];
globalThis.fetch = async (url, init) => { calls.push({ url, init }); return new Response(null, { status: 200 }); };
const send = async (path, ua, body, env) => {
  const res = await worker.fetch(new Request("https://w.example" + path, { method: "POST",
    headers: { "User-Agent": ua, "Content-Type": "application/json" }, body: JSON.stringify(body) }), env);
  return res.status;
};
const sent = () => calls.splice(0).map((c) => ({ url: c.url, auth: c.init.headers["X-Sentry-Auth"] || null,
  body: c.init.body }));
const ID = "0".repeat(32);
const base = (more) => ({ install_id: ID, session_id: 1700000000000, app_version: "0.2.9", os: "darwin",
  python: "3.12", ...more });
const out = {};
"""


def _node(tmp_path: Path, body: str) -> dict:
    script = tmp_path / "run.mjs"
    script.write_text(HELPERS + body + "\nconsole.log(JSON.stringify(out));\n", encoding="utf-8")
    done = subprocess.run(["node", str(script), WORKER], capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def _envelope(text: str) -> list[dict]:
    return [json.loads(x) for x in text.strip().split("\n")]


def test_a_copy_released_before_orkget_is_orklines_and_reaches_amplitude_as_before(tmp_path):
    out = _node(tmp_path, """
const env = { AMPLITUDE_API_KEY: "key" };
out.status = await send("/v1/events", "orkcraft/0.2.9", base({ events: [
  { event: "building_built", time: Date.now(), props: { type: "lake", title: "My secret project" } },
  { event: "install_step", time: Date.now(), props: { step: "uv", ok: true, seconds: "<10", path: "/home/me" } },
  { event: "stage_reached", time: Date.now(), props: { stage: true } },
  { event: "prompt_typed", time: Date.now(), props: { text: "hello" } }] }), env);
out.calls = sent();
""")
    assert out["status"] == 204
    (call,) = out["calls"]
    assert call["url"] == "https://api2.amplitude.com/2/httpapi"
    sent = json.loads(call["body"])
    assert sent["api_key"] == "key"
    assert [(e["event_type"], e["event_properties"]) for e in sent["events"]] == [
        ("building_built", {"type": "lake", "product": "orkline"}),
        ("install_step", {"step": "uv", "ok": True, "seconds": "<10", "product": "orkline"}),
        ("stage_reached", {"product": "orkline"})]
    e = sent["events"][0]
    assert e["device_id"] == "0" * 32 and e["app_version"] == "0.2.9" and e["ip"] == "$remote"
    assert "My secret project" not in call["body"] and "/home/me" not in call["body"]


def test_each_product_sends_only_its_own_events_and_the_installers(tmp_path):
    out = _node(tmp_path, """
const env = { AMPLITUDE_API_KEY: "key" };
out.status = await send("/v1/events", "orkboard/0.1.0", base({ product: "orkboard", app_version: "0.1.0", events: [
  { event: "building_built", props: { type: "lake" } },
  { event: "app_opened", props: { face: "gui", tools: ["claude"], buildings: "2-5" } },
  { event: "install_finished", props: { ok: true, failed_step: "none" } }] }), env);
out.calls = sent();
out.installer = await send("/v1/events", "orkcraft/installer-2", base({ product: "orkline", app_version: "installer-2",
  events: [{ event: "install_started", props: { method: "sh", arch: "arm64", upgrade: false } }] }), env);
out.installerCalls = sent();
""")
    assert out["status"] == 204 and out["installer"] == 204
    events = json.loads(out["calls"][0]["body"])["events"]
    assert [(e["event_type"], e["event_properties"]) for e in events] == [
        ("app_opened", {"face": "gui", "tools": ["claude"], "product": "orkboard"}),
        ("install_finished", {"ok": True, "failed_step": "none", "product": "orkboard"})]
    (started,) = json.loads(out["installerCalls"][0]["body"])["events"]
    assert started["event_properties"] == {"method": "sh", "arch": "arm64", "upgrade": False, "product": "orkline"}


def test_orkmine_sends_only_its_own_events_and_the_installers(tmp_path):
    out = _node(tmp_path, """
const env = { AMPLITUDE_API_KEY: "key" };
out.status = await send("/v1/events", "orkmine/0.1.0", base({ product: "orkmine", app_version: "0.1.0", events: [
  { event: "app_opened", props: { face: "tui", tools: ["claude"], topic: "my secret research" } },
  { event: "app_opened", props: { face: "gui" } },
  { event: "app_closed", props: { minutes: "5-30" } },
  { event: "building_built", props: { type: "lake" } },
  { event: "install_finished", props: { ok: true, failed_step: "none" } }] }), env);
out.calls = sent();
""")
    assert out["status"] == 204
    events = json.loads(out["calls"][0]["body"])["events"]
    assert [(e["event_type"], e["event_properties"]) for e in events] == [
        ("app_opened", {"face": "tui", "tools": ["claude"], "product": "orkmine"}),
        ("app_opened", {"product": "orkmine"}),                    # no window: "gui" is not Orkmine's face
        ("app_closed", {"minutes": "5-30", "product": "orkmine"}),
        ("install_finished", {"ok": True, "failed_step": "none", "product": "orkmine"})]


def test_anything_not_a_products_is_refused(tmp_path):
    out = _node(tmp_path, """
const env = { AMPLITUDE_API_KEY: "key" };
out.curl = await send("/v1/events", "curl/8", base({ events: [] }), env);
out.unknown = await send("/v1/events", "orkcraft/0.3.0", base({ product: "orkweb", events: [] }), env);
out.notText = await send("/v1/events", "orkcraft/0.3.0", base({ product: 3, events: [] }), env);
out.noId = await send("/v1/events", "orkcraft/0.3.0", { events: [] }, env);
out.crash = await send("/v1/crash", "orkboard/0.1.0", base({ product: "orkweb", items: [] }), env);
out.calls = sent();
""")
    assert (out["curl"], out["unknown"], out["notText"], out["noId"], out["crash"]) == (403, 400, 400, 400, 400)
    assert out["calls"] == []


CRASH = """
const event = (file) => ({ type: "event", event_id: "1".repeat(32), time: Date.now(), platform: "python",
  where: "command", handled: true, level: "error", face: "gui", environment: "production", command: "town.build",
  exceptions: [{ type: "KeyError", value: "'…'", frames: [
    { file, function: "command", line: 12, in_app: true },
    { file: "/Users/ann/x.py", function: "f", line: 1, in_app: true }] }] });
const session = { type: "session", sid: "2".repeat(32), init: true, status: "ok", started: Date.now(), duration: 0,
  errors: 0, environment: "production" };
"""


def test_orklines_crashes_go_to_its_sentry_project_as_before(tmp_path):
    out = _node(tmp_path, CRASH + """
const env = { SENTRY_DSN: "https://pubkey@o1.ingest.us.sentry.io/42", SENTRY_DSN_ORKBOARD: "https://b@o1.ingest.de.sentry.io/7" };
out.status = await send("/v1/crash", "orkcraft/0.2.7", base({ app_version: "0.2.7", session_id: undefined,
  items: [event("orkcraft/gui/host.py"), session, { type: "event", event_id: "nope", where: "command", exceptions: [] }] }), env);
out.refused = await send("/v1/crash", "curl/8", {}, env);
out.calls = sent();
""")
    assert out["status"] == 204 and out["refused"] == 403
    (call,) = out["calls"]
    assert call["url"] == "https://o1.ingest.us.sentry.io/api/42/envelope/" and "sentry_key=pubkey" in call["auth"]
    lines = _envelope(call["body"])
    assert [x.get("type") for x in lines[1::2]] == ["event", "session"]
    event, session = lines[2], lines[4]
    assert event["release"] == "orkcraft@0.2.7" and event["user"] == {"id": "0" * 32, "ip_address": None}
    assert [f["filename"] for f in event["exception"]["values"][0]["stacktrace"]["frames"]] == ["orkcraft/gui/host.py"]
    assert event["tags"]["command"] == "town.build" and event["exception"]["values"][0]["mechanism"]["type"] == "command"
    assert session["did"] == "0" * 32 and session["attrs"]["release"] == "orkcraft@0.2.7"


def test_orkboards_crashes_go_to_its_own_project_or_nowhere(tmp_path):
    out = _node(tmp_path, CRASH + """
const body = base({ product: "orkboard", app_version: "0.1.0", items: [event("orkboard/gui/board_host.py"), session] });
out.status = await send("/v1/crash", "orkboard/0.1.0", body,
  { SENTRY_DSN: "https://pubkey@o1.ingest.us.sentry.io/42", SENTRY_DSN_ORKBOARD: "https://bkey@o2.ingest.de.sentry.io/7" });
out.calls = sent();
out.without = await send("/v1/crash", "orkboard/0.1.0", body, { SENTRY_DSN: "https://pubkey@o1.ingest.us.sentry.io/42" });
out.withoutCalls = sent();
""")
    assert out["status"] == 204
    (call,) = out["calls"]
    assert call["url"] == "https://o2.ingest.de.sentry.io/api/7/envelope/" and "sentry_key=bkey" in call["auth"]
    lines = _envelope(call["body"])
    event, session = lines[2], lines[4]
    assert event["release"] == "orkboard@0.1.0" and session["attrs"]["release"] == "orkboard@0.1.0"
    frames = event["exception"]["values"][0]["stacktrace"]["frames"]
    assert [(f["filename"], f["in_app"]) for f in frames] == [("orkboard/gui/board_host.py", True)]
    assert out["without"] == 204 and out["withoutCalls"] == []      # no DSN of Orkboard's: dropped, never Orkline's


def test_amplitude_down_is_worth_a_second_try_and_anything_else_is_final(tmp_path):
    out = _node(tmp_path, """
const env = { AMPLITUDE_API_KEY: "key" };
const answer = async (status) => {
  globalThis.fetch = async () => new Response(null, { status });
  return send("/v1/events", "orkcraft/0.3.0", base({ events: [{ event: "road_laid", props: {} }] }), env);
};
out.busy = await answer(429);
out.down = await answer(502);
out.badKey = await answer(400);
""")
    assert (out["busy"], out["down"], out["badKey"]) == (503, 503, 204)


def test_orkmines_crashes_go_to_its_own_project_as_a_game_in_the_terminal_or_nowhere(tmp_path):
    out = _node(tmp_path, CRASH + """
const tui = (file) => ({ ...event(file), face: "tui" });
const body = base({ product: "orkmine", app_version: "0.1.0", items: [tui("orkmine/cli.py"), session] });
out.status = await send("/v1/crash", "orkmine/0.1.0", body,
  { SENTRY_DSN: "https://pubkey@o1.ingest.us.sentry.io/42", SENTRY_DSN_ORKMINE: "https://mkey@o4.ingest.de.sentry.io/11" });
out.calls = sent();
out.without = await send("/v1/crash", "orkmine/0.1.0", body, { SENTRY_DSN: "https://pubkey@o1.ingest.us.sentry.io/42" });
out.withoutCalls = sent();
""")
    assert out["status"] == 204
    (call,) = out["calls"]
    assert call["url"] == "https://o4.ingest.de.sentry.io/api/11/envelope/" and "sentry_key=mkey" in call["auth"]
    event = _envelope(call["body"])[2]
    assert event["release"] == "orkmine@0.1.0" and event["tags"]["face"] == "tui"
    assert out["without"] == 204 and out["withoutCalls"] == []      # no DSN of Orkmine's: dropped, never Orkline's
