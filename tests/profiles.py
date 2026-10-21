"""The two products' profiles as each writes it in `<package>/product.py` (docs/specs/41-orkget.md §2.2):
the tests run every module of the copy once for each. The values are today's; `version` is a test's."""
from __future__ import annotations

from orkget.profile import Profile

ORKLINE = Profile(
    product="orkline", name="Orkline", package="orkcraft", version="0.3.0", agent="orkcraft",
    manifest="https://raw.githubusercontent.com/orkWorks/orkLine/main/updates.json",
    source="git+https://github.com/orkWorks/orkLine", pypi="orkline", names=("orkline", "orkcraft"),
    manual='pipx install --force "orkcraft[gui] @ git+https://github.com/orkWorks/orkLine"',
    brew="orkcraft/orkcraft/orkcraft", entry="orkcraft.cli", state="updates.json", legacy_files=True)

ORKBOARD = Profile(
    product="orkboard", name="Orkboard", package="orkboard", version="0.1.0", agent="orkboard",
    manifest="https://raw.githubusercontent.com/orkWorks/orkBoard/main/updates.json",
    source="git+https://github.com/orkWorks/orkBoard",
    manual='uv tool install --force "orkboard[gui] @ git+https://github.com/orkWorks/orkBoard"',
    entry="orkboard.gui.board_host", state="orkboard-updates.json")

ALL = (ORKLINE, ORKBOARD)
