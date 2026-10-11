# SecureIoT-X Project State

## Last Updated: 2026-09-09

## Status: SVM Classifier Added & Integrated

### Completed
- [x] SVM Classifier (`sklearn.svm.SVC`) integrated with `probability=True` and configurable hyperparameters
- [x] Zero data leakage verified: train/test split occurs before preprocessing fit; scaler fitted on training data only
- [x] Preprocessing pipeline robust to missing, extra, inf, and NaN features during inference
- [x] Comprehensive evaluation metrics: accuracy, precision, recall, F1, macro F1, weighted F1, ROC-AUC, PR-AUC, confusion matrix, training time, inference time
- [x] Model comparison updated with SVM evaluated side-by-side (SVM ranked objectively without auto-promotion)
- [x] Live prediction schema implemented in `PredictionEngine` with `prediction`, `confidence`, `model`, `model_version`, `timestamp`, `device_id`
- [x] Attack simulator (`TrafficGenerator`) enriched with real flow features (`fwd_pkts_tot`, `bwd_pkts_tot`, byte rates, packet rates, protocols, ports) without hardcoded strings
- [x] Comprehensive test suite in `tests/ml/test_svm.py` (12 tests covering training, prediction, save/load, pipeline, multiclass, missing/invalid features, consistency, simulator compatibility)
- [x] 37/37 ML tests passing (`pytest tests/ml`)
- [x] 116/116 full project tests passing (`pytest tests`)

### Model Registry & Comparison Status
- Models compared: GradientBoosting, RandomForest, DecisionTree, SVM, LogisticRegression
- Current Production Model: GradientBoosting (F1-weighted: 0.2949)
- SVM Status: Validated in registry & compared (F1-weighted: 0.1106 on RT_IOT2022 / 0.9181 on Synthetic)

### Files Modified
- `ai_engine/train.py` — added `build_svm_model`, `train_svm`, `train_svm_pipeline`, updated `_build_model`
- `ai_engine/preprocessing.py` — robust `transform` with feature alignment, numeric type coercion, and safe NaN/inf handling
- `ai_engine/evaluate.py` — added `precision`, `recall`, `f1`, and multiclass `pr_auc` metrics
- `ai_engine/predict.py` — added model auto-discovery, model name resolution, and `model` schema key
- `simulation/traffic_generator.py` — added compatible network flow features
- `iot/telemetry_handler.py` — added model-specific AI engine loading support
- `backend/api/models_api.py` — enhanced `list_models` and `activate_model` with rich model metadata and case-insensitive lookup
- `dashboard/src/services/api.js` — added `activateModel` API method
- `dashboard/src/pages/AIModels.jsx` — added SVM to model registry grid, dynamic backend model fetching, radar chart comparison, and live benchmark tester

### Files Created
- `tests/ml/test_svm.py` — 12 tests for SVM training, prediction, leakage, multiclass, robustness, and compatibility
