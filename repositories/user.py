from db.connection import PostgresConnection 
from schemas.user import UserCreate
from app.metrics.metrics import DB_QUERY_DURATION_SECONDS
import time

class UserRepository:
    """
    Создание пользователя.
    """
    async def create_user(self, user: UserCreate) -> int:
      conn = await PostgresConnection.get()

      query = """
        INSERT INTO public.users (first_name, last_name, is_verified_seller)
        VALUES ($1, $2, $3)
        RETURNING seller_id
        """
      start = time.perf_counter()
      row = await conn.fetchrow(query, user.first_name, user.last_name, user.is_verified_seller)
      DB_QUERY_DURATION_SECONDS.labels(query_type="insert").observe(
            time.perf_counter() - start)
      return int(row["seller_id"])
    
