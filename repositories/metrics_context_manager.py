import time
from contextlib import asynccontextmanager

from app.metrics.metrics import DB_QUERY_DURATION_SECONDS





@asynccontextmanager
async def measure_db_query(query_type: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        DB_QUERY_DURATION_SECONDS.labels(query_type=query_type).observe(
            time.perf_counter() - start
        )