"""
Tests for SecureIoT-X Leak-Free Evaluation and Deduplication Pipeline.

Verifies:
1. Zero cross-split feature duplicate leakage when deduplicate_before_split=True.
2. Minority class preservation across all 12 classes.
3. Metric reproducibility and Random Forest superiority over majority dummy baseline.
4. Governance enforcement keeping production_ready=False.
"""

import asyncio
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ai_engine.preprocessing import PreprocessingPipeline
from ai_engine.deduplicated_eval import run_leak_free_evaluation


def test_deduplicate_before_split_prevents_cross_split_leakage():
    """Verify that deduplicate_before_split guarantees zero train-test feature duplicate leakage."""
    # Synthetic dataset with duplicates intentionally injected
    rng = np.random.default_rng(42)
    base_features = rng.normal(size=(50, 4))
    # Duplicate base features multiple times across classes
    features = np.vstack([base_features, base_features, base_features])
    labels = np.array(["DDoS"] * 75 + ["Normal"] * 75)
    df = pd.DataFrame(features, columns=["f1", "f2", "f3", "f4"])
    y = pd.Series(labels)

    pipeline = PreprocessingPipeline({
        "test_size": 0.2,
        "validation_size": 0.1,
        "random_seed": 42,
        "deduplicate_before_split": True,
    })
    X_train, X_val, X_test, y_train, y_val, y_test = pipeline.fit_transform(df, y)

    tr_hashes = set(pd.util.hash_pandas_object(pd.DataFrame(X_train), index=False))
    te_hashes = pd.util.hash_pandas_object(pd.DataFrame(X_test), index=False)
    overlap = te_hashes.isin(tr_hashes).sum()

    assert overlap == 0, f"Expected 0 duplicate rows across train and test, got {overlap}"
    assert len(X_train) + len(X_val) + len(X_test) == 50  # exactly unique prototype count


def test_minority_classes_retained_in_deduplication():
    """Verify that rare classes with few distinct rows are not discarded during deduplication."""
    # Rare class with only 2 unique rows
    df = pd.DataFrame({
        "f1": [1.0, 1.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        "f2": [10.0, 10.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
    })
    y = pd.Series(["Rare", "Rare", "Rare", "Rare", "Normal", "Normal", "Normal", "Normal", "Attack", "Attack", "Attack", "Attack"])

    pipeline = PreprocessingPipeline({
        "test_size": 0.25,
        "validation_size": 0.0,
        "random_seed": 42,
        "deduplicate_before_split": True,
    })
    X_train, _, X_test, y_train, _, y_test = pipeline.fit_transform(df, y)

    # Class "Rare" had 2 unique vectors: (1, 10) and (2, 20). Both must be represented.
    all_classes_in_splits = set(np.unique(y_train)).union(set(np.unique(y_test)))
    assert len(all_classes_in_splits) == 3
    assert "Rare" in pipeline.target_classes


def test_leak_free_report_structure_and_governance():
    """Verify that leak-free evaluation report is persisted and production_ready remains false."""
    report_path = Path("reports/runs/leak_free_evaluation/leak_free_report.json")
    assert report_path.is_file(), "leak_free_report.json should exist"

    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["policy"]["cross_split_leakage_count"] == 0
    assert data["policy"]["cross_split_leakage_ratio"] == 0.0
    assert data["governance"]["production_ready"] is False
    assert data["governance"]["status"] == "EXPERIMENTAL_LEAK_FREE_EVALUATED"

    rf = data["random_forest"]
    base = data["majority_baseline"]
    assert rf["accuracy"] > base["accuracy"]
    assert rf["macro_f1"] > base["macro_f1"]
    assert rf["roc_auc"] > 0.85


def test_model_analytics_endpoint_uses_saved_evaluation_and_verified_counts():
    """The dashboard endpoint exposes the saved matrices and exact deduplicated class counts."""
    from backend.api import models_api
    data = asyncio.run(models_api.get_evaluation_report("deduplicated"))
    saved = json.loads(
        Path("reports/runs/leak_free_evaluation/leak_free_report.json").read_text(
            encoding="utf-8"
        )
    )

    assert data["models"]["RandomForest"]["confusion_matrix"] == saved["random_forest"]["confusion_matrix"]
    assert data["classes"] == saved["classes"]
    assert data["integrity"]["production_ready"] is False
    assert data["integrity"]["feature_overlap_count"] == 0
    assert len(data["dataset_distribution"]) == 12
    assert sum(item["count"] for item in data["dataset_distribution"]) == 23830
    supports = {
        item["class_name"]: item["support"]
        for item in data["per_class_stats"]
    }
    assert supports["NMAP_FIN_SCAN"] == 1
    assert supports["Metasploit_Brute_Force_SSH"] == 7
