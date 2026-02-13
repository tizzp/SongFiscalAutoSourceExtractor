from __future__ import annotations

import pandas as pd


def build_conflict_log(records_df: pd.DataFrame) -> pd.DataFrame:
    if records_df.empty:
        return pd.DataFrame(columns=["period", "region", "metric", "value_count", "values", "recommended_value", "reason"])
    value_df = records_df.dropna(subset=["value"])
    grouped = value_df.groupby(["period", "region", "metric"], dropna=False)
    rows = []
    for keys, g in grouped:
        uniq = sorted(set(g["value"].tolist()))
        if len(uniq) > 1:
            recommended = g.sort_values(["confidence"], ascending=False).iloc[0]["value"]
            rows.append(
                {
                    "period": keys[0],
                    "region": keys[1],
                    "metric": keys[2],
                    "value_count": len(uniq),
                    "values": "|".join(map(str, uniq[:20])),
                    "recommended_value": recommended,
                    "reason": "multiple candidate values with same period-region-metric",
                }
            )
    return pd.DataFrame(rows)
