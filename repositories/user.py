from db.connection import PostgresConnection 
from schemas.user import UserCreate

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
      row = await conn.fetchrow(query, user.first_name, user.last_name, user.is_verified_seller)
      return int(row["seller_id"])
    
