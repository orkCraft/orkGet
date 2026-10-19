"""One answer (docs/usage.md): the yes or no to usage stats and crash reports, one per machine.

It lives in the machine's settings, `~/.config/orkcraft/`, as `"usage": {"share", "id"}`, which every
product reads alike: once it is answered, in the installer or in any product, no product asks again.
A yes draws a random install id (or takes the one the installer drew), a no forgets it, so a later yes
starts as a new install. The settings object is the product's: anything with `usage` (None until
answered, then True or False) and `install_id`.

    consent.share(machine, True)          # the operator said yes
    consent.sharing(machine)              # a yes, and an id to send with
    consent.blocked()                     # why nothing leaves this machine whatever was answered, or ""

Nothing is sent while `DO_NOT_TRACK` or `ORKCRAFT_NO_USAGE` is set, or under CI.
`ORKCRAFT_USAGE_DEBUG=1` prints what would be sent instead of sending it.
"""
from __future__ import annotations

import os
import re
import uuid
from typing import Any

from .profile import getenv

ID = re.compile(r"[0-9a-f]{32}")


def _set(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() not in ("", "0", "false", "no")


def blocked() -> str:
    """Why nothing is collected whatever the operator said, or "" when nothing stops it."""
    if _set("DO_NOT_TRACK"):
        return "DO_NOT_TRACK is set"
    if getenv("NO_USAGE") not in ("", "0"):
        return "ORKCRAFT_NO_USAGE is set"
    if _set("CI"):
        return "running under CI"
    return ""


def debug() -> bool:
    return getenv("USAGE_DEBUG") not in ("", "0")


def share(machine: Any, on: bool, install_id: str | None = None) -> None:
    """The operator's answer. Off forgets the install id, so a later yes starts as a new install; a yes
    given to the installer brings the id it drew (install.sh)."""
    machine.usage = bool(on)
    given = install_id if install_id and ID.fullmatch(install_id) else ""
    machine.install_id = (given or machine.install_id or uuid.uuid4().hex) if on else ""


def sharing(machine: Any) -> bool:
    return machine.usage is True and bool(machine.install_id)
