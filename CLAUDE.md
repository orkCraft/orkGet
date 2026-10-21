# orkGet — notes for contributors and agents

orkGet installs Orkline, Orkboard and OrkWiki, keeps them up to date and, with a yes, says how the install and the runs go
(docs/specs/41-orkget.md). It serves products; it is never one: no command people run, no window, no package a
product depends on.

## Wording

- In everything a person reads — the installer's lines, the docs, the README — write **ork** / **orks** / **Ork** and
  **orkestration** / **orkestrate**, never "orc" or "orchestration". The products are **Orkline**, **Orkboard** and **OrkWiki**.
- Code keeps its names: identifiers, file names, dict keys, event ids and config values stay as they are. The state
  keeps Orkline's names for every product, so the products read the same settings and the installed copies keep
  working: `~/.config/orkcraft/`, `~/.cache/orkcraft/`, `~/.orkcraft/`, the `ORKCRAFT_*` variables, the User-Agent
  `orkcraft/…`, the Worker `orkcraft-usage`, Sentry's releases `orkcraft@…`.
- Anything about money, privacy or what is sent says plainly what happens.
- Tests that check a visible string use the same wording.

## What never changes (an installed copy depends on it)

- **The proxy's address** (`orkget/usage.py` `ENDPOINT`, `proxy/wrangler.toml` `name`) and **each product's release
  list** (`profile.manifest`): every installed copy has them written in. `tests/` pins them.
- **A body without `product` is Orkline's**: every copy released before orkGet sends one so.
- **Event names and their properties**: a property is removed only when no released copy sends it any more.

## Where code goes

- `orkget/` imports only the standard library and itself (relative imports), never a product. A product hands in what
  differs as its **profile** (`orkget/profile.py`); a module reads it when it works (`profile.current()`), never when
  it is imported.
- A product carries `orkget/`, `schemas/` and `install.sh` as a **copy**, `<package>/orkget/`, stamped by
  `orkget/stamp.py`. A change is made here first, then copied into each product; the copy is never edited there.
- **Every event is listed once**, in `schemas/` (common, install, one file per product). The proxy bundles the same
  files; `worker.js` keeps no list of its own. A new event or value is a commit here first, then the proxy is
  deployed, then the product takes the copy: the proxy knows an event before any release sends it.
- What a report or an event may carry: words from closed lists, buckets, the product's own file paths. Never a path of
  the person's, a name, a prompt, an error's own text, an IP address. `crashes.scrub` and the proxy's checks hold it.
- The installer is plain POSIX `sh` (`dash -n` and `bash -n`); what differs between the products is one `case`.
- Split a module before it grows past ~600 lines.

## Alpha: merge fast, with the critical tests

- While orkGet is in alpha, a change is merged into `main` as soon as the **critical tests** pass: here that is the
  whole suite (`python -m pytest -q`; the proxy's tests need Node). The installer job of CI is not waited for.
- This section is removed when the project leaves alpha.
