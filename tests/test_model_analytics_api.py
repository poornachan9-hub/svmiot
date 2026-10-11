"""
Tests for SecureIoT-X Model Analytics API and Evaluation Reports.

Verifies:
1. Evaluation runs endpoint returns available leak-free and historical runs.
2. Deduplicated evaluation confusion matrix total strictly equals 4,766.
3. Class ordering strictly matches the 12 sorted attack classes.
4. Low-support classes (NMAP_FIN_SCAN N=1, Metasploit_Brute_Force_SSH N=7) are flagged.
5. Historical evaluation metrics and confusion matrix sum equal 24,624.
"""

import asyncio
import pytest
from fastapi import HTTPException

from backend.api import models_api


EXPECTED_CLASSES = [
    "ARP_poisioning",
    "DDOS_Slowloris",
    "DOS_SYN_Hping",
    "MQTT_Publish",
    "Metasploit_Brute_Force_SSH",
    "NMAP_FIN_SCAN",
    "NMAP_OS_DETECTION",
    "NMAP_TCP_scan",
    "NMAP_UDP_SCAN",
    "NMAP_XMAS_TREE_SCAN",
    "Thing_Speak",
    "Wipro_bulb",
]


def test_list_evaluation_runs_returns_both_protocols():
    runs = asyncio.run(models_api.list_evaluation_runs())
    assert isinstance(runs, list)
    run_ids = [r["id"] for r in runs]
    assert "deduplicated" in run_ids
    assert "historical" in run_ids

    dedup = next(r for r in runs if r["id"] == "deduplicated")
    assert dedup["cross_split_leakage_pct"] == 0.0
    assert dedup["test_samples"] == 4766
    assert dedup["production_ready"] is False

    hist = next(r for r in runs if r["id"] == "historical")
    assert hist["cross_split_leakage_pct"] == 81.34
    assert hist["test_samples"] == 24624
    assert hist["production_ready"] is False


def test_deduplicated_evaluation_report_confusion_matrix_total_and_classes():
    report = asyncio.run(models_api.get_evaluation_report("deduplicated"))
    assert report["run_id"] == "deduplicated"
    assert report["classes"] == EXPECTED_CLASSES

    # Verify all 5 algorithms are present in models
    expected_models = ["RandomForest", "DecisionTree", "GradientBoosting", "LogisticRegression", "SVM"]
    for m_id in expected_models:
        assert m_id in report["models"], f"Model {m_id} missing from deduplicated evaluation report"
        model_info = report["models"][m_id]
        assert model_info["evaluated"] is True
        assert model_info["status"] == "EVALUATED"
        assert 0 <= model_info["accuracy"] <= 100
        assert 0 <= model_info["macro_f1"] <= 100
        assert 0 <= model_info["macro_recall"] <= 100
        assert 0 <= model_info["macro_precision"] <= 100
        if model_info["roc_auc"] is not None:
            assert 50 <= model_info["roc_auc"] <= 100

        cm = model_info["confusion_matrix"]
        assert len(cm) == 12
        assert all(len(row) == 12 for row in cm)
        total_samples = sum(sum(row) for row in cm)
        assert total_samples == 4766, f"Expected 4,766 samples for {m_id}, got {total_samples}"

    # Verify reference baseline is separate and marked
    assert "reference_baseline" in report
    ref = report["reference_baseline"]
    assert ref["is_baseline"] is True
    assert ref["name"] == "Majority Baseline (Thing_Speak)"
    assert ref["roc_auc"] == 50.0

    assert report["integrity"]["test_samples"] == 4766
    assert report["integrity"]["feature_overlap_count"] == 0
    assert report["integrity"]["production_ready"] is False


def test_deduplicated_models_metric_values_and_ordering():
    report = asyncio.run(models_api.get_evaluation_report("deduplicated"))
    models = report["models"]

    # Verify Random Forest benchmark is preserved
    rf = models["RandomForest"]
    assert rf["accuracy"] == 98.78
    assert rf["macro_f1"] == 88.12
    assert rf["roc_auc"] == 94.55

    # Verify SVM & Logistic Regression metrics
    svm = models["SVM"]
    assert svm["accuracy"] == 94.36
    assert svm["macro_f1"] == 80.63
    assert svm["roc_auc"] == 99.59

    lr = models["LogisticRegression"]
    assert lr["accuracy"] == 93.52
    assert lr["macro_f1"] == 81.28

    dt = models["DecisionTree"]
    assert dt["accuracy"] == 52.69

    gb = models["GradientBoosting"]
    assert gb["accuracy"] == 65.59


def test_minority_classes_low_support_flagged():
    report = asyncio.run(models_api.get_evaluation_report("deduplicated"))
    per_class = {item["class_name"]: item for item in report["per_class_stats"]}

    # Verify NMAP_FIN_SCAN support is 1 and flagged as low support
    fin_scan = per_class["NMAP_FIN_SCAN"]
    assert fin_scan["support"] == 1
    assert fin_scan["is_low_support"] is True

    # Verify Metasploit_Brute_Force_SSH support is 7 and flagged as low support
    ssh_brute = per_class["Metasploit_Brute_Force_SSH"]
    assert ssh_brute["support"] == 7
    assert ssh_brute["is_low_support"] is True

    # Common class check
    arp = per_class["ARP_poisioning"]
    assert arp["support"] == 1060
    assert arp["is_low_support"] is False


def test_historical_evaluation_report_consistency():
    report = asyncio.run(models_api.get_evaluation_report("historical"))
    assert report["run_id"] == "historical"
    assert set(report["models"].keys()) >= {
        "RandomForest", "DecisionTree", "GradientBoosting", "LogisticRegression", "SVM"
    }

    rf_cm = report["models"]["RandomForest"]["confusion_matrix"]
    total_samples = sum(sum(row) for row in rf_cm)
    assert total_samples == 24624
    assert report["integrity"]["test_samples"] == 24624
    assert report["integrity"]["feature_overlap_count"] == 20029
    assert report["integrity"]["production_ready"] is False


def test_unknown_run_id_raises_http_400():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(models_api.get_evaluation_report("non_existent_run"))
    assert exc_info.value.status_code == 400
