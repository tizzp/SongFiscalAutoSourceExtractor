from __future__ import annotations

import pandas as pd


def build_national_period_panel(records_df: pd.DataFrame) -> pd.DataFrame:
    if records_df.empty:
        return pd.DataFrame(columns=["period", "metric", "value", "unit", "primary_record_ids", "note"])
    nat = records_df[records_df["region"].isna()].copy()
    nat = nat.dropna(subset=["value"])
    rows = []
    for (period, metric), g in nat.groupby(["period", "metric"]):
        top = g.sort_values("confidence", ascending=False).iloc[0]
        rows.append(
            {
                "period": period,
                "metric": metric,
                "value": top["value"],
                "unit": top["unit"],
                "primary_record_ids": "|".join(g["primary_record_id"].astype(str).head(20).tolist()),
                "note": "best-confidence value from Tier A/B records",
            }
        )
    return pd.DataFrame(rows)


def build_grainflow_region_period_panel(records_df: pd.DataFrame) -> pd.DataFrame:
    if records_df.empty:
        return pd.DataFrame(columns=["period", "region", "north_south", "metric", "value", "unit", "primary_record_ids", "note"])
    gf = records_df[records_df["metric"].isin(["pingdi_or_hedi", "supply_capital", "supply_frontier"])].dropna(subset=["value"])
    rows = []
    for (period, region, metric), g in gf.groupby(["period", "region", "metric"], dropna=False):
        top = g.sort_values("confidence", ascending=False).iloc[0]
        rows.append(
            {
                "period": period,
                "region": region,
                "north_south": top["north_south"],
                "metric": metric,
                "value": top["value"],
                "unit": top["unit"],
                "primary_record_ids": "|".join(g["primary_record_id"].astype(str).head(20).tolist()),
                "note": "regional grain flow aggregation",
            }
        )
    return pd.DataFrame(rows)


def build_gap_list(period_cfg: dict, metric_cfg: dict, panel_nat: pd.DataFrame, panel_reg: pd.DataFrame) -> pd.DataFrame:
    rows = []
    national_metrics = ["total_tax", "liangshui_share", "commercial_tax", "commercial_share", "commercial_structure"]
    for p in period_cfg.keys():
        for metric in metric_cfg.keys():
            exists = False
            if metric in national_metrics:
                exists = not panel_nat[(panel_nat["period"] == p) & (panel_nat["metric"] == metric)].empty
            else:
                exists = not panel_reg[(panel_reg["period"] == p) & (panel_reg["metric"] == metric)].empty
            if not exists:
                rows.append(
                    {
                        "period": p,
                        "metric": metric,
                        "gap_type": "missing_value",
                        "suggestion": "Expand Tier A query keywords and locate volume-specific anchors.",
                    }
                )
    return pd.DataFrame(rows)
