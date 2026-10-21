# Spec 42 — Orkwatch (orkGet's part)

Orkwatch, the third product (an inbox played as a tower-defence game), has its spec in its own repository:
[orkWorks/orkWatch `docs/specs/42-orkwatch.md`](https://github.com/orkWorks/orkWatch/blob/main/docs/specs/42-orkwatch.md).
**orkGet's part is its §5 (part B):** the profile, `--product orkwatch`, `schemas/orkwatch.json`, `SENTRY_DSN_ORKWATCH`
in the proxy. Spec 41 holds for it unchanged: orkGet is not a command, not a dependency, and a product takes a stamped
copy. Built with this file; the owner creates the Sentry project and sets the secret before the proxy is deployed
(CLAUDE.md, "Where code goes").
