"""
SecureIoT-X AI Engine — Anomaly Detection.

Unsupervised layer to flag unusual behaviour that doesn't match known patterns.
Uses Isolation Forest (primary) or One-Class SVM (optional).

Output categories: KNOWN_ATTACK | NORMAL | SUSPICIOUS_UNKNOWN
Never claims "zero-day detection" — uses "potential previously unseen anomaly".
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

logger = logging.getLogger("secureiot.ai.anomaly")

# Try optional One-Class SVM
try:
    from sklearn.svm import OneClassSVM
    HAS_OCSVM = True
except ImportError:
    HAS_OCSVM = False


class AnomalyDetector:
    """
    Unsupervised anomaly detection layer.

    Complements supervised classifiers by flagging traffic that doesn't
    confidently match any known pattern.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.method: str = cfg.get("method", "isolation_forest")
        self.contamination: float = cfg.get("contamination", 0.05)
        self.random_state: int = cfg.get("random_state", 42)
        self.model: Optional[Any] = None
        self._is_fitted = False

    def fit(self, X_train: np.ndarray) -> None:
        """Fit the anomaly detector on normal/training data."""
        logger.info("Training anomaly detector: %s (contamination=%.2f)",
                     self.method, self.contamination)

        if self.method == "isolation_forest":
            self.model = IsolationForest(
                contamination=self.contamination,
                random_state=self.random_state,
                n_estimators=100,
                n_jobs=-1,
            )
        elif self.method == "ocsvm" and HAS_OCSVM:
            self.model = OneClassSVM(
                kernel="rbf",
                nu=self.contamination,
            )
        else:
            logger.warning("Method '%s' not available, falling back to IsolationForest", self.method)
            self.model = IsolationForest(
                contamination=self.contamination,
                random_state=self.random_state,
                n_estimators=100,
                n_jobs=-1,
            )

        self.model.fit(X_train)
        self._is_fitted = True
        logger.info("Anomaly detector trained on %d samples", X_train.shape[0])

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict anomaly labels.
        Returns: 1 (normal/inlier) or -1 (anomaly/outlier)
        """
        if not self._is_fitted:
            raise RuntimeError("Anomaly detector not fitted. Call fit() first.")
        return self.model.predict(X)

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """
        Return anomaly scores. Lower = more anomalous.
        """
        if not self._is_fitted:
            raise RuntimeError("Anomaly detector not fitted. Call fit() first.")
        if hasattr(self.model, "score_samples"):
            return self.model.score_samples(X)
        elif hasattr(self.model, "decision_function"):
            return self.model.decision_function(X)
        else:
            # Fallback: use predict
            return self.model.predict(X).astype(float)

    def classify(
        self,
        X: np.ndarray,
        supervised_predictions: np.ndarray,
        supervised_confidences: np.ndarray,
        min_confidence: float = 0.60,
    ) -> list:
        """
        Combine supervised predictions with anomaly detection.

        Returns list of: KNOWN_ATTACK | NORMAL | SUSPICIOUS_UNKNOWN
        """
        anomaly_labels = self.predict(X)
        anomaly_scores = self.score_samples(X)
        results = []

        for i in range(len(X)):
            sup_pred = supervised_predictions[i]
            sup_conf = supervised_confidences[i]
            is_anomaly = anomaly_labels[i] == -1
            a_score = float(anomaly_scores[i])

            if sup_conf >= min_confidence and not is_anomaly:
                # High-confidence supervised prediction
                category = "NORMAL" if str(sup_pred).lower() == "normal" else "KNOWN_ATTACK"
            elif is_anomaly and sup_conf < min_confidence:
                # Anomalous AND low supervised confidence
                category = "SUSPICIOUS_UNKNOWN"
            elif is_anomaly:
                # Anomalous but supervised is confident
                category = "KNOWN_ATTACK" if str(sup_pred).lower() != "normal" else "SUSPICIOUS_UNKNOWN"
            else:
                # Not anomalous, low confidence
                category = "SUSPICIOUS_UNKNOWN" if sup_conf < min_confidence else "NORMAL"

            results.append({
                "category": category,
                "supervised_prediction": str(sup_pred),
                "supervised_confidence": float(sup_conf),
                "is_anomaly": bool(is_anomaly),
                "anomaly_score": a_score,
                "note": "potential previously unseen anomaly" if category == "SUSPICIOUS_UNKNOWN" else None,
            })

        return results

    # ── Serialisation ──────────────────────────────────────────

    def save(self, dirpath: str) -> None:
        """Save fitted anomaly detector."""
        path = Path(dirpath)
        path.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "model": self.model,
            "method": self.method,
            "contamination": self.contamination,
        }, path / "anomaly_detector.joblib")
        logger.info("Anomaly detector saved to %s", path)

    @classmethod
    def load(cls, dirpath: str) -> "AnomalyDetector":
        """Load fitted anomaly detector."""
        path = Path(dirpath)
        state = joblib.load(path / "anomaly_detector.joblib")
        ad = cls()
        ad.model = state["model"]
        ad.method = state["method"]
        ad.contamination = state["contamination"]
        ad._is_fitted = True
        logger.info("Anomaly detector loaded from %s", path)
        return ad
