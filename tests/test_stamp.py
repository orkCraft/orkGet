"""The copy (orkget/stamp.py, docs/specs/41-orkget.md §2.3): written into a product's package and stamped;
a file changed, added or missing there is named; a folder of the product's own is never replaced."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from orkget import stamp

ROOT = Path(__file__).resolve().parents[1]


def _product(tmp_path: Path) -> Path:
    pkg = tmp_path / "product" / "orkthing"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text('__version__ = "1.0.0"\n')
    return pkg


def test_a_copy_holds_the_modules_the_schemas_and_the_installer_and_is_stamped(tmp_path):
    into = _product(tmp_path) / "orkget"
    made = stamp.copy(ROOT, into)
    assert made["from"] == "orkWorks/orkGet" and made["version"] == __import__("orkget").__version__
    assert {"updates.py", "usage.py", "crashes.py", "consent.py", "profile.py", "stamp.py", "__init__.py",
            "install.sh", "schemas/common.json", "schemas/install.json", "schemas/orkline.json",
            "schemas/orkboard.json", "schemas/orkmine.json"} <= set(made["files"])
    assert json.loads((into / "ORKGET.json").read_text()) == made
    assert stamp.problems(into) == []
    assert (into / "install.sh").read_bytes() == (ROOT / "install.sh").read_bytes()


def test_a_change_an_addition_or_a_loss_by_hand_is_named(tmp_path):
    into = _product(tmp_path) / "orkget"
    stamp.copy(ROOT, into)
    with (into / "usage.py").open("a") as f:
        f.write("# a fix made here\n")
    (into / "mine.py").write_text("")
    (into / "schemas" / "orkboard.json").unlink()
    (into / "__pycache__").mkdir()
    (into / "__pycache__" / "usage.cpython-312.pyc").write_bytes(b"")
    said = stamp.problems(into)
    assert said == ["missing: schemas/orkboard.json", "changed: usage.py (a change is made in orkGet, then copied)",
                    "added: mine.py"]


def test_a_copy_without_its_stamp_is_said(tmp_path):
    into = _product(tmp_path) / "orkget"
    stamp.copy(ROOT, into)
    (into / "ORKGET.json").write_text("{")
    assert "ORKGET.json is missing or broken" in stamp.problems(into)[0]


def test_a_folder_of_the_products_own_is_never_replaced(tmp_path):
    pkg = _product(tmp_path)
    with pytest.raises(ValueError, match="not a copy"):
        stamp.copy(ROOT, pkg)
    assert (pkg / "__init__.py").exists()
    with pytest.raises(ValueError, match="not a checkout of orkGet"):
        stamp.copy(pkg, tmp_path / "x")


def test_a_copy_taken_again_replaces_the_old_one(tmp_path):
    into = _product(tmp_path) / "orkget"
    stamp.copy(ROOT, into)
    (into / "gone.py").write_text("")
    (into / "ORKGET.json").write_text(json.dumps({**json.loads((into / "ORKGET.json").read_text()),
                                                  "files": {"gone.py": "0"}}))
    stamp.copy(ROOT, into)
    assert not (into / "gone.py").exists() and stamp.problems(into) == []


def test_the_command_from_orkget_and_from_a_products_copy(tmp_path):
    into = _product(tmp_path) / "orkget"
    done = subprocess.run([sys.executable, "-m", "orkget.stamp", str(into)], cwd=ROOT, capture_output=True,
                          text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    assert "copied to" in done.stdout and stamp.problems(into) == []
    (into / "usage.py").write_text("changed")
    again = subprocess.run([sys.executable, "-m", "orkthing.orkget.stamp", str(ROOT)], cwd=into.parents[1],
                           capture_output=True, text=True, timeout=60)
    assert again.returncode == 0, again.stderr
    assert stamp.problems(into) == []
