from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import click
import pandas as pd
import yaml

from song_fiscal.extract.conflict import build_conflict_log
from song_fiscal.extract.derive import derive_ratios
from song_fiscal.extract.query_plan import build_backtrace_query_plan, build_query_plans
from song_fiscal.extract.record_builder import build_records
from song_fiscal.extract.text_normalize import TextNormalizer
from song_fiscal.panel.build_panel import build_gap_list, build_grainflow_region_period_panel, build_national_period_panel
from song_fiscal.panel.export_excel import export_panel_excel
from song_fiscal.sources.fetch import fetch_sources


def _load_yaml(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _run_report(report_path: Path, sources_df: pd.DataFrame, records_df: pd.DataFrame, conflict_df: pd.DataFrame, gap_df: pd.DataFrame, round_id: int, backtrace_df: pd.DataFrame | None = None) -> None:
    lines = ["# Run Report", ""]
    lines.append(f"## Round {round_id} Summary")
    lines.append(f"- Sources fetched: {len(sources_df)}")
    lines.append(f"- Metric hits: {(records_df.groupby('metric').size().to_dict() if not records_df.empty else {})}")
    cover = records_df.groupby("period")["metric"].nunique().to_dict() if not records_df.empty else {}
    lines.append(f"- Period coverage (#metric): {cover}")
    lines.append("")

    lines.append("## Source Summary")
    tier_counts = Counter(sources_df.get("tier", []))
    lines.append(f"- Tier distribution: {dict(tier_counts)}")
    lines.append("")

    lines.append("## Conflict Summary")
    lines.append(f"- Conflicts: {len(conflict_df)}")
    lines.append("")

    lines.append("## Gap Summary")
    lines.append(f"- Gaps: {len(gap_df)}")
    lines.append(f"- By round: {(gap_df.groupby('round').size().to_dict() if not gap_df.empty else {})}")

    if backtrace_df is not None:
        lines.append("")
        lines.append("## Backtrace Summary")
        succ = 0 if backtrace_df.empty else (backtrace_df["match_status"] == "success").mean()
        lines.append(f"- Backtrace success rate: {succ:.2%}")
        lines.append(f"- Match status: {(backtrace_df['match_status'].value_counts().to_dict() if not backtrace_df.empty else {})}")
        lines.append(f"- Mismatch stats: {(backtrace_df['mismatch_type'].value_counts().to_dict() if not backtrace_df.empty else {})}")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def _build_secondary_leads(fetched: list[Any]) -> pd.DataFrame:
    rows = []
    for i, s in enumerate([x for x in fetched if x.entry.tier == "TIER C"]):
        snippet = s.text[:300]
        rows.append(
            {
                "secondary_lead_id": f"SEC-{i}",
                "secondary_source_id": s.entry.source_id,
                "secondary_url": s.entry.url,
                "secondary_table_title": "unknown",
                "secondary_row_key": f"row-{i}",
                "metric_guess": "commercial_tax" if "商税" in snippet or "商稅" in snippet else "total_tax",
                "period_guess": "unknown",
                "value_raw": None,
                "unit_raw": None,
                "cited_primary_hint": snippet,
                "excerpt": snippet,
                "table_snippet": snippet,
                "confidence_lead": 0.4,
            }
        )
    return pd.DataFrame(rows)


def _backtrace(secondary_df: pd.DataFrame, records_df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if secondary_df.empty or records_df.empty:
        return pd.DataFrame(columns=["secondary_lead_id", "primary_record_id", "match_status", "mismatch_type", "value_secondary_std", "value_primary_std", "unit_std", "delta_abs", "delta_pct", "rationale"])
    tol = float(config.get("backtrace", {}).get("value_tolerance_pct", 0.01))
    rows = []
    for _, lead in secondary_df.iterrows():
        metric = lead["metric_guess"]
        terms = config.get("metrics", {}).get(metric, [metric])
        plan = build_backtrace_query_plan(lead.to_dict(), terms)
        candidates = records_df[records_df["book_title"].isin(plan["primary_book_candidates"]) & (records_df["metric"] == metric)]
        if candidates.empty:
            rows.append({"secondary_lead_id": lead["secondary_lead_id"], "primary_record_id": "NA", "match_status": "fail", "mismatch_type": "metric_mismatch", "value_secondary_std": None, "value_primary_std": None, "unit_std": None, "delta_abs": None, "delta_pct": None, "rationale": "no candidate after metric/book filter"})
            continue
        c = candidates.sort_values("confidence", ascending=False).iloc[0]
        mismatch = ""
        match_status = "candidate"
        if pd.notna(lead.get("value_raw")) and pd.notna(c.get("value_std")):
            delta_abs = abs(float(c["value_std"]) - float(lead["value_raw"]))
            delta_pct = delta_abs / max(abs(float(lead["value_raw"])), 1e-6)
            if delta_pct <= tol:
                match_status = "success"
            else:
                mismatch = "value_mismatch"
        else:
            delta_abs = None
            delta_pct = None
        rows.append(
            {
                "secondary_lead_id": lead["secondary_lead_id"],
                "primary_record_id": c["primary_record_id"],
                "match_status": match_status if not mismatch else "candidate",
                "mismatch_type": mismatch,
                "value_secondary_std": lead.get("value_raw"),
                "value_primary_std": c.get("value_std"),
                "unit_std": c.get("unit_std"),
                "delta_abs": delta_abs,
                "delta_pct": delta_pct,
                "rationale": f"metric={metric};required={plan['required_terms']}",
            }
        )
    return pd.DataFrame(rows)


@click.group()
def cli() -> None:
    """Song fiscal extractor CLI."""


@cli.command()
@click.option("--round", "round_id", default=1, type=int)
@click.option("--enable_backtrace", default=False, type=bool)
@click.option("--config", "config_path", default="song_fiscal/config/example.yaml")
def run(round_id: int, enable_backtrace: bool, config_path: str) -> None:
    config = _load_yaml(config_path)
    synonym_lexicon = _load_yaml("song_fiscal/config/synonym_lexicon.yaml")
    unit_map = _load_yaml("song_fiscal/config/unit_map.yaml")

    round_cfg = config.get("rounds", {}).get(round_id, {})
    output_dir = Path(config["project"].get("output_dir", "outputs"))
    output_dir.mkdir(parents=True, exist_ok=True)

    fetched = fetch_sources(config, allowlist=set(round_cfg.get("sources_allowlist", [])))
    normalizer = TextNormalizer(synonym_lexicon)
    qplans = build_query_plans(
        config,
        synonym_lexicon,
        metric_allowlist=round_cfg.get("metrics_allowlist"),
        keyword_overrides=round_cfg.get("keyword_overrides"),
    )

    records = []
    for src in fetched:
        paragraphs = []
        for p in src.paragraphs:
            raw, normalized = normalizer.normalize_pair(p["text"])
            p2 = dict(p)
            p2["text"] = raw
            p2["normalized_text"] = normalized
            paragraphs.append(p2)
        recs = build_records(
            source_meta={"source_id": src.entry.source_id, "tier": src.entry.tier, "book": src.entry.book, "url": src.entry.url, "anchor": src.entry.anchor},
            paragraphs=paragraphs,
            query_plan=qplans,
            config=config,
            unit_map=unit_map,
            gazetteer_path="song_fiscal/config/place_gazetteer.csv",
            north_south_map_path="song_fiscal/config/north_south_map.csv",
        )
        if src.entry.tier in {"TIER A", "TIER B"}:
            records.extend(recs)

    records_df = pd.DataFrame([r.to_dict() for r in records])
    records_df = derive_ratios(records_df) if not records_df.empty else records_df
    sources_df = pd.DataFrame([s.entry.to_dict() for s in fetched])
    conflict_df = build_conflict_log(records_df)
    panel_nat = build_national_period_panel(records_df)
    panel_reg = build_grainflow_region_period_panel(records_df)
    gap_df = build_gap_list(config["periods"], config["metrics"], panel_nat, panel_reg, config.get("rounds", {}))

    secondary_df = pd.DataFrame()
    backtrace_df = pd.DataFrame()
    if enable_backtrace or config.get("backtrace", {}).get("enable", False):
        secondary_df = _build_secondary_leads(fetched)
        backtrace_df = _backtrace(secondary_df, records_df, config)

    sheets = {
        "Panel_National_Period": panel_nat,
        "Panel_Grainflow_Region_Period": panel_reg,
        "Records_Long": records_df,
        "Sources_Registry": sources_df,
        "Conflict_Log": conflict_df,
        "Gap_List": gap_df,
    }
    if not secondary_df.empty or enable_backtrace:
        sheets["Secondary_Leads"] = secondary_df
        sheets["Backtrace_Map"] = backtrace_df

    excel_path = output_dir / "song_fiscal_panel.xlsx"
    export_panel_excel(str(excel_path), sheets)
    _run_report(output_dir / "Run_Report.md", sources_df, records_df, conflict_df, gap_df, round_id, backtrace_df if (enable_backtrace or config.get("backtrace", {}).get("enable", False)) else None)
    click.echo(f"Run round={round_id} done. Output: {excel_path}")


if __name__ == "__main__":
    cli()
