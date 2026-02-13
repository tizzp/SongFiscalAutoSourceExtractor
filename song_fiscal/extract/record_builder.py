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
    book: str
    metric: str
    period: str
    time_detail: str
    time_precision: str
    region: str | None
    north_south: str | None
    value: float | None
    unit: str | None
    raw_number: str | None
    raw_unit: str | None
    excerpt: str
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
    normalized_text: str,
    raw_text: str,
    source_meta: dict[str, Any],
    query_plan: list[Any],
    config: dict[str, Any],
    unit_map: dict[str, Any],
    gazetteer_path: str,
    north_south_map_path: str,
    offset_seed: int = 0,
) -> list[AtomicRecord]:
    recs: list[AtomicRecord] = []
    periods = config["periods"]
    min_conf = float(config["run"].get("min_confidence", 0.45))
    window = int(config["run"].get("excerpt_window", 40))

    gaz = _load_map(gazetteer_path, "raw_name", "normalized_name")
    ns_map = _load_map(north_south_map_path, "region", "north_south")

    for i, p in enumerate(query_plan):
        for kw in p.keywords:
            start = 0
            while True:
                idx = normalized_text.find(kw, start)
                if idx < 0:
                    break
                span_start = max(0, idx - window)
                span_end = min(len(normalized_text), idx + len(kw) + window)
                excerpt = raw_text[span_start:span_end]
                numbers = parse_numbers_with_units(excerpt, unit_map)
                period, time_detail, precision = _detect_period(excerpt, periods)
                region = None
                for r_raw, r_norm in gaz.items():
                    if r_raw in excerpt or r_norm in excerpt:
                        region = r_norm
                        break
                context_rule = "weak_syntax"
                if any(marker in excerpt for marker in ["凡", "计", "共", "其数", "岁额", "上供"]):
                    context_rule = "aggregate_marker"
                confidence = 0.55 if numbers else 0.4
                if context_rule == "aggregate_marker":
                    confidence += 0.2
                if period != "unknown":
                    confidence += 0.1
                if confidence < min_conf:
                    start = idx + len(kw)
                    continue
                if not numbers:
                    rec = AtomicRecord(
                        primary_record_id=f"PR-{offset_seed+i}-{idx}",
                        source_id=source_meta["source_id"],
                        source_tier=source_meta["tier"],
                        book=source_meta["book"],
                        metric=p.metric,
                        period=period,
                        time_detail=time_detail,
                        time_precision=precision,
                        region=region,
                        north_south=ns_map.get(region) if region else None,
                        value=None,
                        unit=None,
                        raw_number=None,
                        raw_unit=None,
                        excerpt=excerpt,
                        source_url=source_meta["url"],
                        source_anchor=source_meta.get("anchor"),
                        confidence=round(confidence, 3),
                        context_rule=context_rule,
                    )
                    recs.append(rec)
                else:
                    for j, num in enumerate(numbers):
                        rec = AtomicRecord(
                            primary_record_id=f"PR-{offset_seed+i}-{idx}-{j}",
                            source_id=source_meta["source_id"],
                            source_tier=source_meta["tier"],
                            book=source_meta["book"],
                            metric=p.metric,
                            period=period,
                            time_detail=time_detail,
                            time_precision=precision,
                            region=region,
                            north_south=ns_map.get(region) if region else None,
                            value=num["normalized_value"],
                            unit=num["normalized_unit"],
                            raw_number=num["raw_number"],
                            raw_unit=num["raw_unit"],
                            excerpt=excerpt,
                            source_url=source_meta["url"],
                            source_anchor=source_meta.get("anchor"),
                            confidence=round(confidence, 3),
                            context_rule=context_rule,
                        )
                        recs.append(rec)
                start = idx + len(kw)
    return recs
