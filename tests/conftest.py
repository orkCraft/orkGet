"""Every test runs on a product (`product`: each of the two in turn, or Orkline for `orkline`) and leaves
nothing on this machine: the cache, the crash files and HOME are the test's own, nothing is sent and no
list of releases is read unless a test opts in."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from orkget import profile
from profiles import ALL, ORKLINE


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("ORKCRAFT_NO_USAGE", "1")         # test_usage.py and test_crashes.py opt in
    monkeypatch.setenv("ORKCRAFT_CRASH_DIR", str(tmp_path / "crashes"))
    monkeypatch.setenv("ORKCRAFT_NO_UPDATE", "1")        # test_updates.py opts in
    for name in ("ORKCRAFT_USAGE_URL", "ORKCRAFT_CRASH_URL", "ORKCRAFT_UPDATE_URL", "ORKCRAFT_USAGE_DEBUG",
                 "DO_NOT_TRACK", "HOMEBREW_PREFIX"):
        monkeypatch.delenv(name, raising=False)
    before = profile._current
    profile.use(ORKLINE)
    yield
    profile._current = before


@pytest.fixture(params=ALL, ids=[p.product for p in ALL])
def product(request) -> profile.Profile:
    """Each product in turn, as this process's."""
    return profile.use(request.param)


@pytest.fixture
def machine() -> SimpleNamespace:
    """A product's machine settings, as far as the copy reads them: not answered yet."""
    return SimpleNamespace(usage=None, install_id="", updates="critical")


@pytest.fixture
def sharing(monkeypatch):
    """Usage stats and crash reports allowed here, a proxy address, no CI."""
    for name in ("ORKCRAFT_NO_USAGE", "DO_NOT_TRACK", "CI", "ORKCRAFT_USAGE_DEBUG"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ORKCRAFT_USAGE_URL", "https://usage.example/v1/events")
