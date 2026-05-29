import asyncio, os, sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from cricbuzz.client import CricbuzzAPIClient

async def test():
    c = CricbuzzAPIClient()
    print(f"API Key loaded: {bool(c.api_key)} ({c.api_key[:15]}...)")
    print(f"Base URL: {c.base_url}")
    try:
        matches = await c.fetch_live_matches()
        print(f"Found {len(matches)} live matches")
        for m in matches[:10]:
            print(f"  {m.team1} vs {m.team2} - {m.status.name} - ID:{m.match_id}")
    except Exception as e:
        print(f"ERROR: {e}")

asyncio.run(test())
