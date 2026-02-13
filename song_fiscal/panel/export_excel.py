from __future__ import annotations

from pathlib import Path

import pandas as pd


def export_panel_excel(output_path: str, sheets: dict[str, pd.DataFrame]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            safe_df = df.copy()
            safe_df = safe_df.fillna("NA")
            safe_df.to_excel(writer, sheet_name=name[:31], index=False)
