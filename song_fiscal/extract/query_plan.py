from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass
class QueryPlan:
    metric: str
    keywords: list[str]
    required_terms: list[str]
    optional_terms: list[str]


def build_query_plans(config: dict[str, Any], synonym_lexicon: dict[str, Any], metric_allowlist: list[str] | None = None, keyword_overrides: dict[str, Any] | None = None) -> list[QueryPlan]:
    plans: list[QueryPlan] = []
    metrics = config.get("metrics", {})
    concept_groups = synonym_lexicon.get("concept_groups", {})
    for metric, words in metrics.items():
        if metric_allowlist and metric not in metric_allowlist:
            continue
        expanded = set(words)
        if metric in concept_groups:
            expanded.update(concept_groups[metric])
        for vals in concept_groups.values():
            if metric in vals:
                expanded.update(vals)
        override = (keyword_overrides or {}).get(metric, {})
        required = override.get("required_terms", [])
        optional = override.get("optional_terms", [])
        if optional:
            expanded.update(optional)
        plans.append(QueryPlan(metric=metric, keywords=sorted(expanded), required_terms=required, optional_terms=optional))
    return plans


def build_backtrace_query_plan(lead: dict[str, Any], metric_terms: list[str]) -> dict[str, Any]:
    hint = lead.get("cited_primary_hint", "")
    books = []
    for token in ["宋史", "宋会要辑稿", "续资治通鉴长编", "文献通考"]:
        if token in hint:
            books.append(token)
    period_guess = lead.get("period_guess", "")
    period_terms = re.findall(r"[\u4e00-\u9fff]{2,6}", str(period_guess))
    return {
        "primary_book_candidates": books or ["宋史", "宋会要辑稿"],
        "query_terms": list(dict.fromkeys(metric_terms + period_terms)),
        "required_terms": metric_terms[:1] + period_terms[:1],
        "optional_terms": metric_terms[1:] + period_terms[1:],
    }
