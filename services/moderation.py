from dataclasses import dataclass
from schemas.predict import PredictAdvIn


@dataclass(frozen=True)
class ModerationService:

    async def predict(self, data: PredictAdvIn) -> bool:
        # Подтвержденные продавцы - всегда OK
        if data.is_verified_seller:
            return True

        # Неподтвержденные — только если есть картинки
        if data.images_qty and data.images_qty > 0:
            return True

        return False
