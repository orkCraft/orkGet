"""The copy (docs/specs/41-orkget.md §2.3): orkGet's `orkget/`, `schemas/` and `install.sh`, put in a
product's package as `<package>/orkget/` and stamped, as orkUI's copy is. Never edited there: a change
is made in orkGet first, then copied.

    python -m orkget.stamp <into>                   # from a checkout of orkGet: write the copy there
    python -m orkcraft.orkget.stamp <orkGet>        # from a product: take its copy again from that checkout
    stamp.problems()                                # in a product's test: [] while the copy is untouched

The stamp, `ORKGET.json`: {"from", "version", "commit", "files": {path: sha256}}. `commit` ends in
`-dirty` when the checkout had changes of its own.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

FROM = "orkWorks/orkGet"
STAMP = "ORKGET.json"
HERE = Path(__file__).resolve().parent


def is_source(folder: Path) -> bool:
    """`folder` is a checkout of orkGet (its `orkget/`, `schemas/` and `install.sh`)."""
    return (folder / "orkget" / "__init__.py").is_file() and (folder / "schemas").is_dir() \
        and (folder / "install.sh").is_file()


def sources(root: Path) -> dict[str, Path]:
    """What a copy holds, by its path in the copy: the modules, the schemas, the installer."""
    files = {p.name: p for p in sorted((root / "orkget").glob("*.py"))}
    files.update({f"schemas/{p.name}": p for p in sorted((root / "schemas").glob("*.json"))})
    files["install.sh"] = root / "install.sh"
    return files


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _commit(root: Path) -> str:
    try:
        head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True,
                              timeout=30)
        dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--", "orkget", "schemas",
                                "install.sh"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return ""
    if head.returncode != 0:
        return ""
    return head.stdout.strip() + ("-dirty" if dirty.stdout.strip() else "")


def _version(root: Path) -> str:
    for line in (root / "orkget" / "__init__.py").read_text(encoding="utf-8").splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def copy(root: Path, into: Path) -> dict:
    """Replace the copy in `into` with orkGet's at `root`, and stamp it. `into` is a copy already, or
    an empty or new folder: never a folder of the product's own."""
    root, into = root.resolve(), into.resolve()
    if not is_source(root):
        raise ValueError(f"{root} is not a checkout of orkGet")
    if into.exists() and any(into.iterdir()) and not (into / STAMP).is_file():
        raise ValueError(f"{into} holds files and no {STAMP}: it is not a copy of orkGet")
    if into.exists():
        shutil.rmtree(into)
    files = sources(root)
    for rel, src in files.items():
        dest = into / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    stamp = {"from": FROM, "version": _version(root), "commit": _commit(root),
             "files": {rel: _sha(into / rel) for rel in sorted(files)}}
    (into / STAMP).write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")
    return stamp


def problems(into: Path | None = None) -> list[str]:
    """What differs from the stamp: a file missing, changed or added by hand. [] when the copy is untouched."""
    into = into or HERE
    try:
        stamp = json.loads((into / STAMP).read_text(encoding="utf-8"))
        listed = stamp["files"]
    except (OSError, ValueError, KeyError, TypeError):
        return [f"{STAMP} is missing or broken: take the copy again (python -m <package>.orkget.stamp <orkGet>)"]
    out = []
    for rel, sha in sorted(listed.items()):
        path = into / rel
        if not path.is_file():
            out.append(f"missing: {rel}")
        elif _sha(path) != sha:
            out.append(f"changed: {rel} (a change is made in orkGet, then copied)")
    for path in sorted(into.rglob("*")):
        rel = path.relative_to(into).as_posix()
        if path.is_file() and rel != STAMP and "__pycache__" not in path.parts and rel not in listed:
            out.append(f"added: {rel}")
    return out


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0 if args and args[0] in ("-h", "--help") else 2
    target = Path(args[0])
    if is_source(HERE.parent):                 # run from orkGet: the argument is where the copy goes
        root, into = HERE.parent, target
    else:                                      # run from a product's copy: the argument is orkGet
        root, into = target, HERE
    try:
        stamp = copy(root, into)
    except ValueError as e:
        print(f"orkget stamp: {e}", file=sys.stderr)
        return 1
    print(f"orkGet {stamp['version']} ({stamp['commit'] or 'no commit'}) copied to {into}: "
          f"{len(stamp['files'])} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
