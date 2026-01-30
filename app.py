import time
from itertools import combinations
from typing import Dict, List, Optional, Tuple
 
import pandas as pd
import streamlit as st
#NICOLE CHANGE HERE:
#from part2_Optimization.ipynb import functionName
 
 
# ----------------------------
# Page setup
# ----------------------------
st.set_page_config(page_title="Coach Dashboard", layout="wide")
st.title("🏉 Coach Dashboard")
 
 
# ----------------------------
# Load data (your real CSVs)
# ----------------------------
@st.cache_data
def load_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    players = pd.read_csv("Data/player_data.csv")
    stints = pd.read_csv("Data/stint_data.csv")
    return players, stints
 
 
players_raw, stints_df = load_data()
 
# Normalize player columns
# Expected in your file: player, rating
players_df = players_raw.rename(columns={"player": "player_id", "rating": "disability_score"}).copy()
players_df["country"] = players_df["player_id"].astype(str).str.split("_").str[0]
 
 
# ----------------------------
# Compute a baseline "value score" from stints
# value_score = (goal differential while on court) / minutes
# (we can replace later if you already have your own score)
# ----------------------------
@st.cache_data
def compute_value_scores(players_df: pd.DataFrame, stints_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in stints_df.iterrows():
        minutes = float(r.get("minutes", 0))
        if minutes <= 0:
            continue
 
        h_diff = float(r["h_goals"]) - float(r["a_goals"])
        a_diff = -h_diff
 
        home_players = [r["home1"], r["home2"], r["home3"], r["home4"]]
        away_players = [r["away1"], r["away2"], r["away3"], r["away4"]]
 
        for p in home_players:
            rows.append({"player_id": p, "diff": h_diff, "minutes": minutes})
        for p in away_players:
            rows.append({"player_id": p, "diff": a_diff, "minutes": minutes})
 
    long_df = pd.DataFrame(rows)
    out = players_df.copy()
 
    if long_df.empty:
        out["value_score"] = 0.0
        return out
 
    agg = long_df.groupby("player_id", as_index=False).agg(
        total_diff=("diff", "sum"),
        total_minutes=("minutes", "sum"),
    )
    agg["value_score"] = agg["total_diff"] / agg["total_minutes"].replace(0, 1)
 
    out = out.merge(agg[["player_id", "value_score"]], on="player_id", how="left")
    out["value_score"] = out["value_score"].fillna(0.0)
 
    # scale to -10..10 so it's readable
    mx = out["value_score"].abs().max()
    if mx and mx > 0:
        out["value_score"] = (out["value_score"] / mx) * 10
 
    return out
 
 
players_df = compute_value_scores(players_df, stints_df)

# Initialize the optimization model
#NICOLE CHANGE HERE:
@st.cache_resource
def load_optimizer():
    """Load ML-based optimizer (cached for performance)"""
    try:
        return LineupOptimizer("player_scores.xlsx")
    except FileNotFoundError:
        st.warning("player_scores.xlsx not found. Using value_score-based optimization.")
        return None

optimizer = load_optimizer()

# Session state helpers
# ----------------------------
def reset_all():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
 
 
def ensure_state(all_ids: List[str], countries: List[str], game_ids: List[int]):
    if "country" not in st.session_state:
        st.session_state.country = countries[0] if countries else ""
 
    if "selected_game_id" not in st.session_state:
        st.session_state.selected_game_id = game_ids[0] if game_ids else 0
 
    if "availability" not in st.session_state:
        st.session_state.availability = {pid: True for pid in all_ids}
 
    if "fatigue" not in st.session_state:
        st.session_state.fatigue = {pid: 10.0 for pid in all_ids}
 
    if "lineup" not in st.session_state:
        st.session_state.lineup = []  # 4 ids
 
    if "disability_cap" not in st.session_state:
        st.session_state.disability_cap = 8.0
 
    # scoreboard + timers
    if "home_team" not in st.session_state:
        st.session_state.home_team = "H"
    if "away_team" not in st.session_state:
        st.session_state.away_team = "A"
    if "home_score" not in st.session_state:
        st.session_state.home_score = 0
    if "away_score" not in st.session_state:
        st.session_state.away_score = 0
 
    if "game_start" not in st.session_state:
        st.session_state.game_start = None
    if "stint_start" not in st.session_state:
        st.session_state.stint_start = None
 
    if "live_stints" not in st.session_state:
        st.session_state.live_stints = []
 
    if "last_opt" not in st.session_state:
        st.session_state.last_opt = None
 
 
def fmt_time(seconds: Optional[float]) -> str:
    if seconds is None:
        return "00:00"
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"
 
 
def elapsed(ts: Optional[float]) -> Optional[float]:
    if ts is None:
        return None
    return time.time() - ts
 
 
# ----------------------------
# Placeholder optimizer (works now)
# - picks best feasible lineup by value_score - fatigue penalty
# - respects disability cap
# Later: replace this function call with your real optimizer file
# ----------------------------
def optimize_lineup(
    team_df: pd.DataFrame,
    availability: Dict[str, bool],
    fatigue: Dict[str, float],
    disability_cap: float,
    fatigue_weight: float = 2.0,
) -> Dict:
    #CHANGES MADE HERE
    #NICOLE CHANGE HERE:
    """
    Use the ML-based optimizer if available, otherwise fall back to placeholder.
    """
    if optimizer:
        # Use the real ML-based optimization model
        result = optimizer.optimize_lineup(
            team_df=team_df,
            availability=availability,
            fatigue=fatigue,
            disability_cap=disability_cap,
            fatigue_weight=fatigue_weight,
            lineup_size=4
        )
        return result
    else:
        # Fallback to simple optimizer for testing
        df = team_df[team_df["player_id"].map(lambda x: availability.get(x, True))].copy()
        if len(df) < 4:
            return {"lineup": [], "objective": 0.0, "notes": "Not enough available players to form 4-player lineup.", "breakdown": []}
    
        df["fatigue"] = df["player_id"].map(lambda x: fatigue.get(x, 0.0))
        df["score_adj"] = df["value_score"] - fatigue_weight * (df["fatigue"] / 100.0)
    
        df_idx = df.set_index("player_id")
        ids = df["player_id"].tolist()
    
        best_combo = None
        best_obj = -1e18
    
        for combo in combinations(ids, 4):
            dis_sum = float(df_idx.loc[list(combo), "disability_score"].sum())
            if dis_sum <= disability_cap:
                obj = float(df_idx.loc[list(combo), "score_adj"].sum())
                if obj > best_obj:
                    best_obj = obj
                    best_combo = list(combo)
    
        if not best_combo:
            return {"lineup": [], "objective": 0.0, "notes": f"No feasible lineup under cap {disability_cap}.", "breakdown": []}
    
        return {
            "lineup": best_combo,
            "objective": best_obj,
            "notes": "Placeholder optimizer (value - fatigue penalty, with disability cap).",
            "breakdown": []
        }
 
 
# ----------------------------
# Init state
# ----------------------------
all_ids = players_df["player_id"].tolist()
countries = sorted(players_df["country"].unique().tolist())
game_ids = sorted(stints_df["game_id"].unique().tolist()) if len(stints_df) else []
ensure_state(all_ids, countries, game_ids)
 
 
# ----------------------------
# TOP BAR (like your sketch)
# ----------------------------
top_a, top_b, top_c, top_d = st.columns([1.1, 1.1, 1.1, 1.1])
 
with top_a:
    st.session_state.country = st.selectbox(
        "Country",
        countries,
        index=countries.index(st.session_state.country) if st.session_state.country in countries else 0,
    )
 
with top_b:
    st.session_state.selected_game_id = st.selectbox(
        "Game (history view)",
        game_ids,
        index=game_ids.index(st.session_state.selected_game_id) if st.session_state.selected_game_id in game_ids else 0,
    )
 
with top_c:
    st.session_state.disability_cap = st.number_input(
        "Disability cap",
        0.0, 20.0,
        float(st.session_state.disability_cap),
        0.5
    )
 
with top_d:
    if st.button("🧹 Clear / Reset", use_container_width=True):
        reset_all()
        st.rerun()
 
st.divider()
 
 
# ============================
# MAIN LAYOUT
# ============================
left, right = st.columns([1.65, 1.0])
 
team_df = players_df[players_df["country"] == st.session_state.country].copy()
team_ids = team_df["player_id"].tolist()
 
 
# ----------------------------
# LEFT PANEL (country + players + stint history + insights)
# ----------------------------
with left:
    st.subheader("Players")
 
    # Controls in expander to keep clean
    with st.expander("Set availability + fatigue", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Set ALL Available"):
                for pid in team_ids:
                    st.session_state.availability[pid] = True
        with c2:
            if st.button("Set ALL Not Available"):
                for pid in team_ids:
                    st.session_state.availability[pid] = False
 
        st.caption("Toggle availability + adjust fatigue anytime (even between stints).")
        for pid in team_ids:
            cols = st.columns([1.2, 1.0])
            with cols[0]:
                st.session_state.availability[pid] = st.checkbox(
                    pid,
                    value=st.session_state.availability.get(pid, True),
                    key=f"avail_{pid}",
                )
            with cols[1]:
                st.session_state.fatigue[pid] = st.slider(
                    "Fatigue",
                    0.0, 100.0,
                    float(st.session_state.fatigue.get(pid, 10.0)),
                    1.0,
                    key=f"fat_{pid}",
                    label_visibility="collapsed",
                )
 
    # Player table
    table = team_df.copy()
    table["available"] = table["player_id"].map(lambda x: st.session_state.availability.get(x, True))
    table["fatigue"] = table["player_id"].map(lambda x: st.session_state.fatigue.get(x, 0.0))
 
    st.dataframe(
        table[["player_id", "value_score", "disability_score", "available", "fatigue"]]
        .sort_values(["available", "value_score"], ascending=[False, False]),
        use_container_width=True,
        hide_index=True,
    )
 
    st.markdown("**Fatigue (team)**")
    for _, r in table.sort_values("fatigue", ascending=False).iterrows():
        st.progress(int(r["fatigue"]), text=f"{r['player_id']} — {r['fatigue']:.0f}/100")
 
    st.divider()
 
    st.subheader("Stint History (current game)")
    hist = stints_df[stints_df["game_id"] == st.session_state.selected_game_id].copy()
    hist = hist[(hist["h_team"] == st.session_state.country) | (hist["a_team"] == st.session_state.country)]
 
    if hist.empty:
        st.info("No stints found for this country in the selected game.")
    else:
        def fmt_players(r):
            home = [r["home1"], r["home2"], r["home3"], r["home4"]]
            away = [r["away1"], r["away2"], r["away3"], r["away4"]]
            return ", ".join(home) + "  |  " + ", ".join(away)
 
        show = hist[["minutes", "h_goals", "a_goals", "home1", "home2", "home3", "home4",
                    "away1", "away2", "away3", "away4"]].copy()
        show["players_on_court"] = hist.apply(fmt_players, axis=1)
        show = show.rename(columns={"minutes": "duration_min", "h_goals": "home_score_end", "a_goals": "away_score_end"})
        show = show[["duration_min", "home_score_end", "away_score_end", "players_on_court"]]
        st.dataframe(show, use_container_width=True, hide_index=True)
 
    st.divider()
 
    st.subheader("Insights")
    st.info(
        "- Placeholder insights (add later)\n"
        "- Example: lineups with P1+P3 have better diff/min\n"
        "- Example: warning if lineup avg fatigue > 70"
    )
 
 
# ----------------------------
# RIGHT PANEL (scoreboard + game time + lineup + buttons + totals + stint time)
# ----------------------------
with right:
    st.subheader("Scoreboard")
 
    sb1, sb2, sb3 = st.columns([1.0, 0.6, 1.0])
    with sb1:
        st.session_state.home_team = st.text_input("Home", value=st.session_state.home_team)
        st.session_state.home_score = st.number_input("H score", min_value=0, value=int(st.session_state.home_score), step=1)
    with sb2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        st.markdown("### —")
    with sb3:
        st.session_state.away_team = st.text_input("Away", value=st.session_state.away_team)
        st.session_state.away_score = st.number_input("A score", min_value=0, value=int(st.session_state.away_score), step=1)
 
    st.markdown("**Overall game runtime**")
    st.metric("Time", fmt_time(elapsed(st.session_state.game_start)))
 
    g1, g2 = st.columns(2)
    with g1:
        if st.button("▶️ Start Game", use_container_width=True):
            if st.session_state.game_start is None:
                st.session_state.game_start = time.time()
    with g2:
        if st.button("⏹ Stop Game", use_container_width=True):
            st.session_state.game_start = None
 
    st.divider()
 
    st.subheader("Lineup (current stint)")
 
    # 4 slots in a row
    l1, l2, l3, l4 = st.columns(4)
    opts = team_ids
 
    def pick_default(i: int) -> int:
        if len(st.session_state.lineup) == 4 and st.session_state.lineup[i] in opts:
            return opts.index(st.session_state.lineup[i])
        return min(i, max(0, len(opts) - 1))
 
    p1 = l1.selectbox("1", options=opts, index=pick_default(0))
    p2 = l2.selectbox("2", options=opts, index=pick_default(1))
    p3 = l3.selectbox("3", options=opts, index=pick_default(2))
    p4 = l4.selectbox("4", options=opts, index=pick_default(3))
 
    lineup = [p1, p2, p3, p4]
    if len(set(lineup)) < 4:
        st.warning("Lineup must have 4 different players.")
    else:
        st.session_state.lineup = lineup
 
    # Buttons
    b1, b2 = st.columns(2)
    with b1:
        if st.button("⚙️ Optimize", use_container_width=True):
            res = optimize_lineup(
                team_df=team_df,
                availability=st.session_state.availability,
                fatigue=st.session_state.fatigue,
                disability_cap=float(st.session_state.disability_cap),
                fatigue_weight=2.0,
            )
            st.session_state.last_opt = res
            if res["lineup"]:
                st.session_state.lineup = res["lineup"]
                st.rerun()
    with b2:
        if st.button("🧼 Clear lineup", use_container_width=True):
            st.session_state.lineup = []
            st.session_state.last_opt = None
            st.rerun()
 
    # Lineup totals
    st.markdown("**Lineup total disability score**")
    if len(st.session_state.lineup) == 4 and len(set(st.session_state.lineup)) == 4:
        ldf = team_df[team_df["player_id"].isin(st.session_state.lineup)].copy()
        total_dis = float(ldf["disability_score"].sum())
        if total_dis > float(st.session_state.disability_cap):
            st.error(f"{total_dis:.1f} (OVER cap {float(st.session_state.disability_cap):.1f})")
        else:
            st.success(f"{total_dis:.1f} (cap {float(st.session_state.disability_cap):.1f})")
 
        st.markdown("**Fatigue of lineup**")
        for pid in st.session_state.lineup:
            f = float(st.session_state.fatigue.get(pid, 0.0))
            st.progress(int(f), text=f"{pid} — {f:.0f}/100")
    else:
        st.info("Select a valid 4-player lineup to see disability + fatigue.")
 
    st.divider()
 
    st.markdown("**Current stint runtime**")
    st.metric("Time", fmt_time(elapsed(st.session_state.stint_start)))
 
    s1, s2, s3 = st.columns(3)
    with s1:
        if st.button("▶️ Start Stint", use_container_width=True):
            if st.session_state.stint_start is None:
                st.session_state.stint_start = time.time()
    with s2:
        if st.button("⏹ Stop Stint", use_container_width=True):
            st.session_state.stint_start = None
    with s3:
        if st.button("✅ End + Save", use_container_width=True):
            dur = elapsed(st.session_state.stint_start)
            if dur is None:
                st.warning("Start stint timer first.")
            elif len(st.session_state.lineup) != 4 or len(set(st.session_state.lineup)) != 4:
                st.warning("Need a valid 4-player lineup to save the stint.")
            else:
                st.session_state.live_stints.append({
                    "game_id": st.session_state.selected_game_id,
                    "end_time_game": fmt_time(elapsed(st.session_state.game_start)),
                    "stint_duration": fmt_time(dur),
                    "home_score": st.session_state.home_score,
                    "away_score": st.session_state.away_score,
                    "lineup": ", ".join(st.session_state.lineup),
                })
                st.session_state.stint_start = None
                st.success("Saved stint to session history.")
 
    if st.session_state.live_stints:
        st.caption("Session stints saved (this run)")
        st.dataframe(pd.DataFrame(st.session_state.live_stints), use_container_width=True, hide_index=True)
 
    if st.session_state.last_opt:
        st.caption("Optimizer output")
        st.write(st.session_state.last_opt.get("notes", ""))
        st.write(f"Objective: {st.session_state.last_opt.get('objective', 0.0):.3f}")