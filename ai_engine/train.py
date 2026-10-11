"""
SecureIoT-X AI Engine — Multi-Model Training Pipeline.

Trains: Logistic Regression, Decision Tree, Random Forest, SVM, Gradient Boosting.
Tracks training time, model size. Saves models + preprocessing pipeline separately.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.utils.class_weight import compute_sample_weight

logger = logging.getLogger("secureiot.ai.train")

# Try to import XGBoost
try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    logger.info("XGBoost not available — using sklearn GradientBoosting instead")


def build_svm_model(params: Optional[Dict[str, Any]] = None) -> SVC:
    """Instantiate an sklearn.svm.SVC model with configurable hyperparameters."""
    svm_params: Dict[str, Any] = {
        "probability": True,
        "random_state": 42,
    }
    if params:
        svm_params.update(params)
    return SVC(**svm_params)


def _build_model(name: str, params: Dict[str, Any]) -> Any:
    """Instantiate a model by name with given parameters."""
    if name.upper() == "SVM":
        return build_svm_model(params)

    constructors = {
        "LogisticRegression": LogisticRegression,
        "DecisionTree": DecisionTreeClassifier,
        "RandomForest": RandomForestClassifier,
        "GradientBoosting": GradientBoostingClassifier,
    }
    if HAS_XGBOOST:
        constructors["XGBoost"] = XGBClassifier

    ctor = constructors.get(name)
    if ctor is None:
        raise ValueError(f"Unknown model: {name}. Available: {list(constructors.keys()) + ['SVM']}")

    return ctor(**params)


def train_all_models(
    X_train: np.ndarray,
    y_train: np.ndarray,
    model_configs: List[Dict[str, Any]],
    save_dir: str = "models",
    dataset_name: str = "unknown",
    feature_names: Optional[List[str]] = None,
    random_seed: int = 42,
    run_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Train all configured models and save them.

    Returns a list of result dicts with model, metrics, timing, etc.
    """
    results = []
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)
    artifact_run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for cfg in model_configs:
        name = cfg["name"]
        if not cfg.get("enabled", True):
            logger.info("Skipping disabled model: %s", name)
            continue

        params = cfg.get("params", {})
        logger.info("=" * 50)
        logger.info("Training: %s", name)
        logger.info("Params: %s", params)

        try:
            model = _build_model(name, params)

            # Train with timing
            start = time.perf_counter()
            fit_kwargs = {}
            if not params.get("class_weight"):
                fit_kwargs["sample_weight"] = compute_sample_weight(
                    class_weight="balanced", y=y_train
                )
            model.fit(X_train, y_train, **fit_kwargs)
            train_time = time.perf_counter() - start

            # Save model
            version = f"v2_{artifact_run_id}"
            model_dir = save_path / name.lower().replace(" ", "_")
            model_dir.mkdir(parents=True, exist_ok=True)
            model_file = model_dir / f"{name}_{version}.joblib"
            joblib.dump(model, model_file)

            # Model size
            model_size = os.path.getsize(model_file)

            result = {
                "name": name,
                "version": version,
                "model": model,
                "model_path": str(model_file),
                "training_time_seconds": round(train_time, 3),
                "model_size_bytes": model_size,
                "dataset": dataset_name,
                "random_seed": random_seed,
                "params": params,
                "feature_names": feature_names,
                "trained_at": datetime.now(timezone.utc).isoformat(),
            }
            results.append(result)

            logger.info("  [OK] %s trained in %.2fs (size: %d bytes)",
                        name, train_time, model_size)

        except Exception as e:
            logger.error("  [FAIL] Failed to train %s: %s", name, e)
            results.append({
                "name": name,
                "error": str(e),
                "model": None,
            })

    logger.info("=" * 50)
    logger.info("Training complete. %d/%d models succeeded.",
                sum(1 for r in results if r.get("model") is not None), len(results))

    return results


def train_svm(
    X_train: np.ndarray,
    y_train: np.ndarray,
    params: Optional[Dict[str, Any]] = None,
    save_dir: str = "models",
    dataset_name: str = "unknown",
    feature_names: Optional[List[str]] = None,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """
    Train an SVM model with configurable hyperparameters and save it.

    Returns a dict with model, path, training time, size, and metadata.
    """
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    svm_params = dict(params or {})
    if "random_state" not in svm_params:
        svm_params["random_state"] = random_seed
    if "probability" not in svm_params:
        svm_params["probability"] = True

    model = build_svm_model(svm_params)

    logger.info("Training SVM with params: %s", svm_params)
    start = time.perf_counter()
    model.fit(X_train, y_train)
    train_time = time.perf_counter() - start

    version = f"v1_{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    model_dir = save_path / "svm"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_file = model_dir / f"SVM_{version}.joblib"
    joblib.dump(model, model_file)
    model_size = os.path.getsize(model_file)

    metadata = {
        "name": "SVM",
        "version": version,
        "model": model,
        "model_path": str(model_file),
        "training_time_seconds": round(train_time, 3),
        "model_size_bytes": model_size,
        "dataset": dataset_name,
        "random_seed": random_seed,
        "params": svm_params,
        "feature_names": feature_names,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("SVM trained in %.2fs (size: %d bytes)", train_time, model_size)
    return metadata


def train_svm_pipeline(
    X: Any,
    y: Any,
    params: Optional[Dict[str, Any]] = None,
    preprocess_config: Optional[Dict[str, Any]] = None,
    save_dir: str = "models",
    dataset_name: str = "unknown",
    random_seed: int = 42,
) -> Dict[str, Any]:
    """
    End-to-end training and evaluation of SVM with leakage-free preprocessing.

    Data leakage rule:
    1. Splits train/test BEFORE fitting preprocessing.
    2. Fits scaler/encoder ONLY on training data.
    3. Transforms train, val, and test splits with the fitted preprocessing pipeline.
    4. Trains SVM classifier on scaled numerical training data.
    5. Evaluates SVM on test data using comprehensive metrics.

    Produces:
    - SVM model
    - preprocessing pipeline
    - model metadata
    - metrics
    - confusion matrix
    """
    from ai_engine.preprocessing import PreprocessingPipeline
    from ai_engine.evaluate import evaluate_model

    # Initialize preprocessing pipeline
    pp_cfg = {
        "test_size": 0.2,
        "validation_size": 0.1,
        "random_seed": random_seed,
        "scaling_method": "standard",
    }
    if preprocess_config:
        pp_cfg.update(preprocess_config)

    pp = PreprocessingPipeline(pp_cfg)
    X_train, X_val, X_test, y_train, y_val, y_test = pp.fit_transform(X, y)

    # Train SVM
    train_result = train_svm(
        X_train=X_train,
        y_train=y_train,
        params=params,
        save_dir=save_dir,
        dataset_name=dataset_name,
        feature_names=pp.feature_names,
        random_seed=random_seed,
    )

    # Evaluate on test set
    metrics = evaluate_model(
        model=train_result["model"],
        X_test=X_test,
        y_test=y_test,
        model_name="SVM",
        class_names=pp.target_classes,
    )
    metrics["training_time_seconds"] = train_result["training_time_seconds"]
    train_result["metrics"] = metrics

    # Save preprocessing pipeline
    pp_dir = Path(save_dir) / "preprocessing"
    pp.save(str(pp_dir))

    return {
        "model": train_result["model"],
        "preprocessing": pp,
        "metadata": train_result,
        "metrics": metrics,
        "confusion_matrix": metrics.get("confusion_matrix", []),
        "version": train_result["version"],
        "model_path": train_result["model_path"],
        "preprocessing_path": str(pp_dir),
        "target_classes": pp.target_classes,
        "feature_names": pp.feature_names,
    }
