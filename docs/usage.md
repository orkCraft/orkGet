# Anonymous usage stats

Orkline, Orkboard and Orkwatch can share which of their features are used, so we know what to make better. It is **off until
you say yes**, and **one answer covers every product on this computer**: the installer asks once, or the first
product you open, and no product asks again. Each product's Settings, or `orkcraft usage on|off|status`, change it at
any time, for all of them (the answer lives in `~/.config/orkcraft/`, which they all read).

## What is sent

Each event below, with only the properties listed: every event is listed once, in [`schemas/`](../schemas/). Numbers
go as buckets (`0`, `1`, `2-5`, `6-10`, `11+`), never as exact counts.

### Orkline ([schemas/orkline.json](../schemas/orkline.json))

| Event | When | Properties |
|---|---|---|
| `app_opened` | the window opens | `face` (gui), `tools` (claude · agy · codex · hermes · pi · cursor: the ones you turned on), `buildings`, `roads` (buckets) |
| `app_closed` | the window closes | `minutes` it was open (`<5` · `5-30` · `30-120` · `120+`) |
| `building_built` | you raise a building | `type`: its catalog type (lake, forge, …, custom) |
| `building_demolished` | you demolish one | — |
| `road_laid` | you lay a road | — |
| `session_opened` | you open an ork's CLI session | `harness`: claude · agy · codex · … |
| `deed_earned` | you earn a deed | `deed`: its id (town, road, reference, …) |
| `stage_reached` | your mascot grows | `stage`: 1–4 |
| `autonomy_set` | you change the orks' autonomy | `level`: chains · clock · free |
| `halted` | you press Stop all | — |

### Orkboard ([schemas/orkboard.json](../schemas/orkboard.json))

| Event | When | Properties |
|---|---|---|
| `app_opened` | the window opens | `face` (gui), `tools` |
| `app_closed` | the window closes | `minutes` it was open |

### Orkwatch ([schemas/orkwatch.json](../schemas/orkwatch.json))

| Event | When | Properties |
|---|---|---|
| `app_opened` | the window opens | `face` (gui), `tools` |
| `app_closed` | the window closes | `minutes` it was open |

Orkwatch reads your messages (mail, chat, tasks) on your computer to play them as a game. **None of that is ever
sent**: no message, no sender, no source's name, no rule you wrote.

### The installer, for every product ([schemas/install.json](../schemas/install.json), [install.md](install.md))

| Event | When | Properties |
|---|---|---|
| `install_started` | the installer starts | `method` (sh), `arch` (x86_64 · arm64 · other), `upgrade` (already installed) |
| `install_step` | each of its steps ends | `step` (uv · python · package · version · window · agents), `ok`, `seconds` (`<10` · `10-60` · `60-300` · `300+`); when it failed `error`, a kind: disk_full · permission · tls · network · python_download · resolve_failed · build_failed · git_missing · unknown; and per step `found` (uv was there), `source` (git · archive · local), `window` (native · browser), `tools` (claude · codex · agy found) |
| `install_finished` | the installer ends | `ok`, `seconds`, `failed_step` |

Every batch also carries the product (orkline · orkboard · orkwatch), a random install id (drawn when you say yes, the same for
every product on this computer, forgotten when you say no), when this window was opened, the product's version, the
OS (darwin · linux · windows) and the Python version.

**Never sent:** your code, prompts, what the orks or you wrote, file names, paths, project or building names, git
data, your settings' text, your email, your IP address.

The same answer covers [crash reports](crashes.md): where in a product's code something broke, never what was in it.

## Where it goes

To the products' own proxy, a Cloudflare Worker (its code: [proxy/](../proxy/)), which drops anything not in the
tables above and your IP address, and passes the rest to [Amplitude](https://amplitude.com/) in its US data centre,
one project for both products, each event marked with its product.

## When nothing is collected

Whatever you answered, nothing is collected while `DO_NOT_TRACK=1` or `ORKCRAFT_NO_USAGE=1` is set, under CI
(`CI=true`), or in a product's demo (`orkcraft --demo`).

## See it for yourself

`ORKCRAFT_USAGE_DEBUG=1 orkcraft` (or `orkboard`) prints every batch to the terminal instead of sending it.

## For the maintainers

An event, a property or a value is added in `schemas/` first; the proxy is deployed with it; then the product takes
the copy (`orkget/stamp.py`) and sends it. The product's tests check its sets against its code (Orkline: the catalog's
types, the deeds, the tools, the autonomy words), so a building type added there fails until the schema has it.
