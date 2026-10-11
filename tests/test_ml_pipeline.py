import asyncio
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from ai_engine.evaluate import evaluate_model
from ai_engine.model_registry import ModelRegistry
from ai_engine.predict import PredictionEngine
from ai_engine.preprocessing import PreprocessingPipeline
from ai_engine.train import train_all_models
from backend.api import models_api


def _small_dataset():
    values = np.arange(240, dtype=float)
    frame = pd.DataFrame({
        "first": values,
        "second": values[::-1],
    })
    labels = pd.Series(np.where(values < 120, "DDoS", "Normal"))
    return frame, labels


def test_preprocessing_splits_stratified_and_fits_imputer_on_train_only():
    frame, labels = _small_dataset()
    frame.loc[frame.index % 7 == 0, "first"] = np.nan
    train_val_indices, _ = train_test_split(
        np.arange(len(labels)),
        test_size=0.2,
        random_state=42,
        stratify=labels,
    )
    train_indices, _ = train_test_split(
        train_val_indices,
        test_size=0.1 / 0.8,
        random_state=42,
        stratify=labels.iloc[train_val_indices],
    )
    pipeline = PreprocessingPipeline({
        "test_size": 0.2,
        "validation_size": 0.1,
        "random_seed": 42,
    })
    X_train, X_val, X_test, y_train, y_val, y_test = pipeline.fit_transform(
        frame, labels
    )

    expected_median = np.nanmedian(frame.iloc[train_indices]["first"])
    assert pipeline._numeric_imputer.statistics_[0] == expected_median
    assert X_train.shape[1] == X_val.shape[1] == X_test.shape[1] == 2
    assert len(y_train) + len(y_val) + len(y_test) == len(labels)
    assert set(np.unique(y_train)) == set(np.unique(y_test)) == {0, 1}


def test_training_versions_artifacts_and_uses_imbalance_weights(tmp_path):
    X = np.arange(120, dtype=float).reshape(-1, 2)
    y = np.array([0] * 45 + [1] * 15)
    configs = [
        {"name": "LogisticRegression", "params": {"max_iter": 500, "class_weight": "balanced"}},
        {"name": "DecisionTree", "params": {"max_depth": 4, "class_weight": "balanced"}},
        {"name": "RandomForest", "params": {"n_estimators": 10, "class_weight": "balanced", "n_jobs": 1}},
        {"name": "SVM", "params": {"class_weight": "balanced", "probability": True}},
        {"name": "GradientBoosting", "params": {"n_estimators": 5, "max_depth": 1}},
    ]
    trained = train_all_models(
        X, y, configs, save_dir=str(tmp_path), feature_names=["a", "b"],
        random_seed=42, run_id="test-run",
    )

    assert len(trained) == len(configs)
    for result in trained:
        assert result["version"] == "v2_test-run"
        assert result["model"] is not None
        assert Path(result["model_path"]).is_file()
        loaded = joblib.load(result["model_path"])
        assert loaded.n_features_in_ == 2


def test_evaluation_metrics_match_predictions_and_confusion_matrix():
    y_true = np.array([0, 0, 1, 1, 2, 2])
    X_test = np.array([[0], [1], [2], [3], [4], [5]], dtype=float)
    model = LogisticRegression(max_iter=500).fit(X_test, y_true)
    result = evaluate_model(model, X_test, y_true, "test", ["A", "B", "C"])
    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)
    labels = [0, 1, 2]
    confusion = np.asarray(result["confusion_matrix"])

    assert confusion.sum() == len(y_true)
    np.testing.assert_array_equal(
        confusion, confusion_matrix(y_true, predictions, labels=labels)
    )
    assert result["accuracy"] == accuracy_score(y_true, predictions)
    assert result["precision_macro"] == precision_score(
        y_true, predictions, labels=labels, average="macro", zero_division=0
    )
    assert result["recall_macro"] == recall_score(
        y_true, predictions, labels=labels, average="macro", zero_division=0
    )
    assert result["f1_macro"] == f1_score(y_true, predictions, average="macro")
    assert result["roc_auc"] == roc_auc_score(
        y_true, probabilities, labels=model.classes_, multi_class="ovr", average="macro"
    )
    assert result["n_test_samples"] == len(y_true)
    assert result["class_names"] == ["A", "B", "C"]
    assert result["roc_auc"] is not None


def test_prediction_loads_matching_preprocessor_and_decodes_labels(tmp_path):
    frame, labels = _small_dataset()
    pipeline = PreprocessingPipeline({
        "test_size": 0.2,
        "validation_size": 0.1,
        "random_seed": 4,
    })
    X_train, _, _, y_train, _, _ = pipeline.fit_transform(frame, labels)
    model = LogisticRegression(max_iter=500).fit(X_train, y_train)
    model_path = tmp_path / "LogisticRegression_v2_test.joblib"
    joblib.dump(model, model_path)
    pipeline.save(str(tmp_path / "preprocessing"))
    engine = PredictionEngine(
        model_path=str(model_path),
        preprocessing_path=str(tmp_path / "preprocessing"),
    )

    predicted = engine.predict({"second": 239.0, "first": 0.0})
    assert predicted["prediction"] == "DDoS"
    assert predicted["model_prediction"] == "DDoS"
    assert predicted["classification_status"] == "CLASSIFIED"
    assert predicted["model_name"] == "LogisticRegression"
    engine._min_confidence = 1.1
    low_confidence = engine.predict({"first": 0.0, "second": 239.0})
    assert low_confidence["prediction"] == "SUSPICIOUS_UNKNOWN"
    assert low_confidence["model_prediction"] == "DDoS"
    assert low_confidence["classification_status"] == "LOW_CONFIDENCE"
    try:
        engine.predict({"first": 0.0})
    except ValueError as exc:
        assert "Missing required feature columns" in str(exc)
    else:
        raise AssertionError("Inference must reject incomplete model feature input")


def test_model_api_metrics_match_dashboard_contract_without_defaults(tmp_path, monkeypatch):
    model_path = tmp_path / "SVM.joblib"
    model_path.write_bytes(b"artifact")
    preprocessing_path = tmp_path / "preprocessing"
    preprocessing_path.mkdir()
    (preprocessing_path / "preprocessing_pipeline.joblib").write_bytes(b"artifact")
    registry = ModelRegistry(str(tmp_path / "registry.json"))
    test_metrics = {
        "accuracy": 0.75,
        "precision_macro": 0.7,
        "recall_macro": 0.65,
        "f1_macro": 0.67,
        "roc_auc": 0.8,
        "confusion_matrix": [[3, 1], [2, 4]],
        "class_names": ["Normal", "Attack"],
        "n_test_samples": 10,
        "inference_ms_per_sample": 0.01,
        "evaluated_at": "2026-10-11T00:00:00+00:00",
    }
    registry.register(
        "SVM", "v2_test", "RT_IOT2022", ["first", "second"], test_metrics,
        str(model_path), str(preprocessing_path),
    )
    registry.validate_model("SVM", "v2_test")
    registry.set_production("SVM", "v2_test")
    monkeypatch.setattr(models_api, "_get_registry", lambda: registry)

    response = asyncio.run(models_api.list_models())
    svm = next(model for model in response if model["name"] == "SVM")
    missing = next(model for model in response if model["name"] == "RandomForest")

    assert svm["available"] is True
    assert svm["status"] == "ACTIVE"
    assert svm["is_production"] is True
    dashboard_metric_keys = {
        "accuracy", "precision_macro", "recall_macro", "f1_macro",
        "roc_auc", "confusion_matrix",
    }
    assert dashboard_metric_keys <= svm["metrics"].keys()
    assert svm["metrics"]["accuracy"] == test_metrics["accuracy"]
    assert svm["metrics"]["f1_macro"] == test_metrics["f1_macro"]
    assert svm["dataset"] == "RT_IOT2022"
    assert svm["test_size"] == test_metrics["n_test_samples"]
    assert svm["accuracy"] == 75.0
    assert svm["metrics"]["confusion_matrix"] == test_metrics["confusion_matrix"]
    assert missing["status"] == "UNAVAILABLE"
    assert missing["accuracy"] is None


def test_near_random_detection_and_production_readiness_safeguards(tmp_path, monkeypatch):
    """Ensure models with near-random performance are flagged and blocked from production-ready status."""
    model_path = tmp_path / "DecisionTree.joblib"
    model_path.write_bytes(b"artifact")
    preprocessing_path = tmp_path / "preprocessing"
    preprocessing_path.mkdir()
    (preprocessing_path / "preprocessing_pipeline.joblib").write_bytes(b"artifact")
    registry = ModelRegistry(str(tmp_path / "registry.json"))

    # Near-random metrics (ROC-AUC ~ 0.50, F1 macro ~ 0.08)
    near_random_metrics = {
        "accuracy": 0.125,
        "precision_macro": 0.10,
        "recall_macro": 0.12,
        "f1_macro": 0.08,
        "roc_auc": 0.502,
        "confusion_matrix": [[1, 0], [0, 1]],
        "class_names": ["Normal", "Attack"],
        "n_test_samples": 2000,
        "inference_ms_per_sample": 0.01,
        "evaluated_at": "2026-10-11T00:00:00+00:00",
    }
    registry.register(
        "DecisionTree", "v2_rand", "RT_IOT2022", ["proto", "dst_port"], near_random_metrics,
        str(model_path), str(preprocessing_path),
    )
    registry.validate_model("DecisionTree", "v2_rand")
    registry.set_production("DecisionTree", "v2_rand")

    entry = registry.get_model("DecisionTree", "v2_rand")
    assert entry["is_near_random"] is True
    assert entry["production_ready"] is False
    assert "near random chance" in entry["warning"]

    monkeypatch.setattr(models_api, "_get_registry", lambda: registry)
    response = asyncio.run(models_api.list_models())
    dt = next(model for model in response if model["name"] == "DecisionTree")

    assert dt["is_near_random"] is True
    assert dt["production_ready"] is False
    assert dt["warning"] is not None
    assert "near random chance" in dt["warning"]


def test_categorical_onehot_encoding_preserves_signal():
    """Verify categorical features can be properly one-hot encoded without scaling distortion."""
    df = pd.DataFrame({
        "proto": [6, 17, 6, 17, 6, 17],
        "dst_port": [80, 443, 80, 443, 80, 443],
        "flow_duration": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
    })
    y = pd.Series(["Normal", "Attack", "Normal", "Attack", "Normal", "Attack"])

    pipeline = PreprocessingPipeline({
        "test_size": 0.33,
        "validation_size": 0.0,
        "random_seed": 42,
        "categorical_features": ["proto", "dst_port"],
        "encoding_method": "onehot",
    })
    X_train, _, X_test, y_train, _, y_test = pipeline.fit_transform(df, y)

    # 1 continuous + one-hot categories for proto and dst_port
    assert X_train.shape[1] > 3
    assert pipeline._onehot_encoder is not None
    assert set(pipeline.categorical_features) == {"proto", "dst_port"}

