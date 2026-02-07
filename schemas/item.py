from pydantic import BaseModel, Field

class ItemCreate(BaseModel):
  seller_id: int = Field(..., ge=1)
  name: str = Field(..., min_length=1)
  description: str = Field(..., min_length=1)
  category: int = Field(..., example=10)
  images_qty: int = Field(..., ge=0)