from fastapi import APIRouter, HTTPException, status, Request, Depends
from schemas.predict import PredictAdvIn, SimplePredictAdvIn, PredictAdvOut, AsyncPredictAdvOut, ModerationResultOut
from services.moderation import ModerationService
from services.async_moderation import AsyncModerationService
from errors.item_exceptions import ItemNotFoundError
from repositories.redis_storage import RedisPredictionStorage
from repositories.redis_storage import RedisPredictionStorage
from app.metrics.metrics import PREDICTION_ERRORS_TOTAL 
from dependencies.auth import get_current_account
import sentry_sdk

predict_router = APIRouter()


@predict_router.post(
    "/predict",
    response_model=PredictAdvOut,
    status_code=status.HTTP_200_OK,
)
async def predict(dto: PredictAdvIn, request: Request, current_account: dict = Depends(get_current_account)) -> PredictAdvOut:
  try:
      model = request.app.state.model
      redis_client = request.app.state.redis_client
      redisPredictionStorage = RedisPredictionStorage(redis_client, "prediction", 15)
      if model is None:
        PREDICTION_ERRORS_TOTAL.labels(result="model_unavailable").inc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded",
        )

      service = ModerationService(model, redisPredictionStorage)
      is_violation, probability = await service.predict(dto)

      return PredictAdvOut(
          is_violation=is_violation,
          probability=probability,
      )
  
  except HTTPException:
    raise
  except Exception as e:
    sentry_sdk.capture_exception(e)
    PREDICTION_ERRORS_TOTAL.labels(error_type="prediction_error").inc()
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Prediction failed",
    )


@predict_router.post(
    "/simple-predict",
    response_model=PredictAdvOut,
    status_code=status.HTTP_200_OK,
)
async def simple_predict(dto: SimplePredictAdvIn, request: Request, current_account: dict = Depends(get_current_account)) ->  PredictAdvOut:
    try:
      model = request.app.state.model
      redis_client = request.app.state.redis_client
      redisPredictionStorage = RedisPredictionStorage(redis_client, "prediction", 15)
      if model is None:
        PREDICTION_ERRORS_TOTAL.labels(error_type="model_unavailable").inc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded",
        )

      service = ModerationService(model, redisPredictionStorage)
      is_violation, probability = await service.simplePredict(dto)

      return PredictAdvOut(
          is_violation=is_violation,
          probability=probability,
      )

    except ItemNotFoundError as e:
        sentry_sdk.capture_exception(e)
        PREDICTION_ERRORS_TOTAL.labels(error_type="prediction_error").inc()
        raise HTTPException(
            status_code=404,
            detail="Item not found",
        )
    except HTTPException:
        raise
    except Exception as e:
        sentry_sdk.capture_exception(e)
        PREDICTION_ERRORS_TOTAL.labels(error_type="prediction_error").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed",
        )


@predict_router.post(
    "/async-predict",
    response_model=AsyncPredictAdvOut,
    status_code=status.HTTP_200_OK,
)
async def async_predict(dto: SimplePredictAdvIn, request: Request, current_account: dict = Depends(get_current_account)) -> AsyncPredictAdvOut:
    redisPredictionStorage = RedisPredictionStorage(request.app.state.redis_client, "async_prediction", 5)
    asyncModerationService = AsyncModerationService(redisPredictionStorage, request.app.state.kafka)
    try:
        task_id = await asyncModerationService.prepare_data_for_moderation(dto.item_id)
        return AsyncPredictAdvOut(task_id=task_id, status="pending", message="Moderation request accepted")
    except ItemNotFoundError as e:
        sentry_sdk.capture_exception(e)
        raise HTTPException(
            status_code=404,
            detail="Item not found",
        )
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed"
        )


@predict_router.get(
    "/moderation-result/{task_id}",
    response_model=ModerationResultOut,
    status_code=status.HTTP_200_OK,
)
async def get_moderation_result(task_id: int, request: Request, current_account: dict = Depends(get_current_account)) -> ModerationResultOut:
    redisPredictionStorage = RedisPredictionStorage(request.app.state.redis_client, "async_prediction", 15)
    asyncModerationService = AsyncModerationService(redisPredictionStorage)
    try:
       task_id, task_status, is_violation, probability, error_message = await asyncModerationService.get_moderation_result(task_id)
       return  ModerationResultOut(task_id=task_id, status=task_status, message=error_message, is_violation=is_violation, probability=probability)
    except ItemNotFoundError as e:
        sentry_sdk.capture_exception(e)
        raise HTTPException(
            status_code=404,
            detail="Item not found",
        )
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed"
        )

@predict_router.delete(
    "/close/{item_id}",
    status_code=status.HTTP_200_OK,
)
async def close_item(item_id: int, request: Request, current_account: dict = Depends(get_current_account)) -> None:
    try:
       redis_client = request.app.state.redis_client
       redisPredictionStorage = RedisPredictionStorage(redis_client, "prediction", 15)
       service = ModerationService(request.app.state.model, redisPredictionStorage)
       await service.closeItem(item_id)
    except ItemNotFoundError as e:
        sentry_sdk.capture_exception(e)
        raise HTTPException(
            status_code=404,
            detail="Item not found",
        )
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Close item failed"
        )
