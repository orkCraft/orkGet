# Updates

Orkline, Orkboard and Orkmine each look for a newer version of themselves and install it, with the same code
([`orkget/updates.py`](../orkget/updates.py), carried by each as its copy). A **critical update** — a fix for something
that loses work or lets harm in — installs by itself the next time the product opens, before anything else loads.
Any other update is offered: the window asks once per version, and `orkcraft update` (or `orkboard update`) installs
it from the terminal.

## What installs by itself

One setting per machine (Settings → *Updates that install by themselves*, or `orkcraft update <policy>`):

| Policy | When the product opens | In the window |
|---|---|---|
| `critical` (default) | a critical update installs, then the product restarts on it | other updates are offered |
| `auto` | every update installs, then the product restarts on it | — |
| `ask` | nothing installs by itself | every update is offered, a critical one loudly |

An install that fails never stops the product from opening: it says why in the terminal, opens on the version it
has, and tries again after a day (or now, with `orkcraft update`).

The window reads the list when it opens and every 6 hours. When it finds a newer version it asks once; **Update and
restart** installs it, and the window closes and opens again on the new code.

## How it installs

With the tool that installed this copy, so its records stay right:

| Installed with | Updates with |
|---|---|
| the installer ([install.md](install.md)), or `uv tool install …` | `uv tool upgrade orkcraft` (`orkboard`) |
| `pipx install "<package>[gui] @ git+…"` | `pipx upgrade orkcraft` (`orkboard`) |
| from PyPI (Orkline only): `uv tool install orkline`, `pipx install orkline` | `uv tool upgrade orkline`, `pipx upgrade orkline` |
| `pip install orkline` (PyPI) | `python -m pip install --upgrade orkline` |
| `pip install "<package> @ git+…"` | `python -m pip install --upgrade "<package> @ git+…"` (the same URL) |
| Homebrew (Orkline only: `brew install orkcraft/orkcraft/orkcraft`) | `brew update && brew upgrade orkcraft/orkcraft/orkcraft` |
| a git checkout (`pip install -e`, `uv run`) | `git pull --ff-only` (then `uv pip install -e .` when `uv` is there) |

A git checkout updates itself only on `main` and only with no changes of its own: a working copy with edits or on
another branch is yours, so the product says what is out and leaves it alone. What differs between the products — the
package, the names pipx or uv know it by, the formula, the command a restart runs — is the product's profile
([`orkget/profile.py`](../orkget/profile.py)).

## Where the list is

Each product's own `updates.json`, read from its `main` where its installed copies were told to read it, which never
changes (`profile.manifest`; each product's `tests/test_updates.py` pins it):

| Product | The list |
|---|---|
| Orkline | `https://raw.githubusercontent.com/orkWorks/orkLine/main/updates.json` |
| Orkboard | `https://raw.githubusercontent.com/orkWorks/orkBoard/main/updates.json` (while it has none, nothing is offered) |
| Orkmine | `https://raw.githubusercontent.com/orkWorks/orkMine/main/updates.json` (while it has none, nothing is offered) |

What was read is kept in `~/.cache/orkcraft/` (`updates.json` for Orkline, `orkboard-updates.json` for Orkboard,
`orkmine-updates.json` for Orkmine). How a product publishes a release is in its own `docs/updates.md`: one commit to
its `main` that raises its `__version__` and adds the release at the top of its `updates.json`; `"critical": true`
only for a security fix or a bug that loses work.

## When nothing is read

`ORKCRAFT_NO_UPDATE=1` turns updates off: the list is never read and nothing installs. Under CI (`CI=true`) and in a
product's demo nothing is read either. Reading the list sends nothing about you: it is a plain download of a public
file, with `orkcraft/<version>` (or `orkboard/<version>`) as its user agent. `ORKCRAFT_UPDATE_URL` reads it from
elsewhere (a fork, a mirror, a `file://` path).
