# WC2026 Faceless Content Machine ⚽🤖

Fully autonomous. You do nothing after a 15-minute setup.

Every 2 hours: detects finished matches → writes script → generates visuals
→ neural voiceover → assembles 1080p video with captions → creates 3 Shorts
→ uploads everything to YouTube → reads analytics → improves itself.

---

## What gets produced per match

| File | What it is |
|---|---|
| 01_script.md | 650-word storytelling script with visual cues |
| 02_titles.md | 30 scored YouTube titles |
| 03_thumbnails.md | 10 thumbnail concepts with CTR logic |
| 04_shorts.md | 3 vertical short scripts |
| 05_social.md | X thread, Instagram, Facebook, Community, LinkedIn |
| thumbnail.jpg | 1280x720 thumbnail |
| final_video.mp4 | 1080p 16:9 video with captions — auto-uploaded |
| shorts/short1-3.mp4 | 3 vertical Shorts — auto-uploaded |

---

## Setup (15 minutes, all free)

### 1. Football data key
https://www.football-data.org/client/register
Sign up, copy your API token.

### 2. Groq AI key
https://console.groq.com/keys
Sign up, create a key, copy it.

### 3. YouTube credentials
a. Go to https://console.cloud.google.com
b. New Project → name it wc2026
c. APIs & Services → Library → enable "YouTube Data API v3"
d. APIs & Services → Library → enable "YouTube Analytics API"
e. Credentials → Create OAuth 2.0 Client ID → Desktop app → Download JSON
f. Rename download to client_secret.json, put it in this folder
g. Run: pip install google-auth-oauthlib && python3 setup_youtube.py
h. Browser opens → sign in → allow → copy the 3 printed values

### 4. Add GitHub Secrets
Repo → Settings → Secrets and variables → Actions → New repository secret

  FOOTBALL_DATA_KEY      your football-data.org token
  GROQ_API_KEY           your Groq key
  YOUTUBE_CLIENT_ID      from setup_youtube.py
  YOUTUBE_CLIENT_SECRET  from setup_youtube.py
  YOUTUBE_REFRESH_TOKEN  from setup_youtube.py

### 5. Upload files and run
Upload all files from this zip to your GitHub repo (drag and drop in Code tab).
Then: Actions → WC2026 Content Agent → Run workflow.

After that — never touch it again. Runs every 2 hours until July 19.

---

## Cost: $0/month

football-data.org free tier | Groq free tier | Edge TTS free
FFmpeg open source | GitHub Actions free tier | YouTube free

---

## Troubleshooting

"0 finished, 0 new" = scores delayed on free tier, wait 1 hour after match ends.
Upload fails = refresh token expired, re-run setup_youtube.py.
Video fails locally = sudo apt install espeak-ng ffmpeg
