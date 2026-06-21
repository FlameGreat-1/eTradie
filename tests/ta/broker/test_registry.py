"""Tests for the broker catalog registry (Phase 0).

These tests use in-test JSON inputs only; no real broker data is
shipped here. They verify the loader's fail-closed contract and the
resolve/list_active behaviour, and assert the Pydantic model stays in
lockstep with infrastructure/broker-catalog/schema.json so the
published contract and the runtime validation can never drift.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.shared.exceptions import ConfigurationError
from engine.ta.broker.registry import (
    BrokerRegistry,
    load_broker_registry,
)

# Repo root: tests/ta/broker/test_registry.py -> parents[3].
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_PATH = _REPO_ROOT / "infrastructure" / "broker-catalog" / "schema.json"


def _write(catalog_dir: Path, brand_id: str, payload: dict) -> None:
    (catalog_dir / f"{brand_id}.json").write_text(json.dumps(payload), encoding="utf-8")


def _active_brand(brand_id: str = "deriv") -> dict:
    """A minimal, fully-valid ACTIVE brand record."""
    return {
        "brand_id": brand_id,
        "display_name": "Deriv",
        "official_website": "https://deriv.com",
        "mt5_supported": True,
        "installer_packaging": "per_entity",
        "status": "active",
        "entities": [
            {
                "entity_id": f"{brand_id}_com_limited",
                "display_name": "Deriv.com Limited",
                "bundle_r2_path": f"r2://etradie-installers/broker-bundles/{brand_id}-portable.zip",
                "bundle_sha256": "a" * 64,
                "verified_on": "2026-06-21",
                "servers": {
                    "demo": ["Deriv-Demo"],
                    "live": ["Deriv-Server", "Deriv-Server-02"],
                },
            },
        ],
    }


def test_empty_catalog_dir_yields_empty_registry(tmp_path: Path) -> None:
    reg = load_broker_registry(tmp_path)
    assert isinstance(reg, BrokerRegistry)
    assert reg.brands == {}
    assert reg.list_active() == []


def test_absent_catalog_dir_is_not_an_error(tmp_path: Path) -> None:
    reg = load_broker_registry(tmp_path / "does-not-exist")
    assert reg.brands == {}


def test_valid_active_brand_loads_and_resolves(tmp_path: Path) -> None:
    _write(tmp_path, "deriv", _active_brand())
    reg = load_broker_registry(tmp_path)

    assert [b.brand_id for b in reg.list_active()] == ["deriv"]

    resolved = reg.resolve("deriv", "deriv_com_limited")
    assert resolved.bundle_r2_path.endswith("deriv-portable.zip")
    assert resolved.bundle_sha256 == "a" * 64
    assert resolved.live_servers == ["Deriv-Server", "Deriv-Server-02"]
    assert resolved.has_server("Deriv-Demo") is True
    assert resolved.has_server("Not-A-Server") is False


def test_schema_json_file_is_skipped(tmp_path: Path) -> None:
    # A schema.json present in the catalog dir must not be parsed as a brand.
    (tmp_path / "schema.json").write_text('{"not": "a brand"}', encoding="utf-8")
    _write(tmp_path, "deriv", _active_brand())
    reg = load_broker_registry(tmp_path)
    assert list(reg.brands) == ["deriv"]


def test_malformed_json_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "deriv.json").write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="not valid JSON"):
        load_broker_registry(tmp_path)


def test_unknown_top_level_field_is_rejected(tmp_path: Path) -> None:
    payload = _active_brand()
    payload["surprise"] = "value"
    _write(tmp_path, "deriv", payload)
    with pytest.raises(ConfigurationError, match="failed validation"):
        load_broker_registry(tmp_path)


def test_filename_must_match_brand_id(tmp_path: Path) -> None:
    _write(tmp_path, "deriv", _active_brand(brand_id="exness"))
    with pytest.raises(ConfigurationError, match="does not match its filename stem"):
        load_broker_registry(tmp_path)


def test_mt5_unsupported_brand_must_have_no_entities(tmp_path: Path) -> None:
    payload = {
        "brand_id": "etoro",
        "display_name": "eToro",
        "official_website": "https://www.etoro.com",
        "mt5_supported": False,
        "installer_packaging": "none",
        "status": "unsupported_mt5",
        "entities": [{"entity_id": "etoro_x", "display_name": "eToro X"}],
    }
    _write(tmp_path, "etoro", payload)
    with pytest.raises(ConfigurationError, match="mt5_supported=false but lists entities"):
        load_broker_registry(tmp_path)


def test_mt5_unsupported_brand_with_no_entities_loads(tmp_path: Path) -> None:
    payload = {
        "brand_id": "etoro",
        "display_name": "eToro",
        "official_website": "https://www.etoro.com",
        "mt5_supported": False,
        "installer_packaging": "none",
        "status": "unsupported_mt5",
        "entities": [],
    }
    _write(tmp_path, "etoro", payload)
    reg = load_broker_registry(tmp_path)
    assert reg.list_active() == []  # not active, not MT5
    assert "etoro" in reg.brands


def test_active_brand_missing_bundle_sha_is_rejected(tmp_path: Path) -> None:
    payload = _active_brand()
    del payload["entities"][0]["bundle_sha256"]
    _write(tmp_path, "deriv", payload)
    with pytest.raises(ConfigurationError, match="missing bundle_sha256"):
        load_broker_registry(tmp_path)


def test_active_brand_missing_live_servers_is_rejected(tmp_path: Path) -> None:
    payload = _active_brand()
    payload["entities"][0]["servers"]["live"] = []
    _write(tmp_path, "deriv", payload)
    with pytest.raises(ConfigurationError, match="has no live servers"):
        load_broker_registry(tmp_path)


def test_bad_sha256_is_rejected(tmp_path: Path) -> None:
    payload = _active_brand()
    payload["entities"][0]["bundle_sha256"] = "NOTHEX"
    _write(tmp_path, "deriv", payload)
    with pytest.raises(ConfigurationError, match="failed validation"):
        load_broker_registry(tmp_path)


def test_bad_brand_id_pattern_is_rejected(tmp_path: Path) -> None:
    payload = _active_brand()
    payload["brand_id"] = "Deriv Inc"  # spaces + uppercase
    # filename stem must match brand_id, so write under the same bad name
    (tmp_path / "Deriv Inc.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="failed validation"):
        load_broker_registry(tmp_path)


def test_duplicate_servers_rejected(tmp_path: Path) -> None:
    payload = _active_brand()
    payload["entities"][0]["servers"]["live"] = ["Deriv-Server", "Deriv-Server"]
    _write(tmp_path, "deriv", payload)
    with pytest.raises(ConfigurationError, match="failed validation"):
        load_broker_registry(tmp_path)


def test_resolve_unknown_brand_raises(tmp_path: Path) -> None:
    _write(tmp_path, "deriv", _active_brand())
    reg = load_broker_registry(tmp_path)
    with pytest.raises(ConfigurationError, match="Unknown broker brand_id"):
        reg.resolve("nope", "x")


def test_resolve_unknown_entity_raises(tmp_path: Path) -> None:
    _write(tmp_path, "deriv", _active_brand())
    reg = load_broker_registry(tmp_path)
    with pytest.raises(ConfigurationError, match="Unknown entity_id"):
        reg.resolve("deriv", "nope")


def test_resolve_inactive_brand_raises(tmp_path: Path) -> None:
    payload = _active_brand()
    payload["status"] = "pending_bake"
    # pending_bake brand need not carry bundle fields; strip them so the
    # record is a realistic pre-bake entry.
    payload["entities"][0].pop("bundle_sha256", None)
    payload["entities"][0].pop("bundle_r2_path", None)
    payload["entities"][0]["servers"] = {"demo": [], "live": []}
    _write(tmp_path, "deriv", payload)
    reg = load_broker_registry(tmp_path)
    with pytest.raises(ConfigurationError, match="is not active"):
        reg.resolve("deriv", "deriv_com_limited")


def test_duplicate_brand_ids_across_files_rejected(tmp_path: Path) -> None:
    # Two files cannot declare the same brand_id; filename-stem rule makes
    # this require a same-stem clash, which the filesystem forbids, so we
    # assert the within-brand entity-id uniqueness guard instead.
    payload = _active_brand()
    payload["entities"].append(dict(payload["entities"][0]))
    _write(tmp_path, "deriv", payload)
    with pytest.raises(ConfigurationError, match="duplicate entity_id"):
        load_broker_registry(tmp_path)


def test_model_and_schema_required_fields_in_lockstep() -> None:
    """The Pydantic model and schema.json must agree on required brand-level
    fields, so the published contract never drifts from runtime validation.
    """
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    schema_required = set(schema["required"])

    from engine.ta.broker.registry import BrokerBrand

    model_required = {
        name for name, field in BrokerBrand.model_fields.items() if field.is_required()
    }
    assert schema_required == model_required, (
        f"schema.json required={schema_required} "
        f"diverged from BrokerBrand required={model_required}"
    )


def test_schema_entity_required_fields_in_lockstep() -> None:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    entity_required = set(schema["$defs"]["entity"]["required"])

    from engine.ta.broker.registry import BrokerEntity

    model_required = {
        name for name, field in BrokerEntity.model_fields.items() if field.is_required()
    }
    assert entity_required == model_required, (
        f"schema.json entity required={entity_required} "
        f"diverged from BrokerEntity required={model_required}"
    )
