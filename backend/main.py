"""
IPL Pulse — FastAPI + WebSocket Real-Time Server
Live match simulation, predictions, reactions, leaderboard, AI commentary.
"""
import os, json, asyncio, time, random, pathlib
from contextlib import asynccontextmanager
from typing import Dict, List, Set
from dotenv import load_dotenv

# Load .env from backend/ dir first, then project root as fallback
load_dotenv(dotenv_path=pathlib.Path(__file__).parent / ".env")
load_dotenv(dotenv_path=pathlib.Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from match_engine import MatchEngine, TEAMS
from ai_engine import generate_commentary, generate_insight, generate_rivalry, generate_match_summary
from cricbuzz.client import CricbuzzAPIClient
from cricbuzz.cricdata_client import CricDataAPIClient

# Initialize API clients — multi-provider support
cricbuzz_client = CricbuzzAPIClient()
cricdata_client = CricDataAPIClient()

# Active provider: will be set to whichever client works during match_loop init
active_api_client = None  # Will be set to cricdata_client or cricbuzz_client
active_provider_name = "none"  # "cricdata", "cricbuzz", or "simulation"

live_match_id = None
last_processed_ball_id = None
replay_events = []
replay_index = 0


try:
    from backend.database.connection import DatabaseManager
    from backend.database.repository import (
        MatchHistoryRepository, PlayerStatsRepository, TeamStandingRepository,
        UserRepository, AchievementRepository, PredictionRepository
    )
    from backend.services.match_service import MatchService
    from backend.services.statistics_service import StatisticsService
    from backend.services.user_service import UserService
    from backend.services.achievement_service import AchievementService
    from backend.services.poll_service import PollService
    from backend.services.websocket_manager import WebSocketManager
    from backend.services.chat_service import ChatService
    from backend.services.auth_service import AuthService
    from backend.middleware.error_handler import global_error_handler
    from backend.middleware.auth import get_current_user, get_current_active_user
except ModuleNotFoundError:
    from database.connection import DatabaseManager
    from database.repository import (
        MatchHistoryRepository, PlayerStatsRepository, TeamStandingRepository,
        UserRepository, AchievementRepository, PredictionRepository
    )
    from services.match_service import MatchService
    from services.statistics_service import StatisticsService
    from services.user_service import UserService
    from services.achievement_service import AchievementService
    from services.poll_service import PollService
    from services.websocket_manager import WebSocketManager
    from services.chat_service import ChatService
    from services.auth_service import AuthService
    from middleware.error_handler import global_error_handler
    from middleware.auth import get_current_user, get_current_active_user

db_manager = DatabaseManager(os.getenv("DATABASE_URL", "sqlite+aiosqlite:///test_ipl.db"))
ws_manager = WebSocketManager()
chat_service = ChatService(ws_manager)
poll_service = PollService(ws_manager)


BALL_INTERVAL = int(os.getenv("BALL_INTERVAL", "8"))

# ── State ──────────────────────────────────────────────────────────
engine: MatchEngine = None
match_running = False
is_auto_mode = True
ball_interval_seconds = 8
connected_clients: Set[WebSocket] = set()
ws_id_map: Dict[str, WebSocket] = {}  # ws_id -> WebSocket for personalized messages
predictions: Dict[str, dict] = {}  # ws_id -> {prediction, timestamp}
leaderboard: Dict[str, dict] = {}  # username -> {xp, streak, correct, total, team}
fan_reactions: Dict[str, int] = {
    "fire": 0,
    "laugh": 0,
    "shock": 0,
    "heart": 0,
    "bolt": 0,
    "applause": 0,
    "blast": 0,
    "cricket": 0,
}
chat_messages: List[dict] = []
active_quests: Dict[str, dict] = {}  # ws_id -> quest_data
ai_suggestions: Dict[str, dict] = {}  # ws_id -> current AI suggestion for this ball
ai_quest_users: set = set()  # ws_ids that have AI quest mode active
ai_stats: Dict[str, dict] = {}  # ws_id -> {total, correct, followed, followed_correct}
crowd_hype = 0  # Hype meter 0-100
next_ball_trigger = asyncio.Event()
ai_commentary_queue: List[str] = []
last_commentary_time = 0

# ── Lifespan ───────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to database and initialize match
    await db_manager.connect()
    global engine
    # Initialize with Qualifier 2 teams
    engine = MatchEngine("RR", "GT")
    # Auto-start the match loop so live data is fetched immediately
    asyncio.create_task(match_loop())
    yield
    await db_manager.disconnect()

app = FastAPI(title="IPL Pulse", version="1.0.0", lifespan=lifespan)

# Add global exception handler
app.add_exception_handler(Exception, global_error_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Broadcast ──────────────────────────────────────────────────────
async def broadcast(message: dict):
    dead = set()
    for ws in connected_clients:
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)
    connected_clients.difference_update(dead)

# ── Match Loop ─────────────────────────────────────────────────────
async def match_loop():
    global match_running, last_commentary_time, engine, is_auto_mode, ball_interval_seconds, crowd_hype
    global live_match_id, last_processed_ball_id, replay_events, replay_index
    match_running = True
    ball_count = 0

    is_live = False
    event_queue = []

    # Helper to check if a match is an IPL match
    ipl_teams = {"CSK", "MI", "RCB", "KKR", "DC", "PBKS", "RR", "SRH", "LSG", "GT"}

    def select_best_match(live_matches):
        """Pick the best match from a list: IPL first, then any live match."""
        for m in live_matches:
            if m.status.name == "LIVE" and (m.team1 in ipl_teams or m.team2 in ipl_teams):
                return m
        for m in live_matches:
            if m.status.name == "LIVE":
                return m
        return None

    def sync_engine_with_match(selected_match):
        """Sync MatchEngine state with a discovered live match."""
        nonlocal is_live
        global live_match_id, last_processed_ball_id
        live_match_id = selected_match.match_id
        is_live = True

        engine.team1 = selected_match.team1
        engine.team2 = selected_match.team2
        engine.state.team1 = selected_match.team1
        engine.state.team2 = selected_match.team2

        if selected_match.team1 not in TEAMS:
            TEAMS[selected_match.team1] = {"name": selected_match.team1, "color": "#111111", "logo": "🏏", "batsmen": ["Batter 1", "Batter 2", "Batter 3", "Batter 4", "Batter 5"], "bowlers": ["Bowler 1", "Bowler 2", "Bowler 3"]}
        if selected_match.team2 not in TEAMS:
            TEAMS[selected_match.team2] = {"name": selected_match.team2, "color": "#666666", "logo": "🏏", "batsmen": ["Batter 1", "Batter 2", "Batter 3", "Batter 4", "Batter 5"], "bowlers": ["Bowler 1", "Bowler 2", "Bowler 3"]}

        score_str = selected_match.team1_score
        if score_str:
            parts = score_str.split('/')
            if len(parts) >= 1:
                try:
                    engine.state.score = int(parts[0])
                except: pass
            if len(parts) == 2:
                try:
                    engine.state.wickets = int(parts[1])
                except: pass

    # ── Multi-Provider Fallback Chain ──────────────────────────────
    # Priority: CricketData.org → Cricbuzz RapidAPI → Local Simulation

    # 1. Try CricketData.org first (daily quota resets, more sustainable)
    if not is_live and cricdata_client.api_key:
        try:
            print("[Provider] Trying CricketData.org...")
            live_matches = await cricdata_client.fetch_live_matches()
            selected_match = select_best_match(live_matches)
            if selected_match:
                sync_engine_with_match(selected_match)
                active_api_client = cricdata_client
                active_provider_name = "cricdata"
                print(f"[Provider] ✅ CricketData.org — Tracking: {selected_match.team1} vs {selected_match.team2} (ID: {live_match_id})")
            else:
                print(f"[Provider] CricketData.org — No live match found ({len(live_matches)} matches returned).")
        except Exception as e:
            print(f"[Provider] CricketData.org failed: {e}")

    # 2. Fallback to Cricbuzz (RapidAPI) if CricketData didn't find a live match
    if not is_live and cricbuzz_client.api_key:
        try:
            print("[Provider] Trying Cricbuzz (RapidAPI)...")
            live_matches = await cricbuzz_client.fetch_live_matches()
            selected_match = select_best_match(live_matches)
            if selected_match:
                sync_engine_with_match(selected_match)
                active_api_client = cricbuzz_client
                active_provider_name = "cricbuzz"
                print(f"[Provider] ✅ Cricbuzz — Tracking: {selected_match.team1} vs {selected_match.team2} (ID: {live_match_id})")

                # For Cricbuzz, also fetch initial commentary to set last_processed_ball_id
                try:
                    initial_events = await cricbuzz_client.fetch_commentary(live_match_id)
                    if initial_events:
                        last_processed_ball_id = initial_events[-1].ball_id
                except Exception:
                    pass
            else:
                print(f"[Provider] Cricbuzz — No live match found ({len(live_matches)} matches returned).")
        except Exception as e:
            print(f"[Provider] Cricbuzz failed: {e}")

    if not is_live:
        active_provider_name = "simulation"
        print("[Provider] No live match found from any provider. Falling back to local match simulation (RR vs GT).")
        # Use the local simulation engine instead of hitting the API again
        engine.team1 = "RR"
        engine.team2 = "GT"
        engine.state.team1 = "RR"
        engine.state.team2 = "GT"

    prediction_window_sent = False

    while match_running and engine.state.match_status == "live":
        next_ball_trigger.clear()

        # Generate AI suggestion for this ball (based on real match state)
        if not prediction_window_sent:
            ai_suggestion = engine.generate_ai_suggestion()

            # Store per-user suggestions for users who have AI quest active
            ai_suggestions.clear()
            for ws_id in ai_quest_users:
                if ws_id in leaderboard:
                    ai_suggestions[ws_id] = ai_suggestion

            # Send prediction window to all clients
            await broadcast({
                "type": "prediction_window",
                "options": engine.get_prediction_options(),
                "time_left": 60 if is_live else (ball_interval_seconds - 2 if is_auto_mode else 30),
                "state": engine.get_state(),
                "ai_suggestion": ai_suggestion,
            })
            prediction_window_sent = True

        ball = None
        api_backoff = 0  # Extra delay when rate-limited
        while ball is None and match_running and engine.state.match_status == "live":
            # Wait for either the auto timeout interval or manual trigger
            if is_auto_mode or is_live:
                try:
                    poll_interval = int(os.getenv("CRICDATA_POLL_INTERVAL", "90")) if active_provider_name == "cricdata" else 30
                    wait_time = (poll_interval + api_backoff) if is_live else ball_interval_seconds
                    await asyncio.wait_for(next_ball_trigger.wait(), timeout=wait_time)
                except asyncio.TimeoutError:
                    pass  # Normal timeout, proceed to poll API
            else:
                await next_ball_trigger.wait()  # Manual mode, wait indefinitely
                next_ball_trigger.clear()

            if not match_running or engine.state.match_status != "live":
                break

            # Polling Mechanism: Check active API provider for new ball events
            if is_live and active_api_client is not None:
                try:
                    if active_provider_name == "cricdata":
                        # CricketData.org: poll via cricScore for latest scores
                        live_matches = await cricdata_client.fetch_live_matches()
                        for m in live_matches:
                            if m.match_id == live_match_id:
                                # Build a synthetic BallEvent from score change
                                score_str = m.team1_score or m.team2_score or "0/0"
                                parts = score_str.split('/')
                                new_runs = int(parts[0]) if parts else 0
                                new_wickets = int(parts[1]) if len(parts) == 2 else 0
                                runs_diff = new_runs - engine.state.score
                                wicket_diff = new_wickets - engine.state.wickets

                                if runs_diff > 0 or wicket_diff > 0:
                                    from database.models import BallEvent
                                    from datetime import datetime, timezone as tz
                                    synth_event = BallEvent(
                                        ball_id=f"{live_match_id}-{new_runs}-{new_wickets}-{m.overs}",
                                        match_id=live_match_id,
                                        over=m.overs,
                                        batsman="",
                                        bowler="",
                                        runs=runs_diff,
                                        is_wicket=wicket_diff > 0,
                                        commentary=f"{m.team1_score} | {str(m.status.value).title()}" if m.team1_score else f"Score update: +{runs_diff} runs",
                                        timestamp=datetime.now(tz.utc),
                                    )
                                    event_queue.append(synth_event)
                                break
                        api_backoff = 0
                    else:
                        # Cricbuzz: poll commentary for ball-by-ball
                        events = await cricbuzz_client.fetch_commentary(live_match_id)
                        api_backoff = 0  # Reset backoff on success
                        # Find new events we haven't processed yet
                        idx = -1
                        if last_processed_ball_id:
                            for i, e in enumerate(events):
                                if e.ball_id == last_processed_ball_id:
                                    idx = i
                                    break
                        
                        if idx != -1:
                            for e in events[idx+1:]:
                                event_queue.append(e)
                                last_processed_ball_id = e.ball_id
                        elif not last_processed_ball_id and events:
                            # First time, just queue the most recent ball
                            event_queue.append(events[-1])
                            last_processed_ball_id = events[-1].ball_id
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "quota" in error_msg.lower():
                        api_backoff = min(api_backoff + 30, 120)
                        print(f"[{active_provider_name}] Rate limited. Backing off {poll_interval + api_backoff}s before next poll.")
                    else:
                        print(f"[{active_provider_name}] Error polling: {e}")

            if is_live:
                if event_queue:
                    ball = event_queue.pop(0)
            else:
                # Use local simulation engine
                sim_result = engine.simulate_ball()
                if sim_result:
                    ball = sim_result
            
            if ball:
                break
        
        if not match_running or engine.state.match_status != "live" or not ball:
            break
            
        prediction_window_sent = False

        # For live API data, sync MatchEngine state. Simulation already updates state internally.
        if is_live:
            engine.state.score += ball.runs
            if ball.is_wicket:
                engine.state.wickets += 1
            engine.state.overs = int(ball.over)
            engine.state.current_batsmen = [ball.batsman, "Non-Striker"] if ball.batsman else ["Striker", "Non-Striker"]
            engine.state.current_bowler = ball.bowler or "Bowler"
            
            # Calculate balls from overs (e.g. 19.2 -> 19*6 + 2 = 116)
            overs_int = int(ball.over)
            balls_frac = int(round((ball.over - overs_int) * 10))
            engine.state.total_balls = (overs_int * 6) + balls_frac
            engine.state.balls = balls_frac
            
            if engine.state.innings == 1:
                engine.state.target = engine.state.score + 1

        # Extract ball properties for prediction checking
        if is_live:
            is_boundary = ball.runs == 4
            is_six = ball.runs == 6
            is_wide = "wide" in ball.commentary.lower()
            ball_batsman = ball.batsman
            ball_bowler = ball.bowler
            ball_desc = ball.commentary
            ball_runs = ball.runs
            ball_is_wicket = ball.is_wicket
        else:
            # ball is a BallResult from simulate_ball()
            is_boundary = ball.is_boundary
            is_six = ball.is_six
            is_wide = ball.is_wide
            ball_batsman = ball.batsman
            ball_bowler = ball.bowler
            ball_desc = ball.description
            ball_runs = ball.runs
            ball_is_wicket = ball.is_wicket

        # Dummy ball object for check_prediction
        class DummyBall:
            pass
        sim_ball = DummyBall()
        sim_ball.runs = ball_runs
        sim_ball.is_wicket = ball_is_wicket
        sim_ball.is_boundary = is_boundary
        sim_ball.is_six = is_six
        sim_ball.is_wide = is_wide

        ball_data = {
            "ball_number": engine.state.total_balls, "runs": ball_runs,
            "is_wicket": ball_is_wicket, "is_boundary": is_boundary,
            "is_six": is_six, "is_wide": is_wide,
            "batsman": ball_batsman, "bowler": ball_bowler,
            "description": ball_desc,
        }

        # Evaluate predictions
        pred_results = {}
        for ws_id, pred in predictions.items():
            result = engine.check_prediction(pred["prediction"], sim_ball)
            if ws_id in leaderboard:
                lb = leaderboard[ws_id]
                lb["total"] += 1
                if result["correct"]:
                    lb["xp"] += result["xp"]
                    lb["correct"] += 1
                    lb["streak"] += 1
                    if lb["streak"] > 2:
                        result["xp"] += lb["streak"] * 2  # streak bonus
                        lb["xp"] += lb["streak"] * 2
                else:
                    lb["streak"] = 0

                # AI Quest evaluation — dynamic per-ball
                if ws_id in ai_suggestions:
                    suggestion = ai_suggestions[ws_id]
                    stats = ai_stats.setdefault(ws_id, {"total": 0, "correct": 0, "followed": 0, "followed_correct": 0})
                    stats["total"] += 1

                    ai_was_correct = False
                    ai_pred = suggestion["prediction"]
                    # Check if the AI suggestion itself was correct
                    if ai_pred == "dot" and ball.runs == 0 and not ball.is_wicket:
                        ai_was_correct = True
                    elif ai_pred == "single" and ball.runs == 1 and not is_wide:
                        ai_was_correct = True
                    elif ai_pred == "two" and ball.runs == 2:
                        ai_was_correct = True
                    elif ai_pred == "boundary" and is_boundary:
                        ai_was_correct = True
                    elif ai_pred == "six" and is_six:
                        ai_was_correct = True
                    elif ai_pred == "wicket" and ball.is_wicket:
                        ai_was_correct = True

                    if ai_was_correct:
                        stats["correct"] += 1

                    user_followed_ai = (pred["prediction"] == ai_pred)
                    if user_followed_ai:
                        stats["followed"] += 1
                        if result["correct"]:  # user prediction was correct (same as AI, and AI was correct)
                            stats["followed_correct"] += 1
                            # Bonus XP for following a correct AI suggestion
                            bonus = 15
                            lb["xp"] += bonus
                            result["ai_bonus"] = bonus
                            result["ai_correct"] = True

                    result["ai_suggestion"] = ai_pred
                    result["ai_was_correct"] = ai_was_correct
                    result["ai_stats"] = dict(stats)

            pred_results[ws_id] = result
        predictions.clear()

        # Decay crowd hype slowly on each ball simulation (minimum 0)
        crowd_hype = max(0, crowd_hype - 4)

        # Generate commentaries
        ball_count += 1
        commentary = ball_desc
        if ball_count % 3 == 0 or ball_is_wicket or is_six:
            try:
                # Add AI flavor to the real API commentary
                flavor = generate_commentary(engine.get_state())
                commentary = f"{commentary} | {flavor}"
            except Exception:
                pass

        insight = ""
        if ball_count % 6 == 0:
            try:
                insight = generate_insight(engine.get_state())
            except Exception:
                pass

        sorted_lb = sorted(leaderboard.values(), key=lambda x: x["xp"], reverse=True)[:10]

        # Broadcast outcome
        await broadcast({
            "type": "ball_result",
            "ball": ball_data,
            "state": engine.get_state(),
            "commentary": commentary,
            "insight": insight,
            "leaderboard": sorted_lb,
            "reactions": dict(fan_reactions),
            "prediction_results": pred_results,
            "crowd_hype": crowd_hype,
            "ai_quest_users": list(ai_quest_users),
        })

        # Send personalized AI quest stats to each user who has AI quest active
        for uid, user_ws in ws_id_map.items():
            if uid in ai_stats and user_ws in connected_clients:
                try:
                    await user_ws.send_json({
                        "type": "ai_quest_update",
                        "stats": ai_stats[uid],
                        "suggestion": ai_suggestions.get(uid),
                    })
                except Exception:
                    pass

        # Innings check
        if engine.state.innings == 2 and engine.state.total_balls == 0:
            await broadcast({
                "type": "innings_break",
                "state": engine.get_state(),
                "message": f"Innings Break! Target: {engine.state.target}",
            })
            await asyncio.sleep(5)

        # Match complete check
        if engine.state.match_status == "completed":
            summary = "What a match!"
            try:
                summary = generate_match_summary(engine.get_state())
            except Exception:
                pass
            await broadcast({
                "type": "match_end",
                "state": engine.get_state(),
                "summary": summary,
                "leaderboard": sorted_lb,
            })
            match_running = False

    match_running = False

# ── WebSocket Endpoint ─────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    global engine, is_auto_mode, ball_interval_seconds, crowd_hype, match_running
    await ws.accept()
    connected_clients.add(ws)
    ws_id = str(id(ws))
    ws_id_map[ws_id] = ws

    # Send initial connection payload
    await ws.send_json({
        "type": "connected",
        "state": engine.get_state() if engine else {},
        "teams": {k: {"name": v["name"], "color": v["color"], "logo": v["logo"]} for k, v in TEAMS.items()},
        "reactions": dict(fan_reactions),
        "leaderboard": sorted(leaderboard.values(), key=lambda x: x["xp"], reverse=True)[:10],
        "chat": chat_messages[-50:],
        "crowd_hype": crowd_hype,
        "is_auto": is_auto_mode,
        "interval": ball_interval_seconds,
    })

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")

            if msg_type == "join":
                username = data.get("username", f"Fan_{random.randint(1000,9999)}")
                team = data.get("team", "CSK")
                leaderboard[ws_id] = {
                    "username": username, "xp": 0, "streak": 0,
                    "correct": 0, "total": 0, "team": team, "rank": 0,
                }
                await ws.send_json({"type": "joined", "username": username, "team": team})
                await broadcast({
                    "type": "user_joined",
                    "username": username, "team": team,
                    "total_users": len(leaderboard),
                })

            elif msg_type == "predict":
                predictions[ws_id] = {
                    "prediction": data.get("prediction", "dot"),
                    "timestamp": time.time(),
                }
                await ws.send_json({"type": "prediction_locked", "prediction": data.get("prediction")})

            elif msg_type == "react":
                reaction = data.get("reaction") or "fire"
                if reaction in fan_reactions:
                    fan_reactions[reaction] += 1
                    crowd_hype = min(100, crowd_hype + 4)  # Each click builds hype by 4%
                    if ws_id in leaderboard:
                        leaderboard[ws_id]["xp"] += 1  # Earn +1 XP per fan reaction!
                    await broadcast({
                        "type": "reaction",
                        "reaction": reaction,
                        "counts": dict(fan_reactions),
                        "crowd_hype": crowd_hype,
                        "leaderboard": sorted(leaderboard.values(), key=lambda x: x["xp"], reverse=True)[:10]
                    })

            elif msg_type == "chat":
                username = leaderboard.get(ws_id, {}).get("username", "Anonymous")
                team = leaderboard.get(ws_id, {}).get("team", "")
                msg = {
                    "username": username, "team": team,
                    "text": data.get("text", "")[:200],
                    "timestamp": time.time(),
                }
                chat_messages.append(msg)
                if len(chat_messages) > 200:
                    chat_messages.pop(0)
                await broadcast({"type": "chat_message", "message": msg})

            elif msg_type == "start_match":
                if not match_running:
                    t1 = data.get("team1", "CSK")
                    t2 = data.get("team2", "MI")
                    if engine.state.match_status == "scheduled":
                        # Reuse current engine but set to live
                        engine.state.match_status = "live"
                    else:
                        engine = MatchEngine(t1, t2)
                    fan_reactions.update({k: 0 for k in fan_reactions})
                    chat_messages.clear()
                    crowd_hype = 0
                    active_quests.clear()
                    await broadcast({"type": "match_starting", "state": engine.get_state()})
                    asyncio.create_task(match_loop())

            elif msg_type == "next_ball":
                next_ball_trigger.set()

            elif msg_type == "toggle_auto":
                is_auto_mode = data.get("auto", True)
                await broadcast({"type": "auto_toggled", "auto": is_auto_mode})
                next_ball_trigger.set()  # Wake loop in case it's waiting

            elif msg_type == "change_interval":
                ball_interval_seconds = int(data.get("interval", 8))
                await broadcast({"type": "interval_changed", "interval": ball_interval_seconds})

            elif msg_type == "reset_match":
                match_running = False
                next_ball_trigger.set()  # Wake up match loop
                await asyncio.sleep(0.3)
                engine = MatchEngine("RR", "GT")
                engine.state.match_status = "scheduled"  # Show Start Match button
                fan_reactions.update({k: 0 for k in fan_reactions})
                chat_messages.clear()
                predictions.clear()
                crowd_hype = 0
                active_quests.clear()
                ai_quest_users.clear()
                ai_suggestions.clear()
                ai_stats.clear()
                leaderboard.clear()  # Reset leaderboard too
                await broadcast({
                    "type": "match_reset",
                    "state": engine.get_state(),
                    "reactions": dict(fan_reactions),
                    "crowd_hype": crowd_hype,
                    "leaderboard": [],
                })

            elif msg_type == "generate_quest":
                # Toggle AI Quest mode on/off
                if ws_id in ai_quest_users:
                    ai_quest_users.discard(ws_id)
                    ai_suggestions.pop(ws_id, None)
                    await ws.send_json({"type": "quest_generated", "quest": None, "active": False})
                else:
                    ai_quest_users.add(ws_id)
                    # Generate initial suggestion if match is live
                    suggestion = engine.generate_ai_suggestion() if engine and engine.state.match_status == "live" else None
                    if suggestion:
                        ai_suggestions[ws_id] = suggestion
                    stats = ai_stats.setdefault(ws_id, {"total": 0, "correct": 0, "followed": 0, "followed_correct": 0})
                    await ws.send_json({
                        "type": "quest_generated",
                        "quest": {"active": True, "suggestion": suggestion, "stats": stats},
                        "active": True
                    })

    except WebSocketDisconnect:
        connected_clients.discard(ws)
        ws_id_map.pop(ws_id, None)
        if ws_id in leaderboard:
            del leaderboard[ws_id]
        if ws_id in predictions:
            del predictions[ws_id]
        if ws_id in active_quests:
            del active_quests[ws_id]
        ai_quest_users.discard(ws_id)
        ai_suggestions.pop(ws_id, None)
        ai_stats.pop(ws_id, None)

# ── REST Endpoints ─────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "app": "IPL Pulse"}

@app.get("/api/teams")
async def get_teams():
    return {k: {"name": v["name"], "color": v["color"], "logo": v["logo"]} for k, v in TEAMS.items()}

@app.get("/api/match/state")
async def get_match_state():
    if engine:
        return engine.get_state()
    return {"error": "No match in progress"}

@app.get("/api/leaderboard")
async def get_leaderboard():
    sorted_lb = sorted(leaderboard.values(), key=lambda x: x["xp"], reverse=True)[:20]
    for i, entry in enumerate(sorted_lb):
        entry["rank"] = i + 1
    return {"leaderboard": sorted_lb}

@app.get("/api/matches/schedule")
async def get_schedule():
    repo = MatchHistoryRepository(db_manager)
    service = MatchService(repo)
    return await service.get_schedule()

@app.get("/api/matches/history")
async def get_history():
    repo = MatchHistoryRepository(db_manager)
    service = MatchService(repo)
    return await service.get_history()

@app.get("/api/matches/{match_id}/highlights")
async def get_match_highlights(match_id: str):
    repo = MatchHistoryRepository(db_manager)
    service = MatchService(repo)
    return await service.get_match_highlights(match_id)

@app.get("/api/stats/player/{player_id}")
async def get_player_stats(player_id: str):
    player_repo = PlayerStatsRepository(db_manager)
    team_repo = TeamStandingRepository(db_manager)
    service = StatisticsService(player_repo, team_repo)
    stats = await service.get_player_stats(player_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Player not found")
    return stats

@app.get("/api/stats/top/batsmen")
async def get_top_batsmen(limit: int = 10):
    player_repo = PlayerStatsRepository(db_manager)
    team_repo = TeamStandingRepository(db_manager)
    service = StatisticsService(player_repo, team_repo)
    return await service.get_top_run_scorers(limit)

@app.get("/api/stats/top/bowlers")
async def get_top_bowlers(limit: int = 10):
    player_repo = PlayerStatsRepository(db_manager)
    team_repo = TeamStandingRepository(db_manager)
    service = StatisticsService(player_repo, team_repo)
    return await service.get_top_wicket_takers(limit)

@app.get("/api/stats/standings/{season}")
async def get_team_standings(season: str):
    player_repo = PlayerStatsRepository(db_manager)
    team_repo = TeamStandingRepository(db_manager)
    service = StatisticsService(player_repo, team_repo)
    return await service.get_team_standings(season)

# ── Auth Endpoints ─────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    repo = UserRepository(db_manager)
    service = AuthService(repo)
    user = await service.register_user(request.username, request.email, request.password)
    if not user:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    return {"message": "User registered successfully", "user_id": str(user.user_id)}

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    repo = UserRepository(db_manager)
    service = AuthService(repo)
    user = await service.authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    access_token = service.create_access_token(
        data={"sub": str(user.user_id), "username": user.username}
    )
    return {"access_token": access_token, "token_type": "bearer", "user_id": str(user.user_id)}

@app.post("/api/auth/logout")
async def logout():
    # In a real app with stateful JWTs, we would add the token to a blacklist.
    # For stateless JWTs, the client simply deletes the token.
    return {"message": "Successfully logged out"}

# ── User & Social Endpoints ────────────────────────────────────────

@app.get("/api/users/{user_id}/profile")
async def get_user_profile(user_id: str):
    user_repo = UserRepository(db_manager)
    achieve_repo = AchievementRepository(db_manager)
    pred_repo = PredictionRepository(db_manager)
    service = UserService(user_repo, achieve_repo, pred_repo)
    try:
        from uuid import UUID
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    profile = await service.get_user_profile(uid)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return profile

@app.get("/api/users/{user_id}/achievements")
async def get_user_achievements(user_id: str):
    achieve_repo = AchievementRepository(db_manager)
    pred_repo = PredictionRepository(db_manager)
    service = AchievementService(achieve_repo, pred_repo)
    try:
        from uuid import UUID
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    return await service.get_user_achievements(uid)

@app.post("/api/matches/{match_id}/polls")
async def create_poll(match_id: str, payload: dict):
    question = payload.get("question")
    options = payload.get("options")
    if not question or not options or len(options) < 2:
        raise HTTPException(status_code=400, detail="Invalid poll data")
    return await poll_service.create_poll(match_id, question, options)

@app.get("/api/matches/{match_id}/polls/active")
async def get_active_poll(match_id: str):
    poll = await poll_service.get_active_poll(match_id)
    if not poll:
        raise HTTPException(status_code=404, detail="No active poll")
    return poll

@app.post("/api/polls/{poll_id}/respond")
async def respond_to_poll(poll_id: str, payload: dict):
    user_id_str = payload.get("user_id")
    selected_option = payload.get("selected_option")
    if not user_id_str or not selected_option:
        raise HTTPException(status_code=400, detail="Missing response data")
    try:
        from uuid import UUID
        uid = UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
        
    results = await poll_service.record_response(poll_id, uid, selected_option)
    if results is None:
        raise HTTPException(status_code=400, detail="Invalid option or poll not found")
    return {"status": "success", "results": results}

# ── Serve Frontend ─────────────────────────────────────────────────
frontend_dir = pathlib.Path(__file__).parent.parent / "frontend"
class NoCacheStaticFiles(StaticFiles):
    def is_not_modified(self, response_headers, request_headers) -> bool:
        return False

    def file_response(self, full_path, stat_result, scope, status_code=200):
        response = super().file_response(full_path, stat_result, scope, status_code)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

if frontend_dir.exists():
    app.mount("/", NoCacheStaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8081, reload=True)
