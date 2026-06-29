"""MetaAPI Broker Catalog endpoint.

Route:
    GET /api/broker/metaapi/servers
"""

import asyncio
import hashlib
import json
import os
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from engine.dependencies import Container
from engine.shared.auth import AuthenticatedUser, get_current_user
from engine.shared.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

METAAPI_BASE_URL = "https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai"


@router.get("/api/broker/metaapi/servers")
async def search_metaapi_servers(
    request: Request,
    q: str = Query(..., min_length=2, description="Broker name query"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    container: Container = request.app.state.container

    token = os.environ.get("MT5_METAAPI_TOKEN", "")
    if not token:
        logger.warning("metaapi_token_not_configured_for_search")
        return {"brands": []}

    q_lower = q.lower().strip()
    cache_key = f"etradie:metaapi:search:{q_lower}"

    # 1. Check cache
    cached = await container.cache.get(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except json.JSONDecodeError as exc:
            logger.warning("metaapi_search_cache_decode_failed", extra={"error": str(exc)})

    # 2. Fetch from MetaAPI
    headers = {"auth-token": token, "Accept": "application/json"}

    import urllib.parse

    async def fetch_version(version: int) -> dict[str, list[str]]:
        encoded_q = urllib.parse.quote(q)
        url = f"{METAAPI_BASE_URL}/known-mt-servers/{version}/search?query={encoded_q}"
        try:
            res = await container.http_client.get(
                url,
                provider_name="metaapi_provisioning",
                category="server_search",
                headers=headers,
                timeout_override=10,
            )
            if isinstance(res, dict):
                return res
            return {}
        except Exception as exc:
            logger.warning(
                "metaapi_server_search_failed",
                extra={"version": version, "query": q, "error": str(exc)},
            )
            return {}

    mt5_res, mt4_res = await asyncio.gather(fetch_version(5), fetch_version(4))

    brand_entities: dict[str, dict[str, Any]] = {}

    def process_servers(data: dict[str, list[str]], platform: str):
        for entity_name, servers in data.items():
            if entity_name not in brand_entities:
                brand_entities[entity_name] = {
                    "entity_id": f"metaapi_{hashlib.sha256(entity_name.encode()).hexdigest()[:8]}",
                    "display_name": entity_name,
                    "platforms": {},
                }

            demo_servers = []
            live_servers = []
            for srv in servers:
                s_lower = srv.lower()
                if "demo" in s_lower or "trial" in s_lower or "contest" in s_lower or "sq" in s_lower:
                    demo_servers.append(srv)
                else:
                    live_servers.append(srv)

            brand_entities[entity_name]["platforms"][platform] = {
                "bundle_r2_path": "",
                "bundle_sha256": "",
                "servers": {"demo": demo_servers, "live": live_servers},
            }

    process_servers(mt5_res, "mt5")
    process_servers(mt4_res, "mt4")

    if not brand_entities:
        return {"brands": []}

    # Group into a single BrandRecord
    brand_name = q.capitalize()

    from collections import Counter

    words = [name.split()[0] for name in brand_entities if name.split()]
    if words:
        # Use the most common first word as the brand name (e.g. "Exness B.V." -> "Exness")
        brand_name = Counter(words).most_common(1)[0][0]

    brand_record = {
        "brand_id": f"metaapi_{hashlib.sha256(brand_name.encode()).hexdigest()[:8]}",
        "display_name": f"{brand_name}",
        "official_website": "",
        "mt5_supported": bool(mt5_res),
        "mt4_supported": bool(mt4_res),
        "installer_packaging": "none",
        "status": "active",
        "is_metaapi_only": True,
        "entities": list(brand_entities.values()),
    }

    response_data = {"brands": [brand_record]}

    # 4. Cache and return (24 hours = 86400 seconds)
    try:
        await container.cache.set(cache_key, json.dumps(response_data), ttl_seconds=86400)
    except Exception as exc:
        logger.error("metaapi_search_cache_set_failed", extra={"error": str(exc)})

    return response_data
