"""
AI Commentary Engine — Uses Groq (Llama 3.3) for live IPL insights.
"""
import os, json, random
from groq import Groq
from dotenv import load_dotenv
import pathlib

load_dotenv(dotenv_path=pathlib.Path(__file__).parent / ".env")

client = None
def get_client():
    global client
    if client is None:
        key = os.getenv("GROQ_API_KEY", "")
        if key:
            client = Groq(api_key=key)
    return client

COMMENTARY_CACHE = []
FALLBACK_COMMENTARY = [
    "The pressure is mounting on the batting side!",
    "What a crucial moment in this match!",
    "The fielding side needs a breakthrough here.",
    "This partnership is building nicely.",
    "The run rate is climbing — can they sustain this?",
    "A tight over could change the momentum completely.",
    "The crowd is on its feet!",
    "This could be a match-defining moment.",
    "The death overs are going to be intense!",
    "Every ball matters from here on out.",
    "The captain has some tough decisions to make.",
    "This pitch is offering something for everyone.",
    "A wicket here could turn this match on its head!",
    "The momentum has shifted dramatically!",
    "What an incredible display of power hitting!",
]

RIVALRY_TEMPLATES = [
    "{batsman} vs {bowler}: Battle Intensity {intensity}%",
    "{batsman} looking to dominate {bowler} tonight!",
    "{bowler} has {batsman}'s number — tension rising!",
    "Epic showdown: {batsman} faces {bowler} — {intensity}% battle intensity!",
]

def generate_commentary(match_state: dict) -> str:
    """Generate AI commentary based on match state."""
    c = get_client()
    if not c:
        return random.choice(FALLBACK_COMMENTARY)

    batting = match_state.get("batting_team", "Team")
    bowling = match_state.get("bowling_team", "Team")
    score = match_state.get("score", 0)
    wickets = match_state.get("wickets", 0)
    overs = match_state.get("overs", "0.0")
    rr = match_state.get("run_rate", 0)
    batsman = match_state.get("current_batsman", "Batsman")
    bowler = match_state.get("current_bowler", "Bowler")
    phase = match_state.get("phase", "middle")
    intensity = match_state.get("intensity", "MEDIUM")
    innings = match_state.get("innings", 1)
    target = match_state.get("target", 0)
    rrr = match_state.get("required_rate", 0)
    events = match_state.get("recent_events", [])
    last_event = events[-1]["text"] if events else ""

    prompt = f"""You are an exciting, expert IPL cricket commentator. Generate ONE short, punchy commentary line (max 25 words) for this LIVE match moment.

Match: {batting} vs {bowling}
Score: {score}/{wickets} ({overs} overs)
Run Rate: {rr} | Phase: {phase} | Intensity: {intensity}
Batsman: {batsman} | Bowler: {bowler}
{"Target: " + str(target) + " | Required RR: " + str(rrr) if innings == 2 else ""}
Last event: {last_event}

Be dramatic, insightful, and IPL-style exciting. Use cricket terminology. No hashtags."""

    try:
        resp = c.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.9,
        )
        text = resp.choices[0].message.content.strip().strip('"').strip("'")
        return text if len(text) > 5 else random.choice(FALLBACK_COMMENTARY)
    except Exception:
        return random.choice(FALLBACK_COMMENTARY)

def generate_insight(match_state: dict) -> str:
    """Generate a strategic AI insight."""
    c = get_client()
    if not c:
        return _fallback_insight(match_state)

    batting = match_state.get("batting_team", "")
    bowling = match_state.get("bowling_team", "")
    score = match_state.get("score", 0)
    wickets = match_state.get("wickets", 0)
    overs = match_state.get("overs", "0.0")
    phase = match_state.get("phase", "middle")
    rr = match_state.get("run_rate", 0)
    innings = match_state.get("innings", 1)
    target = match_state.get("target", 0)

    prompt = f"""As an IPL cricket analyst, give ONE brief strategic insight (max 20 words) about this match situation.
{batting} {score}/{wickets} ({overs} ov) RR:{rr} Phase:{phase}
{"Chasing " + str(target) if innings == 2 else "Batting first"}
Focus on strategy, not play-by-play. Be analytical and insightful."""

    try:
        resp = c.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.8,
        )
        return resp.choices[0].message.content.strip().strip('"')
    except Exception:
        return _fallback_insight(match_state)

def _fallback_insight(state: dict) -> str:
    phase = state.get("phase", "middle")
    rr = state.get("run_rate", 0)
    wickets = state.get("wickets", 0)
    if phase == "powerplay":
        return "Powerplay strategy: maximize fielding restrictions!"
    elif phase == "death" and rr > 9:
        return "Death overs carnage incoming — expect big shots!"
    elif wickets >= 5:
        return "Lower order exposed — bowling team smells blood."
    else:
        return "Building a platform for the final assault."

def generate_rivalry(batsman: str, bowler: str) -> dict:
    """Generate a rivalry narrative."""
    intensity = random.randint(60, 98)
    template = random.choice(RIVALRY_TEMPLATES)
    return {
        "text": template.format(batsman=batsman, bowler=bowler, intensity=intensity),
        "intensity": intensity,
        "batsman": batsman,
        "bowler": bowler,
    }

def generate_match_summary(match_state: dict) -> str:
    """Generate end-of-match summary for share cards."""
    c = get_client()
    if not c:
        return "What an incredible IPL match! The fans were treated to a spectacle."

    prompt = f"""Write a 2-sentence exciting IPL match summary for sharing on social media.
Team1: {match_state.get('team1')} Team2: {match_state.get('team2')}
First innings: {match_state.get('first_innings_score')}
Result: {match_state.get('recent_events', [{}])[-1].get('text', 'Match completed')}
Make it dramatic and shareable!"""

    try:
        resp = c.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.9,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return "What a match! IPL never disappoints! 🏏🔥"
