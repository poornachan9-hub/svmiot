"""
SecureIoT-X — Dataset Verification Script.

Empirically validates the dataset file, inspecting:
- Exact filename & path
- Row count & column count
- Data types & null values
- Duplicate records
- Class distribution & imbalance
- Numeric feature distributions
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "RT_IOT2022.csv"


def validate_dataset(filepath: Path = DATASET_PATH) -> dict:
    print("=" * 80)
    print("SECUREIOT-X DATASET VALIDATION REPORT")
    print("=" * 80)

    print(f"Exact File Path: {filepath}")
    print(f"File Exists:     {filepath.exists()}")

    if not filepath.exists():
        print(f"[FAIL] Dataset file not found at {filepath}")
        return {"error": "File not found"}

    file_size_bytes = filepath.stat().st_size
    print(f"File Size:       {file_size_bytes:,} bytes ({file_size_bytes / (1024*1024):.2f} MB)")

    df = pd.read_csv(filepath)
    n_rows, n_cols = df.shape
    print(f"\n[1] SHAPE AND STRUCTURE")
    print(f"  Rows:    {n_rows:,}")
    print(f"  Columns: {n_cols}")

    print(f"\n[2] COLUMN NAMES AND DATA TYPES")
    for col in df.columns:
        print(f"  - {col:<25} {str(df[col].dtype):<10} (Nulls: {df[col].isnull().sum()})")

    missing_total = int(df.isnull().sum().sum())
    duplicates_total = int(df.duplicated().sum())
    print(f"\n[3] DATA INTEGRITY")
    print(f"  Total Missing Values: {missing_total}")
    print(f"  Duplicate Rows:       {duplicates_total}")

    # Check target column
    target_col = None
    for cand in ["Attack_type", "attack_type", "label", "Label"]:
        if cand in df.columns:
            target_col = cand
            break

    print(f"\n[4] TARGET / LABEL ANALYSIS")
    print(f"  Target Column: '{target_col}'")
    class_counts = df[target_col].value_counts()
    print(f"  Unique Classes: {len(class_counts)}")
    print(f"\n  Class Breakdown:")
    for cls, count in class_counts.items():
        pct = (count / n_rows) * 100
        print(f"    {cls:<25} {count:>6}  ({pct:5.2f}%)")

    print(f"\n[5] NUMERICAL FEATURE SUMMARY (Sample statistics)")
    num_cols = df.select_dtypes(include=[np.number]).columns
    summary = df[num_cols].describe().T[["mean", "std", "min", "50%", "max"]]
    print(summary.to_string())

    print("\n" + "=" * 80)
    print(f"[VERDICT] Dataset verification completed with real empirical metrics.")
    print("=" * 80)

    return {
        "path": str(filepath),
        "rows": n_rows,
        "cols": n_cols,
        "missing": missing_total,
        "duplicates": duplicates_total,
        "classes": class_counts.to_dict(),
    }


if __name__ == "__main__":
    validate_dataset()
