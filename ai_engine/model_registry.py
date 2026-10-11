"""
SecureIoT-X AI Engine — Model Registry.

Tracks model versions, datasets, features, metrics, and production status.
No auto-promotion without validation.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("secureiot.ai.registry")


class ModelRegistry:
    """Track and manage trained model versions."""

    def __init__(self, registry_path: str = "models/registry.json") -> None:
        self.registry_path = Path(registry_path)
        self._entries: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        """Load registry from disk."""
        if self.registry_path.exists():
            with open(self.registry_path, "r") as f:
                self._entries = json.load(f)
            logger.info("Loaded model registry: %d entries", len(self._entries))

    def _save(self) -> None:
        """Persist registry to disk."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, "w") as f:
            json.dump(self._entries, f, indent=2, default=str)

    def register(
        self,
        model_name: str,
        version: str,
        dataset: str,
        features: List[str],
        metrics: Dict[str, Any],
        model_path: str,
        preprocessing_path: str,
        random_seed: int = 42,
        train_test_split: str = "80/20",
        validation_metrics: Optional[Dict[str, Any]] = None,
        sample_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        is_near_random = bool(
            metrics.get("is_near_random", False)
            or (metrics.get("roc_auc") is not None and metrics["roc_auc"] <= 0.55)
        )
        warning_msg = (
            f"CRITICAL: Model '{model_name}' performs near random chance "
            f"(ROC-AUC={metrics.get('roc_auc')}, F1-macro={metrics.get('f1_macro')}). "
            "Never call a model production-ready solely because training or inference succeeds."
        ) if is_near_random else None

        entry = {
            "model_name": model_name,
            "version": version,
            "dataset": dataset,
            "features": features,
            "training_date": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "validation_metrics": validation_metrics or {},
            "evaluation_date": metrics.get("evaluated_at"),
            "model_path": model_path,
            "preprocessing_path": preprocessing_path,
            "sample_path": sample_path,
            "preprocessing_version": "v1",
            "random_seed": random_seed,
            "train_test_split": train_test_split,
            "is_production": False,
            "validated": False,
            "is_near_random": is_near_random,
            "production_ready": not is_near_random,
            "warning": warning_msg,
        }
        # Replace existing entry if same model_name and version already registered
        for i, existing in enumerate(self._entries):
            if existing["model_name"] == model_name and existing["version"] == version:
                self._entries[i] = entry
                self._save()
                logger.info("Updated model registry: %s %s", model_name, version)
                return entry

        self._entries.append(entry)
        self._save()
        logger.info("Registered model: %s %s", model_name, version)
        return entry

    def set_production(self, model_name: str, version: str) -> None:
        """Mark a validated model as the serving artifact. Unsets previous production models."""
        target = None
        for entry in self._entries:
            if entry["model_name"] == model_name and entry["version"] == version:
                target = entry
            # Unset all others
            entry["is_production"] = False

        if target is None:
            raise ValueError(f"Model {model_name} {version} not found in registry")
        if not target.get("validated", False):
            raise ValueError(f"Model {model_name} {version} not validated. Validate before promoting.")

        target["is_production"] = True
        metrics = target.get("metrics", {})
        is_near_random = bool(
            target.get("is_near_random", False)
            or (metrics.get("roc_auc") is not None and metrics["roc_auc"] <= 0.55)
        )
        target["is_near_random"] = is_near_random
        target["production_ready"] = not is_near_random
        if is_near_random:
            target["warning"] = (
                f"CRITICAL WARNING: Serving model '{model_name}' ({version}) performs near random chance "
                f"(ROC-AUC={metrics.get('roc_auc')}). It is NOT certified for production use."
            )
            logger.warning(
                "Promoted %s %s to active serving with CRITICAL WARNING: near random performance (production_ready=False)",
                model_name, version,
            )
        self._save()
        logger.info("Production model set: %s %s (production_ready=%s)", model_name, version, target["production_ready"])

    def validate_model(self, model_name: str, version: str) -> None:
        """Mark a model as validated (allows promotion to serving artifact)."""
        found = False
        for entry in self._entries:
            if entry["model_name"] == model_name and entry["version"] == version:
                entry["validated"] = True
                metrics = entry.get("metrics", {})
                is_near_random = bool(
                    entry.get("is_near_random", False)
                    or (metrics.get("roc_auc") is not None and metrics["roc_auc"] <= 0.55)
                )
                entry["is_near_random"] = is_near_random
                entry["production_ready"] = not is_near_random
                if is_near_random:
                    entry["warning"] = (
                        f"CRITICAL WARNING: Model '{model_name}' ({version}) performs near random chance. "
                        "Do not deploy to production. Features lack predictive attack signal."
                    )
                    logger.warning(
                        "Model %s %s validated as artifact but NOT production-ready (near random performance)",
                        model_name, version,
                    )
                else:
                    entry["warning"] = None
                found = True
        if found:
            self._save()
            logger.info("Model validated: %s %s", model_name, version)
            return
        raise ValueError(f"Model {model_name} {version} not found")

    def get_production_model(self) -> Optional[Dict[str, Any]]:
        """Get the current production model entry."""
        for entry in self._entries:
            if entry.get("is_production"):
                return entry
        return None

    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models."""
        return self._entries.copy()

    def get_model(self, model_name: str, version: str) -> Optional[Dict[str, Any]]:
        """Get a specific model entry."""
        for entry in self._entries:
            if entry["model_name"] == model_name and entry["version"] == version:
                return entry
        return None
