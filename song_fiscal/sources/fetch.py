from __future__ import annotations

from dataclasses import dataclass
import hashlib
import logging
from typing import Any

import requests

from .ctext import parse_ctext
from .registry import SourceEntry, make_source_entry
from .wikisource import parse_wikisource

LOGGER = logging.getLogger(__name__)


@dataclass
class FetchedSource:
    entry: SourceEntry
    text: str
    anchors: list[str]
    paragraphs: list[dict[str, Any]]


def _parse(parser: str, html: str) -> tuple[str, list[str], list[dict[str, Any]]]:
    if parser == "ctext":
        text, anchors, paragraphs = parse_ctext(html)
        return text, anchors, [p.to_dict() for p in paragraphs]
    if parser == "wikisource":
        text, anchors, paragraphs = parse_wikisource(html)
        return text, anchors, [p.to_dict() for p in paragraphs]
    return html, [], [{"section_path": "正文", "paragraph_index": 0, "text": html[:5000]}]


def fetch_sources(config: dict[str, Any], allowlist: set[str] | None = None) -> list[FetchedSource]:
    output: list[FetchedSource] = []
    timeout_s = int(config["project"].get("request_timeout_s", 20))
    ua = config["project"].get("user_agent", "SongFiscalExtractor/0.1")

    for tier_key in ("tier_a", "tier_b", "tier_c"):
        for item in config.get("sources", {}).get(tier_key, []):
            if allowlist and item["name"] not in allowlist:
                continue
            url = item["base_url"]
            if item.get("query"):
                url = f"{url}?{item['query']}"
            try:
                resp = requests.get(url, timeout=timeout_s, headers={"User-Agent": ua})
                resp.raise_for_status()
                text, anchors, paragraphs = _parse(item.get("parser", "generic"), resp.text)
                entry = make_source_entry(
                    source_id=item["name"],
                    tier=tier_key.upper().replace("_", " "),
                    book=item.get("book", item["name"]),
                    url=url,
                    parser=item.get("parser", "generic"),
                    content=text,
                    anchor=anchors[0] if anchors else None,
                    scope_hint=item.get("query"),
                )
                paragraph_hashes = [hashlib.sha256(p["text"].encode("utf-8", errors="ignore")).hexdigest() for p in paragraphs]
                for p, h in zip(paragraphs, paragraph_hashes):
                    p["paragraph_hash"] = h
                output.append(FetchedSource(entry=entry, text=text, anchors=anchors, paragraphs=paragraphs))
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Failed source fetch: %s (%s)", url, exc)
    return output
