# Spec 41 — orkGet: one installer, one updater, one proxy for Orkline and Orkboard

The owner, 19 October: two products now install from the command line, so the installer and what reports on installs
and runs (the usage stats, the crash reports) leave Orkline for a repository of their own, **orkGet**
(github.com/orkWorks/orkGet), and serve both. Taken into this spec from the PM session's answer: orkGet is the layer
that ships and reports, not a command people run; the release lists stay with each product; nothing changes for a copy
already installed.
**Built:** Claude (A and C elder: the updater, privacy, the live proxy; B and D warrior) · **Review:** full · P1:
A and B may start now (nothing an installed Orkline sees changes); C and D after the testers' week (spec 37 §9) and
release 0.3.0 (Thu 22 October), whose clean-install check (E1, Wed 21 October) runs today's installer.

Wording: CLAUDE.md. **This file is the contract**; the rest is the builder's choice inside its files. It moved here
from Orkline's `docs/specs/` with A's first commit; Orkline's copy points here.

| part | builds | repository | files (and their tests) |
|---|---|---|---|
| **A. orkGet** | §1–§6 | orkWorks/orkGet (new) | `install.sh`, `orkget/` (`__init__.py`, `profile.py`, `updates.py`, `consent.py`, `usage.py`, `crashes.py`, `stamp.py`), `schemas/` (`common.json`, `install.json`, `orkline.json`, `orkboard.json`), `proxy/` (`worker.js`, `wrangler.toml`, `README.md`), `tools/install_banner.py`, `docs/` (`install.md`, `usage.md`, `crashes.md`, `updates.md`, this spec), `CLAUDE.md`, `README.md`, `LICENSE`, `NOTICE`, `.github/workflows/tests.yml`; `tests/test_updates.py`, `test_usage.py`, `test_crashes.py`, `test_installer.py`, `test_schemas.py`, `test_proxy.py`, `test_stamp.py` |
| **B. Orkboard on the copy** | §7 | orkWorks/orkBoard | new `orkboard/orkget/` (the copy), new `orkboard/product.py`, `core/updates.py` (binds the copy), new `core/usage.py`, new `core/crashes.py`, `gui/board_host.py` (`usage`, `update`, the reporter, `crash.window`), `pyproject.toml` (package data), `.github/workflows/tests.yml` (the installer job); `tests/test_updates.py`, new `tests/test_orkget_copy.py`, new `tests/test_crashes.py` |
| **C. The proxy from orkGet** | §8 | orkWorks/orkGet, Cloudflare | `proxy/*`, new `.github/workflows/proxy.yml` (deploys); `tests/test_proxy.py` |
| **D. Orkline on the copy** | §9 | orkWorks/orkLine | new `orkcraft/orkget/` (the copy), new `orkcraft/product.py`, `core/updates.py`, `core/usage.py`, `core/crashes.py` (bind the copy, keep their names), `install.sh` (a forwarder), `tools/usage-worker/` and `tools/install_banner.py` deleted, `pyproject.toml` (package data), `.github/workflows/tests.yml`, `docs/install.md`, `docs/usage-stats.md`, `docs/crash-reports.md`, `docs/updates.md`, `updates.json`; `tests/test_updates.py`, `tests/test_usage.py`, `tests/test_crashes.py`, `tests/test_installer.py` (the product's side only), new `tests/test_orkget_copy.py` |

## 0. The words
- **orkGet**: the repository, and `orkget` its Python package: what puts a product on a machine, keeps it up to date
  and, with a yes, says how the install and the runs go. **Not a command**: nobody installs or runs `orkget` (§1).
- **a product**: Orkline (`orkline`), Orkboard (`orkboard`) or OrkWiki (`orkwiki`, added 21 October: its case in
  `install.sh`, `schemas/orkwiki.json`, its Sentry DSN `SENTRY_DSN_ORKWIKI`, its profile in the tests). Its **profile** (`orkget.Profile`): the few values in
  which the products differ (§2).
- **the copy**: orkGet's `orkget/`, `schemas/` and `install.sh`, put in a product's package (`orkcraft/orkget/`,
  `orkboard/orkget/`), stamped and never edited there, as orkUI's copy is (spec 40 §2).
- **the proxy**: the Cloudflare Worker between the products and Amplitude and Sentry; today `orkLine/tools/usage-worker/`.
- **one answer**: the yes or no to usage stats and crash reports, one per machine (§4).

## 1. What orkGet is, and what it is not
- **It is** the installer (`install.sh`, for every product), the updater, the usage client, the crash reporter, the
  answer, the schemas of every event, the proxy, and their docs. Python's standard library only, POSIX `sh`;
  Apache-2.0.
- **Public**: the proxy serves `install.sh` from orkGet's `main` (§3), as it serves Orkline's today.
- **Not a package manager.** People install a product with one line, brew, uv or pipx, as today; there is no
  `orkget install`. A command of its own waits for a third product and a spec of its own.
- **Not the release lists.** Each product keeps its `updates.json` and its `__version__` where its installed copies
  read them (§6).
- **Not a dependency.** A product carries a copy (§2.3): an orkGet change reaches a product only with a release of that
  product that took the copy, tested by that product's CI. The updater is the one part that cannot be fixed from afar
  once it is broken, so it never ships ahead of the product it updates. `uv.lock` and the Homebrew formula do not
  change.

## 2. The copy and the profile
1. **`orkget/` imports only the standard library and itself** (relative imports), never its product. The product hands
   in what it needs: its profile, its machine settings (anything with `usage` and `install_id`), its `getenv`.
2. **The profile** (`orkget/profile.py`), one per product, in `<package>/product.py` as `PRODUCT`:

   | field | Orkline | Orkboard |
   |---|---|---|
   | `product` · `name` | `orkline` · Orkline | `orkboard` · Orkboard |
   | `package` · `command` | `orkcraft` · `orkcraft` | `orkboard` · `orkboard` |
   | `agent` (the User-Agent; Sentry's release) | `orkcraft` | `orkboard` |
   | `manifest` | `https://raw.githubusercontent.com/Orkcraft/orkcraft/main/updates.json` | `https://raw.githubusercontent.com/Orkcraft/orkboard/main/updates.json` |
   | `source` · `extras` | `git+https://github.com/Orkcraft/orkcraft` · `gui` | `git+https://github.com/Orkcraft/orkboard` · `gui` |
   | `pypi` · `names` | `orkline` · (`orkline`, `orkcraft`) | none · (`orkboard`,) |
   | `manual` | `pipx install --force "orkcraft[gui] @ git+…"` | `uv tool install --force "orkboard[gui] @ git+…"` |
   | `entry` (what a restart runs) | `orkcraft.cli` | `orkboard.gui.board_host` |
   | `state` (the cache's file) | `updates.json` | `orkboard-updates.json` |
   | `brew` (the formula's full name) | `orkcraft/orkcraft/orkcraft` | none |
   | `in_app` (a crash's own frames) | (`orkcraft`,) | (`orkboard`,) |
   | `legacy_files` (session markers with no product in their name) | yes | no |

   These are today's values: the two `core/updates.py` differ only in them. None changes in this spec. A crash file
   and a session marker are named with the product (`crash-orkboard-…`, `session-orkboard-…`), so a product never
   ends another's session; Orkline also reads the markers it wrote before orkGet (`legacy_files`).
3. **The stamp**: `<package>/orkget/ORKGET.json` = `{"from": "orkWorks/orkGet", "version", "commit", "files": {path:
   sha256}}`. `python -m <package>.orkget.stamp <a checkout of orkGet>` replaces the copy and stamps it;
   `stamp.problems()` names a file missing, added or changed by hand. A change is made in orkGet first, then copied.
4. **The product's modules keep their names**: `core/updates.py`, `core/usage.py` and `core/crashes.py` bind the copy to
   `PRODUCT` and export what they export today. No caller changes, and a process that was upgraded under itself still
   finds them.

## 3. The installer (`install.sh`)
- **One script, the product a word**: `--product orkline|orkboard` (default `orkline`), or `?product=` on the proxy's
  `/install.sh` (the proxy writes it into `PRODUCT=""`, as it writes `ROLE` and `LOOK` today).
  `curl -fsSL https://orkcraft.dev/install.sh | sh` installs Orkline, as today.
- **What differs is a `case` on `PRODUCT`**: the profile's values in shell (package, command, source, extras) and the
  banner. The steps, the question, the log and the events are the same for both.
- **Orkline**: the Workchief's banner, `--role` and `--look`, the town opens at the end: today's behaviour.
  **Orkboard**: no banner, no role or look; it ends with "Go to a project and run: orkboard". `--role` or `--look` with
  `--product orkboard` stops before anything is installed.
- **The steps stay** `uv`, `python`, `package`, `version`, `window`, `agents`; the three events (`install_started`,
  `install_step`, `install_finished`) carry `product` in the body (§5.4); `INSTALLER` becomes `installer-2`.
- **The hand-off** is today's: `<command> usage on --id <id>` or `usage off`, for the product installed (§4).
- **A checkout**: `ORKCRAFT_INSTALL_FROM=<folder>` installs that checkout of the product named, so each product's CI
  runs its copy of the script on its own commit (§7, §9).

## 4. One answer
- The answer and the install id stay where they are: the machine settings in `~/.config/orkcraft/`, `"usage":
  {"share", "id"}`, which Orkline and Orkboard already read alike. **One answer per machine covers each product on
  it**, with one install id; once it is answered, no product asks again.
- The question names the product installed and says the answer is the machine's: *Send an anonymous report of how this
  install goes, and later which features of Orkline you use and where it breaks? One answer for this computer.*
  (Orkboard's says its name.) `docs/usage.md` lists the products it covers.
- No forgets the id (today's rule). `DO_NOT_TRACK`, `ORKCRAFT_NO_USAGE`, `CI` and the demo stop everything in every
  product, whatever was answered.

## 5. The events, the schemas, the proxy
1. **Every event is listed once**, in `schemas/`: `common.json` (the buckets: counts, minutes, seconds), `install.json`
   (the installer's three events, its steps and its kinds of error), and one file per product: `orkline.json` (today's
   ten app events, with the building types, the deeds, the tools and the autonomy words), `orkboard.json`
   (`app_opened` and `app_closed` only: Orkboard's own events wait until it is published, decisions §50.1). A
   property's rule is a list of values, `"bool"`, `"set:<name>"` or `"list:<name>"` (a list whose items are in the
   set).
2. **The copy carries the schemas.** The product's `core/usage.py` builds `EVENTS` from them, and the product's tests
   check that each set equals its code's (Orkline: `catalog.TYPES`, `growth.DEEDS`, `settings.TOOLS`,
   `autonomy.WORDS`). A new building type is a commit to orkGet's schema first, then a copy, so the proxy knows an
   event before any release sends it.
3. **The proxy bundles the schemas** (`worker.js` keeps no list of its own) and checks each event by them, as it does
   now.
4. **A product is told by the body's `product`**, read as `orkline` when it is missing (every copy released before D).
   The User-Agent starts with `orkcraft/` or `orkboard/`; anything else is refused, as now. An unknown `product`: 400.
5. **Amplitude**: one project, today's. Each event gets `product` in its properties; event names and `app_version`
   stay as they are.
6. **Sentry**: a project per product. `SENTRY_DSN` stays Orkline's; `SENTRY_DSN_ORKBOARD` is Orkboard's. The release is
   `<agent>@<version>`: `orkcraft@…` keeps Sentry's history of Orkline, `orkboard@…` is new. No DSN for a product: 204,
   dropped. A frame is in-app when its file is under one of the profile's `in_app` packages.
7. **The address stays**: the Worker keeps its name (`orkcraft-usage`), its account and its URL, the one written in
   every installed copy (`ENDPOINT`). `/install.sh` reads orkGet's `main`.

## 6. Updates
- The updater is today's, with the profile in place of its constants; its behaviour does not change: the policies, the
  ways a copy was installed, the restart, the retry after a day, `ORKCRAFT_NO_UPDATE`, `ORKCRAFT_UPDATE_URL`.
- **The release lists never move.** An installed copy reads the URL it was released with. Orkline's
  (`Orkcraft/orkcraft`) answers today through GitHub's redirect to orkWorks/orkLine. Each product's `test_updates.py`
  pins `PRODUCT.manifest`, so it cannot change by accident.
- orkGet's `docs/updates.md` says how a copy updates itself; each product's says how it releases.

## 7. Orkboard on the copy (B)
- `orkboard/orkget/` (the copy), `orkboard/product.py`, and `core/updates.py` bound to it (§2.4).
- **Crash reports**: the reporter starts with the host, as in Orkline; `crash.window` reports the page's errors (today
  it does nothing, `gui/board_host.py`). Each crash is also written to `~/.orkcraft/crashes/`, its file named with the
  product.
- **Usage**: `app_opened` and `app_closed` (§5.1).
- **Commands**: `orkboard usage on|off|status [--id ID]` and `orkboard update [check|auto|critical|ask]`, as Orkline's.
  A folder named `usage` or `update` opens as `orkboard ./usage`.
- **Its CI** gets the installer job: `ORKCRAFT_INSTALL_FROM=. sh orkboard/orkget/install.sh --product orkboard
  --no-report`, then `orkboard --version` and `orkboard usage status`, on Linux and macOS.
- Until C is deployed the proxy refuses `orkboard/` (403): the reports are dropped and the local files stay. Nothing
  else changes for the owner.

## 8. The proxy from orkGet (C)
- After the testers' week and release 0.3.0. `npx wrangler deploy` from orkGet's `proxy/` replaces the Worker deployed
  from `orkLine/tools/usage-worker/`; from then on it is deployed only from orkGet.
- `proxy.yml` deploys it on a push to `main` that changes `proxy/` or `schemas/` (the secret `CLOUDFLARE_API_TOKEN`,
  set by the owner), so a merged schema is a schema the proxy knows.
- **Before the deploy**, `test_proxy.py` sends today's bodies (taken from today's tests: Orkline's events, the
  installer's, a crash, a session; User-Agent `orkcraft/0.2.9`, no `product`) and checks that Amplitude and Sentry get
  what today's Worker sends them, with `product: "orkline"` added. **After it**, today's curl checks
  (`tools/usage-worker/README.md`), once per product.

## 9. Orkline on the copy (D)
- After C. `orkcraft/orkget/` (the copy), `orkcraft/product.py`; `core/updates.py`, `core/usage.py` and
  `core/crashes.py` bound to it (§2.4); `orkcraft usage` and `orkcraft update` unchanged.
- **`install.sh` stays at the root as a forwarder** for the address `docs/install.md` gave
  (`raw.githubusercontent.com/Orkcraft/orkcraft/main/install.sh`): it fetches orkGet's and runs it with
  `--product orkline` and its own options. The CI's installer job runs the copy:
  `ORKCRAFT_INSTALL_FROM=. sh orkcraft/orkget/install.sh --product orkline --no-report`.
- `tools/usage-worker/` and `tools/install_banner.py` are deleted (orkGet has them). `docs/install.md`,
  `usage-stats.md` and `crash-reports.md` shrink to what is Orkline's and a link to orkGet's.
- **With spec 37's "Orkline depends on orkboard"** (a spec of its own, after the testers' week): Orkline's `in_app`
  gets `orkboard`, so the Board's frames count as Orkline's own. Orkline never uses Orkboard's copy.
- A release in `updates.json`, `critical: false`: "Installing, updating and reporting crashes now work the same way for
  Orkline and Orkboard; nothing changes for you."

## Tests
- **A (orkGet):**
  - the updater: today's 30 tests (Orkline's `tests/test_updates.py`) and 29 (Orkboard's), once per profile, unchanged
    but for the profile;
  - the usage client and the reporter: today's `tests/test_usage.py` (all but the window's) and `tests/test_crashes.py`,
    on a profile; an event or a property no schema names is dropped; every body carries `product`;
  - the installer: today's `tests/test_installer.py` for `orkline`, and for `orkboard` its package, its command and no
    banner; `--role` with `--product orkboard` stops first; `?product=orkboard&role=…` written in by the proxy; plain
    POSIX `sh`;
  - the schemas: every rule is a list, `"bool"`, or names a set that exists; no event is in two files;
  - the proxy (Node; skipped without it): today's bodies get today's answers and requests, a missing `product` reads
    as `orkline`; `orkboard/` is taken and goes to `SENTRY_DSN_ORKBOARD`; an unknown product, 400;
  - `stamp`: a copy is written and stamped; a file changed, added or missing is named;
  - each can fail: a fixture schema with `set:nothing` fails the schemas' test; one byte changed in a copied file fails
    `stamp.problems()`; a profile with another `manifest` fails the product's pin.
- **B and D (each product):** `test_orkget_copy.py` (the stamp holds); `test_updates.py` keeps its newest-release check
  and pins `PRODUCT.manifest`; Orkline's sets match its code; the window still counts a road and a building and asks
  once (Orkline's `test_usage.py`); the installer job is green on Linux and macOS; the critical tests (CLAUDE.md
  "Alpha").

## Done when
- orkGet's CI is green, and Orkboard and Orkline run on stamped copies of the same orkGet commit.
- `curl -fsSL https://orkcraft.dev/install.sh | sh` installs Orkline as before; `… | sh -s -- --product orkboard`
  installs Orkboard; each install's events show in Amplitude with its `product`.
- A crash in each product shows in its own Sentry project, as `orkcraft@…` or `orkboard@…`.
- A copy of Orkline released before D (0.2.9) still updates and still sends its events and crashes, untouched.
- Every event, step and kind of error is listed once: in orkGet's `schemas/`.
