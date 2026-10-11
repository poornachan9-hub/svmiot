"""
SecureIoT-X AI Engine — Dataset Loader & Adapters.

Supports RT-IoT2022 (primary), IoT23, and BoT-IoT datasets.
Each adapter inspects columns, identifies targets, validates structure,
and reports statistics. Never silently guesses a target column.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("secureiot.ai.data_loader")


# ═══════════════════════════════════════════════════════════════
# Base Dataset Adapter
# ═══════════════════════════════════════════════════════════════

class DatasetAdapter:
    """Base adapter — subclass for each supported dataset."""

    NAME: str = "unknown"
    KNOWN_TARGET_COLUMNS: List[str] = []
    KNOWN_DROP_COLUMNS: List[str] = []

    def __init__(self, filepath: str) -> None:
        self.filepath = Path(filepath)
        self.df: Optional[pd.DataFrame] = None
        self.target_column: Optional[str] = None

    def load(self) -> pd.DataFrame:
        """Load the CSV dataset."""
        if not self.filepath.exists():
            raise FileNotFoundError(
                f"Dataset not found: {self.filepath}\n"
                f"Please download the {self.NAME} dataset and place it at: {self.filepath}"
            )

        logger.info("Loading dataset: %s from %s", self.NAME, self.filepath)
        self.df = pd.read_csv(self.filepath, low_memory=False)
        logger.info("Loaded %d rows × %d columns", *self.df.shape)
        return self.df

    def identify_target(self) -> str:
        """Identify the target/label column."""
        if self.df is None:
            raise RuntimeError("Call load() before identify_target()")

        for col in self.KNOWN_TARGET_COLUMNS:
            if col in self.df.columns:
                self.target_column = col
                logger.info("Target column identified: '%s'", col)
                return col

        # Heuristic: look for common names
        heuristic_names = ["label", "Label", "attack_type", "Attack_type",
                           "class", "Class", "target", "Target", "category"]
        for col in heuristic_names:
            if col in self.df.columns:
                self.target_column = col
                logger.warning("Target column auto-detected (heuristic): '%s' — please verify", col)
                return col

        # Cannot determine
        raise ValueError(
            f"Cannot automatically identify target column for {self.NAME}.\n"
            f"Available columns: {list(self.df.columns)}\n"
            f"Please set the target column in config/ml.yaml or your adapter."
        )

    def validate(self) -> Dict[str, Any]:
        """Validate dataset structure and return a report."""
        if self.df is None:
            raise RuntimeError("Call load() before validate()")

        report = {
            "dataset": self.NAME,
            "filepath": str(self.filepath),
            "shape": self.df.shape,
            "columns": list(self.df.columns),
            "dtypes": {col: str(dtype) for col, dtype in self.df.dtypes.items()},
            "missing_values": self.df.isnull().sum().to_dict(),
            "total_missing": int(self.df.isnull().sum().sum()),
            "duplicates": int(self.df.duplicated().sum()),
            "numerical_columns": list(self.df.select_dtypes(include=[np.number]).columns),
            "categorical_columns": list(self.df.select_dtypes(include=["object", "category"]).columns),
            "inf_values": {},
        }

        # Check for infinite values in numeric columns
        num_cols = self.df.select_dtypes(include=[np.number]).columns
        for col in num_cols:
            inf_count = int(np.isinf(self.df[col]).sum())
            if inf_count > 0:
                report["inf_values"][col] = inf_count

        # Class distribution
        if self.target_column and self.target_column in self.df.columns:
            dist = self.df[self.target_column].value_counts()
            report["class_distribution"] = dist.to_dict()
            report["num_classes"] = len(dist)
            report["target_column"] = self.target_column

        return report

    def get_features_and_target(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Return (X, y) after dropping irrelevant columns."""
        if self.df is None or self.target_column is None:
            raise RuntimeError("Call load() and identify_target() first")

        drop = [c for c in self.KNOWN_DROP_COLUMNS if c in self.df.columns]
        X = self.df.drop(columns=[self.target_column] + drop)
        y = self.df[self.target_column]
        return X, y

    def print_report(self, report: Dict[str, Any]) -> None:
        """Pretty-print the validation report."""
        print("\n" + "=" * 60)
        print(f"DATASET REPORT: {report['dataset']}")
        print("=" * 60)
        print(f"  Shape:         {report['shape'][0]} rows × {report['shape'][1]} columns")
        print(f"  Missing vals:  {report['total_missing']}")
        print(f"  Duplicates:    {report['duplicates']}")
        print(f"  Numerical:     {len(report['numerical_columns'])} columns")
        print(f"  Categorical:   {len(report['categorical_columns'])} columns")
        if report.get("inf_values"):
            print(f"  Inf values:    {sum(report['inf_values'].values())} total in {len(report['inf_values'])} columns")
        if report.get("class_distribution"):
            print(f"  Target:        {report.get('target_column', '?')}")
            print(f"  Classes:       {report.get('num_classes', '?')}")
            print("  Distribution:")
            for cls, count in sorted(report["class_distribution"].items(), key=lambda x: -x[1]):
                pct = count / report["shape"][0] * 100
                print(f"    {cls:30s} {count:>8d}  ({pct:5.1f}%)")
        print("=" * 60 + "\n")


# ═══════════════════════════════════════════════════════════════
# RT-IoT2022 Adapter
# ═══════════════════════════════════════════════════════════════

class RTIoT2022Adapter(DatasetAdapter):
    """Adapter for RT-IoT2022 dataset."""

    NAME = "RT-IoT2022"
    KNOWN_TARGET_COLUMNS = ["Attack_type", "label", "Label", "Attack_label"]
    KNOWN_DROP_COLUMNS = ["id", "Unnamed: 0", "id.orig_p", "bwd_URG_flag_count"]


# ═══════════════════════════════════════════════════════════════
# IoT23 Adapter
# ═══════════════════════════════════════════════════════════════

class IoT23Adapter(DatasetAdapter):
    """Adapter for Aposemat IoT-23 dataset."""

    NAME = "IoT-23"
    KNOWN_TARGET_COLUMNS = ["label", "detailed-label"]
    KNOWN_DROP_COLUMNS = ["uid", "id.orig_h", "id.resp_h"]


# ═══════════════════════════════════════════════════════════════
# BoT-IoT Adapter
# ═══════════════════════════════════════════════════════════════

class BotIoTAdapter(DatasetAdapter):
    """Adapter for UNSW BoT-IoT dataset."""

    NAME = "BoT-IoT"
    KNOWN_TARGET_COLUMNS = ["attack", "category", "subcategory", "label"]
    KNOWN_DROP_COLUMNS = ["pkSeqID"]


# ═══════════════════════════════════════════════════════════════
# Synthetic Adapter (for testing without real datasets)
# ═══════════════════════════════════════════════════════════════

class SyntheticAdapter(DatasetAdapter):
    """Generate a synthetic IoT traffic dataset for development/testing."""

    NAME = "Synthetic"
    KNOWN_TARGET_COLUMNS = ["label"]

    def load(self) -> pd.DataFrame:
        logger.info("Generating synthetic dataset for development...")
        np.random.seed(42)
        n_samples = 5000

        attack_types = ["Normal", "DDoS", "DoS", "Reconnaissance", "Brute_Force", "Spoofing"]
        weights = [0.50, 0.12, 0.12, 0.10, 0.08, 0.08]

        labels = np.random.choice(attack_types, size=n_samples, p=weights)

        data = {
            "flow_duration": np.abs(np.random.exponential(10, n_samples)),
            "fwd_pkts_tot": np.random.randint(1, 500, n_samples),
            "bwd_pkts_tot": np.random.randint(0, 300, n_samples),
            "fwd_data_pkts_tot": np.random.randint(0, 400, n_samples),
            "bwd_data_pkts_tot": np.random.randint(0, 200, n_samples),
            "fwd_pkts_per_sec": np.abs(np.random.normal(50, 30, n_samples)),
            "bwd_pkts_per_sec": np.abs(np.random.normal(30, 20, n_samples)),
            "flow_pkts_per_sec": np.abs(np.random.normal(80, 40, n_samples)),
            "fwd_byts_per_sec": np.abs(np.random.normal(5000, 3000, n_samples)),
            "bwd_byts_per_sec": np.abs(np.random.normal(3000, 2000, n_samples)),
            "fwd_pkts_payload_avg": np.abs(np.random.normal(200, 100, n_samples)),
            "bwd_pkts_payload_avg": np.abs(np.random.normal(150, 80, n_samples)),
            "proto": np.random.choice([6, 17, 1], n_samples, p=[0.6, 0.3, 0.1]),
            "dst_port": np.random.choice([80, 443, 1883, 8080, 22, 23, 53, 8883], n_samples),
            "conn_state_num": np.random.randint(0, 12, n_samples),
            "label": labels,
        }

        # Make attacks look different from normal
        for i in range(n_samples):
            if labels[i] == "DDoS":
                data["fwd_pkts_per_sec"][i] *= 5
                data["flow_pkts_per_sec"][i] *= 5
                data["fwd_pkts_tot"][i] *= 4
            elif labels[i] == "DoS":
                data["fwd_pkts_per_sec"][i] *= 3
                data["fwd_byts_per_sec"][i] *= 3
            elif labels[i] == "Reconnaissance":
                data["dst_port"][i] = np.random.randint(1, 65535)
                data["flow_duration"][i] *= 0.1
            elif labels[i] == "Brute_Force":
                data["conn_state_num"][i] = np.random.choice([0, 1])
                data["fwd_pkts_tot"][i] = np.random.randint(1, 10)
            elif labels[i] == "Spoofing":
                data["bwd_pkts_tot"][i] = 0
                data["bwd_byts_per_sec"][i] = 0

        self.df = pd.DataFrame(data)
        self.target_column = "label"
        logger.info("Generated synthetic dataset: %d rows × %d columns", *self.df.shape)
        return self.df

    def identify_target(self) -> str:
        self.target_column = "label"
        return "label"


# ═══════════════════════════════════════════════════════════════
# Factory
# ═══════════════════════════════════════════════════════════════

_ADAPTERS = {
    "RT_IOT2022": RTIoT2022Adapter,
    "RT-IoT2022": RTIoT2022Adapter,
    "IoT23": IoT23Adapter,
    "IoT-23": IoT23Adapter,
    "BoT_IoT": BotIoTAdapter,
    "BoT-IoT": BotIoTAdapter,
    "Synthetic": SyntheticAdapter,
}


def get_adapter(dataset_name: str, filepath: str = "") -> DatasetAdapter:
    """Get the appropriate adapter for a dataset."""
    cls = _ADAPTERS.get(dataset_name)
    if cls is None:
        raise ValueError(
            f"Unknown dataset: {dataset_name}. Supported: {list(_ADAPTERS.keys())}"
        )
    if cls == SyntheticAdapter:
        return cls(filepath="synthetic")
    return cls(filepath)
