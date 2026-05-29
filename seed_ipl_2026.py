import asyncio
import datetime
from backend.database.connection import DatabaseManager

async def seed_db():
    db = DatabaseManager("sqlite+aiosqlite:///backend/test_ipl.db")
    await db.connect()
    
    # Clear existing matches for fresh seed
    await db.execute("DELETE FROM match_history")
    
    today = datetime.date(2026, 5, 29)
    
    matches = [
        # Match 70: League Match (May 26)
        ("ipl_2026_70", "simulated", "SRH", "PBKS", "PBKS", "214/4", "215/6", "2026-05-26", "completed"),
        # Eliminator (May 27)
        ("ipl_2026_eliminator", "simulated", "RCB", "GT", "GT", "172/8", "174/4", "2026-05-27", "completed"),
        # Qualifier 1 (May 28)
        ("ipl_2026_q1", "simulated", "KKR", "RR", "KKR", "195/6", "175/10", "2026-05-28", "completed"),
        # Qualifier 2 (May 29 - Today)
        ("155398", "live", "RR", "GT", None, None, None, "2026-05-29", "scheduled"), # Using 155398 so it matches the live Cricbuzz ID!
        # Final (May 31)
        ("ipl_2026_final", "simulated", "KKR", "TBD", None, None, None, "2026-05-31", "scheduled"),
    ]
    
    for m in matches:
        await db.execute(
            """
            INSERT INTO match_history 
            (match_id, match_type, team1, team2, winner, final_score_team1, final_score_team2, match_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7], m[8]
        )
        
    print("Database seeded with IPL 2026 matches.")
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(seed_db())
