from typing import Any
import logging
from pathlib import Path
import joblib
import numpy as np
import numpy.typing as npt
import pandas as pd
from lightgbm import LGBMRegressor

from freqtrade.freqai.prediction_models.PyTorchTransformerRegressor import PyTorchTransformerRegressor
from freqtrade.freqai.data_kitchen import FreqaiDataKitchen

logger = logging.getLogger(__name__)


class HybridTreeTransformer(PyTorchTransformerRegressor):
    """
    🏛️ Institutional Hybrid Ensemble Model (LightGBM + PyTorch Time-Series Transformer)
    
    Architecture:
    1. PyTorch Transformer: Models sequential time-series patterns and temporal dependencies
       over a sliding window (e.g., 24-30 candles) with self-attention.
    2. LightGBM: Captures non-linear tabular threshold boundaries and interaction features.
    3. Meta-Ensemble Blending: Blends predictions with configurable weights to maximize
       information coefficient (IC) while reducing prediction variance.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        hybrid_config = self.freqai_info.get("model_training_parameters", {}).get("hybrid_parameters", {})
        self.tree_weight: float = hybrid_config.get("tree_weight", 0.5)
        self.transformer_weight: float = hybrid_config.get("transformer_weight", 0.5)
        self.lgb_params: dict[str, Any] = hybrid_config.get("lightgbm_parameters", {
            "n_estimators": 500,
            "learning_rate": 0.04,
            "max_depth": 6,
            "random_state": 42,
            "n_jobs": 2
        })
        self.lgb_models: dict[str, Any] = {}

    def fit(self, data_dictionary: dict, dk: FreqaiDataKitchen, **kwargs) -> Any:
        """
        Fits both the PyTorch Transformer and the LightGBM Regressor on the dual-representation data.
        """
        logger.info(f"🏛️ [Hybrid Ensemble] Training PyTorch Transformer for {dk.pair}...")
        # 1. Train the PyTorch Transformer via parent class
        transformer_trainer = super().fit(data_dictionary, dk, **kwargs)

        # 2. Train LightGBM on the tabular feature matrix
        logger.info(f"🏛️ [Hybrid Ensemble] Training LightGBM for {dk.pair}...")
        X_train = data_dictionary["train_features"]
        y_train = data_dictionary["train_labels"].values.ravel() if isinstance(data_dictionary["train_labels"], pd.DataFrame) else data_dictionary["train_labels"]
        sample_weights = data_dictionary.get("train_weights", None)

        eval_set = None
        eval_sample_weight = None
        if self.freqai_info.get("data_split_parameters", {}).get("test_size", 0.1) > 0:
            X_test = data_dictionary["test_features"]
            y_test = data_dictionary["test_labels"].values.ravel() if isinstance(data_dictionary["test_labels"], pd.DataFrame) else data_dictionary["test_labels"]
            eval_set = [(X_test, y_test)]
            eval_sample_weight = [data_dictionary.get("test_weights", None)]

        lgb_model = LGBMRegressor(**self.lgb_params)
        lgb_model.fit(
            X=X_train,
            y=y_train,
            eval_set=eval_set,
            sample_weight=sample_weights,
            eval_sample_weight=eval_sample_weight
        )

        # Save LightGBM model checkpoint alongside the transformer
        lgb_save_path = Path(dk.data_path) / f"lgb_model_{dk.pair.replace('/', '_').replace(':', '_')}.joblib"
        joblib.dump(lgb_model, lgb_save_path)
        self.lgb_models[dk.pair] = lgb_model
        logger.info(f"🏛️ [Hybrid Ensemble] Saved LightGBM checkpoint to {lgb_save_path}")

        return transformer_trainer

    def predict(
        self, unfiltered_df: pd.DataFrame, dk: FreqaiDataKitchen, **kwargs
    ) -> tuple[pd.DataFrame, npt.NDArray[np.int_]]:
        """
        Dual inference:
        1. Infers sequential probabilities using PyTorch Transformer.
        2. Infers tabular probabilities using LightGBM.
        3. Fuses both predictions via weighted ensemble blending.
        """
        # 1. Get PyTorch Transformer prediction and outlier / DI mask
        pred_transformer_df, do_predict = super().predict(unfiltered_df, dk, **kwargs)

        # 2. Load or retrieve LightGBM model for this pair
        lgb_model = self.lgb_models.get(dk.pair)
        if lgb_model is None:
            lgb_save_path = Path(dk.data_path) / f"lgb_model_{dk.pair.replace('/', '_').replace(':', '_')}.joblib"
            if lgb_save_path.exists():
                lgb_model = joblib.load(lgb_save_path)
                self.lgb_models[dk.pair] = lgb_model

        # 3. If LightGBM is available, calculate ensemble blend
        if lgb_model is not None:
            pred_features = dk.data_dictionary["prediction_features"]
            pred_tree = lgb_model.predict(pred_features)
            
            # Align shapes
            pred_tree_series = pd.Series(pred_tree, index=pred_transformer_df.index)
            
            for col in pred_transformer_df.columns:
                trans_vals = pred_transformer_df[col]
                # Weighted Ensemble: w1 * Tree + w2 * Transformer
                blended = (self.tree_weight * pred_tree_series) + (self.transformer_weight * trans_vals)
                pred_transformer_df[col] = blended
        
        return (pred_transformer_df, do_predict)
