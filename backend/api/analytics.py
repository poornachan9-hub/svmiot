"""Analytics API — Dashboard overview stats and AI metrics.

All device/event counts come from MongoDB (the ONLY application database).
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, HTTPException

from backend.core.config import settings
from backend.core.mongodb import get_mongodb

router = APIRouter()
logger = logging.getLogger(__name__)


@lru_cache(maxsize=2)
def _deduplicated_class_counts(
    dataset_path: str,
    dataset_mtime_ns: int,
    expected_classes: Tuple[str, ...],
) -> List[Dict[str, Any]]:
    """Count classes after applying the report's feature-vector modal deduplication."""
    from ai_engine.data_loader import get_adapter
    from ai_engine.feature_engineering import FeatureEngineer
    from ai_engine.preprocessing import PreprocessingPipeline

    config_path = Path(settings.project_root) / "config" / "ml.yaml"
    with config_path.open(encoding="utf-8") as config_file:
        import yaml

        ml_config = yaml.safe_load(config_file) or {}

    adapter = get_adapter("RT-IoT2022", dataset_path)
    adapter.load()
    adapter.identify_target()
    features, labels = adapter.get_features_and_target()
    features = FeatureEngineer(ml_config.get("feature_selection", {})).engineer_features(features)

    pipeline = PreprocessingPipeline({
        "remove_duplicates": False,
        "deduplicate_before_split": True,
    })
    features, labels = pipeline._clean(features, labels)
    grouped = features.copy()
    grouped["__target__"] = labels.to_numpy()
    counts = (
        grouped.groupby(list(features.columns), sort=True)["__target__"]
        .agg(lambda values: values.mode().iloc[0])
        .value_counts()
        .to_dict()
    )
    if set(counts) != set(expected_classes):
        raise ValueError("Deduplicated dataset classes do not match the evaluation report")

    return [
        {"class_name": name, "count": int(counts[name])}
        for name in expected_classes
    ]


def _load_leak_free_report() -> Dict[str, Any]:
    report_path = (
        Path(settings.project_root)
        / "reports"
        / "runs"
        / "leak_free_evaluation"
        / "leak_free_report.json"
    )
    if not report_path.is_file():
        raise HTTPException(status_code=404, detail="Deduplicated evaluation report is unavailable")

    try:
        with report_path.open(encoding="utf-8") as report_file:
            report = json.load(report_file)
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("Could not read leak-free evaluation report")
        raise HTTPException(status_code=503, detail="Deduplicated evaluation report is unreadable") from exc

    try:
        classes = report["classes"]
        sample_sizes = report["sample_sizes"]
        random_forest = report["random_forest"]
        baseline = report["majority_baseline"]
        matrix = random_forest["confusion_matrix"]
        per_class = report["per_class_comparison"]
        governance = report["governance"]
        test_size = sample_sizes["n_test"]
        if (
            report["run_type"] != "leak_free_deduplicated_evaluation"
            or not isinstance(classes, list)
            or len(classes) != sample_sizes["n_classes"]
            or len(set(classes)) != len(classes)
            or len(matrix) != len(classes)
            or any(len(row) != len(classes) for row in matrix)
            or sum(sum(row) for row in matrix) != test_size
            or set(per_class) != set(classes)
            or sum(per_class[name]["test_support"] for name in classes) != test_size
            or governance["production_ready"] is not False
        ):
            raise ValueError("Evaluation report failed schema or integrity validation")
    except (KeyError, TypeError, ValueError) as exc:
        logger.exception("Leak-free evaluation report failed validation")
        raise HTTPException(status_code=503, detail="Deduplicated evaluation report failed validation") from exc

    dataset_path = Path(settings.project_root) / settings.ml_dataset_path
    try:
        class_distribution = _deduplicated_class_counts(
            str(dataset_path),
            dataset_path.stat().st_mtime_ns,
            tuple(classes),
        )
        expected_total = sum(
            sample_sizes[key] for key in ("n_train", "n_val", "n_test")
        )
        if sum(item["count"] for item in class_distribution) != expected_total:
            raise ValueError("Deduplicated class counts do not match the saved split sizes")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        logger.exception("Could not derive deduplicated dataset class distribution")
        raise HTTPException(
            status_code=503,
            detail="Deduplicated dataset class distribution could not be verified",
        ) from exc

    return {
        "run_type": report["run_type"],
        "dataset": report["dataset"],
        "evaluated_at": report["evaluated_at"],
        "random_seed": report["random_seed"],
        "sample_sizes": sample_sizes,
        "classes": classes,
        "random_forest": {
            key: random_forest[key]
            for key in (
                "accuracy", "macro_f1", "macro_recall", "macro_precision",
                "roc_auc", "confusion_matrix",
            )
        },
        "majority_baseline": {
            key: baseline[key]
            for key in ("accuracy", "macro_f1", "macro_recall", "macro_precision")
        },
        "per_class_comparison": per_class,
        "policy": report["policy"],
        "governance": governance,
        "dataset_class_distribution": class_distribution,
    }


@router.get("/model-evaluation", summary="Deduplicated Model Analytics Evaluation")
async def model_evaluation():
    """Return validated saved evaluation results and deduplicated dataset counts."""
    return _load_leak_free_report()


@router.get("/overview", summary="Dashboard Overview Stats")
async def overview():
    """Get overview statistics for the dashboard from MongoDB."""
    db = get_mongodb()

    total_devices = await db.devices.count_documents({})
    online_devices = await db.devices.count_documents({"is_online": {"$ne": False}})
    isolated_devices = await db.devices.count_documents({"is_isolated": True})
    physical_devices = await db.devices.count_documents({"is_simulation": False})
    simulation_devices = await db.devices.count_documents({"is_simulation": {"$ne": False}})
    total_threats = await db.attack_events.count_documents({})
    critical_threats = await db.attack_events.count_documents({"severity": "CRITICAL"})
    total_predictions = await db.predictions.count_documents({})

    return {
        "total_devices": total_devices,
        "online_devices": online_devices,
        "physical_devices": physical_devices,
        "simulation_devices": simulation_devices,
        "total_threats": total_threats,
        "critical_threats": critical_threats,
        "isolated_devices": isolated_devices,
        "total_predictions": total_predictions,
    }


@router.get("/metrics", summary="AI Model Metrics")
async def ai_metrics():
    """Get latest AI model performance metrics."""
    report_path = Path(settings.project_root) / "reports" / "full_training_report.json"
    if not report_path.exists():
        return {"message": "No training report. Run: python -m ai_engine"}
    with open(report_path) as f:
        return json.load(f)


@router.get("/comparison", summary="Model Comparison")
async def model_comparison():
    """Get model comparison data."""
    report_path = Path(settings.project_root) / "reports" / "model_report.json"
    if not report_path.exists():
        return {"message": "No comparison report. Run training first."}
    with open(report_path) as f:
        return json.load(f)
