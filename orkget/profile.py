"""A product's profile (docs/specs/41-orkget.md §2): the few values in which Orkline, Orkboard and Orkmine differ.

The product makes it once, in `<package>/product.py`, and hands it to its copy before anything else runs:

    PRODUCT = profile.use(profile.Profile(product="orkline", name="Orkline", package="orkcraft",
                                          version=__version__, agent="orkcraft", manifest=…, source=…))

Every module of the copy reads it when it works (`current()`), never when it is imported, so the tests
can try each product in turn. One process runs one product: Orkline's process uses `orkcraft.orkget`,
and Orkboard's copy, `orkboard.orkget`, is another module with a profile of its own.

The environment keeps Orkline's names for every product (both read the same settings): `ORKCRAFT_<NAME>`,
falling back to the older `ORCRAFT_<NAME>` and `MGTUI_<NAME>`.
"""
from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path

PREFIXES = ("ORKCRAFT_", "ORCRAFT_", "MGTUI_")


def getenv(name: str, default: str = "") -> str:
    for prefix in PREFIXES:
        value = os.environ.get(prefix + name)
        if value:
            return value.strip()
    return default.strip()


@dataclass(frozen=True)
class Profile:
    product: str                       # orkline · orkboard · orkmine: a body's `product`, the schema's file name
    name: str                          # Orkline: what a person reads
    package: str                       # orkcraft: the import name, the distribution from git, brew's keg
    version: str                       # the product's __version__
    agent: str                         # orkcraft: the User-Agent's word, and Sentry's release (`orkcraft@0.3.0`)
    manifest: str                      # where the installed copies read the list of releases: never changes
    source: str                        # git+https://github.com/…: what a copy from git installs again
    extras: str = "gui"                # the window's packages; "" for a product played in the terminal
    pypi: str = ""                     # the name on PyPI, "" when it is not there
    names: tuple[str, ...] = ()        # the names pipx or uv may know it by (its environment's folder)
    manual: str = ""                   # what to run when it cannot update itself
    brew: str = ""                     # the formula's full name (`tap/name/formula`), "" when there is none
    entry: str = ""                    # the module a restart runs (`orkcraft.cli`)
    state: str = "updates.json"        # the cache of the list, in ~/.cache/orkcraft/
    in_app: tuple[str, ...] = ()       # the packages whose frames are the product's own in a crash report
    legacy_files: bool = False         # Orkline: it wrote crash files before orkGet, with no product in their name

    def __post_init__(self) -> None:
        if not self.names:
            object.__setattr__(self, "names", (self.package,))
        if not self.in_app:
            object.__setattr__(self, "in_app", (self.package,))
        if not self.entry:
            object.__setattr__(self, "entry", f"{self.package}.cli")
        if not self.manual:
            what = f"{self.package}[{self.extras}]" if self.extras else self.package
            object.__setattr__(self, "manual", f'uv tool install --force "{what} @ {self.source}"')


_current: Profile | None = None


def use(profile: Profile) -> Profile:
    """This process's product from now on."""
    global _current
    _current = profile
    return profile


def current() -> Profile:
    if _current is None:
        raise RuntimeError("orkget has no product: the product calls orkget.profile.use(PRODUCT) first")
    return _current


def package_dir(name: str = "") -> Path | None:
    """Where a package lives: the copy's own product when it is inside it (`<package>/orkget/`), else
    wherever Python finds it; None when it is not there."""
    name = name or current().package
    here = Path(__file__).resolve().parents[1]
    if here.name == name and (here / "__init__.py").is_file():
        return here
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError):
        return None
    if spec is None or not spec.submodule_search_locations:
        return None
    return Path(list(spec.submodule_search_locations)[0]).resolve()
