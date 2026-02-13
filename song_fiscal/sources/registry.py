from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from urllib.parse import urlsplit, urlunsplit


@dataclass
class SourceEntry:
    source_id: str
    tier: str
    book: str
    url: str
    canonical_url: str
    parser: str
    parser_version: str
    fetched_at: str
    content_hash: str
    anchor: str | None = None
    scope_hint: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def make_source_entry(source_id: str, tier: str, book: str, url: str, parser: str, content: str, anchor: str | None = None, scope_hint: str | None = None) -> SourceEntry:
    canonical = _canonicalize_url(url)
    digest = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
    fetched_at = datetime.now(timezone.utc).isoformat()
    return SourceEntry(
        source_id=source_id,
        tier=tier,
        book=book,
        url=url,
        canonical_url=canonical,
        parser=parser,
        parser_version="1.1",
        fetched_at=fetched_at,
        content_hash=digest,
        anchor=anchor,
        scope_hint=scope_hint,
    )


def _canonicalize_url(url: str) -> str:
    parts = urlsplit(url)
    clean_query = "&".join(q for q in parts.query.split("&") if q and not q.startswith(("utm_", "ref=")))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, clean_query, ""))
