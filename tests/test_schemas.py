"""The schemas (schemas/, docs/usage.md): every event is listed once, every rule names a set that exists, and
the installer, the proxy and the products' profiles say the same products, steps and kinds of error."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from orkget import usage
from profiles import ALL

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
COMMON = json.loads((SCHEMAS / "common.json").read_text(encoding="utf-8"))
INSTALL = json.loads((SCHEMAS / "install.json").read_text(encoding="utf-8"))
PRODUCTS = sorted(COMMON["products"])


def _schema(name: str) -> dict:
    return json.loads((SCHEMAS / f"{name}.json").read_text(encoding="utf-8"))


def test_each_product_the_proxy_knows_has_a_file_and_nothing_else_does():
    files = {p.stem for p in SCHEMAS.glob("*.json")} - {"common", "install"}
    assert files == set(PRODUCTS) == {"orkline", "orkboard", "orkwiki"}


@pytest.mark.parametrize("product", PRODUCTS)
def test_every_rule_names_a_set_that_exists(product):
    every = usage.events(product)
    assert set(every) == set(INSTALL["events"]) | set(_schema(product)["events"])


@pytest.mark.parametrize("product", PRODUCTS)
def test_no_event_and_no_set_is_listed_twice(product):
    own = _schema(product)
    assert not set(own["events"]) & set(INSTALL["events"]), "an installer's event in a product's file"
    names = [*COMMON["sets"], *INSTALL["sets"], *own.get("sets", {})]
    assert len(names) == len(set(names)), "a set's name is unique across common, install and the product"


def test_a_rule_that_names_no_set_fails(tmp_path):
    for name in ("common", "install"):
        (tmp_path / f"{name}.json").write_text((SCHEMAS / f"{name}.json").read_text(encoding="utf-8"))
    (tmp_path / "fixture.json").write_text(json.dumps({"events": {"x": {"y": "set:nothing"}}}))
    with pytest.raises(ValueError, match="set:nothing"):
        usage.events("fixture", str(tmp_path))
    for bad in ("sets:counts", "list", 3, {"in": ["a"]}):
        with pytest.raises(ValueError):
            usage.rule(bad, {"counts": ["0"]})


def test_a_failed_step_is_none_or_a_step():
    assert INSTALL["sets"]["failed_steps"] == ["none", *INSTALL["sets"]["steps"]]


def test_the_profiles_say_the_proxys_products_and_agents():
    assert {p.product: p.agent for p in ALL} == {k: v["agent"] for k, v in COMMON["products"].items()}


def test_the_installer_knows_the_same_products_steps_and_errors():
    text = (ROOT / "install.sh").read_text(encoding="utf-8")
    block = text[text.index('case "${PRODUCT:-orkline}" in'):]
    block = block[:block.index("\nesac")]
    said = dict(re.findall(r"PRODUCT=(\w+) .*AGENT=(\w+)", block))
    assert said == {k: v["agent"] for k, v in COMMON["products"].items()}
    assert set(re.findall(r"then echo (\w+)", text)) | {"unknown"} == set(INSTALL["sets"]["errors"])
    sent = set(re.findall(r'^\s*step (\w+) ', text, re.M)) | set(re.findall(r'"step\\": \\"(\w+)\\"', text))
    assert sent == set(INSTALL["sets"]["steps"])


def test_the_proxy_bundles_every_products_schema():
    js = (ROOT / "proxy" / "worker.js").read_text(encoding="utf-8")
    imported = set(re.findall(r'^import \w+ from "\.\./schemas/(\w+)\.json" with \{ type: "json" \};$', js, re.M))
    assert imported == {"common", "install", *PRODUCTS}
    assert "const EVENTS" in js and "TYPES" not in js, "the proxy keeps no list of its own"


def test_what_every_installed_copy_has_written_in_never_changes():
    toml = (ROOT / "proxy" / "wrangler.toml").read_text(encoding="utf-8")
    assert re.search(r'^name = "orkcraft-usage"$', toml, re.M), "the Worker's name is in every copy's address"
    assert usage.ENDPOINT == "https://orkcraft-usage.vadim-sidoryk.workers.dev/v1/events"
    assert {p.product: p.manifest for p in ALL} == {
        "orkline": "https://raw.githubusercontent.com/Orkcraft/orkcraft/main/updates.json",
        "orkboard": "https://raw.githubusercontent.com/Orkcraft/orkboard/main/updates.json",
        "orkwiki": "https://raw.githubusercontent.com/orkWorks/orkWiki/main/updates.json"}
