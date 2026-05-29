import asyncio
import os
from database.connection import get_db

async def test():
    print(f"DATABASE_TYPE env: {os.getenv('DATABASE_TYPE')}")
    print(f"SQLITE_DATABASE_URL env: {os.getenv('SQLITE_DATABASE_URL')}")
    db = get_db()
    print('URL:', db.database_url)
    db_path = db.database_url.replace("sqlite:///", "")
    print('Path being used:', db_path)
    await db.connect()
    print('Connected')

asyncio.run(test())
