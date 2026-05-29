import asyncio
import os
from dotenv import load_dotenv

load_dotenv(".env")
from cricbuzz.client import CricbuzzAPIClient

async def main():
    client = CricbuzzAPIClient()
    print(f"API Key present: {bool(client.api_key)}")
    try:
        live_matches = await client.fetch_live_matches()
        print(f"Found {len(live_matches)} matches.")
        for m in live_matches:
            print(f" - {m.match_id}: {m.team1} vs {m.team2} ({m.status.value})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
