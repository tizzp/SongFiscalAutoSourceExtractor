from __future__ import annotations

import pandas as pd


def derive_ratios(records_df: pd.DataFrame) -> pd.DataFrame:
    if records_df.empty:
        return records_df
    df = records_df.copy()
    # placeholder strictness: only derive when both numerator and denominator exist in same period/region.
    to_add = []
    for (period, region), grp in df.groupby(["period", "region"], dropna=False):
        total = grp[grp["metric"] == "total_tax"]["value"].dropna()
        commer = grp[grp["metric"] == "commercial_tax"]["value"].dropna()
        if not total.empty and not commer.empty:
            ratio = commer.iloc[0] / total.iloc[0] if total.iloc[0] else None
            if ratio is not None:
                row = grp.iloc[0].to_dict()
                row["metric"] = "commercial_share"
                row["value"] = ratio
                row["unit"] = "ratio"
                row["raw_number"] = None
                row["raw_unit"] = None
                row["context_rule"] = "derived"
                row["primary_record_id"] = f"DRV-{period}-{region or 'NAT'}-commercial_share"
                row["confidence"] = 0.6
                to_add.append(row)
    if to_add:
        df = pd.concat([df, pd.DataFrame(to_add)], ignore_index=True)
    return df
