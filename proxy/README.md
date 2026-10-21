# The usage proxy

A Cloudflare Worker between Orkline and Orkboard and Amplitude (usage stats, [docs/usage.md](../docs/usage.md)) and
Sentry (crash reports, [docs/crashes.md](../docs/crashes.md)). It also hands out the installer
([docs/install.md](../docs/install.md)).

```
orkcraft / orkboard ──POST /v1/events──▶ Worker ──▶ Amplitude HTTP API v2 (US), one project, `product` on each event
                      User-Agent: orkcraft/x.y · holds AMPLITUDE_API_KEY (a Worker secret)
                      or orkboard/x.y          · keeps only the events and properties of schemas/
                                               · at most 30 batches a minute per install
                                               · drops the person's IP address
                    ──POST /v1/crash───▶ Worker ──▶ Sentry: Orkline's project (SENTRY_DSN), Orkboard's (SENTRY_DSN_ORKBOARD), OrkWiki's (SENTRY_DSN_ORKWIKI)
curl | sh           ──GET /install.sh──▶ Worker ──▶ orkGet's install.sh from main, ?product=…&role=…&look=… written in
```

A body says its `product` (orkline · orkboard); one without it is Orkline's, as every copy released before orkGet
sends it. The repositories hold only the proxy's address (`orkget/usage.py` `ENDPOINT`), never a key. Whoever runs the
proxy can change the analytics behind it without a release of a product.

**Its name, its account and its address never change**: every installed copy sends to
`https://orkcraft-usage.vadim-sidoryk.workers.dev`. It was deployed from Orkline's `tools/usage-worker/` until orkGet
took it over (docs/specs/41-orkget.md §8); from then on it is deployed only from here.

## The events

`worker.js` keeps no list of its own: it bundles [`schemas/`](../schemas/) (`common.json`, `install.json` and one file
per product), the same files each product's copy carries, and checks every event by them. A new product is a file in
`schemas/`, an entry in `common.json` `products` (its User-Agent's word and its Sentry secret's name) and an `import`
line here; `tests/test_schemas.py` checks all three agree.

An event or a value is added to `schemas/` first; deploy; then the products take the copy and send it. An event the
Worker does not know is dropped.

## Set it up

1. **Amplitude.** Create a project (US data centre, `app.amplitude.com`; for one in the EU data centre,
   `analytics.eu.amplitude.com`, set `AMPLITUDE_REGION = "eu"` in `wrangler.toml`). Project settings → General: copy
   the **API Key**. The **Secret Key** is not needed and stays in Amplitude. In the project's settings, turn off IP
   address and location tracking if offered: the only address Amplitude ever sees is Cloudflare's.
2. **Sentry.** A project per product, platform **Python** (the free Developer plan is enough; open-source projects
   can ask for the sponsored plan). In each project's **Security & Privacy**: turn on *Prevent Storing of IP
   Addresses* and keep *Data Scrubber* on. Project settings → Client Keys (DSN): copy the DSN,
   `https://<key>@o….ingest.<region>.sentry.io/<project>`. The Worker sends to the host the DSN names, so the region
   is the project's: Orkline's is in the EU (`ingest.de.sentry.io`).
3. **Cloudflare.** An account (the free plan is enough), and Node 20+ for `wrangler` 4 (it bundles the schemas'
   JSON imports).
4. **Deploy** from this folder:

   ```bash
   cd proxy
   npx wrangler login
   npx wrangler secret put AMPLITUDE_API_KEY       # paste the API Key: it is stored encrypted in Cloudflare
   npx wrangler secret put SENTRY_DSN              # Orkline's DSN
   npx wrangler secret put SENTRY_DSN_ORKBOARD     # Orkboard's DSN
   npx wrangler secret put SENTRY_DSN_ORKWIKI      # OrkWiki's DSN
   npx wrangler deploy                             # → https://orkcraft-usage.<account>.workers.dev
   ```

   Without a product's DSN its crash reports are answered 204 and dropped. For a domain of your own, uncomment
   `routes` in `wrangler.toml` (the domain must be on Cloudflare).
5. **Check it**, once per product, with an event and a report of your own:

   ```bash
   curl -i https://orkcraft-usage.<account>.workers.dev/v1/events \
     -H 'User-Agent: orkboard/0.0.0' -H 'Content-Type: application/json' \
     -d '{"install_id":"0123456789abcdef0123456789abcdef","product":"orkboard","session_id":1,"app_version":"0.0.0","os":"linux","python":"3.12","events":[{"event":"app_closed","time":0,"props":{"minutes":"<5"}}]}'
   # HTTP/2 204; the event shows in Amplitude → User lookup → device 0123…cdef within a minute

   curl -i https://orkcraft-usage.<account>.workers.dev/v1/crash \
     -H 'User-Agent: orkcraft/0.0.0' -H 'Content-Type: application/json' \
     -d '{"install_id":"0123456789abcdef0123456789abcdef","product":"orkline","app_version":"0.0.0","os":"linux","python":"3.12","items":[{"type":"event","event_id":"0123456789abcdef0123456789abcdef","where":"command","handled":true,"exceptions":[{"type":"TestError","value":"a test from curl","frames":[{"file":"orkcraft/cli.py","function":"main","line":1,"in_app":true}]}]}]}'
   # HTTP/2 204; x-sentry-status: 200 when Sentry took it; it shows in Sentry → Issues within a minute
   ```

   Nothing in Amplitude?
   - `npx wrangler secret list` must show `"name": "AMPLITUDE_API_KEY"`. A secret named after the key itself means
     `secret put` got the key where the name goes: delete it and put it again.
   - Send one event to Amplitude itself, without the Worker: `curl -i https://api2.amplitude.com/2/httpapi
     -H 'Content-Type: application/json' -d '{"api_key":"…","events":[{"device_id":"0123456789abcdef0123456789abcdef","event_type":"road_laid"}]}'`.
     `"invalid api_key"` means a wrong key, or a project in the EU data centre (`api.eu.amplitude.com`,
     `AMPLITUDE_REGION = "eu"`).
   - `npx wrangler tail --format pretty` shows the Worker's requests live while you send one.
   - The Worker's answer may carry `x-amplitude-status` (Amplitude's own answer), but Cloudflare's edge does not
     always pass it on: its absence proves nothing.
   - A change to `wrangler.toml` or `schemas/` counts only after `npx wrangler deploy`.

Releases are `<agent>@<version>` (`orkcraft@0.3.0`, `orkboard@0.1.0`), so Sentry → Releases shows the crash-free
sessions of each version. A git checkout reports as environment `checkout`, an installed copy as `production`.

## The installer

The Worker serves [`install.sh`](../install.sh) at `GET /install.sh`, read from orkGet's `main` and cached 5 minutes:
`curl -fsSL https://orkcraft.dev/install.sh | sh` (orkcraft.dev redirects here). `?product=orkboard` writes the product
into the script's `PRODUCT=""`, `?role=…&look=…` (orkcraft.dev/install/<role>/<look>) Orkline's class and look into
`ROLE=""` and `LOOK=""`; only words it knows the shape of. Cloudflare's dashboard (Workers → this Worker → Metrics)
counts its requests: how many fetched the installer, with no data about who.

## Rotate a key

In Amplitude (or Sentry), create a new key, then `npx wrangler secret put AMPLITUDE_API_KEY` (or the product's
`SENTRY_DSN…`) again. No release of a product is needed.
