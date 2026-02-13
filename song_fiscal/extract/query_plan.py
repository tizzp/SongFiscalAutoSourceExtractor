from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class QueryPlan:
    metric: str
    keywords: list[str]


def build_query_plans(config: dict[str, Any], synonym_lexicon: dict[str, Any]) -> list[QueryPlan]:
    plans: list[QueryPlan] = []
    metrics = config.get("metrics", {})
    concept_groups = synonym_lexicon.get("concept_groups", {})
    for metric, words in metrics.items():
        expanded = set(words)
        if metric in concept_groups:
            expanded.update(concept_groups[metric])
        for vals in concept_groups.values():
            if metric in vals:
                expanded.update(vals)
        plans.append(QueryPlan(metric=metric, keywords=sorted(expanded)))
    return plans


def build_backtrace_query_plan(secondary_texts: list[str]) -> list[str]:
    hints: list[str] = []
    for txt in secondary_texts:
        for token in ["宋史", "宋会要辑稿", "食货志", "卷", "志"]:
            if token in txt and token not in hints:
                hints.append(token)
    return hints
