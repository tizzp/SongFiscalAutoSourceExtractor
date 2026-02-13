from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib


@dataclass
class SourceEntry:
    source_id: str
    tier: str
    book: str
    url: str
    parser: str
    fetched_at: str
    content_hash: str
    anchor: str | None = None
    scope_hint: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def make_source_entry(source_id: str, tier: str, book: str, url: str, parser: str, content: str, anchor: str | None = None, scope_hint: str | None = None) -> SourceEntry:
    digest = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
    fetched_at = datetime.now(timezone.utc).isoformat()
    return SourceEntry(
        source_id=source_id,
        tier=tier,
        book=book,
        url=url,
        parser=parser,
        fetched_at=fetched_at,
        content_hash=digest,
        anchor=anchor,
        scope_hint=scope_hint,
    )
