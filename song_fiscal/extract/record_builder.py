from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

from .number_parse import parse_numbers_with_units


@dataclass
class AtomicRecord:
    primary_record_id: str
    source_id: str
    source_tier: str
    book_title: str
    section_path: str
    paragraph_index: int
    paragraph_hash: str
    citation_key: str
    metric: str
    period: str
    time_detail: str
    time_precision: str
    region: str | None
    north_south: str | None
    value_raw: str | None
    unit_raw: str | None
    value_std: float | None
    unit_std: str | None
    parse_confidence: float | None
    parse_notes: str | None
    raw_text: str
    normalized_text: str
    excerpt: str
    context_before: str
    context_after: str
    source_url: str
    source_anchor: str | None
    confidence: float
    context_rule: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _detect_period(text: str, periods: dict[str, Any]) -> tuple[str, str, str]:
    for key, cfg in periods.items():
        for alias in cfg.get("aliases", []):
            if alias in text:
                return key, alias, "era"
    year_match = re.search(r"(10\d{2}|11\d{2})年", text)
    if year_match:
        y = int(year_match.group(1))
        for key, cfg in periods.items():
            if cfg["start_year"] <= y <= cfg["end_year"]:
                return key, f"{y}年", "year"
    return "unknown", "unknown", "dynasty"


def _load_map(csv_path: str, key_col: str, val_col: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    with open(csv_path, encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if idx == 0:
                continue
            parts = line.strip().split(",")
            if len(parts) >= 2:
                mapping[parts[0]] = parts[1]
    return mapping


def build_records(
    source_meta: dict[str, Any],
    paragraphs: list[dict[str, Any]],
    query_plan: list[Any],
    config: dict[str, Any],
    unit_map: dict[str, Any],
    gazetteer_path: str,
    north_south_map_path: str,
) -> list[AtomicRecord]:
    recs: list[AtomicRecord] = []
    periods = config["periods"]
    min_conf = float(config["run"].get("min_confidence", 0.45))
    context_before = int(config.get("extraction", {}).get("context_chars", {}).get("before", 120))
    context_after = int(config.get("extraction", {}).get("context_chars", {}).get("after", 120))

    gaz = _load_map(gazetteer_path, "raw_name", "normalized_name")
    ns_map = _load_map(north_south_map_path, "region", "north_south")

    for paragraph in paragraphs:
        para_raw = paragraph["text"]
        para_norm = paragraph["normalized_text"]
        for p in query_plan:
            if p.required_terms and not all(term in para_norm for term in p.required_terms):
                continue
            if not any(kw in para_norm for kw in p.keywords):
                continue
            excerpt = para_raw
            numbers = parse_numbers_with_units(excerpt, unit_map)
            period, time_detail, precision = _detect_period(excerpt, periods)
            region = None
            for r_raw, r_norm in gaz.items():
                if r_raw in excerpt or r_norm in excerpt:
                    region = r_norm
                    break
            context_rule = "aggregate_marker" if any(marker in excerpt for marker in ["凡", "计", "共", "其数", "岁额", "上供"]) else "weak_syntax"
            confidence = (0.55 if numbers else 0.4) + (0.2 if context_rule == "aggregate_marker" else 0) + (0.1 if period != "unknown" else 0)
            if confidence < min_conf:
                continue
            base = dict(
                source_id=source_meta["source_id"],
                source_tier=source_meta["tier"],
                book_title=source_meta["book"],
                section_path=paragraph["section_path"],
                paragraph_index=paragraph["paragraph_index"],
                paragraph_hash=paragraph["paragraph_hash"],
                citation_key=f"{source_meta['source_id']}::{paragraph['section_path']}::{paragraph['paragraph_index']}",
                metric=p.metric,
                period=period,
                time_detail=time_detail,
                time_precision=precision,
                region=region,
                north_south=ns_map.get(region) if region else None,
                raw_text=para_raw,
                normalized_text=para_norm,
                excerpt=excerpt,
                context_before=para_raw[:context_before],
                context_after=para_raw[-context_after:],
                source_url=source_meta["url"],
                source_anchor=source_meta.get("anchor"),
                confidence=round(confidence, 3),
                context_rule=context_rule,
            )
            if not numbers:
                recs.append(AtomicRecord(primary_record_id=f"PR-{source_meta['source_id']}-{paragraph['paragraph_index']}-{p.metric}", value_raw=None, unit_raw=None, value_std=None, unit_std=None, parse_confidence=None, parse_notes=None, **base))
                continue
            for j, num in enumerate(numbers):
                recs.append(
                    AtomicRecord(
                        primary_record_id=f"PR-{source_meta['source_id']}-{paragraph['paragraph_index']}-{p.metric}-{j}",
                        value_raw=num["value_raw"],
                        unit_raw=num["unit_raw"],
                        value_std=num["value_std"],
                        unit_std=num["unit_std"],
                        parse_confidence=num["parse_confidence"],
                        parse_notes=num["parse_notes"],
                        **base,
                    )
                )
    return recs
