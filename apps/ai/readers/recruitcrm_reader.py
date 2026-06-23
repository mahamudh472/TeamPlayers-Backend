from pathlib import Path

import pandas as pd


def read_recruitcrm_export(
    file_path: str | Path,
) -> pd.DataFrame:
    """
    Read RecruitCRM export.
    """

    extension = Path(file_path).suffix.lower()

    if extension == ".csv":
        return pd.read_csv(file_path)

    if extension in [".xlsx", ".xls"]:
        return pd.read_excel(file_path)

    raise ValueError("Unsupported RecruitCRM file.")
