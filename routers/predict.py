from fastapi import APIRouter, HTTPException, status, Request
from schemas.predict import PredictAdvIn, SimplePredictAdvIn, PredictAdvOut, AsyncPredictAdvOut, ModerationResultOut
from services.moderation import ModerationService
from services.async_moderation import AsyncModerationService
from services.exceptions import ItemNotFoundError

import traceback

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


@predict_router.post(
    "/async-predict",
    response_model=AsyncPredictAdvOut,
    status_code=status.HTTP_200_OK,
)
async def async_predict(dto: SimplePredictAdvIn, request: Request) -> AsyncPredictAdvOut:
    asyncModerationService = AsyncModerationService(request.app.state.kafka)
    try:
        task_id = await asyncModerationService.prepare_data_for_moderation(dto.item_id)
        return AsyncPredictAdvOut(task_id=task_id, status="pending", message="Moderation request accepted")
    except ItemNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Item not found",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed"
        )


@predict_router.get(
    "/moderation-result/{task_id}",
    response_model=ModerationResultOut,
    status_code=status.HTTP_200_OK,
)
async def get_moderation_result(task_id: int, request: Request) -> ModerationResultOut:
    asyncModerationService = AsyncModerationService()
    try:
       task_id, task_status, is_violation, probability, error_message = await asyncModerationService.get_moderation_result(task_id)
       return  ModerationResultOut(task_id=task_id, status=task_status, message=error_message, is_violation=is_violation, probability=probability)
    except ItemNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Item not found",
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed"
        )