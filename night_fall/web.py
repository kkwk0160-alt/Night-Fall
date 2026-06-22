from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

logger = logging.getLogger("night_fall.web")

MEMORY_PAGE = Path(__file__).resolve().parent.parent / "memory-page" / "index.html"


def _bucket_to_dict(bucket: dict) -> dict:
    meta = bucket.get("metadata", {})
    content = bucket.get("content", "")
    parsed: dict[str, Any] = {"id": "", "name": "", "tags": [], "valence": -1, "arousal": -1,
                               "pinned": False, "summary": "", "core_facts": [], "date": "",
                               "content": content, "domain": "", "importance": 0}

    parsed["id"] = str(meta.get("id") or bucket.get("id", ""))
    parsed["name"] = str(meta.get("name") or meta.get("bucket_name") or parsed["id"][:12])
    parsed["pinned"] = bool(meta.get("pinned"))
    parsed["importance"] = int(meta.get("importance", 0))
    parsed["domain"] = str(meta.get("domain") or "")

    tags = meta.get("keywords") or meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    parsed["tags"] = tags

    valence = meta.get("valence", -1)
    arousal = meta.get("arousal", -1)
    if isinstance(valence, (int, float)):
        parsed["valence"] = float(valence)
    if isinstance(arousal, (int, float)):
        parsed["arousal"] = float(arousal)

    parsed["date"] = str(meta.get("updated_at") or meta.get("created_at") or "")

    if isinstance(content, str):
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                parsed["summary"] = data.get("summary", "")
                parsed["core_facts"] = data.get("core_facts", [])
                if not parsed["tags"] and data.get("keywords"):
                    kw = data["keywords"]
                    parsed["tags"] = kw if isinstance(kw, list) else [str(kw)]
        except (json.JSONDecodeError, TypeError):
            lines = content.strip().split("\n")
            parsed["summary"] = lines[0][:200] if lines else ""

    return parsed


def create_memory_routes(ombre_server: Any) -> list[Route]:

    async def serve_page(request: Request) -> HTMLResponse:
        if MEMORY_PAGE.exists():
            return HTMLResponse(MEMORY_PAGE.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>memory-page/index.html not found</h1>", status_code=404)

    async def api_memories(request: Request) -> JSONResponse:
        query = request.query_params.get("q", "")
        domain = request.query_params.get("domain", "")
        pinned_only = request.query_params.get("pinned", "").lower() in ("1", "true")
        limit = min(int(request.query_params.get("limit", "50")), 100)

        bucket_mgr = getattr(ombre_server, "bucket_mgr", None)
        if bucket_mgr is None:
            return JSONResponse({"error": "bucket_mgr not available"}, status_code=503)

        try:
            if query:
                embedding_engine = getattr(ombre_server, "embedding_engine", None)
                if embedding_engine and getattr(embedding_engine, "enabled", False):
                    results = await bucket_mgr.search(query, max_results=limit)
                    buckets = results if isinstance(results, list) else []
                else:
                    all_buckets = await bucket_mgr.list_all(include_archive=False)
                    q_lower = query.lower()
                    buckets = [b for b in all_buckets
                               if q_lower in json.dumps(b, ensure_ascii=False).lower()][:limit]
            else:
                buckets = await bucket_mgr.list_all(include_archive=False)
        except Exception as exc:
            logger.error(f"Failed to fetch memories: {exc}")
            return JSONResponse({"error": str(exc)}, status_code=500)

        memories = [_bucket_to_dict(b) for b in buckets]

        if domain:
            memories = [m for m in memories if domain.lower() in m["domain"].lower()]
        if pinned_only:
            memories = [m for m in memories if m["pinned"]]

        memories.sort(key=lambda m: (m["pinned"], m["importance"], m["date"]), reverse=True)
        memories = memories[:limit]

        return JSONResponse({"memories": memories, "total": len(memories)})

    async def api_stats(request: Request) -> JSONResponse:
        bucket_mgr = getattr(ombre_server, "bucket_mgr", None)
        if bucket_mgr is None:
            return JSONResponse({"error": "bucket_mgr not available"}, status_code=503)

        try:
            buckets = await bucket_mgr.list_all(include_archive=False)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)

        memories = [_bucket_to_dict(b) for b in buckets]
        total = len(memories)
        pinned = sum(1 for m in memories if m["pinned"])
        vals = [m["valence"] for m in memories if m["valence"] >= 0]
        avg_valence = round(sum(vals) / len(vals), 2) if vals else 0

        tags: dict[str, int] = {}
        for m in memories:
            for t in m["tags"]:
                tags[t] = tags.get(t, 0) + 1
        top_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:10]

        domains: dict[str, int] = {}
        for m in memories:
            d = m["domain"] or "未分类"
            domains[d] = domains.get(d, 0) + 1

        return JSONResponse({
            "total": total,
            "pinned": pinned,
            "avg_valence": avg_valence,
            "top_tags": top_tags,
            "domains": domains,
        })

    return [
        Route("/memory", serve_page),
        Route("/api/memories", api_memories),
        Route("/api/stats", api_stats),
    ]
