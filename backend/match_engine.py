"""
IPL Match Simulation Engine — Ball-by-ball realistic cricket simulation.
"""
import random, math, time
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict

TEAMS = {
    "CSK": {"name": "Chennai Super Kings", "color": "#ffd700", "logo": "🦁",
            "batsmen": ["Ruturaj Gaikwad", "Devon Conway", "Moeen Ali", "Ambati Rayudu", "Ravindra Jadeja", "MS Dhoni", "Shivam Dube"],
            "bowlers": ["Deepak Chahar", "Tushar Deshpande", "Maheesh Theekshana", "Matheesha Pathirana", "Ravindra Jadeja"]},
    "MI":  {"name": "Mumbai Indians", "color": "#004ba0", "logo": "🏏",
            "batsmen": ["Rohit Sharma", "Ishan Kishan", "Suryakumar Yadav", "Tilak Varma", "Hardik Pandya", "Tim David", "Nehal Wadhera"],
            "bowlers": ["Jasprit Bumrah", "Piyush Chawla", "Jason Behrendorff", "Akash Madhwal", "Hardik Pandya"]},
    "RCB": {"name": "Royal Challengers Bengaluru", "color": "#d4213d", "logo": "👑",
            "batsmen": ["Virat Kohli", "Faf du Plessis", "Glenn Maxwell", "Rajat Patidar", "Dinesh Karthik", "Shahbaz Ahmed", "Cameron Green"],
            "bowlers": ["Mohammed Siraj", "Josh Hazlewood", "Wanindu Hasaranga", "Harshal Patel", "Glenn Maxwell"]},
    "KKR": {"name": "Kolkata Knight Riders", "color": "#3a225d", "logo": "⚔️",
            "batsmen": ["Rahmanullah Gurbaz", "Venkatesh Iyer", "Shreyas Iyer", "Nitish Rana", "Rinku Singh", "Andre Russell", "Sunil Narine"],
            "bowlers": ["Mitchell Starc", "Varun Chakravarthy", "Harshit Rana", "Sunil Narine", "Andre Russell"]},
    "SRH": {"name": "Sunrisers Hyderabad", "color": "#ff822a", "logo": "🌅",
            "batsmen": ["Travis Head", "Abhishek Sharma", "Heinrich Klaasen", "Aiden Markram", "Abdul Samad", "Rahul Tripathi", "Pat Cummins"],
            "bowlers": ["Pat Cummins", "Bhuvneshwar Kumar", "T Natarajan", "Jaydev Unadkat", "Abhishek Sharma"]},
    "DC":  {"name": "Delhi Capitals", "color": "#17479e", "logo": "🦅",
            "batsmen": ["David Warner", "Jake Fraser-McGurk", "Rishabh Pant", "Tristan Stubbs", "Axar Patel", "Mitchell Marsh", "Prithvi Shaw"],
            "bowlers": ["Anrich Nortje", "Kuldeep Yadav", "Ishant Sharma", "Mukesh Kumar", "Axar Patel"]},
    "PBKS":{"name": "Punjab Kings", "color": "#ed1f27", "logo": "🗡️",
            "batsmen": ["Shikhar Dhawan", "Jonny Bairstow", "Liam Livingstone", "Sam Curran", "Jitesh Sharma", "Sikandar Raza", "Prabhsimran Singh"],
            "bowlers": ["Kagiso Rabada", "Arshdeep Singh", "Sam Curran", "Rahul Chahar", "Liam Livingstone"]},
    "RR":  {"name": "Rajasthan Royals", "color": "#ea1a85", "logo": "👸",
            "batsmen": ["Yashasvi Jaiswal", "Jos Buttler", "Sanju Samson", "Shimron Hetmyer", "Dhruv Jurel", "Riyan Parag", "Rovman Powell"],
            "bowlers": ["Trent Boult", "Yuzvendra Chahal", "Sandeep Sharma", "Ravichandran Ashwin", "Riyan Parag"]},
    "GT":  {"name": "Gujarat Titans", "color": "#1c1c2b", "logo": "🛡️",
            "batsmen": ["Shubman Gill", "Wriddhiman Saha", "Sai Sudharsan", "Vijay Shankar", "David Miller", "Rahul Tewatia", "Kane Williamson"],
            "bowlers": ["Mohammed Shami", "Rashid Khan", "Josh Little", "Noor Ahmad", "Vijay Shankar"]},
    "LSG": {"name": "Lucknow Super Giants", "color": "#a72056", "logo": "🐅",
            "batsmen": ["KL Rahul", "Quinton de Kock", "Ayush Badoni", "Marcus Stoinis", "Nicholas Pooran", "Deepak Hooda", "Kyle Mayers"],
            "bowlers": ["Mark Wood", "Ravi Bishnoi", "Avesh Khan", "Krunal Pandya", "Marcus Stoinis"]},
}

STAR_PLAYERS = {
    "Virat Kohli": {"aggression": 0.7, "consistency": 0.9},
    "Rohit Sharma": {"aggression": 0.8, "consistency": 0.85},
    "MS Dhoni": {"aggression": 0.6, "consistency": 0.8},
    "Jasprit Bumrah": {"economy": 0.3, "wicket_threat": 0.9},
    "Suryakumar Yadav": {"aggression": 0.9, "consistency": 0.75},
    "Andre Russell": {"aggression": 0.95, "consistency": 0.6},
    "Rinku Singh": {"aggression": 0.7, "consistency": 0.75},
    "Heinrich Klaasen": {"aggression": 0.85, "consistency": 0.7},
    "Travis Head": {"aggression": 0.9, "consistency": 0.7},
    "Jos Buttler": {"aggression": 0.85, "consistency": 0.8},
    "Glenn Maxwell": {"aggression": 0.9, "consistency": 0.55},
    "Ravindra Jadeja": {"aggression": 0.65, "consistency": 0.8},
    "Pat Cummins": {"economy": 0.35, "wicket_threat": 0.8},
    "Mitchell Starc": {"economy": 0.4, "wicket_threat": 0.85},
    "Rashid Khan": {"economy": 0.25, "wicket_threat": 0.85},
    "Yuzvendra Chahal": {"economy": 0.35, "wicket_threat": 0.8},
}

@dataclass
class BallResult:
    ball_number: int
    over: int
    ball_in_over: int
    runs: int
    is_wicket: bool
    is_wide: bool
    is_noball: bool
    is_boundary: bool
    is_six: bool
    batsman: str
    bowler: str
    description: str
    score_after: int
    wickets_after: int
    rr_after: float
    win_prob_team1: float
    win_prob_team2: float
    momentum_team1: float

@dataclass
class MatchState:
    team1: str
    team2: str
    innings: int = 1
    score: int = 0
    wickets: int = 0
    overs: int = 0
    balls: int = 0
    total_balls: int = 0
    target: int = 0
    first_innings_score: int = 0
    current_batsman: str = ""
    non_striker: str = ""
    current_bowler: str = ""
    batsman_runs: int = 0
    batsman_balls: int = 0
    partnership: int = 0
    partnership_balls: int = 0
    last_six_balls: list = field(default_factory=list)
    run_rate: float = 0.0
    required_rate: float = 0.0
    win_prob_team1: float = 50.0
    win_prob_team2: float = 50.0
    momentum: float = 50.0
    momentum_history: list = field(default_factory=list)
    match_status: str = "live"
    ball_log: list = field(default_factory=list)
    over_summary: list = field(default_factory=list)
    phase: str = "powerplay"
    intensity: str = "MEDIUM"
    pressure_on: str = ""
    batsman_index: int = 2
    recent_events: list = field(default_factory=list)

    def to_dict(self):
        return {
            "team1": self.team1, "team2": self.team2,
            "team1_data": TEAMS[self.team1], "team2_data": TEAMS[self.team2],
            "innings": self.innings, "score": self.score, "wickets": self.wickets,
            "overs": f"{self.overs}.{self.balls}", "total_balls": self.total_balls,
            "target": self.target, "first_innings_score": self.first_innings_score,
            "current_batsman": self.current_batsman, "non_striker": self.non_striker,
            "current_bowler": self.current_bowler,
            "batsman_runs": self.batsman_runs, "batsman_balls": self.batsman_balls,
            "partnership": self.partnership, "partnership_balls": self.partnership_balls,
            "last_six_balls": self.last_six_balls[-6:],
            "run_rate": round(self.run_rate, 2),
            "required_rate": round(self.required_rate, 2) if self.innings == 2 else 0,
            "total_score": self.score,
            "current_run_rate": round(self.run_rate, 2),
            "required_run_rate": round(self.required_rate, 2) if self.innings == 2 else 0,
            "win_prob_team1": round(self.win_prob_team1, 1),
            "win_prob_team2": round(self.win_prob_team2, 1),
            "momentum": round(self.momentum, 1),
            "momentum_history": self.momentum_history[-40:],
            "match_status": self.match_status, "phase": self.phase,
            "intensity": self.intensity, "pressure_on": self.pressure_on,
            "over_summary": self.over_summary,
            "recent_events": self.recent_events[-5:],
            "batting_team": self.team1 if self.innings == 1 else self.team2,
            "bowling_team": self.team2 if self.innings == 1 else self.team1,
        }


class MatchEngine:
    def __init__(self, team1: str = "CSK", team2: str = "MI"):
        self.team1 = team1 if team1 in TEAMS else "CSK"
        self.team2 = team2 if team2 in TEAMS else "MI"
        self.state = MatchState(team1=self.team1, team2=self.team2)
        self._init_innings()

    def _init_innings(self):
        bt = self.team1 if self.state.innings == 1 else self.team2
        bw = self.team2 if self.state.innings == 1 else self.team1
        team = TEAMS[bt]
        self.state.current_batsman = team["batsmen"][0]
        self.state.non_striker = team["batsmen"][1]
        self.state.batsman_index = 2
        self.state.current_bowler = TEAMS[bw]["bowlers"][0]
        self.state.score = 0
        self.state.wickets = 0
        self.state.overs = 0
        self.state.balls = 0
        self.state.total_balls = 0
        self.state.batsman_runs = 0
        self.state.batsman_balls = 0
        self.state.partnership = 0
        self.state.partnership_balls = 0
        self.state.last_six_balls = []
        self.state.over_summary = []
        self.state.run_rate = 0.0

    def _get_phase(self) -> str:
        overs = self.state.overs + self.state.balls / 6
        if overs < 6: return "powerplay"
        elif overs < 15: return "middle"
        else: return "death"

    def _get_outcome_weights(self) -> dict:
        phase = self._get_phase()
        base = {0: 38, 1: 26, 2: 10, 3: 2, 4: 13, 6: 5, "W": 4, "wd": 2}
        if phase == "powerplay":
            base.update({4: 15, 6: 6, 0: 34, "W": 5})
        elif phase == "death":
            base.update({4: 14, 6: 9, 0: 30, 1: 20, "W": 6, 2: 12})

        batsman = self.state.current_batsman
        if batsman in STAR_PLAYERS:
            sp = STAR_PLAYERS[batsman]
            agg = sp.get("aggression", 0.7)
            base[4] = int(base[4] * (1 + agg * 0.3))
            base[6] = int(base[6] * (1 + agg * 0.5))
            base[0] = int(base[0] * (1 - agg * 0.15))

        bowler = self.state.current_bowler
        if bowler in STAR_PLAYERS:
            sp = STAR_PLAYERS[bowler]
            eco = sp.get("economy", 0.5)
            wt = sp.get("wicket_threat", 0.5)
            base[0] = int(base[0] * (1 + eco * 0.3))
            base["W"] = int(base["W"] * (1 + wt * 0.4))
            base[4] = int(base[4] * (1 - eco * 0.2))
            base[6] = int(base[6] * (1 - eco * 0.3))

        if self.state.innings == 2:
            balls_left = 120 - self.state.total_balls
            runs_needed = self.state.target - self.state.score
            if balls_left > 0:
                rrr = (runs_needed / balls_left) * 6
                if rrr > 12:
                    base[4] += 5; base[6] += 5; base[0] -= 8; base["W"] += 3
                elif rrr > 9:
                    base[4] += 3; base[6] += 3; base[0] -= 5
        return base

    def generate_ai_suggestion(self) -> dict:
        """Generate a smart AI prediction based on match context.
        
        Uses outcome weights + anti-repeat logic to produce varied,
        context-aware suggestions that feel like a real AI assistant.
        """
        weights = self._get_outcome_weights()
        phase = self._get_phase()
        batsman = self.state.current_batsman
        bowler = self.state.current_bowler

        # Map weight keys to prediction IDs
        outcome_map = {
            0: "dot", 1: "single", 2: "two", 3: "single",
            4: "boundary", 6: "six", "W": "wicket"
        }

        # Merge weights into prediction categories
        pred_weights = {"dot": 0, "single": 0, "two": 0, "boundary": 0, "six": 0, "wicket": 0}
        for outcome_key, weight in weights.items():
            if outcome_key == "wd":
                continue
            pred_id = outcome_map.get(outcome_key, "single")
            pred_weights[pred_id] += max(0, weight)

        total = sum(pred_weights.values())
        if total == 0:
            total = 1

        # Calculate probabilities
        probabilities = {k: v / total for k, v in pred_weights.items()}

        # Track last suggestion to avoid repeating the same pick
        last_pick = getattr(self, '_last_ai_pick', None)

        # Boost rarer outcomes to make suggestions more exciting
        # Flatten the distribution: give rare outcomes more weight
        boosted = {}
        for k, v in pred_weights.items():
            if k in ("six", "wicket"):
                boosted[k] = v * 2.5        # Rarer picks get a big boost
            elif k in ("boundary", "two"):
                boosted[k] = v * 1.8        # Medium picks get a moderate boost
            elif k == "single":
                boosted[k] = v * 1.2        # Singles stay roughly the same
            else:
                boosted[k] = v * 0.8        # Dot balls get slightly reduced

        # If last pick exists, reduce its weight to avoid repeats
        if last_pick and last_pick in boosted:
            boosted[last_pick] *= 0.2  # 80% penalty for repeating

        # Strategy with better variety:
        # 25% → pick from top-2 probable outcomes (smart but varied)
        # 35% → weighted random with boosted rare outcomes
        # 25% → contextual pick based on game situation
        # 15% → pure random (ensures all options show up sometimes)
        roll = random.random()

        if roll < 0.25:
            # Smart pick: pick from top-2 probable (not just #1)
            sorted_probs = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
            top_2 = [p[0] for p in sorted_probs[:3]]  # top 3 candidates
            if last_pick in top_2 and len(top_2) > 1:
                top_2 = [p for p in top_2 if p != last_pick]
            suggestion = random.choice(top_2)
        elif roll < 0.60:
            # Boosted weighted random — rare outcomes appear more
            items = list(boosted.keys())
            w = [max(1, v) for v in boosted.values()]
            suggestion = random.choices(items, weights=w, k=1)[0]
        elif roll < 0.85:
            # Contextual pick based on game situation
            if phase == "death" and self.state.wickets < 4:
                suggestion = random.choice(["boundary", "six", "single", "wicket"])
            elif phase == "death":
                suggestion = random.choice(["dot", "wicket", "single", "boundary"])
            elif phase == "powerplay":
                suggestion = random.choice(["boundary", "single", "dot", "six"])
            elif self.state.innings == 2 and self.state.target:
                runs_needed = self.state.target - self.state.score
                balls_left = 120 - self.state.total_balls
                rrr = (runs_needed / max(1, balls_left)) * 6
                if rrr > 10:
                    suggestion = random.choice(["six", "boundary", "wicket"])
                elif rrr > 7:
                    suggestion = random.choice(["boundary", "two", "six"])
                elif rrr < 5:
                    suggestion = random.choice(["dot", "wicket", "single"])
                else:
                    suggestion = random.choice(["single", "two", "boundary", "dot"])
            else:
                suggestion = random.choice(["single", "two", "boundary", "dot", "wicket"])
        else:
            # Pure random — ensures every option shows up sometimes
            all_options = ["dot", "single", "two", "boundary", "six", "wicket"]
            if last_pick:
                all_options = [o for o in all_options if o != last_pick]
            suggestion = random.choice(all_options)

        # Final anti-repeat check: if we still picked the same, re-roll once
        if suggestion == last_pick:
            alternatives = [k for k in pred_weights if k != last_pick]
            if alternatives:
                # Pick from alternatives weighted by boosted weights
                alt_w = [max(1, boosted.get(k, 1)) for k in alternatives]
                suggestion = random.choices(alternatives, weights=alt_w, k=1)[0]

        # Save this pick to avoid repeating next time
        self._last_ai_pick = suggestion

        # Generate reasoning
        label_map = {
            "dot": "Dot Ball", "single": "1 Run", "two": "2 Runs",
            "boundary": "Boundary", "six": "SIX!", "wicket": "Wicket"
        }
        label = label_map.get(suggestion, suggestion)

        # Build reasoning based on context
        reasons = []
        if batsman in STAR_PLAYERS:
            sp = STAR_PLAYERS[batsman]
            agg = sp.get("aggression", 0.7)
            if agg > 0.8 and suggestion in ("boundary", "six"):
                reasons.append(f"{batsman.split()[-1]} in attacking mode")
            elif agg > 0.8 and suggestion in ("dot", "wicket"):
                reasons.append(f"Against {batsman.split()[-1]}'s aggression — risky play")
            elif agg < 0.6 and suggestion in ("dot", "single"):
                reasons.append(f"{batsman.split()[-1]} playing cautiously")
            elif suggestion == "two":
                reasons.append(f"{batsman.split()[-1]} looking to rotate strike")
            elif suggestion == "wicket":
                reasons.append(f"Pressure building on {batsman.split()[-1]}")
            else:
                reasons.append(f"Reading {batsman.split()[-1]}'s intent")
        else:
            if suggestion in ("dot", "single"):
                reasons.append(f"{batsman.split()[-1]} settling in")
            elif suggestion in ("boundary", "six"):
                reasons.append(f"{batsman.split()[-1]} looking to attack")
            else:
                reasons.append(f"{batsman.split()[-1]} at the crease")

        if bowler in STAR_PLAYERS:
            sp = STAR_PLAYERS[bowler]
            wt = sp.get("wicket_threat", 0.5)
            eco = sp.get("economy", 0.5)
            if wt > 0.7 and suggestion == "wicket":
                reasons.append(f"{bowler.split()[-1]} is deadly here")
            elif eco < 0.35 and suggestion in ("dot", "single"):
                reasons.append(f"{bowler.split()[-1]} bowling tight lines")
            elif suggestion in ("boundary", "six"):
                reasons.append(f"Pressure on {bowler.split()[-1]}")
            elif suggestion == "two":
                reasons.append(f"Gap in {bowler.split()[-1]}'s field")
        else:
            if suggestion == "wicket":
                reasons.append("Bowling change could be key")
            elif suggestion in ("boundary", "six"):
                reasons.append("Loose delivery likely")

        if phase == "death":
            reasons.append("Death overs intensity")
        elif phase == "powerplay":
            reasons.append("Powerplay field restrictions")
        elif phase == "middle":
            if suggestion in ("dot", "wicket"):
                reasons.append("Middle overs squeeze")
            else:
                reasons.append("Building momentum")

        if self.state.innings == 2 and self.state.target:
            runs_needed = self.state.target - self.state.score
            balls_left = 120 - self.state.total_balls
            if balls_left > 0:
                rrr = (runs_needed / balls_left) * 6
                if rrr > 10:
                    reasons.append(f"RRR {rrr:.1f} — must attack")
                elif rrr > 7:
                    reasons.append(f"RRR {rrr:.1f} — pressure mounting")

        confidence = probabilities.get(suggestion, 0.15)
        # Scale confidence: rarer picks get lower confidence, common ones higher
        display_confidence = int(35 + confidence * 160)
        display_confidence = max(30, min(85, display_confidence))

        return {
            "prediction": suggestion,
            "label": label,
            "reason": " · ".join(reasons[:2]),
            "confidence": display_confidence,
            "phase": phase,
            "batsman": batsman,
            "bowler": bowler,
        }


    def _calc_win_prob(self):
        if self.state.innings == 1:
            overs = self.state.overs + self.state.balls / 6
            if overs == 0: return 50.0
            projected = (self.state.score / overs) * 20 if overs > 0 else 0
            advantage = (projected - 170) / 5
            self.state.win_prob_team1 = max(15, min(85, 50 + advantage))
            self.state.win_prob_team2 = 100 - self.state.win_prob_team1
        else:
            balls_left = 120 - self.state.total_balls
            runs_needed = self.state.target - self.state.score
            wickets_left = 10 - self.state.wickets
            if runs_needed <= 0:
                self.state.win_prob_team2 = 99
                self.state.win_prob_team1 = 1
                return
            if balls_left <= 0 or wickets_left <= 0:
                self.state.win_prob_team1 = 99
                self.state.win_prob_team2 = 1
                return
            rrr = (runs_needed / balls_left) * 6
            resource_factor = wickets_left / 10
            difficulty = rrr / (self.state.run_rate + 0.01)
            chase_prob = max(5, min(95, 50 - (difficulty - 1) * 20 + resource_factor * 15))
            self.state.win_prob_team2 = chase_prob
            self.state.win_prob_team1 = 100 - chase_prob

    def _calc_momentum(self, runs, is_wicket):
        batting_team_is_1 = self.state.innings == 1
        delta = 0
        if is_wicket:
            delta = -8 if batting_team_is_1 else 8
        elif runs == 6:
            delta = 6 if batting_team_is_1 else -6
        elif runs == 4:
            delta = 4 if batting_team_is_1 else -4
        elif runs == 0:
            delta = -2 if batting_team_is_1 else 2
        else:
            delta = (runs - 1) * (1 if batting_team_is_1 else -1)
        self.state.momentum = max(5, min(95, self.state.momentum + delta))
        self.state.momentum_history.append(round(self.state.momentum, 1))

    def _update_intensity(self):
        phase = self._get_phase()
        rr = self.state.run_rate
        if phase == "death" or (self.state.innings == 2 and self.state.required_rate > 10):
            self.state.intensity = "EXTREME"
        elif rr > 9 or self.state.wickets >= 5:
            self.state.intensity = "HIGH"
        elif rr > 7:
            self.state.intensity = "MEDIUM"
        else:
            self.state.intensity = "LOW"

        if self.state.innings == 2 and self.state.required_rate > 12:
            bt = self.team2
            self.state.pressure_on = f"{bt} Batsmen"
        elif self.state.wickets >= 6:
            bt = self.team1 if self.state.innings == 1 else self.team2
            self.state.pressure_on = f"{bt} Lower Order"
        elif self.state.run_rate < 6 and self.state.overs > 10:
            bt = self.team1 if self.state.innings == 1 else self.team2
            self.state.pressure_on = f"{bt} Batsmen"
        else:
            bw = self.team2 if self.state.innings == 1 else self.team1
            self.state.pressure_on = f"{bw} Bowlers"

    def simulate_ball(self) -> Optional[BallResult]:
        if self.state.match_status != "live":
            return None

        striker = self.state.current_batsman
        bowler = self.state.current_bowler
        weights = self._get_outcome_weights()
        outcomes = []
        probs = []
        for k, v in weights.items():
            outcomes.append(k)
            probs.append(v)
        total = sum(probs)
        probs = [p / total for p in probs]
        result = random.choices(outcomes, weights=probs, k=1)[0]

        is_wide = result == "wd"
        is_wicket = result == "W"
        runs = 0 if (is_wicket or is_wide) else int(result)
        if is_wide:
            runs = 1

        is_boundary = runs == 4
        is_six = runs == 6
        self.state.score += runs

        if not is_wide:
            self.state.balls += 1
            self.state.total_balls += 1
            self.state.batsman_balls += 1
        else:
            self.state.score += 0  # wide already added 1

        self.state.batsman_runs += runs if not is_wide else 0
        self.state.partnership += runs
        self.state.partnership_balls += 0 if is_wide else 1

        desc = ""
        ball_display = ""
        if is_wicket:
            desc = f"OUT! {self.state.current_batsman} dismissed by {self.state.current_bowler}!"
            ball_display = "W"
            self.state.wickets += 1
            bt = self.team1 if self.state.innings == 1 else self.team2
            if self.state.batsman_index < len(TEAMS[bt]["batsmen"]):
                self.state.current_batsman = TEAMS[bt]["batsmen"][self.state.batsman_index]
                self.state.batsman_index += 1
            self.state.batsman_runs = 0
            self.state.batsman_balls = 0
            self.state.partnership = 0
            self.state.partnership_balls = 0
            self.state.recent_events.append({"type": "wicket", "text": desc})
        elif is_six:
            desc = f"SIX! {self.state.current_batsman} smashes {self.state.current_bowler}!"
            ball_display = "6"
            self.state.recent_events.append({"type": "six", "text": desc})
        elif is_boundary:
            desc = f"FOUR! {self.state.current_batsman} finds the gap!"
            ball_display = "4"
            self.state.recent_events.append({"type": "four", "text": desc})
        elif is_wide:
            desc = f"Wide ball by {self.state.current_bowler}"
            ball_display = "wd"
        elif runs == 0:
            desc = f"Dot ball. Good delivery by {self.state.current_bowler}"
            ball_display = "0"
        else:
            desc = f"{runs} run{'s' if runs > 1 else ''} taken by {self.state.current_batsman}"
            ball_display = str(runs)

        self.state.last_six_balls.append(ball_display)

        # Rotate strike on odd runs
        if runs % 2 == 1 and not is_wide:
            self.state.current_batsman, self.state.non_striker = self.state.non_striker, self.state.current_batsman
            self.state.batsman_runs = 0
            self.state.batsman_balls = 0

        # Over complete
        if self.state.balls == 6:
            over_runs = sum(int(b) if b.isdigit() else (0 if b == "W" else 1) for b in self.state.last_six_balls[-6:])
            self.state.over_summary.append({"over": self.state.overs + 1, "runs": over_runs, "balls": list(self.state.last_six_balls[-6:])})
            self.state.overs += 1
            self.state.balls = 0
            # Rotate strike at end of over
            self.state.current_batsman, self.state.non_striker = self.state.non_striker, self.state.current_batsman
            self.state.batsman_runs, self.state.batsman_balls = 0, 0
            # Change bowler
            bw = self.team2 if self.state.innings == 1 else self.team1
            bowlers = TEAMS[bw]["bowlers"]
            self.state.current_bowler = bowlers[self.state.overs % len(bowlers)]

        # Update stats
        total_overs = self.state.overs + self.state.balls / 6
        self.state.run_rate = self.state.score / total_overs if total_overs > 0 else 0
        if self.state.innings == 2:
            balls_left = 120 - self.state.total_balls
            runs_needed = self.state.target - self.state.score
            self.state.required_rate = (runs_needed / balls_left) * 6 if balls_left > 0 else 999

        self.state.phase = self._get_phase()
        self._calc_win_prob()
        self._calc_momentum(runs if not is_wide else 0, is_wicket)
        self._update_intensity()

        ball = BallResult(
            ball_number=self.state.total_balls, over=self.state.overs,
            ball_in_over=self.state.balls, runs=runs,
            is_wicket=is_wicket, is_wide=is_wide, is_noball=False,
            is_boundary=is_boundary, is_six=is_six,
            batsman=striker, bowler=bowler,
            description=desc, score_after=self.state.score,
            wickets_after=self.state.wickets, rr_after=round(self.state.run_rate, 2),
            win_prob_team1=round(self.state.win_prob_team1, 1),
            win_prob_team2=round(self.state.win_prob_team2, 1),
            momentum_team1=round(self.state.momentum, 1),
        )
        self.state.ball_log.append(ball_display)

        # Check innings/match end
        if self.state.overs >= 20 or self.state.wickets >= 10:
            if self.state.innings == 1:
                self.state.first_innings_score = self.state.score
                self.state.target = self.state.score + 1
                self.state.innings = 2
                self._init_innings()
                self.state.recent_events.append({
                    "type": "innings_break",
                    "text": f"Innings Break! {self.team2} need {self.state.target} to win!"
                })
            else:
                self.state.match_status = "completed"
                if self.state.score >= self.state.target:
                    self.state.recent_events.append({
                        "type": "result",
                        "text": f"{self.team2} win by {10 - self.state.wickets} wickets!"
                    })
                else:
                    self.state.recent_events.append({
                        "type": "result",
                        "text": f"{self.team1} win by {self.state.target - self.state.score - 1} runs!"
                    })

        if self.state.innings == 2 and self.state.score >= self.state.target:
            self.state.match_status = "completed"
            self.state.recent_events.append({
                "type": "result",
                "text": f"{self.team2} win by {10 - self.state.wickets} wickets!"
            })

        return ball

    def get_state(self) -> dict:
        return self.state.to_dict()

    def get_prediction_options(self) -> list:
        # Get context info
        batsman = self.state.current_batsman
        bowler = self.state.current_bowler
        phase = self._get_phase()
        intensity = self.state.intensity

        # Get batsman characteristics (aggression)
        agg = 0.5  # default moderate aggression
        if batsman in STAR_PLAYERS:
            agg = STAR_PLAYERS[batsman].get("aggression", 0.5)

        # Get bowler characteristics (economy and wicket threat)
        eco = 0.5  # default economy
        wt = 0.5  # default wicket threat
        if bowler in STAR_PLAYERS:
            eco = STAR_PLAYERS[bowler].get("economy", 0.5)
            wt = STAR_PLAYERS[bowler].get("wicket_threat", 0.5)

        # dot ball likelihood: higher if defensive batsman or tight bowler
        dot_prob_factor = (1.0 - agg * 0.4) * (1.0 + (1.0 - eco) * 0.5)
        # single likelihood: higher if consistent batsman, lower if aggressive
        single_prob_factor = (1.0 - (agg - 0.5) * 0.3)
        # two runs likelihood: higher if consistent accumulator
        two_prob_factor = 1.0 if phase != "death" else 0.8
        # boundary likelihood: higher in powerplay/death, higher for aggressive batsmen, lower for tight bowlers
        boundary_prob_factor = (1.0 + agg * 0.6) * (1.0 - eco * 0.4)
        if phase == "powerplay":
            boundary_prob_factor *= 1.2
        elif phase == "death":
            boundary_prob_factor *= 1.3
        # six likelihood: higher for aggressive batsmen in death
        six_prob_factor = (1.0 + agg * 1.0) * (1.0 - eco * 0.5)
        if phase == "death":
            six_prob_factor *= 1.5
        elif phase == "powerplay":
            six_prob_factor *= 0.9
        # wicket likelihood: higher if high wicket threat bowler
        wicket_prob_factor = (1.0 + wt * 0.8)
        if intensity == "EXTREME":
            wicket_prob_factor *= 1.3
        elif intensity == "HIGH":
            wicket_prob_factor *= 1.1

        # Calculate odds and XP
        dot_odds = max(1.2, min(5.0, 1.8 / dot_prob_factor))
        dot_xp = max(5, min(40, int(10 * (dot_odds / 1.8))))

        single_odds = max(1.1, min(4.0, 1.5 / single_prob_factor))
        single_xp = max(4, min(30, int(8 * (single_odds / 1.5))))

        two_odds = max(2.0, min(8.0, 3.5 / two_prob_factor))
        two_xp = max(10, min(50, int(18 * (two_odds / 3.5))))

        boundary_odds = max(2.0, min(10.0, 4.0 / boundary_prob_factor))
        boundary_xp = max(12, min(70, int(25 * (boundary_odds / 4.0))))

        six_odds = max(3.0, min(15.0, 6.0 / six_prob_factor))
        six_xp = max(20, min(100, int(40 * (six_odds / 6.0))))

        wicket_odds = max(4.0, min(20.0, 8.0 / wicket_prob_factor))
        wicket_xp = max(25, min(150, int(55 * (wicket_odds / 8.0))))

        intensity_boost = 1.0
        if intensity == "EXTREME":
            intensity_boost = 1.3
        elif intensity == "HIGH":
            intensity_boost = 1.1

        self.current_options = [
            {"id": "dot", "label": "Dot Ball", "emoji": "⚫", "odds": f"{dot_odds:.1f}x", "xp": int(dot_xp * intensity_boost)},
            {"id": "single", "label": "1 Run", "emoji": "1️⃣", "odds": f"{single_odds:.1f}x", "xp": int(single_xp * intensity_boost)},
            {"id": "two", "label": "2 Runs", "emoji": "2️⃣", "odds": f"{two_odds:.1f}x", "xp": int(two_xp * intensity_boost)},
            {"id": "boundary", "label": "Boundary", "emoji": "🏏", "odds": f"{boundary_odds:.1f}x", "xp": int(boundary_xp * intensity_boost)},
            {"id": "six", "label": "SIX!", "emoji": "6️⃣", "odds": f"{six_odds:.1f}x", "xp": int(six_xp * intensity_boost)},
            {"id": "wicket", "label": "Wicket", "emoji": "🔴", "odds": f"{wicket_odds:.1f}x", "xp": int(wicket_xp * intensity_boost)},
        ]
        return self.current_options

    def check_prediction(self, prediction: str, ball: BallResult) -> dict:
        correct = False
        
        # Get XP from self.current_options if it exists
        opt_xp = 10  # default fallback
        if hasattr(self, 'current_options') and self.current_options:
            for opt in self.current_options:
                if opt['id'] == prediction:
                    opt_xp = opt['xp']
                    break
        else:
            fallbacks = {"dot": 10, "single": 8, "two": 15, "boundary": 20, "six": 30, "wicket": 50}
            opt_xp = fallbacks.get(prediction, 10)

        if prediction == "dot" and ball.runs == 0 and not ball.is_wicket:
            correct = True
        elif prediction == "single" and ball.runs == 1 and not ball.is_wide:
            correct = True
        elif prediction == "two" and ball.runs == 2:
            correct = True
        elif prediction == "boundary" and ball.is_boundary:
            correct = True
        elif prediction == "six" and ball.is_six:
            correct = True
        elif prediction == "wicket" and ball.is_wicket:
            correct = True
            
        return {"correct": correct, "xp": opt_xp if correct else 0, "prediction": prediction}
