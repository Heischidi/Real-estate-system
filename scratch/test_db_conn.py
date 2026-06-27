import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine("postgresql+asyncpg://realestate_user:realestate_dev_password@localhost:5432/realestate")
    try:
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT 1"))
            print("Connection successful! Result:", res.scalar())
    except Exception as e:
        print("Failed to connect to PostgreSQL:", e)

if __name__ == "__main__":
    asyncio.run(main())
