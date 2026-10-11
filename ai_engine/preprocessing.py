"""
SecureIoT-X AI Engine — Preprocessing Pipeline.

CRITICAL: Fit transformations ONLY on training data to prevent data leakage.
Then transform train, validation, and test sets separately.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import (
    LabelEncoder,
    StandardScaler,
    MinMaxScaler,
    RobustScaler,
    OneHotEncoder,
)

logger = logging.getLogger("secureiot.ai.preprocessing")


class PreprocessingPipeline:
    """
    End-to-end preprocessing pipeline with leakage prevention.

    Usage:
        pp = PreprocessingPipeline(config)
        X_train, X_val, X_test, y_train, y_val, y_test = pp.fit_transform(X, y)
        pp.save("models/preprocessing/")

        # Later
        pp2 = PreprocessingPipeline.load("models/preprocessing/")
        X_new = pp2.transform(X_new_raw)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.test_size: float = cfg.get("test_size", 0.2)
        self.val_size: float = cfg.get("validation_size", 0.1)
        self.random_seed: int = cfg.get("random_seed", 42)
        self.scaling_method: str = cfg.get("scaling_method", "standard")
        self.handle_inf: bool = cfg.get("handle_inf", True)
        self.remove_duplicates: bool = cfg.get("remove_duplicates", True)
        self.deduplicate_before_split: bool = cfg.get("deduplicate_before_split", False)
        self.max_missing_ratio: float = cfg.get("max_missing_ratio", 0.5)
        self.categorical_features: List[str] = list(cfg.get("categorical_features", []))
        self.encoding_method: str = cfg.get("encoding_method", "label")

        # Fitted transformers (set during fit)
        self._scaler: Optional[Any] = None
        self._label_encoders: Dict[str, LabelEncoder] = {}
        self._onehot_encoder: Optional[OneHotEncoder] = None
        self._target_encoder: Optional[LabelEncoder] = None
        self._numeric_imputer: Optional[SimpleImputer] = None
        self._categorical_imputer: Optional[SimpleImputer] = None
        self._feature_columns: List[str] = []
        self._numerical_columns: List[str] = []
        self._categorical_columns: List[str] = []
        self._encoded_feature_names: List[str] = []
        self._dropped_columns: List[str] = []
        self._reference_features: Dict[str, Any] = {}
        self._is_fitted = False

    # ── Main API ───────────────────────────────────────────────

    def fit_transform(
        self,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Full pipeline: clean → split → fit on train → transform all splits.
        Returns: (X_train, X_val, X_test, y_train, y_val, y_test)
        """
        logger.info("Starting preprocessing pipeline...")

        # Remove unlabeled rows before splitting; do not inspect or clean features
        # across the holdout boundary.
        X_clean, y_clean = self._clean(X, y)

        if self.deduplicate_before_split:
            # Documented Deduplication Policy:
            # 1. Deduplicate by exact feature pattern + target to preserve distinct class behaviors.
            # 2. For ambiguous feature rows sharing identical features across different classes,
            #    assign to modal class to prevent contradictory training/test signals.
            combined = X_clean.copy()
            combined["__target__"] = y_clean
            feature_cols = list(X_clean.columns)
            mode_series = combined.groupby(feature_cols)["__target__"].agg(lambda s: s.mode()[0])
            X_clean = mode_series.index.to_frame(index=False)
            y_clean = pd.Series(mode_series.values, index=X_clean.index, name=y_clean.name)
            logger.info("Deduplicated before split: %d unique rows across all classes", len(X_clean))

        # Split before fitting any data-dependent preprocessing.
        if not self._can_stratify(y_clean):
            raise ValueError("Stratified splitting requires at least two samples per class")
        X_train_val, X_test, y_train_val, y_test = train_test_split(
            X_clean, y_clean,
            test_size=self.test_size,
            random_state=self.random_seed,
            stratify=y_clean,
        )

        if self.val_size > 0:
            val_ratio = self.val_size / (1 - self.test_size)
            X_train, X_val, y_train, y_val = train_test_split(
                X_train_val, y_train_val,
                test_size=val_ratio,
                random_state=self.random_seed,
                stratify=y_train_val,
            )
        else:
            X_train, y_train = X_train_val, y_train_val
            X_val, y_val = pd.DataFrame(), pd.Series(dtype=y_clean.dtype)

        if self.remove_duplicates and not self.deduplicate_before_split:
            train_rows = X_train.copy()
            train_rows["__target__"] = y_train
            train_rows = train_rows.drop_duplicates()
            y_train = train_rows.pop("__target__")
            X_train = train_rows

        logger.info("Split sizes — train: %d, val: %d, test: %d",
                     len(X_train), len(X_val), len(X_test))

        # Learn dropped columns, fill values, encoders and scaling from train only.
        X_train = self._handle_inf_values(X_train)
        X_val = self._handle_inf_values(X_val)
        X_test = self._handle_inf_values(X_test)
        missing_ratio = X_train.isnull().mean()
        self._dropped_columns = missing_ratio[
            missing_ratio > self.max_missing_ratio
        ].index.tolist()
        if self._dropped_columns:
            X_train = X_train.drop(columns=self._dropped_columns)
            X_val = X_val.drop(columns=self._dropped_columns, errors="ignore")
            X_test = X_test.drop(columns=self._dropped_columns, errors="ignore")

        # Identify column types from training data.
        cat_candidates = list(X_train.select_dtypes(include=["object", "category"]).columns)
        for col in self.categorical_features:
            if col in X_train.columns and col not in cat_candidates:
                cat_candidates.append(col)
        self._categorical_columns = cat_candidates
        self._numerical_columns = [
            c for c in X_train.select_dtypes(include=[np.number]).columns
            if c not in self._categorical_columns
        ]
        self._feature_columns = list(X_train.columns)

        X_train = self._fit_imputers(X_train)
        X_val = self._transform_imputers(X_val)
        X_test = self._transform_imputers(X_test)
        self._reference_features = X_train.iloc[0].to_dict()

        # Encode categoricals — fit on train only.
        X_train = self._fit_encode_categoricals(X_train)
        X_val = self._transform_encode_categoricals(X_val)
        X_test = self._transform_encode_categoricals(X_test)

        # Scale numericals — fit on train only.
        X_train = self._fit_scale(X_train)
        X_val = self._transform_scale(X_val)
        X_test = self._transform_scale(X_test)

        # Step 6: Encode target labels
        self._target_encoder = LabelEncoder()
        y_train_enc = self._target_encoder.fit_transform(y_train)
        y_val_enc = self._target_encoder.transform(y_val) if len(y_val) > 0 else np.array([])
        y_test_enc = self._target_encoder.transform(y_test)

        self._is_fitted = True
        logger.info("Preprocessing complete. Features: %d", X_train.shape[1])

        return (
            X_train.values if isinstance(X_train, pd.DataFrame) else X_train,
            X_val.values if isinstance(X_val, pd.DataFrame) else X_val,
            X_test.values if isinstance(X_test, pd.DataFrame) else X_test,
            y_train_enc, y_val_enc, y_test_enc,
        )

    def transform(self, X: Any) -> np.ndarray:
        """Transform new data using fitted pipeline (for inference)."""
        if not self._is_fitted:
            raise RuntimeError("Pipeline not fitted. Call fit_transform() first or load().")

        if isinstance(X, dict):
            X = pd.DataFrame([X])
        elif isinstance(X, list):
            X = pd.DataFrame(X)
        elif not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)

        X = X.copy()

        # Require the model's real input schema instead of silently substituting
        # zeros for missing traffic measurements.
        if self._feature_columns:
            missing = [col for col in self._feature_columns if col not in X.columns]
            if missing:
                raise ValueError(f"Missing required feature columns: {missing}")
            X = X[self._feature_columns]

            # Enforce numeric types on numerical columns
            for col in self._numerical_columns:
                if col in X.columns:
                    X[col] = pd.to_numeric(X[col], errors="coerce")

        X = self._handle_inf_values(X)
        X = self._transform_imputers(X)
        X = self._transform_encode_categoricals(X)
        X = self._transform_scale(X)
        return X.values if isinstance(X, pd.DataFrame) else X

    def inverse_transform_target(self, y: np.ndarray) -> np.ndarray:
        """Convert encoded labels back to original strings."""
        if self._target_encoder is None:
            raise RuntimeError("Target encoder not fitted")
        return self._target_encoder.inverse_transform(y)

    @property
    def target_classes(self) -> List[str]:
        if self._target_encoder is None:
            return []
        return list(self._target_encoder.classes_)

    @property
    def feature_names(self) -> List[str]:
        if self._encoded_feature_names:
            return self._encoded_feature_names.copy()
        return self._feature_columns.copy()

    @property
    def sample_features(self) -> Dict[str, Any]:
        """A real, training-only row for inference smoke tests (not evaluation)."""
        return {
            name: value.item() if isinstance(value, np.generic) else value
            for name, value in self._reference_features.items()
        }

    # ── Cleaning ───────────────────────────────────────────────

    def _clean(self, X: pd.DataFrame, y: pd.Series) -> Tuple[pd.DataFrame, pd.Series]:
        """Remove unlabeled rows without learning from feature distributions."""
        X = X.copy()
        y = y.copy()
        mask = y.notna()
        X = X.loc[mask].reset_index(drop=True)
        y = y.loc[mask].reset_index(drop=True)
        return X, y

    def _handle_inf_values(self, X: pd.DataFrame) -> pd.DataFrame:
        """Replace infinite values with NaN, then handle as missing."""
        if self.handle_inf:
            num_cols = [c for c in self._numerical_columns if c in X.columns] if self._numerical_columns else list(X.select_dtypes(include=[np.number]).columns)
            if num_cols:
                inf_count = np.isinf(X[num_cols]).sum().sum()
                if inf_count > 0:
                    logger.info("Replacing %d infinite values with NaN", inf_count)
                    X[num_cols] = X[num_cols].replace([np.inf, -np.inf], np.nan)
        return X

    def _fit_imputers(self, X: pd.DataFrame) -> pd.DataFrame:
        """Fit missing-value replacements using training rows only."""
        X = X.copy()
        if self._numerical_columns:
            self._numeric_imputer = SimpleImputer(strategy="median")
            X[self._numerical_columns] = self._numeric_imputer.fit_transform(
                X[self._numerical_columns]
            )
        if self._categorical_columns:
            self._categorical_imputer = SimpleImputer(
                strategy="most_frequent", fill_value="UNKNOWN"
            )
            X[self._categorical_columns] = self._categorical_imputer.fit_transform(
                X[self._categorical_columns]
            )
        return X

    def _transform_imputers(self, X: pd.DataFrame) -> pd.DataFrame:
        """Apply training-fitted imputers without learning from validation/test."""
        X = X.copy()
        if len(X) == 0:
            return X
        if self._numeric_imputer is not None and self._numerical_columns:
            X[self._numerical_columns] = self._numeric_imputer.transform(
                X[self._numerical_columns]
            )
        if self._categorical_imputer is not None and self._categorical_columns:
            X[self._categorical_columns] = self._categorical_imputer.transform(
                X[self._categorical_columns]
            )
        return X

    # ── Encoding ───────────────────────────────────────────────

    def _fit_encode_categoricals(self, X: pd.DataFrame) -> pd.DataFrame:
        """Fit encoders on training data categorical columns."""
        if not self._categorical_columns:
            return X
        if self.encoding_method == "onehot":
            cols_to_encode = [c for c in self._categorical_columns if c in X.columns]
            if cols_to_encode:
                self._onehot_encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
                encoded = self._onehot_encoder.fit_transform(X[cols_to_encode].astype(str))
                encoded_cols = list(self._onehot_encoder.get_feature_names_out(cols_to_encode))
                encoded_df = pd.DataFrame(encoded, columns=encoded_cols, index=X.index)
                X = pd.concat([X.drop(columns=cols_to_encode), encoded_df], axis=1)
                self._encoded_feature_names = list(X.columns)
            return X
        else:
            self._label_encoders = {}
            for col in self._categorical_columns:
                if col not in X.columns:
                    continue
                le = LabelEncoder()
                X[col] = le.fit_transform(X[col].astype(str))
                self._label_encoders[col] = le
            return X

    def _transform_encode_categoricals(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform categorical columns using fitted encoders."""
        if len(X) == 0 or not self._categorical_columns:
            return X
        if self.encoding_method == "onehot" and self._onehot_encoder is not None:
            cols_to_encode = [c for c in self._categorical_columns if c in X.columns]
            if cols_to_encode:
                encoded = self._onehot_encoder.transform(X[cols_to_encode].astype(str))
                encoded_cols = list(self._onehot_encoder.get_feature_names_out(cols_to_encode))
                encoded_df = pd.DataFrame(encoded, columns=encoded_cols, index=X.index)
                X = pd.concat([X.drop(columns=cols_to_encode), encoded_df], axis=1)
            return X
        else:
            for col, le in self._label_encoders.items():
                if col not in X.columns:
                    continue
                # Handle unseen categories gracefully
                X[col] = X[col].astype(str)
                known = set(le.classes_)
                X[col] = X[col].apply(lambda v: v if v in known else le.classes_[0])
                X[col] = le.transform(X[col])
            return X

    # ── Scaling ────────────────────────────────────────────────

    def _fit_scale(self, X: pd.DataFrame) -> pd.DataFrame:
        """Fit scaler on training data numerical columns."""
        if self.scaling_method == "standard":
            self._scaler = StandardScaler()
        elif self.scaling_method == "minmax":
            self._scaler = MinMaxScaler()
        elif self.scaling_method == "robust":
            self._scaler = RobustScaler()
        else:
            logger.warning("Unknown scaling method '%s', using StandardScaler", self.scaling_method)
            self._scaler = StandardScaler()

        num_cols = [c for c in self._numerical_columns if c in X.columns]
        if num_cols:
            X[num_cols] = self._scaler.fit_transform(X[num_cols])
        return X

    def _transform_scale(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform data using fitted scaler."""
        if self._scaler is None or len(X) == 0:
            return X
        num_cols = [c for c in self._numerical_columns if c in X.columns]
        if num_cols:
            X[num_cols] = self._scaler.transform(X[num_cols])
        return X

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _can_stratify(y: pd.Series) -> bool:
        """Check if stratification is possible (each class has ≥2 samples)."""
        if len(y) == 0:
            return False
        counts = y.value_counts()
        return counts.min() >= 2

    # ── Serialisation ──────────────────────────────────────────

    def save(self, dirpath: str) -> None:
        """Save the fitted pipeline to disk."""
        path = Path(dirpath)
        path.mkdir(parents=True, exist_ok=True)

        state = {
            "scaler": self._scaler,
            "label_encoders": self._label_encoders,
            "onehot_encoder": self._onehot_encoder,
            "target_encoder": self._target_encoder,
            "numeric_imputer": self._numeric_imputer,
            "categorical_imputer": self._categorical_imputer,
            "feature_columns": self._feature_columns,
            "numerical_columns": self._numerical_columns,
            "categorical_columns": self._categorical_columns,
            "encoded_feature_names": self._encoded_feature_names,
            "categorical_features": self.categorical_features,
            "encoding_method": self.encoding_method,
            "dropped_columns": self._dropped_columns,
            "reference_features": self._reference_features,
            "scaling_method": self.scaling_method,
            "handle_inf": self.handle_inf,
        }
        joblib.dump(state, path / "preprocessing_pipeline.joblib")
        logger.info("Preprocessing pipeline saved to %s", path)

    @classmethod
    def load(cls, dirpath: str) -> "PreprocessingPipeline":
        """Load a fitted pipeline from disk."""
        path = Path(dirpath)
        state = joblib.load(path / "preprocessing_pipeline.joblib")

        pp = cls()
        pp._scaler = state["scaler"]
        pp._label_encoders = state.get("label_encoders", {})
        pp._onehot_encoder = state.get("onehot_encoder")
        pp._target_encoder = state["target_encoder"]
        pp._numeric_imputer = state.get("numeric_imputer")
        pp._categorical_imputer = state.get("categorical_imputer")
        pp._feature_columns = state["feature_columns"]
        pp._numerical_columns = state["numerical_columns"]
        pp._categorical_columns = state["categorical_columns"]
        pp._encoded_feature_names = state.get("encoded_feature_names", [])
        pp.categorical_features = state.get("categorical_features", [])
        pp.encoding_method = state.get("encoding_method", "label")
        pp._dropped_columns = state["dropped_columns"]
        pp._reference_features = state.get("reference_features", {})
        pp.scaling_method = state["scaling_method"]
        pp.handle_inf = state["handle_inf"]
        pp._is_fitted = True
        logger.info("Preprocessing pipeline loaded from %s", path)
        return pp
