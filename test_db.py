import asyncio
from backend.database.connection import DatabaseManager

async def check():
    db = DatabaseManager("sqlite+aiosqlite:///backend/test_ipl.db")
    await db.connect()
    
    matches = await db.fetch_all("SELECT * FROM match_history LIMIT 10")
    print(f"Total matches in DB: {len(matches)}")
    for m in matches:
        print(m.get('match_id'), m.get('team1'), m.get('team2'), m.get('status'), m.get('match_date'))
            
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check())
