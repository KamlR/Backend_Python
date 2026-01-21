from fastapi import APIRouter, HTTPException, status
from schemas.predict import PredictAdvIn, PredictAdvOut
from services.moderation import ModerationService

router = APIRouter()

moderationService = ModerationService()


@router.post(
    "/",
    response_model=PredictAdvOut,
    status_code=status.HTTP_200_OK,
)
async def predict(dto: PredictAdvIn) -> PredictAdvOut:
  try:
    result = await moderationService.predict(dto)
    return PredictAdvOut(is_allowed=result)

  except Exception:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail="Prediction failed",
    )


