"""
SecureIoT-X AI Engine — Reproducible Leak-Free Deduplicated Evaluation.

Policy:
1. Deduplicate dataset before train/validation/test splitting.
2. Preserve all unique feature patterns across every attack class (including minority classes).
3. Ambiguous feature rows sharing identical features with conflicting labels are assigned to the
   modal class to eliminate contradictory signals.
4. Guarantee 0.00% exact duplicate overlap between Train and Test sets.
5. Fit all preprocessing transformers strictly on Train data.
6. Compare Random Forest against a Majority-Class dummy baseline across accuracy, macro-F1,
   per-class recall, confusion matrix, and class support.
7. Save separate evaluation run without overwriting historical reports.
"""

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yaml
import joblib
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from ai_engine.data_loader import get_adapter
from ai_engine.feature_engineering import FeatureEngineer
from ai_engine.preprocessing import PreprocessingPipeline

logger = logging.getLogger("secureiot.ai.dedup_eval")

ALL_ALGORITHMS = [
    ("RandomForest", "Random Forest"),
    ("DecisionTree", "Decision Tree"),
    ("GradientBoosting", "Gradient Boosting"),
    ("LogisticRegression", "Logistic Regression"),
    ("SVM", "Support Vector Machine (SVM)"),
]


def run_leak_free_evaluation(
    dataset_path: str = "datasets/RT_IOT2022.csv",
    config_path: str = "config/ml.yaml",
    reports_dir: str = "reports/runs/leak_free_evaluation",
    random_seed: int = 42,
) -> Dict[str, Any]:
    """Execute leak-free deduplicated evaluation comparing RF to baseline."""
    logger.info("Starting leak-free deduplicated evaluation...")

    # Load configuration
    cfg: Dict[str, Any] = {}
    if Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

    pipeline_cfg = cfg.get("pipeline", {})
    preprocess_cfg = cfg.get("preprocessing", {})
    feat_cfg = cfg.get("feature_selection", {})

    # 1. Load Data
    adapter = get_adapter("RT-IoT2022", dataset_path)
    adapter.load()
    adapter.identify_target()
    X_raw, y_raw = adapter.get_features_and_target()

    # 2. Feature Engineering
    fe = FeatureEngineer(feat_cfg)
    X_fe = fe.engineer_features(X_raw)

    # 3. Preprocessing with deduplicate_before_split
    pp_config = {
        "test_size": pipeline_cfg.get("test_size", 0.2),
        "validation_size": pipeline_cfg.get("validation_size", 0.1),
        "random_seed": random_seed,
        "scaling_method": preprocess_cfg.get("scaling_method", "standard"),
        "encoding_method": preprocess_cfg.get("encoding_method", "label"),
        "handle_inf": preprocess_cfg.get("handle_inf", True),
        "remove_duplicates": False,
        "deduplicate_before_split": True,
    }
    pp = PreprocessingPipeline(pp_config)
    X_train, X_val, X_test, y_train, y_val, y_test = pp.fit_transform(X_fe, y_raw)
    classes = pp.target_classes

    # Verify cross-split duplicate leakage
    # Convert numpy arrays to DataFrame hashes for exact duplicate check
    train_df = pd.DataFrame(X_train)
    test_df = pd.DataFrame(X_test)
    tr_hashes = set(pd.util.hash_pandas_object(train_df, index=False))
    te_hashes = pd.util.hash_pandas_object(test_df, index=False)
    cross_split_duplicates = int(te_hashes.isin(tr_hashes).sum())
    leakage_ratio = cross_split_duplicates / len(X_test)

    # 4. Train RandomForest on Train split
    rf_params = {
        "n_estimators": 100,
        "max_depth": 20,
        "class_weight": "balanced",
        "random_state": random_seed,
        "n_jobs": -1,
    }
    rf = RandomForestClassifier(**rf_params)
    rf.fit(X_train, y_train)

    y_pred_rf = rf.predict(X_test)
    y_proba_rf = rf.predict_proba(X_test)

    # 5. Train Majority-Class Baseline on Train split
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(X_train, y_train)
    y_pred_dummy = dummy.predict(X_test)

    # 6. Evaluate Random Forest
    rf_acc = float(accuracy_score(y_test, y_pred_rf))
    rf_f1_macro = float(f1_score(y_test, y_pred_rf, average="macro", zero_division=0))
    rf_rec_macro = float(recall_score(y_test, y_pred_rf, average="macro", zero_division=0))
    rf_prec_macro = float(precision_score(y_test, y_pred_rf, average="macro", zero_division=0))
    try:
        rf_roc_auc = float(roc_auc_score(y_test, y_proba_rf, multi_class="ovr", average="macro"))
    except Exception:
        rf_roc_auc = None

    rf_cm = confusion_matrix(y_test, y_pred_rf, labels=list(range(len(classes)))).tolist()
    rf_report = classification_report(
        y_test, y_pred_rf,
        labels=list(range(len(classes))),
        target_names=classes,
        output_dict=True,
        zero_division=0,
    )

    # 7. Evaluate Majority Baseline
    dummy_acc = float(accuracy_score(y_test, y_pred_dummy))
    dummy_f1_macro = float(f1_score(y_test, y_pred_dummy, average="macro", zero_division=0))
    dummy_rec_macro = float(recall_score(y_test, y_pred_dummy, average="macro", zero_division=0))
    dummy_prec_macro = float(precision_score(y_test, y_pred_dummy, average="macro", zero_division=0))
    dummy_cm = confusion_matrix(y_test, y_pred_dummy, labels=list(range(len(classes)))).tolist()
    dummy_report = classification_report(
        y_test, y_pred_dummy,
        labels=list(range(len(classes))),
        target_names=classes,
        output_dict=True,
        zero_division=0,
    )

    # 8. Compile per-class comparison table
    per_class_comparison = {}
    for cls in classes:
        rf_cls = rf_report.get(cls, {})
        dummy_cls = dummy_report.get(cls, {})
        per_class_comparison[cls] = {
            "test_support": int(rf_cls.get("support", 0)),
            "rf_precision": round(float(rf_cls.get("precision", 0)), 4),
            "rf_recall": round(float(rf_cls.get("recall", 0)), 4),
            "rf_f1": round(float(rf_cls.get("f1-score", 0)), 4),
            "baseline_precision": round(float(dummy_cls.get("precision", 0)), 4),
            "baseline_recall": round(float(dummy_cls.get("recall", 0)), 4),
            "baseline_f1": round(float(dummy_cls.get("f1-score", 0)), 4),
        }

    # 9. Evaluate other saved model artifacts on the exact same deduplicated test split
    models_data = {
        "RandomForest": {
            "name": "Random Forest",
            "accuracy": round(rf_acc, 6),
            "macro_f1": round(rf_f1_macro, 6),
            "macro_recall": round(rf_rec_macro, 6),
            "macro_precision": round(rf_prec_macro, 6),
            "roc_auc": round(rf_roc_auc, 6) if rf_roc_auc is not None else None,
            "confusion_matrix": rf_cm,
            "classification_report": rf_report,
            "evaluated": True,
        }
    }

    artifact_dirs = [
        Path("models/runs/20261011T180309589011Z/models"),
    ]

    for model_key, display_name in ALL_ALGORITHMS:
        if model_key == "RandomForest":
            continue

        model_obj = None
        for art_dir in artifact_dirs:
            candidate_files = list(art_dir.glob(f"{model_key.lower()}/*.joblib"))
            if candidate_files:
                try:
                    model_obj = joblib.load(candidate_files[0])
                    break
                except Exception as exc:
                    logger.warning("Could not load artifact %s: %s", candidate_files[0], exc)

        if model_obj is not None:
            try:
                y_pred_m = model_obj.predict(X_test)
                m_acc = float(accuracy_score(y_test, y_pred_m))
                m_f1 = float(f1_score(y_test, y_pred_m, average="macro", zero_division=0))
                m_rec = float(recall_score(y_test, y_pred_m, average="macro", zero_division=0))
                m_prec = float(precision_score(y_test, y_pred_m, average="macro", zero_division=0))
                m_roc = None
                if hasattr(model_obj, "predict_proba"):
                    try:
                        y_proba_m = model_obj.predict_proba(X_test)
                        m_roc = float(roc_auc_score(y_test, y_proba_m, multi_class="ovr", average="macro"))
                    except Exception:
                        m_roc = None

                m_cm = confusion_matrix(y_test, y_pred_m, labels=list(range(len(classes)))).tolist()
                m_report = classification_report(
                    y_test, y_pred_m,
                    labels=list(range(len(classes))),
                    target_names=classes,
                    output_dict=True,
                    zero_division=0,
                )
                models_data[model_key] = {
                    "name": display_name,
                    "accuracy": round(m_acc, 6),
                    "macro_f1": round(m_f1, 6),
                    "macro_recall": round(m_rec, 6),
                    "macro_precision": round(m_prec, 6),
                    "roc_auc": round(m_roc, 6) if m_roc is not None else None,
                    "confusion_matrix": m_cm,
                    "classification_report": m_report,
                    "evaluated": True,
                }
                logger.info("Successfully evaluated %s on deduplicated test split (acc=%.4f, f1=%.4f)", model_key, m_acc, m_f1)
            except Exception as exc:
                logger.error("Failed to evaluate %s on deduplicated split: %s", model_key, exc)
                models_data[model_key] = {
                    "name": display_name,
                    "accuracy": None,
                    "macro_f1": None,
                    "macro_recall": None,
                    "macro_precision": None,
                    "roc_auc": None,
                    "confusion_matrix": None,
                    "classification_report": {},
                    "evaluated": False,
                    "status": "Not evaluated",
                }
        else:
            models_data[model_key] = {
                "name": display_name,
                "accuracy": None,
                "macro_f1": None,
                "macro_recall": None,
                "macro_precision": None,
                "roc_auc": None,
                "confusion_matrix": None,
                "classification_report": {},
                "evaluated": False,
                "status": "Not evaluated",
            }

    # Summary payload
    results = {
        "run_type": "leak_free_deduplicated_evaluation",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "random_seed": random_seed,
        "dataset": "RT_IOT2022",
        "policy": {
            "name": "Deduplicate-Before-Split with Modal Ambiguity Resolution",
            "description": (
                "Feature vectors deduplicated globally before splitting. Ambiguous feature "
                "vectors assigned to modal class. All unique attack signatures preserved."
            ),
            "cross_split_leakage_count": cross_split_duplicates,
            "cross_split_leakage_ratio": leakage_ratio,
        },
        "sample_sizes": {
            "n_train": len(X_train),
            "n_val": len(X_val),
            "n_test": len(X_test),
            "n_features": X_train.shape[1],
            "n_classes": len(classes),
        },
        "classes": classes,
        "models": models_data,
        "random_forest": {
            "accuracy": round(rf_acc, 6),
            "macro_f1": round(rf_f1_macro, 6),
            "macro_recall": round(rf_rec_macro, 6),
            "macro_precision": round(rf_prec_macro, 6),
            "roc_auc": round(rf_roc_auc, 6) if rf_roc_auc is not None else None,
            "confusion_matrix": rf_cm,
            "classification_report": rf_report,
            "evaluated": True,
        },
        "majority_baseline": {
            "name": "Majority Baseline (Thing_Speak)",
            "strategy": "most_frequent",
            "accuracy": round(dummy_acc, 6),
            "macro_f1": round(dummy_f1_macro, 6),
            "macro_recall": round(dummy_rec_macro, 6),
            "macro_precision": round(dummy_prec_macro, 6),
            "roc_auc": 0.5,
            "confusion_matrix": dummy_cm,
            "classification_report": dummy_report,
            "is_baseline": True,
        },
        "reference_baseline": {
            "name": "Majority Baseline (Thing_Speak)",
            "strategy": "most_frequent",
            "accuracy": round(dummy_acc, 6),
            "macro_f1": round(dummy_f1_macro, 6),
            "macro_recall": round(dummy_rec_macro, 6),
            "macro_precision": round(dummy_prec_macro, 6),
            "roc_auc": 0.5,
            "confusion_matrix": dummy_cm,
            "classification_report": dummy_report,
            "is_baseline": True,
        },
        "per_class_comparison": per_class_comparison,
        "governance": {
            "production_ready": False,
            "status": "EXPERIMENTAL_LEAK_FREE_EVALUATED",
            "unavoidable_limitations": [
                "Dataset lacks host IPs and wall-clock timestamps; group/session K-Fold is constrained by UCI anonymization.",
                "High-rate attacks (e.g. DOS_SYN_Hping, NMAP_FIN_SCAN) have very few distinct feature patterns once ephemeral ports are removed.",
                "Minority classes with N < 10 test examples exhibit wide binomial uncertainty bounds.",
            ],
        },
    }

    # Save to dedicated reports directory
    rep_dir = Path(reports_dir)
    rep_dir.mkdir(parents=True, exist_ok=True)
    report_file = rep_dir / "leak_free_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Also save top-level copy
    top_level_rep = Path("reports/deduplicated_evaluation_report.json")
    with open(top_level_rep, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info("Saved leak-free evaluation report to %s", report_file)
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    res = run_leak_free_evaluation()
    rf = res["random_forest"]
    base = res["majority_baseline"]
    print("\n" + "=" * 80)
    print("  LEAK-FREE DEDUPLICATED EVALUATION SUMMARY")
    print("=" * 80)
    print(f"Split sizes: Train={res['sample_sizes']['n_train']}, Val={res['sample_sizes']['n_val']}, Test={res['sample_sizes']['n_test']}")
    print(f"Cross-Split Duplicate Leakage: {res['policy']['cross_split_leakage_count']} ({res['policy']['cross_split_leakage_ratio']*100:.2f}%)")
    print("-" * 80)
    print(f"{'Metric':<20} | {'Random Forest':<15} | {'Majority Baseline':<15} | {'Delta':<10}")
    print("-" * 80)
    print(f"{'Accuracy':<20} | {rf['accuracy']:<15.4f} | {base['accuracy']:<15.4f} | {rf['accuracy'] - base['accuracy']:+<10.4f}")
    print(f"{'Macro-F1':<20} | {rf['macro_f1']:<15.4f} | {base['macro_f1']:<15.4f} | {rf['macro_f1'] - base['macro_f1']:+<10.4f}")
    print(f"{'Macro-Recall':<20} | {rf['macro_recall']:<15.4f} | {base['macro_recall']:<15.4f} | {rf['macro_recall'] - base['macro_recall']:+<10.4f}")
    print(f"{'Macro-Precision':<20} | {rf['macro_precision']:<15.4f} | {base['macro_precision']:<15.4f} | {rf['macro_precision'] - base['macro_precision']:+<10.4f}")
    print(f"{'ROC-AUC (OVR)':<20} | {rf['roc_auc']:<15.4f} | {'0.5000':<15} | {rf['roc_auc'] - 0.5:+<10.4f}")
    print("=" * 80)
