#!/usr/bin/env python3
"""
WC2026 CONTENT AGENT  —  autonomous, copyright-safe World Cup content factory
=============================================================================

What it does, end to end, every time it runs:
  1. DETECT   : asks football-data.org which World Cup matches just finished
  2. DEDUPE   : skips matches it already processed (state file)
  3. ANALYSE  : scores the 11 video types (A-K) and picks the strongest angle
  4. WRITE    : Groq LLM writes a 3-5 min storytelling script (HOOK->CTA)
  5. PACKAGE  : 30 scored titles, 10 thumbnail concepts, 3 Shorts, social posts
  6. SAVE     : drops everything into output/<match>/ as readable files

It is NOT a "press button, 100 identical videos" machine (that gets channels
deleted under YouTube's 2026 inauthentic-content policy). It does the boring
80% and hands YOU a finished script + assets to record/cut in your own voice.

RUN IT:
    pip install requests
    export FOOTBALL_DATA_KEY="your_key"     # https://www.football-data.org/client/register
    export GROQ_API_KEY="your_key"          # https://console.groq.com/keys
    python3 wc2026_agent.py                  # one pass over finished matches
    python3 wc2026_agent.py --watch          # loop forever, poll every 15 min
    python3 wc2026_agent.py --demo           # no keys needed, uses a sample match

AUTOMATE IT (so you never touch it):
    Linux/Mac cron  (every 30 min):
        */30 * * * * cd /path/to/wc2026 && /usr/bin/python3 wc2026_agent.py >> run.log 2>&1
    Windows Task Scheduler:
        Action = python.exe  Args = wc2026_agent.py  Trigger = repeat every 30 min
"""

import os
import re
import sys
import json
import time
import datetime as dt

try:
    import requests
except ImportError:
    sys.exit("Missing dependency. Run:  pip install requests")

# ----------------------------------------------------------------------------
# CONFIG  (override any of these with environment variables)
# ----------------------------------------------------------------------------
FOOTBALL_DATA_KEY = os.environ.get("FOOTBALL_DATA_KEY", "")
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY", "")
COMPETITION       = os.environ.get("COMPETITION", "WC")          # WC = World Cup
GROQ_MODEL        = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
POLL_SECONDS      = int(os.environ.get("POLL_SECONDS", "900"))    # 15 min
OUTPUT_DIR        = os.environ.get("OUTPUT_DIR", "output")
STATE_FILE        = os.path.join(OUTPUT_DIR, "processed_matches.json")

FOOTBALL_BASE = "https://api.football-data.org/v4"
GROQ_URL      = "https://api.groq.com/openai/v1/chat/completions"

VIDEO_TYPES = {
    "A": "Deep Match Analysis",
    "B": "Tactical Breakdown",
    "C": "Group Implications",
    "D": "Upset Alert",
    "E": "Player Spotlight",
    "F": "Prediction Update",
    "G": "Hidden Story",
    "H": "Daily World Cup Intelligence Report",
    "I": "Tournament Simulation",
    "J": "Power Ranking Update",
    "K": "What-If Scenario",
}


def log(msg):
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


# ----------------------------------------------------------------------------
# 1. DETECT  — pull finished matches
# ----------------------------------------------------------------------------
def fetch_finished_matches():
    if not FOOTBALL_DATA_KEY:
        log("No FOOTBALL_DATA_KEY set — skipping live fetch.")
        return []
    url = f"{FOOTBALL_BASE}/competitions/{COMPETITION}/matches?status=FINISHED"
    try:
        r = requests.get(url, headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=30)
        r.raise_for_status()
    except Exception as e:
        log(f"Data fetch failed: {e}")
        return []
    return [normalize_match(m) for m in r.json().get("matches", [])]


def normalize_match(m):
    """Reduce the API blob to a clean dict we control."""
    score = m.get("score", {}).get("fullTime", {})
    return {
        "id": str(m.get("id")),
        "utc": m.get("utcDate", ""),
        "stage": m.get("stage", ""),
        "group": m.get("group") or "",
        "home": m.get("homeTeam", {}).get("name", "Home"),
        "away": m.get("awayTeam", {}).get("name", "Away"),
        "home_goals": score.get("home"),
        "away_goals": score.get("away"),
        "winner": m.get("score", {}).get("winner", ""),  # HOME_TEAM/AWAY_TEAM/DRAW
    }


# ----------------------------------------------------------------------------
# 2. STATE  — never process the same match twice
# ----------------------------------------------------------------------------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return set()


def save_state(done):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(done), f, indent=2)


# ----------------------------------------------------------------------------
# 3. ANALYSE  — heuristic score to pick the strongest video angle
# ----------------------------------------------------------------------------
def score_video_types(m):
    """Cheap, fast scoring so we don't burn an LLM call just to choose an angle.
    The LLM still gets the final say but starts from this ranking."""
    h, a = m.get("home_goals") or 0, m.get("away_goals") or 0
    margin = abs(h - a)
    total = h + a
    scores = {k: 1.0 for k in VIDEO_TYPES}

    if margin >= 3:
        scores["D"] += 4   # blowout -> upset / giant in trouble energy
        scores["A"] += 2
    if total >= 4:
        scores["A"] += 2   # goal-fest = juicy match analysis
        scores["E"] += 2   # someone had a monster game
    if m["winner"] == "DRAW":
        scores["C"] += 3   # draws scramble the group table
        scores["K"] += 2
    if m["stage"] in ("GROUP_STAGE", "LEAGUE_STAGE"):
        scores["C"] += 3   # qualification implications always relevant
        scores["F"] += 2
    if m["stage"] in ("LAST_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL"):
        scores["B"] += 3   # knockouts reward tactical depth
        scores["G"] += 2
    scores["H"] += 1.5     # daily report is always a safe evergreen option
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return ranked


def build_data_context(m):
    res = f"{m['home']} {m['home_goals']}-{m['away_goals']} {m['away']}"
    stage = m["stage"].replace("_", " ").title()
    grp = f" (Group {m['group']})" if m["group"] else ""
    return f"FINAL: {res}\nStage: {stage}{grp}\nDate: {m['utc']}"


# ----------------------------------------------------------------------------
# 4 + 5. GENERATE  — call Groq for script, then for the packaging
# ----------------------------------------------------------------------------
def groq_chat(system, user, temperature=0.8, mock=None):
    if mock is not None:                       # demo mode without a key
        return mock
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set — cannot generate.")
    payload = {
        "model": GROQ_MODEL,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    r = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                 "Content-Type": "application/json"},
        json=payload, timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def parse_json(text):
    """LLMs love wrapping JSON in prose / fences. Dig it out safely."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


SCRIPT_SYSTEM = (
    "You are the head writer of a premium football analysis YouTube channel, "
    "comparable to Tifo or The Athletic. You write in a confident, human, "
    "storytelling voice — never robotic match-report language. You use ZERO "
    "broadcaster footage; everything is described so it can be shown with "
    "original charts, tactical boards, and data visuals. Be specific and bold, "
    "but never invent fake stats — only reason from the data you are given."
)

PACKAGE_SYSTEM = (
    "You are a YouTube growth strategist. You write irresistible, honest "
    "(non-clickbait-lie) packaging that maximizes CTR and retention. "
    "Return STRICT JSON only — no prose, no markdown fences."
)


def gen_script(m, ctx, video_type_code, mock=None):
    vt = VIDEO_TYPES[video_type_code]
    user = f"""Match data:
{ctx}

Chosen video format: TYPE {video_type_code} — {vt}

Write a 3-5 minute YouTube script (~600-750 words) with these labelled sections:
HOOK (first 10 sec must stop the scroll, tease the payoff, no fluff)
CONFLICT (the central tension / question of the match)
BREAKDOWN (what happened and WHY — reference tactics/momentum, describe the
           charts or tactical-board moments to show on screen in [brackets])
BIG INSIGHT (the thing most viewers missed)
TOURNAMENT IMPACT (what changes now — group/bracket/momentum)
PREDICTION (a bold but defensible call about what happens next)
CTA (ask for sub + tease the next video)

Keep it punchy. Mark on-screen visual cues in [square brackets]."""
    return groq_chat(SCRIPT_SYSTEM, user, temperature=0.85, mock=mock)


def gen_package(m, ctx, script, mock=None):
    user = f"""Match: {m['home']} {m['home_goals']}-{m['away_goals']} {m['away']}
Script:
\"\"\"{script[:2500]}\"\"\"

Return STRICT JSON with this exact shape:
{{
  "titles": [{{"text": "...", "score": 0-100, "lever": "curiosity|stakes|conflict|consequence|surprise"}}],  // EXACTLY 30, sorted best first
  "thumbnails": [{{"text": "max 4 words on image", "emotion": "...", "ctr_logic": "...", "layout": "..."}}],   // EXACTLY 10
  "shorts": [{{"hook": "first 3 sec line", "script": "30-60s vertical script"}}],                              // EXACTLY 3
  "social": {{"x_thread": ["tweet1","..."], "instagram": "...", "facebook": "...", "community": "...", "linkedin": "..."}}
}}
No text outside the JSON."""
    if isinstance(mock, dict):          # demo mode hands us a ready dict
        return mock
    raw = groq_chat(PACKAGE_SYSTEM, user, temperature=0.7, mock=mock)
    return parse_json(raw)


# ----------------------------------------------------------------------------
# 6. SAVE
# ----------------------------------------------------------------------------
def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def save_package(m, vt_code, ranking, script, pkg):
    folder = os.path.join(OUTPUT_DIR, f"{m['id']}_{slug(m['home'])}-vs-{slug(m['away'])}")
    os.makedirs(folder, exist_ok=True)

    with open(os.path.join(folder, "01_script.md"), "w") as f:
        f.write(f"# {m['home']} {m['home_goals']}-{m['away_goals']} {m['away']}\n")
        f.write(f"**Video type:** {vt_code} — {VIDEO_TYPES[vt_code]}\n\n")
        f.write(f"**Angle ranking:** {', '.join(c for c,_ in ranking[:4])}\n\n---\n\n")
        f.write(script)

    titles = pkg.get("titles", [])
    with open(os.path.join(folder, "02_titles.md"), "w") as f:
        f.write("# 30 Titles (best first)\n\n")
        for i, t in enumerate(titles, 1):
            f.write(f"{i:>2}. [{t.get('score','?')}] ({t.get('lever','?')}) {t.get('text','')}\n")

    with open(os.path.join(folder, "03_thumbnails.md"), "w") as f:
        f.write("# 10 Thumbnail Concepts\n\n")
        for i, t in enumerate(pkg.get("thumbnails", []), 1):
            f.write(f"## {i}. \"{t.get('text','')}\"\n")
            f.write(f"- Emotion: {t.get('emotion','')}\n")
            f.write(f"- CTR logic: {t.get('ctr_logic','')}\n")
            f.write(f"- Layout: {t.get('layout','')}\n\n")

    with open(os.path.join(folder, "04_shorts.md"), "w") as f:
        f.write("# 3 Shorts\n\n")
        for i, s in enumerate(pkg.get("shorts", []), 1):
            f.write(f"## Short {i}\n**Hook:** {s.get('hook','')}\n\n{s.get('script','')}\n\n")

    with open(os.path.join(folder, "05_social.md"), "w") as f:
        soc = pkg.get("social", {})
        f.write("# Social Posts\n\n## X / Twitter thread\n")
        for tw in soc.get("x_thread", []):
            f.write(f"- {tw}\n")
        for key in ("instagram", "facebook", "community", "linkedin"):
            f.write(f"\n## {key.title()}\n{soc.get(key,'')}\n")

    with open(os.path.join(folder, "package.json"), "w") as f:
        json.dump({"match": m, "video_type": vt_code, "package": pkg}, f, indent=2)

    log(f"Saved -> {folder}  (best title: {titles[0]['text'] if titles else 'n/a'})")
    return folder


# ----------------------------------------------------------------------------
# PIPELINE
# ----------------------------------------------------------------------------
def process_match(m, mock_script=None, mock_pkg=None):
    ctx = build_data_context(m)
    ranking = score_video_types(m)
    vt_code = ranking[0][0]
    log(f"{m['home']} {m['home_goals']}-{m['away_goals']} {m['away']} -> "
        f"TYPE {vt_code} ({VIDEO_TYPES[vt_code]})")
    script = gen_script(m, ctx, vt_code, mock=mock_script)
    pkg = gen_package(m, ctx, script, mock=mock_pkg)
    return save_package(m, vt_code, ranking, script, pkg)


def run_once():
    done = load_state()
    matches = fetch_finished_matches()
    fresh = [m for m in matches if m["id"] not in done]
    log(f"{len(matches)} finished, {len(fresh)} new to process.")
    for m in fresh:
        try:
            process_match(m)
            done.add(m["id"])
            save_state(done)
        except Exception as e:
            log(f"ERROR on {m['id']}: {e}")
    return len(fresh)


def run_demo():
    """No keys needed — proves the full pipeline writes correct files."""
    log("DEMO MODE — sample match, mock AI output.")
    m = {"id": "demo1", "utc": "2026-06-20T19:00:00Z", "stage": "GROUP_STAGE",
         "group": "F", "home": "Argentina", "away": "Nigeria",
         "home_goals": 1, "away_goals": 2, "winner": "AWAY_TEAM"}
    mock_script = ("HOOK\n[Zoom on scoreline graphic] The world champions just "
                   "lost — and almost nobody is talking about WHY.\n\nCONFLICT\n"
                   "Argentina had 68% possession and still walked off beaten...\n\n"
                   "BREAKDOWN\n[Tactical board: Nigeria's low block]...\n\n"
                   "BIG INSIGHT\nThe goals came from the channel Argentina left "
                   "open when their full-back pushed up...\n\nTOURNAMENT IMPACT\n"
                   "Group F is now wide open...\n\nPREDICTION\nNigeria reaches the "
                   "last 16.\n\nCTA\nSubscribe — tomorrow we break down the group.")
    mock_pkg = {
        "titles": [{"text": f"Why Argentina REALLY Lost (#{i})", "score": 90 - i,
                    "lever": "curiosity"} for i in range(30)],
        "thumbnails": [{"text": "GIANTS FALL", "emotion": "shock",
                        "ctr_logic": "upset + recognizable badge",
                        "layout": "split crest vs crest, red arrow"} for _ in range(10)],
        "shorts": [{"hook": "Argentina lost and nobody noticed THIS.",
                    "script": "30s breakdown of the open channel..."} for _ in range(3)],
        "social": {"x_thread": ["1/ Argentina lost. Here's why 🧵", "2/ The full-back..."],
                   "instagram": "The champions fell. Swipe for why ⚽️",
                   "facebook": "Big upset in Group F...",
                   "community": "Did you spot why Argentina lost? 👀",
                   "linkedin": "A lesson in risk management, from football."}
    }
    process_match(m, mock_script=mock_script, mock_pkg=mock_pkg)
    log("Demo complete. Check the output/ folder.")


def main():
    args = sys.argv[1:]
    if "--demo" in args:
        run_demo()
    elif "--watch" in args:
        log(f"WATCH mode — polling every {POLL_SECONDS//60} min. Ctrl-C to stop.")
        while True:
            run_once()
            time.sleep(POLL_SECONDS)
    else:
        run_once()


if __name__ == "__main__":
    main()
