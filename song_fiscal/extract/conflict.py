from __future__ import annotations

import pandas as pd


def build_conflict_log(records_df: pd.DataFrame) -> pd.DataFrame:
    if records_df.empty:
        return pd.DataFrame(columns=["period", "region", "metric", "unit_std", "time_precision", "candidate_values", "recommended_value", "reason"])
    value_df = records_df.dropna(subset=["value_std"])
    grouped = value_df.groupby(["period", "region", "metric", "unit_std", "time_precision"], dropna=False)
    rows = []
    for keys, g in grouped:
        uniq = sorted(set(g["value_std"].tolist()))
        if len(uniq) > 1:
            recommended = g.sort_values(["source_tier", "time_precision", "confidence"], ascending=[True, True, False]).iloc[0]["value_std"]
            rows.append(
                {
                    "period": keys[0],
                    "region": keys[1],
                    "metric": keys[2],
                    "unit_std": keys[3],
                    "time_precision": keys[4],
                    "candidate_values": "|".join(map(str, uniq[:20])),
                    "recommended_value": recommended,
                    "reason": "tier/time_precision/anchor completeness prioritized",
                }
            )
    return pd.DataFrame(rows)
