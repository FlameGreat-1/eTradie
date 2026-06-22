"""Broker Catalog Registry — control-plane source of truth for
multi-broker MT5 provisioning.

This module loads the versioned broker catalog committed under
``infrastructure/broker-catalog/*.json`` and exposes a validated,
in-memory model the rest of the engine consumes:

  - :func:`load_broker_registry` — read + validate every brand file,
    fail-closed on any violation (raises
    :class:`engine.shared.exceptions.ConfigurationError`).
  - :meth:`BrokerRegistry.resolve` — (brand_id, entity_id) -> the
    entity's bundle reference + server lists, for the
    ``HostedProvisioner`` to layer the broker bundle into a tenant pod.
  - :meth:`BrokerRegistry.list_active` — active brands for the
    dashboard 'Find Broker' wizard API.

Design decisions (see MT5_Multi_Broker_Provisioning_Architecture.md):
  - The catalog is stored as JSON, parsed with ``orjson`` (already a
    core runtime dependency). ``PyYAML`` and ``jsonschema`` are NOT
    declared engine dependencies and are deliberately not introduced;
    validation is performed with Pydantic v2 (also a core dependency),
    whose model mirrors ``infrastructure/broker-catalog/schema.json``
    exactly. ``schema.json`` remains the published, human/CI-facing
    contract; a test asserts the two never drift.
  - ``acquisition_url`` (the broker's own installer URL, used ONCE by a
    human on the bake workstation) is kept strictly separate from
    ``bundle_r2_path`` (the only path the provisioner ever fetches).
    The CI build guard blocks ``download.mql5.com`` as a build arg, so
    an acquisition URL must never leak into a runtime fetch.
  - Validation is fail-closed at engine boot: a malformed or
    contract-violating catalog raises ``ConfigurationError`` rather
    than silently shipping a broken multi-broker surface.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import orjson
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from engine.shared.exceptions import ConfigurationError
from engine.shared.logging import get_logger

logger = get_logger(__name__)

# Repository-root-relative location of the broker catalog. Resolved
# relative to this file so it works from the engine image, pytest, and
# local dev identically:
#   src/engine/ta/broker/registry.py -> parents[4] == repo root.
_DEFAULT_CATALOG_DIR = Path(__file__).resolve().parents[4] / "infrastructure" / "broker-catalog"

# Mirrors schema.json identifier patterns so the loader rejects the
# same shapes the JSON Schema does, even though we validate via Pydantic.
_ID_PATTERN = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_DATE_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")

PlatformType = Literal["mt4", "mt5"]
InstallerPackaging = Literal["unified", "per_entity", "none", "unknown"]
BrandStatus = Literal["active", "pending_bake", "unsupported_mt5", "inactive"]


class EntityServers(BaseModel):
    """Exact server strings extracted from the baked ``servers.dat``.

    Verbatim, every numbered variant; never researched as free text
    (see runbook §6 step 5).
    """

    model_config = ConfigDict(extra="forbid")

    demo: list[str] = Field(default_factory=list)
    live: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _non_empty_and_unique(self) -> EntityServers:
        for field_name, values in (("demo", self.demo), ("live", self.live)):
            for value in values:
                if not value.strip():
                    raise ValueError(f"servers.{field_name} contains an empty string")
            if len(set(values)) != len(values):
                raise ValueError(f"servers.{field_name} contains duplicate entries")
        return self


class PlatformConfig(BaseModel):
    """Platform-specific provisioning configuration (MT4 or MT5)."""

    model_config = ConfigDict(extra="forbid")

    # Human-only acquisition URL; never a runtime fetch path.
    acquisition_url: str | None = None
    # The ONLY path the provisioner pulls from.
    bundle_r2_path: str = Field(min_length=1, max_length=512)
    bundle_sha256: str
    verified_on: str | None = None
    servers: EntityServers

    @model_validator(mode="after")
    def _validate_platform_fields(self) -> PlatformConfig:
        if not _SHA256_PATTERN.match(self.bundle_sha256):
            raise ValueError("bundle_sha256 must be 64 lowercase hex chars")
        if self.verified_on is not None and not _DATE_PATTERN.match(self.verified_on):
            raise ValueError("verified_on must be YYYY-MM-DD")
        if self.acquisition_url is not None and not self.acquisition_url.startswith("https://"):
            raise ValueError("acquisition_url must be an https:// URL")
        return self


class BrokerEntity(BaseModel):
    """A single legal entity under a broker brand."""

    model_config = ConfigDict(extra="forbid")

    entity_id: str
    display_name: str = Field(min_length=1, max_length=120)
    regulator: str | None = Field(default=None, max_length=80)
    platforms: dict[PlatformType, PlatformConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_fields(self) -> BrokerEntity:
        if not _ID_PATTERN.match(self.entity_id):
            raise ValueError(
                f"entity_id {self.entity_id!r} must be lowercase, underscore-separated",
            )
        return self


class BrokerBrand(BaseModel):
    """A broker brand: one file under infrastructure/broker-catalog/."""

    model_config = ConfigDict(extra="forbid")

    brand_id: str
    display_name: str = Field(min_length=1, max_length=100)
    official_website: str
    mt5_supported: bool
    mt4_supported: bool
    installer_packaging: InstallerPackaging
    status: BrandStatus
    notes: str | None = None
    entities: list[BrokerEntity] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_brand(self) -> BrokerBrand:
        if not _ID_PATTERN.match(self.brand_id):
            raise ValueError(
                f"brand_id {self.brand_id!r} must be lowercase, underscore-separated",
            )
        if not self.official_website.startswith("https://"):
            raise ValueError(f"official_website for {self.brand_id!r} must be an https:// URL")

        # Neither supported => no entities; either supported => at least one.
        if not self.mt5_supported and not self.mt4_supported and self.entities:
            raise ValueError(
                f"brand {self.brand_id!r} has neither mt5_supported nor mt4_supported but lists entities",
            )
        if (self.mt5_supported or self.mt4_supported) and not self.entities:
            raise ValueError(
                f"brand {self.brand_id!r} supports MT but lists no entities",
            )

        # Unique entity ids within the brand.
        ids = [e.entity_id for e in self.entities]
        if len(set(ids)) != len(ids):
            raise ValueError(f"brand {self.brand_id!r} has duplicate entity_id values")

        # status:active => every entity is fully provisioned and bootable:
        # a sha-pinned R2 bundle AND at least one live server. This is the
        # gate that makes a half-baked 'active' brand un-loadable.
        if self.status == "active":
            if not self.entities:
                raise ValueError(f"active brand {self.brand_id!r} has no entities")
            for entity in self.entities:
                if not entity.platforms:
                    raise ValueError(f"active brand {self.brand_id!r} entity {entity.entity_id!r} has no platforms configured")
                for platform_id, config in entity.platforms.items():
                    if not config.servers.live:
                        raise ValueError(
                            f"active brand {self.brand_id!r} entity {entity.entity_id!r} "
                            f"platform {platform_id!r} has no live servers",
                        )
        return self

    def entity(self, entity_id: str) -> BrokerEntity | None:
        for e in self.entities:
            if e.entity_id == entity_id:
                return e
        return None


class ResolvedBroker(BaseModel):
    """Flat resolution result the HostedProvisioner consumes."""

    model_config = ConfigDict(extra="forbid")

    brand_id: str
    entity_id: str
    display_name: str
    bundle_r2_path: str
    bundle_sha256: str
    demo_servers: list[str]
    live_servers: list[str]

    def has_server(self, server_name: str) -> bool:
        return server_name in self.demo_servers or server_name in self.live_servers


class BrokerRegistry:
    """Validated, in-memory view of the broker catalog."""

    def __init__(self, brands: list[BrokerBrand]) -> None:
        self._brands: dict[str, BrokerBrand] = {b.brand_id: b for b in brands}

    @property
    def brands(self) -> dict[str, BrokerBrand]:
        return dict(self._brands)

    def list_active(self) -> list[BrokerBrand]:
        """Active brands for the 'Find Broker' wizard."""
        return [b for b in self._brands.values() if b.status == "active" and (b.mt5_supported or b.mt4_supported)]

    def resolve(self, brand_id: str, entity_id: str, platform: str) -> ResolvedBroker:
        """Resolve (brand_id, entity_id, platform) to its bundle + server lists.

        Raises ConfigurationError when the brand/entity/platform is unknown,
        the brand is not active, or the platform is missing from the entity.
        The model_validator already guarantees an active brand's platforms
        carry bundle_r2_path + bundle_sha256 + live servers.
        this is a clear-error lookup, not a re-validation.
        """
        brand = self._brands.get(brand_id)
        if brand is None:
            raise ConfigurationError(
                f"Unknown broker brand_id {brand_id!r}",
                details={"brand_id": brand_id},
            )
        if brand.status != "active":
            raise ConfigurationError(
                f"Broker brand {brand_id!r} is not active (status={brand.status})",
                details={"brand_id": brand_id, "status": brand.status},
            )
        entity = brand.entity(entity_id)
        if entity is None:
            raise ConfigurationError(
                f"Unknown entity_id {entity_id!r} for broker brand {brand_id!r}",
                details={"brand_id": brand_id, "entity_id": entity_id},
            )
        
        # We explicitly type-cast to suppress a pyright warning since we 
        # validate the platform string in HostedProvisioner.
        pf = entity.platforms.get(platform)  # type: ignore
        if pf is None:
            raise ConfigurationError(
                f"Platform {platform!r} is not configured for entity_id {entity_id!r} of brand {brand_id!r}",
                details={"brand_id": brand_id, "entity_id": entity_id, "platform": platform},
            )
            
        return ResolvedBroker(
            brand_id=brand.brand_id,
            entity_id=entity.entity_id,
            display_name=entity.display_name,
            bundle_r2_path=pf.bundle_r2_path,
            bundle_sha256=pf.bundle_sha256,
            demo_servers=list(pf.servers.demo),
            live_servers=list(pf.servers.live),
        )


def _parse_brand_file(path: Path) -> BrokerBrand:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ConfigurationError(
            f"Cannot read broker catalog file {path.name}: {exc}",
            details={"file": str(path)},
        ) from exc
    try:
        data = orjson.loads(raw)
    except orjson.JSONDecodeError as exc:
        raise ConfigurationError(
            f"Broker catalog file {path.name} is not valid JSON: {exc}",
            details={"file": str(path)},
        ) from exc
    if not isinstance(data, dict):
        raise ConfigurationError(
            f"Broker catalog file {path.name} must contain a JSON object",
            details={"file": str(path)},
        )
    try:
        brand = BrokerBrand.model_validate(data)
    except ValidationError as exc:
        raise ConfigurationError(
            f"Broker catalog file {path.name} failed validation: {exc}",
            details={"file": str(path), "errors": exc.errors(include_url=False)},
        ) from exc
    if brand.brand_id != path.stem:
        raise ConfigurationError(
            f"Broker catalog file {path.name} has brand_id {brand.brand_id!r} "
            f"that does not match its filename stem {path.stem!r}",
            details={"file": str(path), "brand_id": brand.brand_id},
        )
    return brand


def load_broker_registry(catalog_dir: Path | None = None) -> BrokerRegistry:
    """Load + validate every brand file in the catalog directory.

    Fail-closed: any unreadable file, malformed JSON, schema violation,
    filename/brand_id mismatch, or duplicate brand_id raises
    ConfigurationError so a broken catalog cannot ship silently.

    A missing or empty catalog directory yields an empty registry (the
    multi-broker surface is simply not yet populated) and is NOT an
    error, so the engine boots cleanly before the first broker is
    onboarded.
    """
    directory = catalog_dir or _DEFAULT_CATALOG_DIR
    if not directory.is_dir():
        logger.info("broker_registry_catalog_dir_absent", extra={"dir": str(directory)})
        return BrokerRegistry([])

    brands: list[BrokerBrand] = []
    seen: set[str] = set()
    # 'schema.json' is the contract, not a brand file; skip it explicitly.
    for path in sorted(directory.glob("*.json")):
        if path.name == "schema.json":
            continue
        brand = _parse_brand_file(path)
        if brand.brand_id in seen:
            raise ConfigurationError(
                f"Duplicate broker brand_id {brand.brand_id!r} across catalog files",
                details={"brand_id": brand.brand_id, "file": str(path)},
            )
        seen.add(brand.brand_id)
        brands.append(brand)

    logger.info(
        "broker_registry_loaded",
        extra={
            "brands_total": len(brands),
            "brands_active": sum(1 for b in brands if b.status == "active" and (b.mt5_supported or b.mt4_supported)),
            "dir": str(directory),
        },
    )
    return BrokerRegistry(brands)
