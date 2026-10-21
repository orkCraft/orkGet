"""The products' profiles as each writes it in `<package>/product.py` (docs/specs/41-orkget.md §2.2):
the tests run every module of the copy once for each. The values are today's; `version` is a test's."""
from __future__ import annotations

from orkget.profile import Profile

ORKLINE = Profile(
    product="orkline", name="Orkline", package="orkcraft", version="0.3.0", agent="orkcraft",
    manifest="https://raw.githubusercontent.com/Orkcraft/orkcraft/main/updates.json",
    source="git+https://github.com/Orkcraft/orkcraft", pypi="orkline", names=("orkline", "orkcraft"),
    manual='pipx install --force "orkcraft[gui] @ git+https://github.com/Orkcraft/orkcraft"',
    brew="orkcraft/orkcraft/orkcraft", entry="orkcraft.cli", state="updates.json", legacy_files=True)

ORKBOARD = Profile(
    product="orkboard", name="Orkboard", package="orkboard", version="0.1.0", agent="orkboard",
    manifest="https://raw.githubusercontent.com/Orkcraft/orkboard/main/updates.json",
    source="git+https://github.com/Orkcraft/orkboard",
    manual='uv tool install --force "orkboard[gui] @ git+https://github.com/Orkcraft/orkboard"',
    entry="orkboard.gui.board_host", state="orkboard-updates.json")

ORKWATCH = Profile(
    product="orkwatch", name="Orkwatch", package="orkwatch", version="0.1.0", agent="orkwatch",
    manifest="https://raw.githubusercontent.com/orkWorks/orkWatch/main/updates.json",
    source="git+https://github.com/orkWorks/orkWatch",
    manual='uv tool install --force "orkwatch[gui] @ git+https://github.com/orkWorks/orkWatch"',
    entry="orkwatch.gui.watch_host", state="orkwatch-updates.json")

ALL = (ORKLINE, ORKBOARD, ORKWATCH)
