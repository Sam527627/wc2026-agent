#!/usr/bin/env python3
"""
ANALYTICS + SELF-IMPROVEMENT ENGINE
=====================================
Runs after every video upload. Reads real YouTube performance data,
identifies what's working, updates the agent's prompt strategy automatically.

What it does:
  1. Fetches CTR, watch time, retention, views for every video
  2. Scores each video's hook, title style, video type
  3. Identifies the top-performing patterns
  4. Writes an updated STRATEGY.md the main agent reads before generating
  5. Flags underperforming videos so the agent avoids similar angles

GitHub Actions runs this separately every 6 hours.
"""

import os, json, datetime as dt, requests, statistics

YOUTUBE_CLIENT_ID     = os.environ.get("YOUTUBE_CLIENT_ID","")
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET","")
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN","")
OUTPUT_DIR            = os.environ.get("OUTPUT_DIR","output")
STRATEGY_FILE         = os.path.join(OUTPUT_DIR,"STRATEGY.md")
ANALYTICS_FILE        = os.path.join(OUTPUT_DIR,"analytics.json")

def log(msg): print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)

def get_token():
    if not all([YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN]):
        return None
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id":     YOUTUBE_CLIENT_ID,
        "client_secret": YOUTUBE_CLIENT_SECRET,
        "refresh_token": YOUTUBE_REFRESH_TOKEN,
        "grant_type":    "refresh_token",
    })
    return r.json().get("access_token") if r.status_code == 200 else None

def fetch_channel_videos(token):
    """Get last 50 uploaded videos."""
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={"part":"snippet","forMine":"true","type":"video",
                "maxResults":"50","order":"date"},
        headers={"Authorization": f"Bearer {token}"}
    )
    if r.status_code != 200: return []
    return [item["id"]["videoId"] for item in r.json().get("items",[])]

def fetch_video_stats(token, video_ids):
    """Fetch views, likes, comments for a batch of videos."""
    if not video_ids: return {}
    ids = ",".join(video_ids[:50])
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"part":"statistics,snippet","id":ids},
        headers={"Authorization": f"Bearer {token}"}
    )
    if r.status_code != 200: return {}
    results = {}
    for item in r.json().get("items",[]):
        vid_id = item["id"]
        stats  = item.get("statistics",{})
        snip   = item.get("snippet",{})
        results[vid_id] = {
            "title":        snip.get("title",""),
            "published":    snip.get("publishedAt",""),
            "views":        int(stats.get("viewCount",0)),
            "likes":        int(stats.get("likeCount",0)),
            "comments":     int(stats.get("commentCount",0)),
        }
    return results

def fetch_analytics(token, video_ids):
    """Fetch CTR and watch time from YouTube Analytics API."""
    analytics = {}
    for vid_id in video_ids[:20]:   # analytics API limit
        r = requests.get(
            "https://youtubeanalytics.googleapis.com/v2/reports",
            params={
                "ids":        "channel==MINE",
                "startDate":  "2026-06-01",
                "endDate":    dt.date.today().isoformat(),
                "metrics":    "views,estimatedMinutesWatched,averageViewDuration,"
                              "averageViewPercentage,annotationClickThroughRate",
                "dimensions": "video",
                "filters":    f"video=={vid_id}",
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        if r.status_code == 200:
            rows = r.json().get("rows",[])
            if rows:
                row = rows[0]
                analytics[vid_id] = {
                    "views":            row[1] if len(row)>1 else 0,
                    "watch_minutes":    row[2] if len(row)>2 else 0,
                    "avg_view_sec":     row[3] if len(row)>3 else 0,
                    "retention_pct":    row[4] if len(row)>4 else 0,
                }
    return analytics

def load_package_data():
    """Read all package.json files to correlate video_id with our metadata."""
    packages = {}
    if not os.path.exists(OUTPUT_DIR): return packages
    for match_folder in os.listdir(OUTPUT_DIR):
        pkg_path = os.path.join(OUTPUT_DIR, match_folder, "package.json")
        if os.path.exists(pkg_path):
            with open(pkg_path) as f:
                try:
                    pkg = json.load(f)
                    vid_id = pkg.get("youtube_id") or pkg.get("youtube_url","").split("v=")[-1]
                    if vid_id:
                        packages[vid_id] = pkg
                except Exception:
                    pass
    return packages

def analyse_performance(stats, analytics, packages):
    """Identify winning patterns from real performance data."""
    combined = []
    for vid_id, st in stats.items():
        row = {"video_id": vid_id, **st}
        row.update(analytics.get(vid_id, {}))
        row["package"] = packages.get(vid_id, {})
        combined.append(row)

    if not combined:
        return {"status": "no_data", "insights": []}

    # Sort by views
    combined.sort(key=lambda x: x.get("views",0), reverse=True)

    views_list = [c.get("views",0) for c in combined]
    avg_views  = statistics.mean(views_list) if views_list else 0

    top    = combined[:max(1, len(combined)//4)]    # top 25%
    bottom = combined[-(max(1,len(combined)//4)):]  # bottom 25%

    def extract_patterns(rows):
        patterns = {"video_types":[], "title_levers":[], "avg_views":0}
        for r in rows:
            pkg = r.get("package",{})
            vt  = pkg.get("type","")
            if vt: patterns["video_types"].append(vt)
            # Detect title lever from best_title
            title = pkg.get("best_title","").lower()
            for kw, lever in [("why","curiosity"),("secret","curiosity"),
                               ("nobody","surprise"),("if","consequence"),
                               ("danger","stakes"),("trouble","stakes"),
                               ("vs","conflict"),("beat","conflict")]:
                if kw in title:
                    patterns["title_levers"].append(lever)
                    break
        views = [r.get("views",0) for r in rows]
        patterns["avg_views"] = int(statistics.mean(views)) if views else 0
        return patterns

    top_patterns    = extract_patterns(top)
    bottom_patterns = extract_patterns(bottom)

    insights = []
    if top_patterns["video_types"]:
        best_type = max(set(top_patterns["video_types"]),
                        key=top_patterns["video_types"].count)
        insights.append(f"Best performing video type: {best_type}")
    if top_patterns["title_levers"]:
        best_lever = max(set(top_patterns["title_levers"]),
                         key=top_patterns["title_levers"].count)
        insights.append(f"Highest CTR title lever: {best_lever}")
    if avg_views > 0:
        insights.append(f"Channel average views per video: {int(avg_views):,}")
    if top_patterns["avg_views"] > 0:
        insights.append(f"Top quartile average: {top_patterns['avg_views']:,} views")

    return {
        "status":           "ok",
        "total_videos":     len(combined),
        "avg_views":        int(avg_views),
        "top_patterns":     top_patterns,
        "bottom_patterns":  bottom_patterns,
        "insights":         insights,
        "top_videos":       [{"id":r["video_id"],"title":r["title"],
                              "views":r["views"]} for r in top[:3]],
    }

def write_strategy(analysis):
    """Write STRATEGY.md — the main agent reads this before every generation."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    top = analysis.get("top_patterns",{})
    bottom = analysis.get("bottom_patterns",{})
    insights = analysis.get("insights",[])

    lines = [
        "# WC2026 AGENT STRATEGY  (auto-updated by analytics engine)",
        f"Last updated: {dt.datetime.utcnow().isoformat()} UTC",
        f"Total videos analysed: {analysis.get('total_videos',0)}",
        f"Channel avg views: {analysis.get('avg_views',0):,}",
        "",
        "## WINNING PATTERNS (prioritise these)",
    ]
    for ins in insights:
        lines.append(f"- {ins}")

    if top.get("video_types"):
        best = max(set(top["video_types"]), key=top["video_types"].count)
        lines += ["", f"## BEST VIDEO TYPE: {best}",
                  "Bias angle selection toward this type when scores are close."]

    if top.get("title_levers"):
        best = max(set(top["title_levers"]), key=top["title_levers"].count)
        lines += ["", f"## BEST TITLE LEVER: {best}",
                  "Use this emotional hook in the best_title and top 5 titles."]

    if bottom.get("video_types"):
        worst = max(set(bottom["video_types"]), key=bottom["video_types"].count)
        lines += ["", f"## AVOID: {worst} (lowest performer)",
                  "Only use this type if score is 3+ higher than alternatives."]

    tv = analysis.get("top_videos",[])
    if tv:
        lines += ["","## TOP 3 VIDEOS (study these hooks and formats)"]
        for v in tv:
            lines.append(f"- [{v['views']:,} views] {v['title']}")
            lines.append(f"  https://youtube.com/watch?v={v['id']}")

    lines += [
        "","## SCRIPT INSTRUCTIONS (always apply)",
        "- Hook must reference a specific number or surprising fact in first 8 words",
        "- Never start with 'In this video' or 'Today we look at'",
        "- BIG INSIGHT section must contain something viewers cannot find in match reports",
        "- End PREDICTION with a specific scoreline or outcome, not vague language",
        "- CTA must tease tomorrow's specific match or angle by name",
    ]

    with open(STRATEGY_FILE,"w") as f:
        f.write("\n".join(lines))
    log(f"Strategy updated → {STRATEGY_FILE}")

def run():
    token = get_token()
    if not token:
        log("No YouTube credentials — writing default strategy only")
        write_strategy({"status":"no_credentials","total_videos":0,
                        "avg_views":0,"top_patterns":{},"bottom_patterns":{},
                        "insights":["No data yet — defaults in use"],"top_videos":[]})
        return

    log("Fetching channel videos...")
    video_ids = fetch_channel_videos(token)
    log(f"Found {len(video_ids)} videos")

    log("Fetching stats...")
    stats = fetch_video_stats(token, video_ids)

    log("Fetching analytics...")
    analytics = fetch_analytics(token, video_ids)

    packages = load_package_data()

    log("Analysing performance...")
    analysis = analyse_performance(stats, analytics, packages)

    # Save raw analytics
    with open(ANALYTICS_FILE,"w") as f:
        json.dump({"updated": dt.datetime.utcnow().isoformat(),
                   "analysis": analysis, "raw_stats": stats}, f, indent=2)

    write_strategy(analysis)

    log("Analytics complete:")
    for ins in analysis.get("insights",[]):
        log(f"  → {ins}")

if __name__ == "__main__":
    run()
