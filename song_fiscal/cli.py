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


def _run_report(
    report_path: Path,
    sources_df: pd.DataFrame,
    records_df: pd.DataFrame,
    conflict_df: pd.DataFrame,
    gap_df: pd.DataFrame,
    backtrace_df: pd.DataFrame | None = None,
) -> None:
    lines = ["# Run Report", ""]
    lines.append("## Source Summary")
    tier_counts = Counter(sources_df.get("tier", []))
    lines.append(f"- Sources fetched: {len(sources_df)}")
    lines.append(f"- Tier distribution: {dict(tier_counts)}")
    lines.append("")

    lines.append("## Metric Hit Summary")
    mcounts = records_df.groupby("metric").size().to_dict() if not records_df.empty else {}
    lines.append(f"- Metric hits: {mcounts}")
    coverage = records_df.groupby("period")["metric"].nunique().to_dict() if not records_df.empty else {}
    lines.append(f"- Period coverage (#metric types): {coverage}")
    lines.append("")

    lines.append("## Conflict Summary")
    top_conf = conflict_df.groupby("metric").size().sort_values(ascending=False).head(5).to_dict() if not conflict_df.empty else {}
    lines.append(f"- Top conflict metrics: {top_conf}")
    lines.append("")

    lines.append("## Gap Summary")
    top_gap = gap_df.groupby(["period", "metric"]).size().sort_values(ascending=False).head(10)
    lines.append("- Top period×metric gaps:")
    for (period, metric), cnt in top_gap.items():
        lines.append(f"  - {period} × {metric}: {cnt}")
    lines.append("")

    if backtrace_df is not None:
        lines.append("## Backtrace Summary")
        success = 0 if backtrace_df.empty else (backtrace_df["backtrace_status"] == "matched").mean()
        lines.append(f"- Backtrace records: {len(backtrace_df)}")
        lines.append(f"- Success rate: {success:.2%}")
        diff = backtrace_df["difference_note"].value_counts().to_dict() if not backtrace_df.empty else {}
        lines.append(f"- Difference stats: {diff}")

    report_path.write_text("\n".join(lines), encoding="utf-8")


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

    output_dir = Path(config["project"].get("output_dir", "outputs"))
    output_dir.mkdir(parents=True, exist_ok=True)

    fetched = fetch_sources(config)
    normalizer = TextNormalizer(synonym_lexicon)
    qplans = build_query_plans(config, synonym_lexicon)

    records = []
    for idx, src in enumerate(fetched):
        normalized = normalizer.normalize(src.text)
        meta = src.entry.to_dict()
        recs = build_records(
            normalized_text=normalized,
            raw_text=src.text,
            source_meta={
                "source_id": meta["source_id"],
                "tier": meta["tier"],
                "book": meta["book"],
                "url": meta["url"],
                "anchor": meta["anchor"],
            },
            query_plan=qplans,
            config=config,
            unit_map=unit_map,
            gazetteer_path="song_fiscal/config/place_gazetteer.csv",
            north_south_map_path="song_fiscal/config/north_south_map.csv",
            offset_seed=round_id * 100000 + idx * 1000,
        )
        # 主面板仅Tier A/B
        if meta["tier"] in {"TIER A", "TIER B"}:
            records.extend(recs)

    records_df = pd.DataFrame([r.to_dict() for r in records])
    records_df = derive_ratios(records_df) if not records_df.empty else records_df

    sources_df = pd.DataFrame([s.entry.to_dict() for s in fetched])
    conflict_df = build_conflict_log(records_df)

    panel_nat = build_national_period_panel(records_df)
    panel_reg = build_grainflow_region_period_panel(records_df)
    gap_df = build_gap_list(config["periods"], config["metrics"], panel_nat, panel_reg)

    secondary_df = pd.DataFrame()
    backtrace_df = pd.DataFrame()
    if enable_backtrace:
        secondary = [s for s in fetched if s.entry.tier == "TIER C"]
        secondary_df = pd.DataFrame(
            [
                {
                    "secondary_lead_id": f"SEC-{i}",
                    "source_id": s.entry.source_id,
                    "url": s.entry.url,
                    "lead_excerpt": s.text[:300],
                }
                for i, s in enumerate(secondary)
            ]
        )
        hints = build_backtrace_query_plan([s.text for s in secondary])
        rows = []
        for i, row in secondary_df.iterrows():
            matched = any(h in row["lead_excerpt"] for h in hints)
            rows.append(
                {
                    "secondary_lead_id": row["secondary_lead_id"],
                    "primary_record_id": records_df.iloc[0]["primary_record_id"] if matched and not records_df.empty else "NA",
                    "backtrace_status": "matched" if matched and not records_df.empty else "unmatched",
                    "difference_note": "no_numeric_alignment_checked" if matched else "no_primary_anchor",
                }
            )
        backtrace_df = pd.DataFrame(rows)

    excel_path = output_dir / "song_fiscal_panel.xlsx"
    sheets = {
        "Panel_National_Period": panel_nat,
        "Panel_Grainflow_Region_Period": panel_reg,
        "Records_Long": records_df,
        "Sources_Registry": sources_df,
        "Conflict_Log": conflict_df,
        "Gap_List": gap_df,
    }
    if enable_backtrace:
        sheets["Secondary_Leads"] = secondary_df
        sheets["Backtrace_Map"] = backtrace_df

    export_panel_excel(str(excel_path), sheets)
    _run_report(output_dir / "Run_Report.md", sources_df, records_df, conflict_df, gap_df, backtrace_df if enable_backtrace else None)

    click.echo(f"Run round={round_id} done. Output: {excel_path}")


if __name__ == "__main__":
    cli()
