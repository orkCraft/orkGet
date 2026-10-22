# Crash reports

When something breaks in Orkline, Orkboard or Orkmine, a report says **where in the product's own code** it broke, so
it can be fixed. Crash reports share one answer with the [usage stats](usage.md): **off until you say yes**, one answer
for every product on this computer, in the installer, a product's window or its Settings (`orkcraft usage on|off`).

## What a report holds

- the product (orkline · orkboard · orkmine);
- the error's type (`KeyError`, `TypeError`…) and its message with everything that could be yours taken out: paths,
  URLs, e-mail addresses and anything in quotes become `<path>`, `<url>`, `<email>`, `'…'`;
- the stack: for each line, the file **in the product** (`orkcraft/gui/host.py`, `orkboard/gui/board_host.py`) or the
  library (`websockets/server.py`), the function and the line number. A line in any other file — your project, a
  script of yours — is only `<other>`, with no name;
- where it happened: an error nobody caught, on a thread, in the server's loop, in a command of the window, in the
  product's clock, or in the window's page;
- the product's version, the OS (darwin · linux · windows), the Python version, and the same random install id as the
  usage stats.

**Never sent:** local variables, your code, prompts, what the orks or you wrote, logs, file, project or building
names, your IP address.

At most 20 reports per run, and the same error once.

## Sessions

Each run of a product's window is also a *session*: it starts, and ends as *exited*, *crashed* (an error nobody
caught), or *abnormal* (the process died without closing; found when that product's next run starts — never another
product's). A session carries only its random id, its start, how long it ran and how many errors it had. That is how
we see the share of runs of each version that ended well.

## Where it goes

To the products' own proxy, the same Cloudflare Worker as the usage stats ([proxy/](../proxy/), `POST /v1/crash`). It
checks every field again, keeps only the ones above, drops your IP address and passes the report to
[Sentry](https://sentry.io/), in its EU data centre (Frankfurt): a project per product, its releases
`orkcraft@<version>` for Orkline, `orkboard@<version>` for Orkboard and `orkmine@<version>` for Orkmine.

## On your machine

Whatever you answered, each crash's full traceback is written to `~/.orkcraft/crashes/` (the last 30 of each
product, named `crash-<product>-<time>.txt`), on your machine only: attach one to an issue if you like.
`ORKCRAFT_USAGE_DEBUG=1 orkcraft` prints every report instead of sending it. Nothing is sent while
`DO_NOT_TRACK=1` or `ORKCRAFT_NO_USAGE=1` is set, under CI, or in a product's demo.

The code: [`orkget/crashes.py`](../orkget/crashes.py) (what a report holds, the scrubbing), carried by each product as
its copy, and each product's `js/crashes.js` (the window's errors).
