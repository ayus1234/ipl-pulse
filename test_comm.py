import asyncio
from backend.cricbuzz.client import CricbuzzAPIClient
from dotenv import load_dotenv

load_dotenv("backend/.env")

async def main():
    client = CricbuzzAPIClient()
    try:
        matches = await client.fetch_live_matches()
        if not matches:
            print("No matches")
            return
        m = matches[0]
        print(f"Match: {m.match_id}")
        comm = await client.fetch_commentary(m.match_id)
        print(f"Commentary length: {len(comm)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
