"""Anonymous usage stats (docs/usage.md): which features are used, never what is in them.

Off until the operator says yes (`consent.py`: one answer per machine). Then the events `schemas/` lists
for this product — each with only the properties named there, each a word from a known set or a bucket —
go in batches to the proxy (proxy/), which holds the analytics key and passes them on to Amplitude. No
code, prompt, path, file or project name, no text an ork or a person wrote, no IP address: the proxy
drops it before Amplitude sees the request.

    u = Usage(machine, face="gui", demo=demo)
    u.track("building_built", type="lake")   # an unknown event or property is dropped, never sent
    u.tick(time.monotonic())                 # from the host's clock: a batch at most once a minute
    u.close()                                # the window closed: what is left goes, briefly

Each event is listed once, in `schemas/` (common.json, install.json and the product's own file); the
proxy bundles the same files. A product's tests check the sets against its code.

Nothing is collected while `DO_NOT_TRACK` or `ORKCRAFT_NO_USAGE` is set, under CI, in the demo, or
while `ENDPOINT` is empty. `ORKCRAFT_USAGE_DEBUG=1` prints each batch to stderr instead of sending it.
"""
from __future__ import annotations

import json
import platform
import sys
import threading
import time
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from . import profile
from .consent import ID, blocked, debug, share, sharing  # noqa: F401  (the product's `usage` says them too)
from .profile import getenv

# The proxy's address (proxy/README.md): the one every installed copy has. Empty: nothing leaves the machine.
ENDPOINT = "https://orkcraft-usage.vadim-sidoryk.workers.dev/v1/events"
FLUSH_S = 60.0           # a batch at most this often
BATCH = 50               # …or as soon as this many wait
KEEP = 200               # what waits when the proxy cannot be reached: the oldest go first
TIMEOUT_S = 5.0
CLOSE_TIMEOUT_S = 2.0    # the window never waits longer than this for the last batch


# -- the schemas --------------------------------------------------------------------------------

def schema_dir() -> Path:
    """`schemas/` beside the package in orkGet, inside it in a product's copy."""
    here = Path(__file__).resolve().parent
    return here / "schemas" if (here / "schemas").is_dir() else here.parent / "schemas"


@lru_cache(maxsize=None)
def schema(name: str, folder: str = "") -> dict[str, Any]:
    """One schema file (`common`, `install`, `orkline`…), as JSON."""
    path = Path(folder or schema_dir()) / f"{name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} is not a JSON object")
    return data


def sets(product: str, folder: str = "") -> dict[str, list]:
    """Every set a product's rules may name: common.json's, install.json's and its own."""
    out: dict[str, list] = {}
    for name in ("common", "install", product):
        out.update(schema(name, folder).get("sets") or {})
    return out


def _one_of(value: Any, values: list) -> bool:
    """`value` is one of `values`, as JavaScript's `includes` says it: True is not 1."""
    return any(type(value) is type(v) and value == v for v in values)


def rule(text: Any, known: dict[str, list]) -> Callable[[Any], bool]:
    """A property's check from its rule: a list of values, "bool", "set:<name>" or "list:<name>"."""
    if text == "bool":
        return lambda v: isinstance(v, bool)
    if isinstance(text, list):
        return lambda v: _one_of(v, text)
    if isinstance(text, str) and ":" in text:
        kind, name = text.split(":", 1)
        values = known.get(name)
        if values is not None and kind == "set":
            return lambda v: _one_of(v, values)
        if values is not None and kind == "list":
            return lambda v: isinstance(v, list) and len(v) <= len(values) and all(_one_of(x, values) for x in v)
    raise ValueError(f"not a rule: {text!r}")


def events(product: str = "", folder: str = "") -> dict[str, dict[str, Callable[[Any], bool]]]:
    """Every event a product (this process's by default) may send and every property it may carry: the
    installer's and its own."""
    return _events(product or profile.current().product, folder)


@lru_cache(maxsize=None)
def _events(product: str, folder: str) -> dict[str, dict[str, Callable[[Any], bool]]]:
    known = sets(product, folder)
    out: dict[str, dict[str, Callable[[Any], bool]]] = {}
    for name in ("install", product):
        for event, props in (schema(name, folder).get("events") or {}).items():
            out[event] = {prop: rule(text, known) for prop, text in props.items()}
    return out


def __getattr__(name: str) -> Any:            # `usage.EVENTS`: this product's, read when asked
    if name == "EVENTS":
        return events()
    raise AttributeError(name)


_COMMON = schema("common")["sets"]
_INSTALL = schema("install")["sets"]
COUNTS = tuple(_COMMON["counts"])
MINUTES = tuple(_COMMON["minutes"])
SECONDS = tuple(_COMMON["seconds"])
INSTALL_STEPS = tuple(_INSTALL["steps"])
INSTALL_ERRORS = tuple(_INSTALL["errors"])


def clean(event: str, props: dict[str, Any]) -> dict[str, Any] | None:
    """Only the properties the schema names, each with a value it allows; None for an unknown event."""
    allowed = events().get(event)
    if allowed is None:
        return None
    return {k: v for k, v in props.items() if k in allowed and allowed[k](v)}


def count(n: int) -> str:
    """A number of things as a bucket: no exact count leaves the machine."""
    return "0" if n <= 0 else "1" if n == 1 else "2-5" if n <= 5 else "6-10" if n <= 10 else "11+"


def minutes(seconds: float) -> str:
    m = seconds / 60
    return "<5" if m < 5 else "5-30" if m < 30 else "30-120" if m < 120 else "120+"


def endpoint() -> str:
    return getenv("USAGE_URL") or ENDPOINT


# -- the batches --------------------------------------------------------------------------------

class Usage:
    def __init__(self, machine: Any, face: str = "gui", demo: bool = False,
                 send: Callable[[str, bytes], None] | None = None) -> None:
        self.machine = machine
        self.face = face
        self.demo = demo
        self.started = time.time()
        self.session_id = int(self.started * 1000)   # Amplitude's session: when this one began, in ms
        self._send = send or _post
        self._queue: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._sent_at = time.monotonic()

    def enabled(self) -> bool:
        return sharing(self.machine) and not self.demo and not blocked() and bool(endpoint() or debug())

    def should_ask(self) -> bool:
        """The operator has not answered yet and an answer would matter here."""
        return self.machine.usage is None and not self.demo and not blocked() and bool(endpoint())

    def track(self, event: str, **props: Any) -> None:
        if not self.enabled():
            return
        kept = clean(event, props)
        if kept is None:
            return
        with self._lock:
            self._queue.append({"event": event, "time": int(time.time() * 1000), "props": kept})
            full = len(self._queue) >= BATCH
        if full:
            self.flush()

    def tick(self, now: float) -> None:
        if now - self._sent_at >= FLUSH_S:
            self._sent_at = now
            self.flush()

    def flush(self, wait: float | None = None) -> None:
        """What waits goes on a thread of its own; `wait` seconds at most for it (None: no wait)."""
        with self._lock:
            batch, self._queue = self._queue, []
        if not batch:
            return
        if not self.enabled():          # the operator said no meanwhile: what waited is forgotten
            return
        body = self.payload(batch)
        if debug():
            sys.stderr.write(f"{profile.current().agent} usage: " + json.dumps(body, ensure_ascii=False) + "\n")
            return
        thread = threading.Thread(target=self._deliver, args=(batch, body), daemon=True, name="usage")
        thread.start()
        if wait:
            thread.join(wait)

    def _deliver(self, batch: list[dict[str, Any]], body: dict[str, Any]) -> None:
        try:
            self._send(endpoint(), json.dumps(body).encode("utf-8"))
        except urllib.error.HTTPError as e:     # refused: only a busy or broken proxy is worth a second try
            if e.code == 429 or e.code >= 500:
                self._keep(batch)
        except Exception:               # unreachable: the stats never trouble the product, they wait
            self._keep(batch)

    def _keep(self, batch: list[dict[str, Any]]) -> None:
        with self._lock:
            self._queue = (batch + self._queue)[-KEEP:]

    def payload(self, batch: list[dict[str, Any]]) -> dict[str, Any]:
        p = profile.current()
        return {"install_id": self.machine.install_id, "product": p.product, "session_id": self.session_id,
                "app_version": p.version, "os": platform.system().lower() or "unknown",
                "python": ".".join(platform.python_version_tuple()[:2]), "events": batch}

    def close(self) -> None:
        self.track("app_closed", minutes=minutes(time.time() - self.started))
        self.flush(wait=CLOSE_TIMEOUT_S)


def _post(url: str, data: bytes) -> None:
    p = profile.current()
    request = urllib.request.Request(url, data=data, method="POST", headers={
        "Content-Type": "application/json", "User-Agent": f"{p.agent}/{p.version}"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_S):   # an answer of 4xx/5xx raises HTTPError
        pass
