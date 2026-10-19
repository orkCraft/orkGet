"""Updates (orkget/updates.py, docs/updates.md): the list of releases, what is offered, what installs by
itself when the product opens, and how each kind of install upgrades — once for each product.

These are Orkline's and Orkboard's tests of their `core/updates.py` before orkGet, with the profile in
place of the constants; what is a product's own (its updates.json, its command line, its window) stays
in the product's tests."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from orkget import profile, updates
from profiles import ORKBOARD, ORKLINE


def manifest(*rels: tuple[str, bool]) -> dict:
    return {"releases": [{"version": v, "critical": c, "notes": f"notes of {v}"} for v, c in rels]}


@pytest.fixture
def on(monkeypatch):
    """Updates are read here (conftest turns them off for every other test)."""
    monkeypatch.delenv("ORKCRAFT_NO_UPDATE", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv(updates.UPDATED_ENV, raising=False)


class Runs:
    """subprocess.run as a script: each command answered from `answers` (by its first words), all kept."""

    def __init__(self, version: str = "9.0.0", fail: str = "", status: str = "", branch: str = "main"):
        self.calls: list[list[str]] = []
        self.version, self.fail, self.status, self.branch = version, fail, status, branch

    def __call__(self, cmd, **kw):
        self.calls.append(list(cmd))
        line = " ".join(cmd)
        if f"import {profile.current().package}" in line:
            return SimpleNamespace(returncode=0, stdout=self.version + "\n", stderr="")
        if " status " in f" {line} ":
            return SimpleNamespace(returncode=0, stdout=self.status, stderr="")
        if "symbolic-ref" in line:
            return SimpleNamespace(returncode=0 if self.branch else 1, stdout=self.branch + "\n", stderr="")
        if self.fail and self.fail in line:
            return SimpleNamespace(returncode=1, stdout="", stderr="no network")
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")


# -- versions and the list ----------------------------------------------------------------------

def test_versions_compare_as_numbers():
    assert updates.newer("0.1.10", "0.1.9")
    assert not updates.newer("0.2", "0.2.0") and not updates.newer("0.2.0", "0.2")
    assert updates.newer("v1.0.0", "0.9.9")
    assert updates.version_key("1.2.0rc1") == (1, 2)


def test_nothing_is_offered_when_nothing_is_newer(product):
    assert updates.offer(manifest(("0.0.1", True), (product.version, False))) is None
    assert updates.offer({}) is None and updates.offer("broken") is None


def test_an_offer_is_critical_when_any_release_on_the_way_is():
    found = updates.offer(manifest(("0.4.0", False), ("0.3.0", True), ("0.1.0", True)), current="0.2.0")
    assert found.version == "0.4.0" and found.critical
    assert found.notes == ["0.4.0: notes of 0.4.0", "0.3.0: notes of 0.3.0"]
    assert found.critical_notes == ["0.3.0: notes of 0.3.0"]
    calm = updates.offer(manifest(("0.4.0", False), ("0.1.0", True)), current="0.2.0")
    assert calm.version == "0.4.0" and not calm.critical


def test_malformed_releases_are_left_out():
    found = updates.offer({"releases": [{"version": 3}, "x", {"notes": "no version"}, {"version": "0.9.0"}]},
                          current="0.1.0")
    assert found.version == "0.9.0" and not found.critical


def test_what_installs_by_itself_follows_the_policy(product):
    critical = updates.offer(manifest(("9.0.0", True)))
    calm = updates.offer(manifest(("9.0.0", False)))
    assert updates.due(critical, "critical") and updates.due(critical, "auto") and not updates.due(critical, "ask")
    assert not updates.due(calm, "critical") and updates.due(calm, "auto") and not updates.due(calm, "ask")
    assert not updates.due(None, "auto")


def test_each_product_reads_its_own_list_and_keeps_its_own_cache(product, tmp_path):
    assert updates.url() == product.manifest
    assert updates.state_path() == tmp_path / "cache" / "orkcraft" / product.state
    assert {ORKLINE.state, ORKBOARD.state} == {"updates.json", "orkboard-updates.json"}


# -- reading the list ---------------------------------------------------------------------------

def test_the_list_is_read_again_only_when_old(on, product, tmp_path):
    file = tmp_path / "state.json"
    reads = []
    read = lambda: reads.append(1) or manifest(("9.0.0", False))   # noqa: E731
    s = updates.check(now=1000.0, file=file, read=read)
    assert s.manifest["releases"][0]["version"] == "9.0.0" and len(reads) == 1
    updates.check(now=1000.0 + updates.CHECK_EVERY_S - 1, file=file, read=read)
    assert len(reads) == 1
    updates.check(now=1000.0 + updates.CHECK_EVERY_S + 1, file=file, read=read)
    assert len(reads) == 2


def test_a_list_that_cannot_be_read_keeps_the_last(on, product, tmp_path):
    file = tmp_path / "state.json"
    updates.check(now=0.0, file=file, read=lambda: manifest(("9.0.0", True)))

    def broken():
        raise OSError("offline")
    s = updates.check(now=updates.CHECK_EVERY_S * 2, file=file, read=broken)
    assert updates.offer(s.manifest).critical
    with pytest.raises(OSError):
        updates.check(force=True, file=file, read=broken)


def test_the_list_reads_from_a_file_url(on, product, tmp_path, monkeypatch):
    where = tmp_path / "updates.json"
    where.write_text(json.dumps(manifest(("9.0.0", True))), encoding="utf-8")
    monkeypatch.setenv("ORKCRAFT_UPDATE_URL", where.as_uri())
    assert updates.fetch()["releases"][0]["version"] == "9.0.0"


def test_nothing_is_read_when_turned_off(product, tmp_path, monkeypatch):
    monkeypatch.setenv("ORKCRAFT_NO_UPDATE", "1")
    assert updates.blocked()
    s = updates.check(force=True, file=tmp_path / "s.json", read=lambda: pytest.fail("read while off"))
    assert s.manifest == {}
    monkeypatch.delenv("ORKCRAFT_NO_UPDATE")
    monkeypatch.setenv("CI", "true")
    assert updates.blocked() == "running under CI"


# -- how this copy upgrades ---------------------------------------------------------------------

def checkout(tmp_path: Path, package: str) -> Path:
    root = tmp_path / f"{package}-src"
    (root / ".git").mkdir(parents=True)
    (root / package).mkdir()
    (root / "pyproject.toml").write_text(f'[project]\nname = "{package}"\n', encoding="utf-8")
    return root


def test_a_git_checkout_pulls(product, tmp_path):
    root = checkout(tmp_path, product.package)
    pkg = root / product.package
    way = updates.method(pkg, prefix=str(root / ".venv"), which=lambda name: "/bin/" + name)
    assert way.kind == "git" and way.steps[0] == ("git", "-C", str(root), "pull", "--ff-only")
    assert way.steps[1][:3] == ("uv", "pip", "install")
    assert updates.method(pkg, prefix="/x", which=lambda name: None).steps == way.steps[:1]


def test_a_checkout_of_the_other_product_is_not_this_one(tmp_path, monkeypatch):
    profile.use(ORKBOARD)
    monkeypatch.setattr(updates, "_direct_url", lambda: "")
    root = checkout(tmp_path, "orkcraft")                     # Orkline's checkout, read by Orkboard's copy
    assert updates.method(root / "orkcraft", prefix="/usr", which=lambda n: None).kind == "none"


def test_pipx_and_uv_upgrade_with_their_own_tool(product, tmp_path):
    pkg = tmp_path / "site" / product.package
    has = lambda name: "/bin/" + name   # noqa: E731
    name = product.names[-1]
    pipx = updates.method(pkg, prefix=f"/home/a/.local/share/pipx/venvs/{name}", which=has)
    assert pipx.kind == "pipx" and pipx.steps == (("pipx", "upgrade", name),)
    uv = updates.method(pkg, prefix=f"/home/a/.local/share/uv/tools/{name}", which=has)
    assert uv.kind == "uv" and uv.steps == (("uv", "tool", "upgrade", name),)
    missing = updates.method(pkg, prefix=f"/home/a/.local/share/pipx/venvs/{name}", which=lambda n: None)
    assert not missing.can and product.manual in missing.why
    other = updates.method(pkg, prefix="/home/a/.local/share/uv/tools/something-else", which=has)
    assert other.steps == (("uv", "tool", "upgrade", product.package),)


def test_orkline_upgrades_from_pypi_by_its_name_there(monkeypatch, tmp_path):
    profile.use(ORKLINE)
    has = lambda name: "/bin/" + name   # noqa: E731
    pipx = updates.method(tmp_path / "orkcraft", prefix="/home/a/.local/share/pipx/venvs/orkline", which=has)
    assert pipx.steps == (("pipx", "upgrade", "orkline"),)
    monkeypatch.setattr(updates, "_direct_url", lambda: "")
    monkeypatch.setattr(updates, "_from_pypi", lambda: True)
    pip = updates.method(tmp_path / "orkcraft", prefix="/usr", which=lambda n: None)
    assert pip.kind == "pip" and pip.steps[0][-1] == "orkline"


def test_orkboard_is_never_the_pypi_copy():
    profile.use(ORKBOARD)
    assert ORKBOARD.pypi == "" and not updates._from_pypi()


def test_homebrew_upgrades_with_brew_and_restarts_under_opt(tmp_path, monkeypatch):
    profile.use(ORKLINE)
    pkg = tmp_path / "site" / "orkcraft"
    has = lambda name: "/opt/homebrew/bin/" + name   # noqa: E731
    brew = updates.method(pkg, prefix="/opt/homebrew/Cellar/orkcraft/0.2.1/libexec", which=has)
    assert brew.kind == "brew" and brew.steps == (("/opt/homebrew/bin/brew", "update", "--quiet"),
                                                  ("/opt/homebrew/bin/brew", "upgrade", "orkcraft/orkcraft/orkcraft"))
    assert brew.python == "/opt/homebrew/opt/orkcraft/libexec/bin/python"
    monkeypatch.setenv("HOMEBREW_PREFIX", "/home/linuxbrew/.linuxbrew")
    opt = updates.method(pkg, prefix="/home/linuxbrew/.linuxbrew/opt/orkcraft/libexec", which=has)
    assert opt.kind == "brew" and opt.python == "/home/linuxbrew/.linuxbrew/opt/orkcraft/libexec/bin/python"
    nowhere = tmp_path / "brew"                         # a Homebrew with no brew in it, whatever this machine has
    missing = updates.method(pkg, prefix=str(nowhere / "Cellar/orkcraft/0.2.1/libexec"), which=lambda n: None)
    assert not missing.can and "brew upgrade orkcraft/orkcraft/orkcraft" in missing.why
    runs = Runs(version="9.0.0")
    assert updates.install(brew, runs).ok and runs.calls[-1][0] == brew.python   # the new version, read under opt/
    seen = []
    monkeypatch.delenv(updates.UPDATED_ENV, raising=False)
    updates.restart(["gui"], "9.0.0", execv=lambda exe, args: seen.append(exe), python=brew.python)
    assert seen == [brew.python]


def test_a_product_with_no_formula_says_what_to_run_under_homebrew(tmp_path):
    profile.use(ORKBOARD)
    way = updates.method(tmp_path / "orkboard", prefix="/opt/homebrew/Cellar/orkboard/0.1.0/libexec",
                         which=lambda n: "/bin/" + n)
    assert not way.can and "no formula of Orkboard" in way.why and ORKBOARD.manual in way.why


def test_a_copy_from_elsewhere_says_what_to_run(product, tmp_path, monkeypatch):
    monkeypatch.setattr(updates, "_direct_url", lambda: "")
    monkeypatch.setattr(updates, "_from_pypi", lambda: False)
    way = updates.method(tmp_path / "site" / product.package, prefix="/usr", which=lambda n: None)
    assert not way.can and product.source in way.why
    github = product.source.removeprefix("git+")
    monkeypatch.setattr(updates, "_direct_url", lambda: github)
    pip = updates.method(tmp_path / "site" / product.package, prefix="/usr", which=lambda n: None)
    assert pip.kind == "pip" and pip.steps[0][-1] == f"{product.package} @ {product.source}"


def test_an_install_runs_each_step_and_reads_the_new_version(product):
    way = updates.Method("pipx", (("pipx", "upgrade", product.package),))
    runs = Runs(version="9.0.0")
    result = updates.install(way, runs)
    assert result.ok and result.version == "9.0.0" and runs.calls[0] == ["pipx", "upgrade", product.package]
    assert f"import {product.package}; print({product.package}.__version__)" in runs.calls[-1]


def test_an_install_that_fails_or_changes_nothing_is_not_ok(product):
    way = updates.Method("pipx", (("pipx", "upgrade", product.package),))
    failed = updates.install(way, Runs(fail="pipx"))
    assert not failed.ok and "no network" in failed.output
    same = updates.install(way, Runs(version=product.version))
    assert not same.ok and f"still {product.version}" in same.output


def test_a_checkout_with_changes_or_off_main_is_left_alone(product, tmp_path):
    way = updates.Method("git", (("git", "pull", "--ff-only"),), cwd=str(tmp_path))
    dirty = Runs(status=f" M {product.package}/cli.py\n")
    assert not updates.install(way, dirty).ok and ["git", "pull", "--ff-only"] not in dirty.calls
    branch = Runs(branch="my-feature")
    result = updates.install(way, branch)
    assert not result.ok and "my-feature" in result.output and ["git", "pull", "--ff-only"] not in branch.calls
    assert updates.install(way, Runs()).ok


# -- when the product opens ---------------------------------------------------------------------

def launch(tmp_path, policy, rels, runs=None, monkeypatch=None, can=True):
    said, execs = [], []
    package = profile.current().package
    way = updates.Method("pipx", (("pipx", "upgrade", package),)) if can else updates.Method("none", why="no way")
    monkeypatch.setattr(updates, "method", lambda: way)
    found = updates.at_launch(["gui"], policy, say=said.append, now=10.0, file=tmp_path / "s.json",
                              read=lambda: manifest(*rels), run=runs or Runs(), execv=lambda *a: execs.append(a))
    return found, said, execs


def test_a_critical_update_installs_and_restarts_before_the_product_loads(on, product, tmp_path, monkeypatch):
    runs = Runs(version="9.0.0")
    found, said, execs = launch(tmp_path, "critical", [("9.0.0", True)], runs, monkeypatch)
    assert found is None and ["pipx", "upgrade", product.package] in runs.calls
    assert execs and execs[0][1][-1] == "gui" and execs[0][1][1:3] == ["-m", product.entry]
    assert any("critical update 9.0.0" in line for line in said)
    assert os.environ.get(updates.UPDATED_ENV) == "9.0.0"


def test_an_ordinary_update_waits_unless_the_policy_is_auto(on, product, tmp_path, monkeypatch):
    found, said, execs = launch(tmp_path, "critical", [("9.0.0", False)], monkeypatch=monkeypatch)
    assert found.version == "9.0.0" and not execs and not said
    found, _, execs = launch(tmp_path / "b", "auto", [("9.0.0", False)], monkeypatch=monkeypatch)
    assert found is None and execs


def test_ask_installs_nothing_even_critical(on, product, tmp_path, monkeypatch):
    found, said, execs = launch(tmp_path, "ask", [("9.0.0", True)], monkeypatch=monkeypatch)
    assert found.critical and not execs and not said


def test_a_failed_install_lets_the_product_open_and_waits_a_day(on, product, tmp_path, monkeypatch):
    found, said, execs = launch(tmp_path, "critical", [("9.0.0", True)], Runs(fail="pipx"), monkeypatch)
    assert found.version == "9.0.0" and not execs and any("did not install" in line for line in said)
    assert any(f"{product.name} opens on {product.version}" in line for line in said)
    assert updates.load_state(tmp_path / "s.json").failed_version == "9.0.0"
    runs = Runs()
    again = updates.at_launch(["gui"], "critical", say=said.append, now=20.0, file=tmp_path / "s.json",
                              read=lambda: manifest(("9.0.0", True)), run=runs, execv=lambda *a: None)
    assert again.version == "9.0.0" and runs.calls == []


def test_a_critical_update_that_cannot_install_itself_is_said(on, product, tmp_path, monkeypatch):
    found, said, execs = launch(tmp_path, "critical", [("9.0.0", True)], monkeypatch=monkeypatch, can=False)
    assert found.critical and not execs and "no way" in said[0]


def test_the_restarted_process_never_installs_again(on, product, tmp_path, monkeypatch):
    monkeypatch.setenv(updates.UPDATED_ENV, "9.0.0")
    found, said, execs = launch(tmp_path, "auto", [("9.0.0", True)], monkeypatch=monkeypatch)
    assert found is None and not execs and not said


def test_the_restart_runs_the_same_command(product, monkeypatch):
    seen = []
    monkeypatch.delenv(updates.UPDATED_ENV, raising=False)
    monkeypatch.setattr(updates, "method", lambda: updates.Method("none"))
    updates.restart(["gui", "--browser"], "9.0.0", execv=lambda exe, args: seen.append((exe, args)))
    assert seen == [(sys.executable, [sys.executable, "-m", product.entry, "gui", "--browser"])]


def test_no_product_no_update():
    profile._current = None
    with pytest.raises(RuntimeError, match="profile.use"):
        updates.url()
