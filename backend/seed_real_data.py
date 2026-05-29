import asyncio
import re
from datetime import datetime
from database.connection import DatabaseManager

DB_URL = "sqlite+aiosqlite:///test_ipl.db"

TEAM_MAP = {
    "chennai-super-kings": "CSK",
    "delhi-capitals": "DC",
    "gujarat-titans": "GT",
    "kolkata-knight-riders": "KKR",
    "lucknow-super-giants": "LSG",
    "mumbai-indians": "MI",
    "punjab-kings": "PBKS",
    "rajasthan-royals": "RR",
    "royal-challengers-bengaluru": "RCB",
    "sunrisers-hyderabad": "SRH",
    "tbc": "TBD",
}

def parse_score(score_str):
    if score_str.lower() == "tbc" or score_str.startswith("No result") or "opt to bat" in score_str:
        return None
    # 201-9 (20) -> 201/9
    # 127 (19.4) -> 127/10
    score_str = score_str.split('(')[0].strip()
    if '-' in score_str:
        return score_str.replace('-', '/')
    else:
        return f"{score_str}/10"

async def main():
    db = DatabaseManager(DB_URL)
    await db.connect()
    
    # Clear existing history
    await db.execute("DELETE FROM match_history")
    print("Cleared existing match_history table.")

    with open('schedule_data.txt', 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    i = 0
    matches = []
    current_date_str = ""
    match_id = 1
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this line is a date (e.g., Sat, Mar 28 2026)
        if re.match(r'^[A-Z][a-z]{2}, [A-Z][a-z]{2} \d{1,2} 2026$', line) or re.match(r'^[A-Z][a-z]{2}, [A-Z][a-z]{2} \d{1,2} \d{4}$', line):
            current_date_str = line
            i += 1
            continue
            
        if "Match starts at" in line or "Sunday, May 31" in line or "7:30 PM" in line:
            i += 1
            continue

        # Next line should be Title • Venue
        if ' • ' in line:
            title_venue = line
            title = lines[i+1]
            t1_slug = lines[i+2]
            t1_name = lines[i+3]
            t1_score_str = lines[i+4]
            t2_slug = lines[i+5]
            t2_name = lines[i+6]
            
            # Now we need to figure out if line i+7 is t2 score or result
            t2_score_str = lines[i+7]
            result_str = None
            if "won by" in t2_score_str or "No result" in t2_score_str or "opt to bat" in t2_score_str or "tied" in t2_score_str.lower():
                result_str = t2_score_str
                t2_score_str = None
                i += 8
            else:
                result_str = lines[i+8] if i+8 < len(lines) and not (' • ' in lines[i+8] or re.match(r'^[A-Z][a-z]{2},', lines[i+8])) else None
                i += 9 if result_str else 8

            # Build match object
            # For date, parse "Sat, Mar 28 2026"
            try:
                # e.g., "Mar 28 2026"
                date_part = current_date_str.split(', ')[1]
                match_date = datetime.strptime(date_part, "%b %d %Y").strftime("%Y-%m-%d")
            except:
                match_date = "2026-05-31"

            t1 = TEAM_MAP.get(t1_slug, t1_slug.upper())
            t2 = TEAM_MAP.get(t2_slug, t2_slug.upper())
            
            t1_final = parse_score(t1_score_str)
            t2_final = parse_score(t2_score_str) if t2_score_str else None

            status = "completed"
            if t1_final is None or (result_str and "opt to bat" in result_str):
                status = "scheduled"
            if "Qualifier 2" in title:
                # Force Qualifier 2 to be the live match tracking in cricbuzz
                status = "scheduled"
                mid = "155398"
                match_type = "live"
            else:
                mid = f"ipl_2026_{match_id}"
                match_type = "simulated"
            
            if "Final" in title:
                status = "scheduled"

            winner = None
            if result_str and "won by" in result_str:
                if t1_name in result_str or t1_slug.split('-')[0].capitalize() in result_str:
                    winner = t1
                elif t2_name in result_str or t2_slug.split('-')[0].capitalize() in result_str:
                    winner = t2
                elif "LSG" in result_str and t1 == "LSG":
                    winner = t1
                elif "LSG" in result_str and t2 == "LSG":
                    winner = t2

            matches.append({
                "match_id": mid,
                "match_type": match_type,
                "team1": t1,
                "team2": t2,
                "winner": winner,
                "final_score_team1": t1_final,
                "final_score_team2": t2_final,
                "match_date": match_date,
                "status": status
            })
            match_id += 1
        else:
            i += 1

    # Insert into database
    query = '''
        INSERT INTO match_history 
        (match_id, match_type, team1, team2, winner, final_score_team1, final_score_team2, match_date, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    '''
    for m in matches:
        try:
            await db.execute(
                query,
                m["match_id"], m["match_type"], m["team1"], m["team2"],
                m["winner"], m["final_score_team1"], m["final_score_team2"],
                m["match_date"], m["status"]
            )
        except Exception as e:
            print(f"Error inserting {m['match_id']}: {e}")

    print(f"Successfully seeded {len(matches)} real IPL matches!")
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
