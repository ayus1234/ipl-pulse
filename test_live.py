import asyncio
from backend.cricbuzz.client import CricbuzzAPIClient
from dotenv import load_dotenv
import os

load_dotenv("backend/.env")

async def main():
    client = CricbuzzAPIClient()
    try:
        matches = await client.fetch_live_matches()
        print(f"Total live matches retrieved: {len(matches)}")
        for m in matches:
            print(f"ID: {m.match_id}, Status: {m.status}, Teams: {m.team1} vs {m.team2}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
