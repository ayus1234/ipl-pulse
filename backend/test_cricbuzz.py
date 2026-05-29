import asyncio
import os
import json
from dotenv import load_dotenv
load_dotenv()
from cricbuzz.client import CricbuzzAPIClient

async def main():
    client = CricbuzzAPIClient()
    try:
        match_id = "155387" # Rajasthan Royals vs Sunrisers Hyderabad
        events = await client.fetch_commentary(match_id)
        print(f"Got {len(events)} events.")
        for e in events[:5]:
            print(f"Over {e.over}: {e.runs} runs [W: {e.is_wicket}] - {e.commentary[:60]}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
