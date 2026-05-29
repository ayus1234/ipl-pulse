import asyncio
from backend.cricbuzz.client import CricbuzzAPIClient
async def main():
    c = CricbuzzAPIClient()
    events = await c.fetch_commentary('155387')
    print(len(events))
asyncio.run(main())
