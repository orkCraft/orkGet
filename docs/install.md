# The installer

For macOS and Linux, one line puts everything in place:

```bash
curl -fsSL https://orkcraft.dev/install.sh | sh                            # Orkline
curl -fsSL https://orkcraft.dev/install.sh | sh -s -- --product orkboard   # Orkboard
```

[`install.sh`](../install.sh) at the root of this repository is the whole installer, for every product: read it
before you run it. It needs only `sh` and `curl`. Orkline's opens with the Workchief in a terminal, drawn from his
sprite in 12×5 cells (`tools/install_banner.py`; his words beside him only when the terminal is 48 columns or wider;
not with `NO_COLOR` or outside a terminal). Orkboard's has no banner.

Orkline's ends by opening the town. orkcraft.dev hands it the class and look picked there, in the address:

```bash
curl -fsSL https://orkcraft.dev/install/engineer/camp | sh
```

That address redirects to the usage proxy ([proxy/](../proxy/)), which writes the words into the script's
`PRODUCT=""`, `ROLE=""` and `LOOK=""` lines (only words it knows the shape of; anything else leaves them empty):
`…/install.sh?product=orkboard` for Orkboard. The same file is also at
`https://raw.githubusercontent.com/orkWorks/orkGet/main/install.sh`, with options instead:
`… | sh -s -- --role engineer --look camp`.

| Option | |
|---|---|
| `--product orkline\|orkboard` | which product (Orkline when it is not given) |
| `--role ROLE`, `--look camp\|office` | Orkline's: passed to `orkcraft` when the town opens (`orkcraft --help`); with `--product orkboard` they stop the installer before anything is installed |
| `--no-open` | install only; with no terminal (a script, CI) it never opens |
| `--report`, `--no-report` | the question below, answered beforehand |

On Linux without GTK or Qt for Python the product opens in the browser.

## What it does

| Step | What happens |
|---|---|
| `uv` | uses the [uv](https://docs.astral.sh/uv/) that is there and answers, or puts the pinned version in `~/.local/bin` |
| `python` | `uv python install 3.12`: a Python of its own, whatever the system has |
| `package` | `uv tool install "<package>[gui] @ git+https://github.com/Orkcraft/<repository>"` (GitHub's archive of `main` when git does not work, e.g. a Mac without the developer tools): `orkcraft` for Orkline, `orkboard` for Orkboard |
| `version` | `orkcraft --version` (or `orkboard --version`) runs |
| `window` | whether the product gets a window of its own or opens in the browser |
| `agents` | which AI tools are on the PATH: `claude`, `codex`, `agy` |

Each step's command and everything it printed go to `~/.orkcraft/install.log`. When a step fails the installer
stops, says which step, and gives a link to open an issue in the product's repository: attach that file.

A product installed so updates like any uv tool: `orkcraft update`, or `uv tool upgrade orkcraft`
([updates.md](updates.md)). Run the installer again to reinstall.

## The question it asks

In a terminal it asks once whether you send an anonymous report of how the install goes. The answer is also the
answer to the [usage stats](usage.md) and the [crash reports](crashes.md) of every product on this computer
(**one answer per machine**): no product asks again, and a yes keeps the same random install id, so the install
and the first days of use are one install. With no terminal to ask in (a script, `curl | sh` without a tty) nothing
is sent and the product asks later.

- `sh install.sh --report` or `ORKCRAFT_REPORT=1`: yes, without the question.
- `sh install.sh --no-report` or `ORKCRAFT_REPORT=0`: no.
- `DO_NOT_TRACK`, `ORKCRAFT_NO_USAGE` or `CI` set: nothing is sent, whatever was said.
- `ORKCRAFT_USAGE_DEBUG=1` prints each event instead of sending it.

## What is sent after a yes

One event at the start, one per step and one at the end (`install_started`, `install_step`, `install_finished`,
listed with their properties in [usage.md](usage.md)): the product, the step, ok or failed, how long it took as a
bucket, and the kind of error as a word from a closed list. They go to the same proxy as the usage stats, which
keeps only those properties and drops your IP address. **Never sent:** paths, user or project names, the error's
own text, the log.

## For the maintainers

- `ORKCRAFT_INSTALL_FROM=<folder>` installs that checkout of the product named instead of its `main`: each product's
  CI runs its copy of the script (`<package>/orkget/install.sh`) on its own commit, on Linux and macOS. orkGet's own
  CI installs each product from its `main`.
- The steps and kinds of error are listed once, in [`schemas/install.json`](../schemas/install.json);
  `tests/test_schemas.py` checks that the script sends those and no others. What differs between the products is
  the one `case "${PRODUCT:-orkline}"` near the top (and `orkget/profile.py`, `schemas/common.json`, which
  `tests/test_schemas.py` holds to the same products).
- The proxy serves the script at `/install.sh` (from orkGet's `main`, cached 5 minutes); Cloudflare's request counts
  for that path say how many fetched it.
