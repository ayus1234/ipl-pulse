import asyncio
from backend.cricbuzz.client import CricbuzzAPIClient
from dotenv import load_dotenv

load_dotenv("backend/.env")

async def main():
    client = CricbuzzAPIClient()
    try:
        # Check live
        payload = await client._request_json("/matches/v1/live")
        matches = client.parse_live_matches(payload)
        print("LIVE:")
        for m in matches:
            print(f"ID: {m.match_id}, Status: {m.status.name}, Teams: {m.team1} vs {m.team2}")
            
        # Check recent
        payload = await client._request_json("/matches/v1/recent")
        matches = client.parse_live_matches(payload)
        print("\nRECENT:")
        for m in matches[:10]: # Print top 10
            print(f"ID: {m.match_id}, Status: {m.status.name}, Teams: {m.team1} vs {m.team2}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
