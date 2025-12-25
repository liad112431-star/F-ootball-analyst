import streamlit as st
import requests
import datetime
import math

# =====================
# CONFIG
# =====================
API_KEY = "PUT_YOUR_API_KEY_HERE"  # <<< כאן תדביק את המפתח
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY
}

# =====================
# HELPERS
# =====================
def api_get(endpoint, params=None):
    r = requests.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params)
    return r.json()["response"]

def poisson_prob(lmbd, goals):
    return (math.exp(-lmbd) * (lmbd ** goals)) / math.factorial(goals)

def over_probability(avg_goals, line=2.5):
    prob = 0
    for g in range(0, int(line) + 1):
        prob += poisson_prob(avg_goals, g)
    return 1 - prob

# =====================
# DATA
# =====================
def get_fixtures_today():
    today = datetime.date.today().strftime("%Y-%m-%d")
    return api_get("fixtures", {"date": today})

def get_team_stats(team_id, league_id, season):
    return api_get("teams/statistics", {
        "team": team_id,
        "league": league_id,
        "season": season
    })

def get_h2h(home, away):
    return api_get("fixtures/headtohead", {
        "h2h": f"{home}-{away}"
    })

# =====================
# ANALYST ENGINE
# =====================
def analyze_match(fx):
    home = fx["teams"]["home"]
    away = fx["teams"]["away"]

    league_id = fx["league"]["id"]
    season = fx["league"]["season"]

    home_stats = get_team_stats(home["id"], league_id, season)
    away_stats = get_team_stats(away["id"], league_id, season)

    home_goals = home_stats["goals"]["for"]["average"]["total"]
    away_goals = away_stats["goals"]["for"]["average"]["total"]

    avg_goals = home_goals + away_goals

    over25 = over_probability(avg_goals, 2.5)
    over15 = over_probability(avg_goals, 1.5)

    btts = min(home_goals, away_goals) / max(home_goals, away_goals)

    recommendation = []
    if over25 > 0.6:
        recommendation.append("Over 2.5")
    elif over15 > 0.75:
        recommendation.append("Over 1.5")

    if btts > 0.55:
        recommendation.append("BTTS")

    if home_goals > away_goals * 1.2:
        recommendation.append("Home Win / Double Chance")

    confidence = round((over25 + over15 + btts) / 3 * 100, 1)

    return {
        "match": f'{home["name"]} vs {away["name"]}',
        "recommendations": recommendation,
        "confidence": confidence
    }

# =====================
# BET BUILDER
# =====================
def bet_builder(matches):
    base_prob = 1
    for m in matches:
        base_prob *= m["confidence"] / 100

    risk = "נמוך" if len(matches) <= 3 else "בינוני" if len(matches) <= 6 else "גבוה"

    return {
        "matches": len(matches),
        "hit_rate": round(base_prob * 100, 1),
        "risk": risk
    }

# =====================
# UI
# =====================
st.set_page_config(page_title="Football Betting Analyst", layout="wide")
st.title("⚽ אנליסט כדורגל חכם להימורים")

fixtures = get_fixtures_today()

analyses = []

for fx in fixtures:
    with st.expander(f'{fx["teams"]["home"]["name"]} vs {fx["teams"]["away"]["name"]}'):
        result = analyze_match(fx)
        analyses.append(result)

        st.write("📊 המלצות חזקות:")
        for r in result["recommendations"]:
            st.success(r)

        st.write(f'🔥 ביטחון: {result["confidence"]}%')

st.divider()
st.header("🧾 בניית טופס חכם")

selected = st.multiselect(
    "בחר משחקים לטופס",
    analyses,
    format_func=lambda x: x["match"]
)

if selected:
    summary = bet_builder(selected)
    st.metric("מספר משחקים", summary["matches"])
    st.metric("אחוז פגיעה משוער", f'{summary["hit_rate"]}%')
    st.metric("רמת סיכון", summary["risk"])
