"""
SecureIoT-X AI Engine — Model Evaluation & Comparison.

Generates per-model metrics, comparison tables, confusion matrices,
and selects the best model based on F1 + recall (not accuracy alone).
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    roc_auc_score,
    average_precision_score,
)

logger = logging.getLogger("secureiot.ai.evaluate")


def evaluate_model(
    model: Any,
    X_test: np.ndarray,
    y_test: np.ndarray,
    model_name: str,
    class_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Evaluate a single model and return comprehensive metrics.
    """
    # Inference timing
    start = time.perf_counter()
    y_pred = model.predict(X_test)
    inference_time = (time.perf_counter() - start) * 1000  # ms

    n_classes = len(class_names) if class_names else len(np.unique(y_test))
    is_binary = n_classes == 2
    labels = list(range(n_classes))
    average = "binary" if is_binary else "weighted"

    metrics: Dict[str, Any] = {
        "model_name": model_name,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 6),
        "precision": round(float(precision_score(y_test, y_pred, average=average, zero_division=0)), 6),
        "recall": round(float(recall_score(y_test, y_pred, average=average, zero_division=0)), 6),
        "f1": round(float(f1_score(y_test, y_pred, average=average, zero_division=0)), 6),
        "precision_weighted": round(float(precision_score(y_test, y_pred, average="weighted", zero_division=0)), 6),
        "recall_weighted": round(float(recall_score(y_test, y_pred, average="weighted", zero_division=0)), 6),
        "f1_weighted": round(float(f1_score(y_test, y_pred, average="weighted", zero_division=0)), 6),
        "precision_macro": round(float(precision_score(y_test, y_pred, average="macro", zero_division=0)), 6),
        "recall_macro": round(float(recall_score(y_test, y_pred, average="macro", zero_division=0)), 6),
        "f1_macro": round(float(f1_score(y_test, y_pred, average="macro", zero_division=0)), 6),
        "inference_time_ms": round(inference_time, 3),
        "inference_ms_per_sample": round(inference_time / max(len(y_test), 1), 6),
        "n_test_samples": len(y_test),
        "n_classes": n_classes,
        "class_names": class_names or labels,
    }

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    metrics["confusion_matrix"] = cm.tolist()

    # Per-class report
    report = classification_report(
        y_test, y_pred,
        labels=labels,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    metrics["per_class_report"] = report

    # ROC-AUC & PR-AUC (requires probability estimates)
    try:
        if hasattr(model, "predict_proba"):
            y_proba = model.predict_proba(X_test)
            model_classes = getattr(model, "classes_", np.arange(y_proba.shape[1]))
            if is_binary:
                positive_class = model_classes[1]
                positive_scores = y_proba[:, 1]
                metrics["roc_auc"] = round(
                    float(roc_auc_score(y_test == positive_class, positive_scores)), 6
                )
                metrics["pr_auc"] = round(
                    float(average_precision_score(y_test == positive_class, positive_scores)), 6
                )
            else:
                from sklearn.preprocessing import label_binarize
                if len(model_classes) == y_proba.shape[1] and len(model_classes) > 1:
                    metrics["roc_auc"] = round(float(roc_auc_score(
                        y_test, y_proba, labels=model_classes,
                        multi_class="ovr", average="macro"
                    )), 6)
                    y_test_bin = label_binarize(y_test, classes=model_classes)
                    metrics["pr_auc"] = round(float(average_precision_score(
                        y_test_bin, y_proba, average="macro"
                    )), 6)
                else:
                    raise ValueError("Model probability columns do not match its class labels")
    except Exception as e:
        logger.warning("Could not compute ROC-AUC / PR-AUC for %s: %s", model_name, e)
        metrics["roc_auc"] = None
        metrics["pr_auc"] = None
        metrics["roc_auc_error"] = str(e)

    # Detect near-random performance
    roc = metrics.get("roc_auc")
    f1_m = metrics.get("f1_macro", 0.0)
    is_near_random = False
    if roc is not None and roc <= 0.55:
        is_near_random = True
    elif roc is None and n_classes > 2 and f1_m <= (1.2 / n_classes):
        is_near_random = True

    metrics["is_near_random"] = is_near_random
    if is_near_random:
        metrics["performance_warning"] = (
            f"Model '{model_name}' performs near random chance "
            f"(ROC-AUC={roc}, F1-macro={f1_m:.4f}). "
            "Features lack predictive attack signal on this evaluation set."
        )
        metrics["operational_readiness"] = "NOT_PRODUCTION_READY"
        logger.warning(
            "Near-random performance detected for %s: ROC-AUC=%s, F1=%s. Model is NOT production-ready.",
            model_name, roc, f1_m,
        )
    else:
        metrics["performance_warning"] = None
        metrics["operational_readiness"] = "PRODUCTION_READY"

    return metrics


def evaluate_all_models(
    train_results: List[Dict[str, Any]],
    X_test: np.ndarray,
    y_test: np.ndarray,
    class_names: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Evaluate all trained models and add metrics to results."""
    evaluated = []

    for result in train_results:
        model = result.get("model")
        if model is None:
            continue

        name = result["name"]
        logger.info("Evaluating: %s", name)

        try:
            metrics = evaluate_model(model, X_test, y_test, name, class_names)
            result["metrics"] = metrics
            evaluated.append(result)

            logger.info("  Accuracy: %.4f | F1: %.4f | Recall: %.4f | Inference: %.1fms",
                        metrics["accuracy"], metrics["f1_weighted"],
                        metrics["recall_weighted"], metrics["inference_time_ms"])

        except Exception as e:
            logger.error("  [FAIL] Evaluation failed for %s: %s", name, e)

    return evaluated


def select_best_model(
    evaluated_results: List[Dict[str, Any]],
    primary_metric: str = "f1_macro",
    secondary_metric: str = "recall_macro",
) -> Dict[str, Any]:
    """
    Select the best model based on F1 (primary) and recall (secondary).
    Does NOT select solely by accuracy — considers false negatives.
    """
    if not evaluated_results:
        raise ValueError("No evaluated models to select from")

    # Sort by primary metric desc, then secondary desc
    sorted_results = sorted(
        evaluated_results,
        key=lambda r: (
            r.get("metrics", {}).get(primary_metric, 0),
            r.get("metrics", {}).get(secondary_metric, 0),
        ),
        reverse=True,
    )

    best = sorted_results[0]
    logger.info("Best model: %s (macro-F1=%.4f, macro-recall=%.4f)",
                best["name"],
                best["metrics"][primary_metric],
                best["metrics"][secondary_metric])
    if best.get("metrics", {}).get("is_near_random"):
        logger.warning(
            "Selected model '%s' performs near random chance. It is NOT operationally reliable.",
            best["name"],
        )

    return best


def generate_comparison_report(
    evaluated_results: List[Dict[str, Any]],
    save_path: str = "reports",
) -> Dict[str, Any]:
    """Generate a model comparison report and save as JSON."""
    report_dir = Path(save_path)
    report_dir.mkdir(parents=True, exist_ok=True)

    comparison = []
    for r in evaluated_results:
        m = r.get("metrics", {})
        comparison.append({
            "model": r["name"],
            "version": r.get("version", "?"),
            "accuracy": m.get("accuracy"),
            "precision_macro": m.get("precision_macro"),
            "recall_macro": m.get("recall_macro"),
            "f1_macro": m.get("f1_macro"),
            "precision_weighted": m.get("precision_weighted"),
            "recall_weighted": m.get("recall_weighted"),
            "f1_weighted": m.get("f1_weighted"),
            "f1_macro": m.get("f1_macro"),
            "roc_auc": m.get("roc_auc"),
            "inference_time_ms": m.get("inference_time_ms"),
            "training_time_s": r.get("training_time_seconds"),
            "model_size_bytes": r.get("model_size_bytes"),
        })

    # Sort deterministically by macro F1 then macro recall.
    comparison.sort(
        key=lambda c: (
            c.get("f1_macro") if c.get("f1_macro") is not None else -1.0,
            c.get("recall_macro") if c.get("recall_macro") is not None else -1.0,
        ),
        reverse=True,
    )

    report = {
        "comparison": comparison,
        "highest_test_macro_f1_model": comparison[0]["model"] if comparison else None,
        "selection_criteria": (
            "Production selection uses validation macro-F1 then macro recall; "
            "this report contains descriptive held-out test metrics."
        ),
        "note": "These are OUR implementation results, not reference paper results.",
    }

    # Save JSON
    json_path = report_dir / "model_report.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info("Comparison report saved to %s", json_path)

    # Print comparison table in ranked order.
    _print_comparison_table(comparison)

    return report


def _print_comparison_table(comparison: List[Dict[str, Any]]) -> None:
    """Pretty-print model comparison table in ranked order."""
    print("\n" + "=" * 100)
    print("MODEL COMPARISON REPORT (RANKED BY MACRO-F1 ON TEST SET)")
    print("=" * 100)
    header = f"{'Rank':<5} {'Model':<22} {'Accuracy':>10} {'Macro P':>10} {'Macro R':>10} {'Macro F1':>10} {'ROC-AUC':>10} {'Infer(ms)':>10}"
    print(header)
    print("-" * 100)
    for i, c in enumerate(comparison, 1):
        roc = f"{c.get('roc_auc'):.4f}" if isinstance(c.get('roc_auc'), (int, float)) else "N/A"
        row = (
            f"#{i:<4} "
            f"{c['model']:<22} "
            f"{c.get('accuracy', 0):>10.4f} "
            f"{c.get('precision_macro', 0):>10.4f} "
            f"{c.get('recall_macro', 0):>10.4f} "
            f"{c.get('f1_macro', 0):>10.4f} "
            f"{roc:>10} "
            f"{c.get('inference_time_ms', 0):>10.1f}"
        )
        print(row)
    print("=" * 100)
    if comparison:
        print(f"[*] Highest test-set macro F1: {comparison[0]['model']} (F1={comparison[0].get('f1_macro', 0):.4f})")
    print()
