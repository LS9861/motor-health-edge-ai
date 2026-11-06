#!/usr/bin/env python3
"""Quick sanity check on the 9 JGA25 raw CSVs before training."""
import glob
from pathlib import Path

import pandas as pd

files = sorted(glob.glob("data/raw/jga25/*.csv"))
if not files:
    print("No CSVs found in data/raw/jga25/")
    raise SystemExit(1)

print(f"{'file':<20} {'rows':>6} {'rpm_mean':>9} {'cur_mean':>9} {'az_std':>8}")
print("-" * 56)
for f in files:
    df = pd.read_csv(f)
    name = Path(f).name
    print(f"{name:<20} {len(df):>6} "
          f"{df['rpm'].mean():>9.1f} "
          f"{df['current_mA'].mean():>9.1f} "
          f"{df['az'].std():>8.3f}")