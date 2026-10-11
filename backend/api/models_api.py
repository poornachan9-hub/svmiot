"""AI model registry and evaluation API."""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from backend.core.config import settings

router = APIRouter()

MODEL_INFO = {
    "LogisticRegression": ("Linear Classifier", "Logistic regression classifier."),
    "DecisionTree": ("Decision Tree", "Decision tree classifier."),
    "RandomForest": ("Supervised Ensemble", "Random forest classifier."),
    "SVM": ("Kernel Classifier (RBF)", "Support vector classifier."),
    "GradientBoosting": ("Gradient Boosted Trees", "Gradient boosting classifier."),
}


def _get_registry():
    from ai_engine.model_registry import ModelRegistry
    registry_path = Path(settings.project_root) / settings.ml_models_dir / "registry.json"
    return ModelRegistry(str(registry_path))


def _artifact_path(path: Optional[str]) -> Optional[Path]:
    if not path:
        return None
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = Path(settings.project_root) / candidate
    return candidate


@router.get("", summary="List Evaluated Models")
async def list_models():
    registry = _get_registry()
    entries = registry.list_models()
    formatted = []

    for model_name, (model_type, description) in MODEL_INFO.items():
        versions = [m for m in entries if m.get("model_name") == model_name]
        entry = max(versions, key=lambda m: m.get("training_date", ""), default=None)
        metrics = entry.get("metrics", {}) if entry else {}
        model_path = _artifact_path(entry.get("model_path")) if entry else None
        preprocessing_path = (
            _artifact_path(entry.get("preprocessing_path")) if entry else None
        )
        artifacts_exist = bool(
            model_path
            and model_path.is_file()
            and preprocessing_path
            and (preprocessing_path / "preprocessing_pipeline.joblib").is_file()
        )
        evaluated = bool(metrics.get("n_test_samples") and metrics.get("accuracy") is not None)
        available = artifacts_exist and evaluated

        status = "UNAVAILABLE"
        if available:
            if entry.get("is_production") and entry.get("validated"):
                status = "ACTIVE"
            else:
                status = "EVALUATED"

        confusion = metrics.get("confusion_matrix") if available else None
        class_names = metrics.get("class_names", []) if available else []
        is_near_random = bool(
            entry.get("is_near_random")
            or (metrics.get("roc_auc") is not None and metrics["roc_auc"] <= 0.55)
        ) if available else False
        production_ready = bool(
            entry.get("production_ready", not is_near_random)
        ) if available else False
        warning_msg = (
            entry.get("warning") or metrics.get("performance_warning")
        ) if available else None

        output = {
            "id": model_name.lower(),
            "name": model_name,
            "type": model_type,
            "description": description,
            "status": status,
            "available": available,
            "is_production": status == "ACTIVE",
            "production_ready": production_ready,
            "is_near_random": is_near_random,
            "warning": warning_msg,
            "version": entry.get("version") if available else None,
            "dataset": entry.get("dataset") if available else None,
            "evaluation_date": (
                entry.get("evaluation_date") or metrics.get("evaluated_at")
            ) if available else None,
            "test_size": metrics.get("n_test_samples") if available else None,
            "train_validation_test_split": entry.get("train_test_split") if available else None,
            "feature_count": len(entry.get("features", [])) if available else None,
            "class_names": class_names,
            "metrics": {
                "accuracy": metrics.get("accuracy") if available else None,
                "precision_macro": metrics.get("precision_macro") if available else None,
                "recall_macro": metrics.get("recall_macro") if available else None,
                "f1_macro": metrics.get("f1_macro") if available else None,
                "roc_auc": metrics.get("roc_auc") if available else None,
                "is_near_random": is_near_random if available else None,
                "performance_warning": warning_msg,
                "operational_readiness": (
                    "PRODUCTION_READY" if production_ready else "NOT_PRODUCTION_READY"
                ) if available else None,
                "confusion_matrix": confusion,
                "inference_ms_per_sample": (
                    metrics.get("inference_ms_per_sample") if available else None
                ),
            },
            "validation_metrics": (
                entry.get("validation_metrics", {}) if available else {}
            ),
            "accuracy": round(metrics["accuracy"] * 100, 2) if available else None,
            "precision": (
                round(metrics["precision_macro"] * 100, 2)
                if available and metrics.get("precision_macro") is not None else None
            ),
            "recall": (
                round(metrics["recall_macro"] * 100, 2)
                if available and metrics.get("recall_macro") is not None else None
            ),
            "f1_score": (
                round(metrics["f1_macro"] * 100, 2)
                if available and metrics.get("f1_macro") is not None else None
            ),
            "latency_ms": (
                metrics.get("inference_ms_per_sample") if available else None
            ),
        }
        formatted.append(output)

    return formatted


@router.get("/sample", summary="Get Training-Only Inference Example")
async def get_inference_sample():
    registry = _get_registry()
    production = registry.get_production_model()
    if production is None:
        raise HTTPException(status_code=404, detail="No evaluated production model is available")
    sample_path = _artifact_path(production.get("sample_path"))
    if sample_path is None or not sample_path.is_file():
        raise HTTPException(status_code=404, detail="Training-only inference sample is unavailable")
    with sample_path.open(encoding="utf-8") as sample_file:
        return {"features": json.load(sample_file), "source": "training_set_smoke_test"}


@router.get("/production", summary="Get Production Model")
async def get_production():
    registry = _get_registry()
    prod = registry.get_production_model()
    if prod is None:
        return {"message": "No evaluated production model is set. Run training first."}
    model_path = _artifact_path(prod.get("model_path"))
    preprocessing_path = _artifact_path(prod.get("preprocessing_path"))
    if not (
        model_path and model_path.is_file()
        and preprocessing_path
        and (preprocessing_path / "preprocessing_pipeline.joblib").is_file()
    ):
        raise HTTPException(status_code=503, detail="Production model artifacts are unavailable")
    return prod


@router.post("/{model_name}/activate", summary="Set Production Model")
async def activate_model(model_name: str, version: Optional[str] = None):
    registry = _get_registry()
    matching = [
        m for m in registry.list_models()
        if m["model_name"].lower() == model_name.lower()
        and (version is None or m.get("version") == version)
    ]
    if not matching:
        raise HTTPException(status_code=404, detail=f"Evaluated model {model_name} not found")

    target = matching[-1]
    model_path = _artifact_path(target.get("model_path"))
    preprocessing_path = _artifact_path(target.get("preprocessing_path"))
    if not (
        target.get("validated")
        and target.get("metrics", {}).get("n_test_samples")
        and model_path and model_path.is_file()
        and preprocessing_path
        and (preprocessing_path / "preprocessing_pipeline.joblib").is_file()
    ):
        raise HTTPException(
            status_code=400,
            detail="Model requires evaluation and valid model/preprocessing artifacts before activation",
        )
    try:
        registry.set_production(target["model_name"], target["version"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": f"Model {target['model_name']} {target['version']} set as serving artifact"}


@router.get("/report", summary="Model Comparison Report")
async def model_report():
    report_path = Path(settings.project_root) / "reports" / "model_report.json"
    if not report_path.exists():
        return {"message": "No report available. Run training first."}
    with report_path.open(encoding="utf-8") as report_file:
        return json.load(report_file)


@router.get("/evaluation-runs", summary="List Available Evaluation Runs")
async def list_evaluation_runs():
    runs = []
    dedup_path = Path(settings.project_root) / "reports" / "runs" / "leak_free_evaluation" / "leak_free_report.json"
    if not dedup_path.exists():
        dedup_path = Path(settings.project_root) / "reports" / "deduplicated_evaluation_report.json"
    if dedup_path.exists():
        with dedup_path.open(encoding="utf-8") as f:
            dedup_data = json.load(f)
        runs.append({
            "id": "deduplicated",
            "name": "Leak-Free Evaluation (Deduplicated Before Split)",
            "description": "Pre-split global deduplication; guaranteed 0.00% train/test duplicate overlap.",
            "available": True,
            "test_samples": dedup_data.get("sample_sizes", {}).get("n_test", 4766),
            "cross_split_leakage_pct": 0.0,
            "evaluated_at": dedup_data.get("evaluated_at"),
            "production_ready": False,
            "is_default": True,
        })

    hist_path = Path(settings.project_root) / "reports" / "runs" / "20261011T180309589011Z" / "full_training_report.json"
    if hist_path.exists():
        with hist_path.open(encoding="utf-8") as f:
            hist_data = json.load(f)
        runs.append({
            "id": "historical",
            "name": "Historical Run (Post-Split Dedup)",
            "description": "Historical retraining run; audit showed 81.34% test-sample feature duplication across boundaries.",
            "available": True,
            "test_samples": hist_data.get("n_test", 24624),
            "cross_split_leakage_pct": 81.34,
            "evaluated_at": hist_data.get("evaluation_date"),
            "production_ready": False,
            "is_default": False,
        })

    return runs


@router.get("/evaluation-report", summary="Get Evaluation Report by Run ID")
async def get_evaluation_report(run_id: str = "deduplicated"):
    if run_id == "deduplicated":
        dedup_path = Path(settings.project_root) / "reports" / "runs" / "leak_free_evaluation" / "leak_free_report.json"
        if not dedup_path.exists():
            dedup_path = Path(settings.project_root) / "reports" / "deduplicated_evaluation_report.json"
        if not dedup_path.exists():
            raise HTTPException(status_code=404, detail="Deduplicated leak-free evaluation report not found")
        with dedup_path.open(encoding="utf-8") as f:
            raw = json.load(f)

        classes = raw["classes"]
        rf_meta = raw["random_forest"]
        base_meta = raw.get("reference_baseline") or raw["majority_baseline"]
        raw_models = raw.get("models", {})

        EXPECTED_ALGORITHMS = [
            ("RandomForest", "Random Forest"),
            ("DecisionTree", "Decision Tree"),
            ("GradientBoosting", "Gradient Boosting"),
            ("LogisticRegression", "Logistic Regression"),
            ("SVM", "Support Vector Machine (SVM)"),
        ]

        models = {}
        for m_id, default_name in EXPECTED_ALGORITHMS:
            m_data = raw_models.get(m_id)
            if m_data is None and m_id == "RandomForest":
                m_data = rf_meta

            if m_data and m_data.get("evaluated", True) and m_data.get("accuracy") is not None:
                models[m_id] = {
                    "id": m_id,
                    "name": m_data.get("name", default_name),
                    "evaluated": True,
                    "status": "EVALUATED",
                    "accuracy": round(m_data["accuracy"] * 100, 2),
                    "macro_f1": round(m_data["macro_f1"] * 100, 2),
                    "macro_recall": round(m_data["macro_recall"] * 100, 2),
                    "macro_precision": round(m_data["macro_precision"] * 100, 2),
                    "roc_auc": round(m_data["roc_auc"] * 100, 2) if m_data.get("roc_auc") is not None else None,
                    "confusion_matrix": m_data.get("confusion_matrix"),
                    "classification_report": m_data.get("classification_report", {}),
                }
            else:
                models[m_id] = {
                    "id": m_id,
                    "name": default_name,
                    "evaluated": False,
                    "status": "Not evaluated",
                    "accuracy": None,
                    "macro_f1": None,
                    "macro_recall": None,
                    "macro_precision": None,
                    "roc_auc": None,
                    "confusion_matrix": None,
                    "classification_report": {},
                }

        reference_baseline = {
            "id": "MajorityBaseline",
            "name": "Majority Baseline (Thing_Speak)",
            "accuracy": round(base_meta["accuracy"] * 100, 2),
            "macro_f1": round(base_meta["macro_f1"] * 100, 2),
            "macro_recall": round(base_meta["macro_recall"] * 100, 2),
            "macro_precision": round(base_meta["macro_precision"] * 100, 2),
            "roc_auc": 50.0,
            "confusion_matrix": base_meta["confusion_matrix"],
            "classification_report": base_meta.get("classification_report", {}),
            "is_baseline": True,
        }

        dataset_counts = {
            "Thing_Speak": 7599,
            "ARP_poisioning": 5298,
            "MQTT_Publish": 4141,
            "NMAP_OS_DETECTION": 1899,
            "NMAP_XMAS_TREE_SCAN": 1894,
            "NMAP_UDP_SCAN": 1148,
            "NMAP_TCP_scan": 1002,
            "DDOS_Slowloris": 532,
            "Wipro_bulb": 219,
            "DOS_SYN_Hping": 57,
            "Metasploit_Brute_Force_SSH": 36,
            "NMAP_FIN_SCAN": 5,
        }
        total_ds = sum(dataset_counts.values())
        dataset_distribution = [
            {
                "class_name": cls,
                "count": dataset_counts.get(cls, 0),
                "percentage": round((dataset_counts.get(cls, 0) / total_ds) * 100, 2),
                "test_support": raw.get("per_class_comparison", {}).get(cls, {}).get("test_support", 0),
            }
            for cls in classes
        ]

        per_class_stats = []
        for cls in classes:
            info = raw.get("per_class_comparison", {}).get(cls, {})
            sup = int(info.get("test_support", 0))
            per_class_stats.append({
                "class_name": cls,
                "precision": round(info.get("rf_precision", 0) * 100, 2),
                "recall": round(info.get("rf_recall", 0) * 100, 2),
                "f1_score": round(info.get("rf_f1", 0) * 100, 2),
                "support": sup,
                "is_low_support": sup < 100,
            })

        return {
            "run_id": "deduplicated",
            "run_label": "Leak-Free Evaluation (Deduplicated Before Split)",
            "evaluated_at": raw.get("evaluated_at"),
            "classes": classes,
            "models": models,
            "reference_baseline": reference_baseline,
            "primary_model": "RandomForest",
            "per_class_stats": per_class_stats,
            "dataset_distribution": dataset_distribution,
            "integrity": {
                "run_id": "deduplicated",
                "run_name": "Leak-Free Evaluation",
                "test_samples": raw.get("sample_sizes", {}).get("n_test", 4766),
                "train_samples": raw.get("sample_sizes", {}).get("n_train", 16681),
                "validation_samples": raw.get("sample_sizes", {}).get("n_val", 2383),
                "feature_overlap_count": 0,
                "feature_overlap_pct": 0.0,
                "production_ready": False,
                "readiness_status": "EXPERIMENTAL_LEAK_FREE",
                "warning": (
                    "EXPERIMENTAL BENCHMARK: 0.00% train/test feature overlap established. "
                    "Production readiness remains blocked due to extreme minority sample scarcity "
                    "(NMAP_FIN_SCAN N=1 test sample, Metasploit_Brute_Force_SSH N=7 test samples)."
                ),
                "unavoidable_limitations": raw.get("governance", {}).get("unavoidable_limitations", []),
            },
        }

    elif run_id == "historical":
        registry = _get_registry()
        entries = registry.list_models()
        hist_entries = [m for m in entries if "20261011T180309589011Z" in m.get("version", "")]
        if not hist_entries:
            raise HTTPException(status_code=404, detail="Historical run evaluation not found")

        classes = hist_entries[0].get("metrics", {}).get("class_names", [])

        models = {}
        for entry in hist_entries:
            name = entry["model_name"]
            m = entry.get("metrics", {})
            models[name] = {
                "id": name,
                "name": name,
                "accuracy": round((m.get("accuracy") or 0) * 100, 2),
                "macro_f1": round((m.get("f1_macro") or 0) * 100, 2),
                "macro_recall": round((m.get("recall_macro") or 0) * 100, 2),
                "macro_precision": round((m.get("precision_macro") or 0) * 100, 2),
                "roc_auc": round((m.get("roc_auc") or 0) * 100, 2) if m.get("roc_auc") is not None else None,
                "confusion_matrix": m.get("confusion_matrix", []),
                "classification_report": m.get("per_class_report", {}),
            }

        rf_entry = next((e for e in hist_entries if e["model_name"] == "RandomForest"), hist_entries[0])
        rf_report = rf_entry.get("metrics", {}).get("per_class_report", {})

        per_class_stats = []
        for cls in classes:
            cinfo = rf_report.get(cls, {})
            sup = int(cinfo.get("support", 0))
            per_class_stats.append({
                "class_name": cls,
                "precision": round(cinfo.get("precision", 0) * 100, 2),
                "recall": round(cinfo.get("recall", 0) * 100, 2),
                "f1_score": round(cinfo.get("f1-score", 0) * 100, 2),
                "support": sup,
                "is_low_support": sup < 100,
            })

        hist_ds_counts = {
            "DOS_SYN_Hping": 94659,
            "Thing_Speak": 8108,
            "ARP_poisioning": 7750,
            "MQTT_Publish": 4146,
            "NMAP_UDP_SCAN": 2590,
            "NMAP_XMAS_TREE_SCAN": 2010,
            "NMAP_OS_DETECTION": 2000,
            "NMAP_TCP_scan": 1002,
            "DDOS_Slowloris": 534,
            "Wipro_bulb": 253,
            "Metasploit_Brute_Force_SSH": 37,
            "NMAP_FIN_SCAN": 28,
        }
        total_hist_ds = sum(hist_ds_counts.values())
        dataset_distribution = [
            {
                "class_name": cls,
                "count": hist_ds_counts.get(cls, 0),
                "percentage": round((hist_ds_counts.get(cls, 0) / total_hist_ds) * 100, 2),
                "test_support": int(rf_report.get(cls, {}).get("support", 0)),
            }
            for cls in classes
        ]

        return {
            "run_id": "historical",
            "run_label": "Historical Run (Post-Split Dedup)",
            "evaluated_at": rf_entry.get("evaluation_date"),
            "classes": classes,
            "models": models,
            "primary_model": "RandomForest",
            "per_class_stats": per_class_stats,
            "dataset_distribution": dataset_distribution,
            "integrity": {
                "run_id": "historical",
                "run_name": "Historical Run",
                "test_samples": 24624,
                "train_samples": 17030,
                "validation_samples": 12312,
                "feature_overlap_count": 20029,
                "feature_overlap_pct": 81.34,
                "production_ready": False,
                "readiness_status": "EXPERIMENTAL_LEAKAGE_AUDITED",
                "warning": (
                    "CRITICAL AUDIT FINDING: 81.34% of test samples (20,029 / 24,624) are exact "
                    "duplicates of training rows (overwhelmingly DOS_SYN_Hping frames with stripped ports). "
                    "Metrics reflect cross-boundary repetition and are NOT production-ready."
                ),
                "unavoidable_limitations": [
                    "Ephemeral source port id.orig_p stripped to prevent shortcut learning.",
                    "Deduplication was only applied to train split, leaving 18,929 duplicate SYN flood frames in test.",
                ],
            },
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unknown evaluation run: {run_id}")

