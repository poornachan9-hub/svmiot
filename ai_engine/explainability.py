"""
SecureIoT-X AI Engine — Explainability.

Provides basic explainability for AI predictions.
- Tree models: feature importance
- Individual predictions: top contributing features
Never fabricates explanations.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("secureiot.ai.explainability")


class Explainer:
    """Provide interpretable explanations for model predictions."""

    def __init__(self, feature_names: Optional[List[str]] = None) -> None:
        self.feature_names = feature_names or []

    def explain_model(self, model: Any) -> Dict[str, Any]:
        """Get global model feature importances."""
        importances = {}

        if hasattr(model, "feature_importances_"):
            for i, imp in enumerate(model.feature_importances_):
                name = self.feature_names[i] if i < len(self.feature_names) else f"feature_{i}"
                importances[name] = round(float(imp), 6)
        elif hasattr(model, "coef_"):
            coefs = np.abs(model.coef_)
            if coefs.ndim > 1:
                coefs = coefs.mean(axis=0)
            for i, imp in enumerate(coefs):
                name = self.feature_names[i] if i < len(self.feature_names) else f"feature_{i}"
                importances[name] = round(float(imp), 6)
        else:
            logger.info("Model type does not expose feature importances directly")
            return {"note": "Feature importances not available for this model type"}

        # Sort descending
        importances = dict(sorted(importances.items(), key=lambda x: -x[1]))

        return {
            "feature_importances": importances,
            "top_5": list(importances.keys())[:5],
            "model_type": type(model).__name__,
        }

    def explain_prediction(
        self,
        model: Any,
        features: np.ndarray,
        prediction: str,
    ) -> Dict[str, Any]:
        """
        Explain a single prediction by showing top contributing features.
        Uses feature importance weighted by feature values.
        """
        if len(features.shape) == 1:
            features = features.reshape(1, -1)

        explanation = {
            "prediction": prediction,
            "contributing_features": [],
        }

        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            # Weight by actual feature values (absolute contribution)
            contributions = importances * np.abs(features[0])
            top_indices = np.argsort(contributions)[::-1][:5]

            for idx in top_indices:
                name = self.feature_names[idx] if idx < len(self.feature_names) else f"feature_{idx}"
                explanation["contributing_features"].append({
                    "feature": name,
                    "importance": round(float(importances[idx]), 6),
                    "value": round(float(features[0][idx]), 4),
                    "contribution": round(float(contributions[idx]), 6),
                })

        elif hasattr(model, "coef_"):
            coefs = model.coef_
            if coefs.ndim > 1:
                coefs = coefs.mean(axis=0)
            contributions = np.abs(coefs) * np.abs(features[0])
            top_indices = np.argsort(contributions)[::-1][:5]

            for idx in top_indices:
                name = self.feature_names[idx] if idx < len(self.feature_names) else f"feature_{idx}"
                explanation["contributing_features"].append({
                    "feature": name,
                    "coefficient": round(float(coefs[idx]), 6),
                    "value": round(float(features[0][idx]), 4),
                    "contribution": round(float(contributions[idx]), 6),
                })
        else:
            explanation["note"] = "Detailed per-prediction explanation not available for this model type"

        return explanation

    def generate_threat_explanation(
        self,
        prediction: str,
        contributing_features: List[Dict[str, Any]],
    ) -> str:
        """Generate a human-readable threat explanation."""
        if not contributing_features:
            return f"Threat detected: {prediction}"

        reasons = []
        for f in contributing_features[:4]:
            name = f["feature"].replace("_", " ").title()
            reasons.append(f"High {name}")

        explanation = f"Threat detected ({prediction}) because:\n"
        for r in reasons:
            explanation += f"  • {r}\n"

        return explanation
