#!/usr/bin/env python3
"""
Create tiny fixture CSVs for CI testing.
Takes the first 200 rows of one raw CSV per class and saves to tests/fixtures/.
Run once. Commit the resulting files.
"""

import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"
FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

ROWS = 200

for label in ["healthy", "imbalanced", "friction"]:
    # Find first CSV for this label (sorted, take the first)
    files = sorted(RAW_DIR.glob(f"{label}_*.csv"))
    if not files:
        raise FileNotFoundError(f"No raw CSV found for label '{label}' in {RAW_DIR}")
    src = files[0]
    df = pd.read_csv(src).head(ROWS)
    out = FIXTURE_DIR / f"{label}_fixture.csv"
    df.to_csv(out, index=False)
    print(f"  {src.name[:40]:40s} → {out.name} ({len(df)} rows)")