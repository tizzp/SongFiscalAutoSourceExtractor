from __future__ import annotations

import re
from typing import Any

CN_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
CN_UNITS = {"十": 10, "百": 100, "千": 1000, "万": 10000, "億": 100000000, "亿": 100000000}


def chinese_to_number(raw: str) -> float | None:
    if raw.isdigit():
        return float(raw)
    total = 0
    section = 0
    number = 0
    for ch in raw:
        if ch in CN_DIGITS:
            number = CN_DIGITS[ch]
        elif ch in CN_UNITS:
            unit = CN_UNITS[ch]
            if unit >= 10000:
                section = (section + number) * unit
                total += section
                section = 0
            else:
                section += (number or 1) * unit
            number = 0
    total += section + number
    return float(total) if total > 0 else None


def parse_numbers_with_units(text: str, unit_map: dict[str, Any]) -> list[dict[str, Any]]:
    pattern = re.compile(r"([一二三四五六七八九十百千万億亿兩两〇零\d]{1,12})([贯貫緡缗文石斛斗升成分])")
    out: list[dict[str, Any]] = []
    merged = {}
    merged.update(unit_map.get("currency", {}))
    merged.update(unit_map.get("grain", {}))
    merged.update(unit_map.get("share", {}))

    for m in pattern.finditer(text):
        num_raw, unit_raw = m.group(1), m.group(2)
        value = chinese_to_number(num_raw)
        if value is None:
            continue
        mapping = merged.get(unit_raw, {"normalized_unit": unit_raw, "multiplier": 1})
        out.append(
            {
                "raw_number": num_raw,
                "raw_unit": unit_raw,
                "value": value,
                "normalized_unit": mapping["normalized_unit"],
                "normalized_value": value * float(mapping.get("multiplier", 1)),
                "span": m.span(),
            }
        )
    return out
