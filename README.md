# orkGet

What installs **Orkline**, **Orkboard** and **Orkmine**, keeps them up to date and, with a yes, says how the install
and the runs go: one installer, one updater, one place for the usage stats and the crash reports, and the proxy behind
them ([docs/specs/41-orkget.md](docs/specs/41-orkget.md)).

```bash
curl -fsSL https://orkcraft.dev/install.sh | sh                            # Orkline
curl -fsSL https://orkcraft.dev/install.sh | sh -s -- --product orkboard   # Orkboard
curl -fsSL https://orkcraft.dev/install.sh | sh -s -- --product orkmine    # Orkmine, played in the terminal
```

| | |
|---|---|
| [`install.sh`](install.sh) | the installer of every product, for macOS and Linux ([docs/install.md](docs/install.md)) |
| [`orkget/`](orkget/) | the Python a product carries as a copy: `updates`, `consent`, `usage`, `crashes`, `profile`, `stamp`; the standard library only |
| [`schemas/`](schemas/) | every event a product or the installer may send, listed once ([docs/usage.md](docs/usage.md)) |
| [`proxy/`](proxy/) | the Cloudflare Worker between the products and Amplitude and Sentry ([proxy/README.md](proxy/README.md)) |

orkGet is not a command people run, and no product depends on it as a package: each carries a stamped copy,
`<package>/orkget/`, taken with `python -m orkget.stamp <product>/<package>/orkget` and never edited there. The
release lists stay with each product ([docs/updates.md](docs/updates.md)).

```bash
uv venv && uv pip install -e ".[dev]"
.venv/bin/python -m pytest -q          # the proxy's tests need Node
```

Apache-2.0.
