from fastapi import APIRouter, HTTPException, status, Request
from schemas.predict import PredictAdvIn, SimplePredictAdvIn, PredictAdvOut
from services.moderation import ModerationService
from services.exceptions import ItemNotFoundError



predict_router = APIRouter()


@predict_router.post(
    "/predict",
    response_model=PredictAdvOut,
    status_code=status.HTTP_200_OK,
)
async def predict(dto: PredictAdvIn, request: Request) -> PredictAdvOut:
  try:
      model = request.app.state.model
      if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded",
        )

      service = ModerationService(model)
      is_violation, probability = await service.predict(dto)

      return PredictAdvOut(
          is_violation=is_violation,
          probability=probability,
      )
  
  except HTTPException:
    raise
  except Exception:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Prediction failed",
    )


@predict_router.post(
    "/simple-predict",
    response_model=PredictAdvOut,
    status_code=status.HTTP_200_OK,
)
async def simple_predict(dto: SimplePredictAdvIn, request: Request) ->  PredictAdvOut:
    try:
      model = request.app.state.model
      if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded",
        )

      service = ModerationService(model)
      is_violation, probability = await service.simplePredict(dto)

      return PredictAdvOut(
          is_violation=is_violation,
          probability=probability,
      )

    except ItemNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Item not found",
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed",
        )

