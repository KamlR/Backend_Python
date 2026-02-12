from pydantic import BaseModel, Field


class PredictAdvIn(BaseModel):
  seller_id: int = Field(..., example=1)
  is_verified_seller: bool = Field(..., example=True)
  item_id: int = Field(..., example=100)
  name: str = Field(..., min_length=1)
  description: str = Field(..., min_length=1)
  category: int = Field(..., example=10)
  images_qty: int = Field(..., ge=0)


class SimplePredictAdvIn(BaseModel):
  item_id: int = Field(..., example=100)

class PredictAdvOut(BaseModel):
  is_violation: bool
  probability: float

class AsyncPredictAdvOut(BaseModel):
  task_id: int 
  status: str
  message: str

class ModerationResultOut(BaseModel):
  task_id: int 
  status: str
  message: str | None
  is_violation: bool | None
  probability: float | None

