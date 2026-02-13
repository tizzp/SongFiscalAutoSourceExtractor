from __future__ import annotations

import pandas as pd


def build_national_period_panel(records_df: pd.DataFrame) -> pd.DataFrame:
    if records_df.empty:
        return pd.DataFrame(columns=["period", "metric", "value_std", "unit_std", "value_raw_examples", "primary_record_ids", "note"])
    nat = records_df[records_df["region"].isna()].copy()
    nat = nat.dropna(subset=["value_std"])
    rows = []
    for (period, metric), g in nat.groupby(["period", "metric"]):
        top = g.sort_values("confidence", ascending=False).iloc[0]
        rows.append(
            {
                "period": period,
                "metric": metric,
                "value_std": top["value_std"],
                "unit_std": top["unit_std"],
                "value_raw_examples": f"{top['value_raw'] or ''}{top['unit_raw'] or ''}",
                "primary_record_ids": "|".join(g["primary_record_id"].astype(str).head(20).tolist()),
                "note": f"time_precision={top['time_precision']}; tier={top['source_tier']}",
            }
        )
    return pd.DataFrame(rows)


def build_grainflow_region_period_panel(records_df: pd.DataFrame) -> pd.DataFrame:
    if records_df.empty:
        return pd.DataFrame(columns=["period", "region", "north_south", "metric", "value_std", "unit_std", "value_raw_examples", "primary_record_ids", "note"])
    gf = records_df[records_df["metric"].isin(["pingdi_or_hedi", "supply_capital", "supply_frontier"])].dropna(subset=["value_std"])
    rows = []
    for (period, region, metric), g in gf.groupby(["period", "region", "metric"], dropna=False):
        top = g.sort_values("confidence", ascending=False).iloc[0]
        rows.append(
            {
                "period": period,
                "region": region,
                "north_south": top["north_south"],
                "metric": metric,
                "value_std": top["value_std"],
                "unit_std": top["unit_std"],
                "value_raw_examples": f"{top['value_raw'] or ''}{top['unit_raw'] or ''}",
                "primary_record_ids": "|".join(g["primary_record_id"].astype(str).head(20).tolist()),
                "note": f"time_precision={top['time_precision']}; tier={top['source_tier']}",
            }
        )
    return pd.DataFrame(rows)


def build_gap_list(period_cfg: dict, metric_cfg: dict, panel_nat: pd.DataFrame, panel_reg: pd.DataFrame, rounds_cfg: dict) -> pd.DataFrame:
    rows = []
    national_metrics = ["total_tax", "liangshui_share", "commercial_tax", "commercial_share", "commercial_structure"]
    for p in period_cfg.keys():
        for metric in metric_cfg.keys():
            exists = False
            round_name = "1" if metric in national_metrics else "2"
            if metric in national_metrics:
                exists = not panel_nat[(panel_nat["period"] == p) & (panel_nat["metric"] == metric)].empty
            else:
                exists = not panel_reg[(panel_reg["period"] == p) & (panel_reg["metric"] == metric)].empty
            if not exists:
                r_cfg = rounds_cfg.get(int(round_name), rounds_cfg.get(round_name, {}))
                rows.append(
                    {
                        "round": int(round_name),
                        "period": p,
                        "metric": metric,
                        "region": None,
                        "gap_type": "missing_value",
                        "suggested_query_terms": "|".join((r_cfg.get("keyword_overrides", {}).get(metric, {}).get("optional_terms", []))[:8]),
                        "suggested_sources": "|".join(r_cfg.get("sources_allowlist", [])),
                    }
                )
    return pd.DataFrame(rows)
