"""orkGet: what puts a product on a machine, keeps it up to date and, with a yes, says how it goes.

A product (Orkline, Orkboard, OrkWiki) never depends on this package: it carries a copy of it, `<package>/orkget/`,
stamped and never edited there (`stamp.py`, docs/specs/41-orkget.md §2). The copy imports only the
standard library and itself; the product hands in what differs, its profile:

    from orkcraft.orkget import profile
    PRODUCT = profile.use(profile.Profile(product="orkline", name="Orkline", package="orkcraft", …))

    updates.py    the list of releases, what is offered, what installs by itself, how each kind of install upgrades
    consent.py    the one answer per machine to usage stats and crash reports
    usage.py      the usage stats: the events `schemas/` lists, in batches to the proxy
    crashes.py    the crash reports and each run as a session, to the proxy
    stamp.py      the copy: written into a product, and checked there
"""
__version__ = "0.1.0"
