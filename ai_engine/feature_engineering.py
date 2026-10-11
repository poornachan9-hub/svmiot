"""
SecureIoT-X AI Engine — Feature Engineering & Selection.

Creates features from available dataset columns only.
Generates feature importance and correlation reports.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("secureiot.ai.features")


class FeatureEngineer:
    """Configurable feature engineering for IoT network traffic datasets."""

    # Features we CAN create if the raw columns exist
    DERIVABLE_FEATURES = {
        "packet_rate": ("fwd_pkts_tot", "flow_duration"),
        "byte_rate": ("fwd_byts_per_sec",),
        "pkt_size_avg": ("fwd_pkts_tot", "bwd_pkts_tot"),
        "fwd_bwd_ratio": ("fwd_pkts_tot", "bwd_pkts_tot"),
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.correlation_threshold: float = cfg.get("correlation_threshold", 0.95)
        self.importance_threshold: float = cfg.get("importance_threshold", 0.01)
        self.max_features: int = cfg.get("max_features", 50)

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create derived features from available columns. Never invents unavailable features."""
        df = df.copy()
        created = []

        # Packet rate = packets / duration
        if "fwd_pkts_tot" in df.columns and "flow_duration" in df.columns:
            df["packet_rate"] = df["fwd_pkts_tot"] / df["flow_duration"].replace(0, 1e-6)
            created.append("packet_rate")

        # Forward/backward ratio
        if "fwd_pkts_tot" in df.columns and "bwd_pkts_tot" in df.columns:
            df["fwd_bwd_ratio"] = df["fwd_pkts_tot"] / (df["bwd_pkts_tot"] + 1)
            created.append("fwd_bwd_ratio")

        # Total packets
        if "fwd_pkts_tot" in df.columns and "bwd_pkts_tot" in df.columns:
            df["total_pkts"] = df["fwd_pkts_tot"] + df["bwd_pkts_tot"]
            created.append("total_pkts")

        # Traffic burstiness (std/mean of packet rate)
        if "fwd_pkts_per_sec" in df.columns:
            # Per-row burstiness approximation using forward rate vs backward
            if "bwd_pkts_per_sec" in df.columns:
                df["traffic_asymmetry"] = (
                    df["fwd_pkts_per_sec"] - df["bwd_pkts_per_sec"]
                ) / (df["fwd_pkts_per_sec"] + df["bwd_pkts_per_sec"] + 1e-6)
                created.append("traffic_asymmetry")

        # Replace any infinities created
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        num_cols = df.select_dtypes(include=[np.number]).columns
        df[num_cols] = df[num_cols].fillna(0)

        if created:
            logger.info("Engineered %d features: %s", len(created), created)
        else:
            logger.info("No additional features could be derived from available columns")

        return df

    def analyze_correlation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze feature correlations and identify highly correlated pairs."""
        num_df = df.select_dtypes(include=[np.number])
        if num_df.empty:
            return {"correlated_pairs": [], "dropped": []}

        corr_matrix = num_df.corr().abs()
        upper = corr_matrix.where(
            np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        )

        high_corr_pairs = []
        to_drop = set()

        for col in upper.columns:
            correlated = upper.index[upper[col] > self.correlation_threshold].tolist()
            for c in correlated:
                high_corr_pairs.append((c, col, float(upper.loc[c, col])))
                to_drop.add(col)  # Drop the second column in each pair

        report = {
            "correlated_pairs": high_corr_pairs,
            "dropped": list(to_drop),
            "threshold": self.correlation_threshold,
        }

        if high_corr_pairs:
            logger.info("Found %d highly correlated pairs (threshold=%.2f). Candidates to drop: %s",
                        len(high_corr_pairs), self.correlation_threshold, list(to_drop))

        return report

    def remove_correlated(self, df: pd.DataFrame, to_drop: List[str]) -> pd.DataFrame:
        """Remove highly correlated features."""
        existing = [c for c in to_drop if c in df.columns]
        if existing:
            logger.info("Removing %d correlated features: %s", len(existing), existing)
            df = df.drop(columns=existing)
        return df

    def get_feature_importance(
        self,
        model: Any,
        feature_names: List[str],
    ) -> Dict[str, float]:
        """Extract feature importances from a fitted tree-based model."""
        importances = {}
        if hasattr(model, "feature_importances_"):
            for name, imp in zip(feature_names, model.feature_importances_):
                importances[name] = float(imp)
        elif hasattr(model, "coef_"):
            coefs = np.abs(model.coef_)
            if coefs.ndim > 1:
                coefs = coefs.mean(axis=0)
            for name, imp in zip(feature_names, coefs):
                importances[name] = float(imp)
        else:
            logger.warning("Model does not expose feature importances")
            return {}

        # Sort by importance descending
        importances = dict(sorted(importances.items(), key=lambda x: -x[1]))
        return importances

    def select_top_features(
        self,
        importances: Dict[str, float],
    ) -> List[str]:
        """Select top features above importance threshold."""
        selected = [
            name for name, imp in importances.items()
            if imp >= self.importance_threshold
        ][:self.max_features]

        logger.info("Selected %d features (threshold=%.4f, max=%d)",
                     len(selected), self.importance_threshold, self.max_features)
        return selected

    def generate_report(
        self,
        importances: Dict[str, float],
        correlation_report: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate a comprehensive feature analysis report."""
        return {
            "feature_importances": importances,
            "top_10_features": list(importances.keys())[:10],
            "total_features": len(importances),
            "correlation_analysis": correlation_report,
            "importance_threshold": self.importance_threshold,
            "max_features": self.max_features,
        }
