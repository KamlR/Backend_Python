from pydantic import BaseModel, Field
from typing import Optional


class PredictAdvIn(BaseModel):
  seller_id: int = Field(..., example=1)
  is_verified_seller: bool = Field(..., example=True)
  item_id: int = Field(..., example=100)
  name: str = Field(..., min_length=1)
  description: str = Field(..., min_length=1)
  category: int = Field(..., example=10)
  images_qty: Optional[int] = Field(None, ge=0)


class PredictAdvOut(BaseModel):
  is_violation: bool
  probability: float
