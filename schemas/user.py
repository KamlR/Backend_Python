from pydantic import BaseModel, Field

class UserCreate(BaseModel):
  first_name: str = Field(..., min_length=1)
  last_name: str = Field(..., min_length=1)
  is_verified_seller: bool = False