from dataclasses import dataclass
from schemas.predict import PredictAdvIn
import numpy as np
import logging

logger = logging.getLogger("moderation")


class ModerationService:
    def __init__(self, model):
        self.model = model

    def _to_features(self, data: PredictAdvIn) -> np.ndarray:
        return np.array([[
            1.0 if data.is_verified_seller else 0.0,
            min(data.images_qty, 10) / 10.0,
            min(len(data.description), 1000) / 1000.0,
            min(data.category, 100) / 100.0,
        ]])

    async def predict(self, data: PredictAdvIn) -> tuple[bool, float]:
        features = self._to_features(data)
        proba = float(self.model.predict_proba(features)[0][1])
        is_violation = proba >= 0.5

        logger.info(
            "result seller_id=%s item_id=%s is_violation=%s probability=%.4f",
            data.seller_id,
            data.item_id,
            is_violation,
            proba,
        )

        return is_violation, proba
