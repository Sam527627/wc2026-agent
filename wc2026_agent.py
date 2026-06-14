#!/usr/bin/env python3
"""
WC2026 FACELESS CONTENT MACHINE  v3.1  — HARDENED + COMPLETE
=============================================================
100% automated. Zero human input needed during the tournament.

Every 2 hours on GitHub Actions:
  1.  Detects newly-finished World Cup matches (football-data.org free)
  2.  Reads STRATEGY.md — self-improving from real YouTube analytics
  3.  Picks strongest angle from 11 video types (A-K)
  4.  Writes 650-word premium storytelling script (Groq LLM, free)
  5.  Generates 6 visual frames — title card, stats, tactics, momentum,
      sections, thumbnail (matplotlib + Pillow, 1920x1080)
  6.  Neural voiceover — edge-tts (Microsoft neural) → espeak-ng fallback
  7.  Assembles 1080p 16:9 MP4 with burnt-in captions (FFmpeg)
  8.  3 vertical 9:16 Shorts for YouTube/TikTok/Reels
  9.  30 scored titles, 10 thumbnail concepts, social posts for 5 platforms
  10. Uploads main video + thumbnail + 3 Shorts to YouTube
  11. Saves all content to repo — never reprocesses same match

GITHUB SECRETS (all free):
  FOOTBALL_DATA_KEY       football-data.org
  GROQ_API_KEY            console.groq.com
  YOUTUBE_CLIENT_ID       Google Cloud Console
  YOUTUBE_CLIENT_SECRET   Google Cloud Console
  YOUTUBE_REFRESH_TOKEN   run setup_youtube.py once
"""

import os, re, sys, json, time, datetime as dt
try:
    import requests
except ImportError:
    sys.exit("pip install requests")

# ── CONFIG ───────────────────────────────────────────────────────────────────
FOOTBALL_DATA_KEY     = os.environ.get("FOOTBALL_DATA_KEY","")
GROQ_API_KEY          = os.environ.get("GROQ_API_KEY","")
YOUTUBE_CLIENT_ID     = os.environ.get("YOUTUBE_CLIENT_ID","")
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET","")
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN","")
COMPETITION           = os.environ.get("COMPETITION","WC")
GROQ_MODEL            = os.environ.get("GROQ_MODEL","llama-3.3-70b-versatile")
OUTPUT_DIR            = os.environ.get("OUTPUT_DIR","output")
SKIP_VIDEO            = os.environ.get("SKIP_VIDEO","").lower()=="true"
SKIP_UPLOAD           = os.environ.get("SKIP_UPLOAD","").lower()=="true"
SKIP_SHORTS           = os.environ.get("SKIP_SHORTS","").lower()=="true"
STATE_FILE            = os.path.join(OUTPUT_DIR,"processed_matches.json")
STRATEGY_FILE         = os.path.join(OUTPUT_DIR,"STRATEGY.md")
FOOTBALL_BASE         = "https://api.football-data.org/v4"
GROQ_URL              = "https://api.groq.com/openai/v1/chat/completions"

VIDEO_TYPES = {
    "A":"Deep Match Analysis",    "B":"Tactical Breakdown",
    "C":"Group Implications",     "D":"Upset Alert",
    "E":"Player Spotlight",       "F":"Prediction Update",
    "G":"Hidden Story",           "H":"Daily WC Intelligence Report",
    "I":"Tournament Simulation",  "J":"Power Ranking Update",
    "K":"What-If Scenario",
}

def log(msg): print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)
def slug(s):  return re.sub(r"[^a-z0-9]+","-",s.lower()).strip("-")[:60]

# ── MATCH DATA ────────────────────────────────────────────────────────────────
def fetch_matches():
    if not FOOTBALL_DATA_KEY:
        log("No FOOTBALL_DATA_KEY set — skipping live fetch")
        return []
    try:
        r = requests.get(
            f"{FOOTBALL_BASE}/competitions/{COMPETITION}/matches?status=FINISHED",
            headers={"X-Auth-Token": FOOTBALL_DATA_KEY}, timeout=30)
        r.raise_for_status()
        return [_norm(m) for m in r.json().get("matches",[])]
    except Exception as e:
        log(f"Football API error: {e}"); return []

def _norm(m):
    sc = m.get("score",{}).get("fullTime",{})
    # BUG FIX: coerce None scores to 0 safely
    def safe_int(v): 
        try: return int(v) if v is not None else 0
        except: return 0
    return {
        "id":         str(m.get("id","")),
        "utc":        m.get("utcDate",""),
        "stage":      m.get("stage","GROUP_STAGE"),
        "group":      m.get("group") or "",
        "home":       m.get("homeTeam",{}).get("name","Home"),
        "away":       m.get("awayTeam",{}).get("name","Away"),
        "home_goals": safe_int(sc.get("home")),
        "away_goals": safe_int(sc.get("away")),
        "winner":     m.get("score",{}).get("winner",""),
    }

# ── STATE (dedupe — never process same match twice) ───────────────────────────
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f: return set(json.load(f))
        except Exception:
            log("State file corrupt — starting fresh")
    return set()

def save_state(done):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(STATE_FILE,"w") as f: json.dump(sorted(done), f, indent=2)

# ── STRATEGY (self-improvement feedback) ─────────────────────────────────────
def load_strategy():
    if os.path.exists(STRATEGY_FILE):
        try:
            with open(STRATEGY_FILE) as f: return f.read()
        except Exception: pass
    return ""

# ── ANGLE SELECTION ───────────────────────────────────────────────────────────
def score_types(m):
    h = int(m.get("home_goals") or 0)
    a = int(m.get("away_goals") or 0)
    mg, tot = abs(h-a), h+a
    s = {k:1.0 for k in VIDEO_TYPES}
    if mg >= 3:  s["D"]+=4; s["A"]+=2
    if tot >= 4: s["A"]+=2; s["E"]+=2
    if m.get("winner")=="DRAW": s["C"]+=3; s["K"]+=2
    if m.get("stage") in("GROUP_STAGE","LEAGUE_STAGE"): s["C"]+=3; s["F"]+=2
    if m.get("stage") in("LAST_16","QUARTER_FINALS","SEMI_FINALS","FINAL"):
        s["B"]+=3; s["G"]+=2
    s["H"] += 1.5
    return sorted(s.items(), key=lambda kv:kv[1], reverse=True)

# ── LLM ───────────────────────────────────────────────────────────────────────
def groq(system, user, temp=0.8):
    if not GROQ_API_KEY: raise RuntimeError("GROQ_API_KEY not set")
    r = requests.post(GROQ_URL,
        headers={"Authorization":f"Bearer {GROQ_API_KEY}",
                 "Content-Type":"application/json"},
        json={"model":GROQ_MODEL,"temperature":temp,
              "messages":[{"role":"system","content":system},
                          {"role":"user","content":user}]},
        timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def parse_json(text):
    """Extract JSON from LLM output that may contain prose/fences."""
    text = re.sub(r"```(?:json)?","",text).strip()
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e != -1: text = text[s:e+1]
    return json.loads(text)

SCRIPT_SYS = """You are the head writer of a premium football YouTube channel like Tifo Football.
Confident human storytelling voice — never robotic match summaries.
Zero broadcaster footage — describe [visual cues in brackets] for original charts and tactical boards.
Be specific and bold. Never invent statistics. Every sentence must earn its place."""

PACKAGE_SYS = """You are a YouTube growth strategist at the top of your field.
Write irresistible, honest (no lie-bait) packaging that maximises CTR and retention.
STRICT JSON only — zero prose before or after, zero markdown fences."""

def gen_script(m, vt_code, strategy=""):
    ctx  = f"FINAL: {m['home']} {m['home_goals']}-{m['away_goals']} {m['away']}\n"
    ctx += f"Stage: {m['stage'].replace('_',' ').title()}"
    ctx += f"  Group {m['group']}\n" if m.get("group") else "\n"
    strat = f"\nCHANNEL STRATEGY (apply these learnings):\n{strategy[:600]}\n" if strategy else ""
    user = f"""Match data:
{ctx}{strat}
Video type: TYPE {vt_code} — {VIDEO_TYPES[vt_code]}

Write a 3-5 min YouTube script (~650 words) with EXACTLY these section headers on their own line:
HOOK
CONFLICT
BREAKDOWN
BIG INSIGHT
TOURNAMENT IMPACT
PREDICTION
CTA

Rules:
- HOOK: first 8 words must contain a specific number or surprising fact. No fluff. Stop the scroll.
- CONFLICT: the one central tension that defines this match
- BREAKDOWN: describe tactics with [visual cue in square brackets] for every key moment
- BIG INSIGHT: something NOT in any match report — the hidden story
- TOURNAMENT IMPACT: specific consequence for the group table and bracket
- PREDICTION: a specific outcome with reasoning, not vague language
- CTA: name tomorrow's exact topic to create FOMO
- Overall tone: confident sports documentary narrator"""
    return groq(SCRIPT_SYS, user, temp=0.85)

def gen_package(m, script):
    h, a = m['home_goals'], m['away_goals']
    user = f"""Match: {m['home']} {h}-{a} {m['away']}
Script (first 2500 chars):
\"\"\"{script[:2500]}\"\"\"

Return STRICT JSON with this EXACT structure (no extra keys, no missing keys):
{{
  "best_title": "the single best title (curiosity + stakes, under 70 chars, no CAPS LOCK spam)",
  "description": "YouTube description ~200 words: what happened, why it matters, 5 timestamps, 10 hashtags",
  "tags": ["World Cup 2026","FIFA WC 2026","football analysis","WC2026","{m['home']}","{m['away']}","soccer","football"],
  "titles": [
    {{"text": "title string", "score": 0-100, "lever": "curiosity|stakes|conflict|consequence|surprise"}}
  ],
  "thumbnails": [
    {{"text": "max 4 words for image text", "emotion": "one word", "ctr_logic": "why this works", "layout": "describe the visual layout"}}
  ],
  "shorts": [
    {{"hook": "first 3 sec hook — must shock or surprise", "script": "30-60s punchy vertical script"}}
  ],
  "social": {{
    "x_thread": ["1/ hook tweet with emoji 🧵", "2/ key insight", "3/ bold prediction", "4/ CTA with channel mention"],
    "instagram": "caption with emojis, 100-150 words, ends with question to drive comments",
    "facebook": "engaging 80-word post, shares the big insight",
    "community": "YouTube community post — ask a question to drive comments (under 100 words)",
    "linkedin": "professional tactical angle, 80 words, no emojis"
  }}
}}

REQUIREMENTS:
- titles: EXACTLY 30 items, sorted best-first
- thumbnails: EXACTLY 10 items
- shorts: EXACTLY 3 items
- No text whatsoever outside the JSON object"""
    raw = groq(PACKAGE_SYS, user, temp=0.7)
    try:
        return parse_json(raw)
    except json.JSONDecodeError:
        # Retry once with stricter prompt
        log("JSON parse failed — retrying package generation")
        raw2 = groq(PACKAGE_SYS, user + "\n\nIMPORTANT: Return ONLY the JSON object, nothing else.", temp=0.5)
        return parse_json(raw2)

# ── YOUTUBE ───────────────────────────────────────────────────────────────────
def get_yt_token():
    if not all([YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN]):
        return None
    try:
        r = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id":     YOUTUBE_CLIENT_ID,
            "client_secret": YOUTUBE_CLIENT_SECRET,
            "refresh_token": YOUTUBE_REFRESH_TOKEN,
            "grant_type":    "refresh_token",
        }, timeout=15)
        return r.json().get("access_token") if r.status_code==200 else None
    except Exception as e:
        log(f"YT token error: {e}"); return None

def yt_upload(token, video_path, title, description, tags, is_short=False):
    if not token or not os.path.exists(video_path):
        return None
    meta = {
        "snippet": {"title":title[:100],"description":description,
                    "tags":tags,"categoryId":"17","defaultLanguage":"en"},
        "status":  {"privacyStatus":"public","selfDeclaredMadeForKids":False},
    }
    try:
        init = requests.post(
            "https://www.googleapis.com/upload/youtube/v3/videos"
            "?uploadType=resumable&part=snippet,status",
            headers={"Authorization":f"Bearer {token}",
                     "Content-Type":"application/json",
                     "X-Upload-Content-Type":"video/mp4"},
            json=meta, timeout=30)
        if init.status_code != 200:
            log(f"YT init failed: {init.status_code}"); return None
        upload_url = init.headers["Location"]
        with open(video_path,"rb") as f: data = f.read()
        res = requests.put(upload_url,
            headers={"Authorization":f"Bearer {token}",
                     "Content-Type":"video/mp4",
                     "Content-Length":str(len(data))},
            data=data, timeout=300)
        if res.status_code not in(200,201):
            log(f"YT upload failed: {res.status_code}"); return None
        vid_id = res.json().get("id")
        kind = "Short" if is_short else "Video"
        log(f"✅ {kind} live → https://youtube.com/watch?v={vid_id}")
        return vid_id
    except Exception as e:
        log(f"Upload exception: {e}"); return None

def yt_set_thumbnail(token, video_id, thumb_path):
    if not token or not os.path.exists(thumb_path): return
    try:
        with open(thumb_path,"rb") as f: td = f.read()
        requests.post(
            f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
            f"?videoId={video_id}&uploadType=media",
            headers={"Authorization":f"Bearer {token}",
                     "Content-Type":"image/jpeg","Content-Length":str(len(td))},
            data=td, timeout=60)
        log(f"Thumbnail set on {video_id}")
    except Exception as e:
        log(f"Thumbnail error: {e}")

# ── SAVE ALL CONTENT ──────────────────────────────────────────────────────────
def save_all(m, folder, vt_code, ranking, script, pkg,
             video_id=None, short_ids=None):
    short_ids = short_ids or []

    with open(os.path.join(folder,"01_script.md"),"w") as f:
        f.write(f"# {m['home']} {m['home_goals']}-{m['away_goals']} {m['away']}\n")
        f.write(f"**Type:** {vt_code} — {VIDEO_TYPES[vt_code]}\n\n---\n\n{script}")

    with open(os.path.join(folder,"02_titles.md"),"w") as f:
        f.write("# 30 Titles (best first)\n\n")
        for i,t in enumerate(pkg.get("titles",[]),1):
            f.write(f"{i:>2}. [{t.get('score','?')}] "
                    f"({t.get('lever','?')}) {t.get('text','')}\n")

    with open(os.path.join(folder,"03_thumbnails.md"),"w") as f:
        f.write("# 10 Thumbnail Concepts\n\n")
        for i,t in enumerate(pkg.get("thumbnails",[]),1):
            f.write(f"## {i}. \"{t.get('text','')}\"\n"
                    f"- Emotion  : {t.get('emotion','')}\n"
                    f"- CTR logic: {t.get('ctr_logic','')}\n"
                    f"- Layout   : {t.get('layout','')}\n\n")

    with open(os.path.join(folder,"04_shorts.md"),"w") as f:
        f.write("# 3 Shorts Scripts\n\n")
        for i,s in enumerate(pkg.get("shorts",[]),1):
            f.write(f"## Short {i}\n"
                    f"**Hook (0-3s):** {s.get('hook','')}\n\n"
                    f"{s.get('script','')}\n\n---\n\n")

    soc = pkg.get("social",{})
    with open(os.path.join(folder,"05_social.md"),"w") as f:
        f.write("# Social Posts\n\n## X / Twitter Thread\n")
        for tw in soc.get("x_thread",[]): f.write(f"- {tw}\n")
        for k in("instagram","facebook","community","linkedin"):
            f.write(f"\n## {k.title()}\n{soc.get(k,'')}\n")

    with open(os.path.join(folder,"package.json"),"w") as f:
        json.dump({
            "match":       m,
            "type":        vt_code,
            "best_title":  pkg.get("best_title",""),
            "description": pkg.get("description",""),
            "tags":        pkg.get("tags",[]),
            "youtube_id":  video_id,
            "youtube_url": (f"https://youtube.com/watch?v={video_id}"
                            if video_id else None),
            "shorts_ids":  short_ids,
            "shorts_urls": [f"https://youtube.com/shorts/{s}"
                            for s in short_ids],
            "generated_at": dt.datetime.utcnow().isoformat(),
        }, f, indent=2)

    log(f"Content saved → {folder}")
    if video_id:
        log(f"▶ Main   https://youtube.com/watch?v={video_id}")
    for sid in short_ids:
        log(f"▶ Short  https://youtube.com/shorts/{sid}")

# ── MAIN PIPELINE ─────────────────────────────────────────────────────────────
def process_match(m):
    folder = os.path.join(OUTPUT_DIR,
        f"{m['id']}_{slug(m['home'])}-vs-{slug(m['away'])}")
    os.makedirs(folder, exist_ok=True)

    strategy = load_strategy()
    ranking  = score_types(m)
    vt_code  = ranking[0][0]
    log(f"▶ {m['home']} {m['home_goals']}-{m['away_goals']} {m['away']} "
        f"→ TYPE {vt_code} ({VIDEO_TYPES[vt_code]})")

    # Script
    log("Writing script via Groq...")
    script = gen_script(m, vt_code, strategy)

    # Package
    log("Generating titles, thumbnails, social posts...")
    pkg = gen_package(m, script)

    # Main video
    video_path = None
    thumb_path = os.path.join(folder, "thumbnail.jpg")
    if not SKIP_VIDEO:
        try:
            log("Building 1080p video...")
            import video as ve
            video_path = ve.generate_video(m, script, folder)
        except Exception as e:
            log(f"Video build error (non-fatal): {e}")

    # Shorts
    short_paths = []
    if not SKIP_SHORTS:
        try:
            log("Building 3 Shorts...")
            import shorts as sh
            short_paths = sh.generate_all_shorts(
                m, pkg.get("shorts",[]), folder)
        except Exception as e:
            log(f"Shorts error (non-fatal): {e}")

    # Upload
    video_id  = None
    short_ids = []
    if not SKIP_UPLOAD:
        token = get_yt_token()
        if token:
            # Upload main video
            if video_path:
                title = pkg.get("best_title",
                    f"{m['home']} vs {m['away']} | WC2026 Analysis")
                desc  = pkg.get("description", script[:800])
                tags  = pkg.get("tags",
                    ["World Cup 2026","football","FIFA","soccer","WC2026"])
                video_id = yt_upload(token, video_path, title, desc, tags)
                if video_id:
                    yt_set_thumbnail(token, video_id, thumb_path)

            # Upload Shorts
            for i, sp in enumerate(short_paths, 1):
                st = pkg.get("shorts",[{}]*i)[i-1]
                short_title = f"{st.get('hook','WC2026 Short')[:80]} #Shorts"
                sid = yt_upload(
                    token, sp, short_title,
                    f"WC2026 Short #{i}\n\n#Shorts #WC2026 #Football #FIFA",
                    ["Shorts","WC2026","football","FIFA","soccer","football shorts"],
                    is_short=True)
                if sid: short_ids.append(sid)
        else:
            log("No YouTube credentials — skipping upload (add secrets to GitHub)")

    save_all(m, folder, vt_code, ranking, script, pkg, video_id, short_ids)
    return folder

def run_once():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    done    = load_state()
    matches = fetch_matches()
    fresh   = [m for m in matches if m["id"] not in done]
    log(f"{len(matches)} finished matches found, {len(fresh)} new to process")
    for m in fresh:
        try:
            process_match(m)
            done.add(m["id"])
            save_state(done)
        except Exception as e:
            log(f"ERROR processing {m['id']}: {e}")
            # Still mark as done to avoid infinite retry loops on bad data
            done.add(m["id"])
            save_state(done)

def run_demo():
    """Demo mode — no football API or YouTube needed. Groq still needed."""
    log("DEMO MODE — Germany 4-0 Curacao (Group E)")
    os.environ.setdefault("SKIP_UPLOAD","true")
    m = {"id":"demo_v31","utc":"2026-06-14T18:00:00Z",
         "stage":"GROUP_STAGE","group":"E",
         "home":"Germany","away":"Curacao",
         "home_goals":4,"away_goals":0,"winner":"HOME_TEAM"}
    process_match(m)
    log("Demo complete. Check output/demo_v31_germany-vs-curacao/")

def main():
    args = sys.argv[1:]
    if   "--demo"  in args: run_demo()
    elif "--watch" in args:
        log("Watch mode — polling every 15 min. Ctrl-C to stop.")
        while True: run_once(); time.sleep(900)
    else:
        run_once()

if __name__ == "__main__":
    main()
