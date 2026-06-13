# WC2026 Content Agent ⚽🤖

An autonomous, copyright-safe World Cup 2026 content factory. Every time it runs
it finds newly-finished matches, picks the strongest story angle, and writes you
a ready-to-record **script + 30 titles + 10 thumbnail concepts + 3 Shorts + social
posts**. It runs free in GitHub's cloud — your computer does not need to be on.

It does the boring 80%. You add your voice and final edit (that human layer is
what keeps the channel monetizable under YouTube's 2026 rules).

---

## Setup — about 10 minutes, all free, zero coding

### 1. Get two free keys
- **Football data:** https://www.football-data.org/client/register → copy your API token
- **AI brain (Groq):** https://console.groq.com/keys → create a key

### 2. Put this folder on GitHub
- Make a free account at https://github.com if you don't have one
- Click **New repository** → name it `wc2026-agent` → **Private** is fine
- Upload these files (drag-and-drop in the browser works):
  `wc2026_agent.py`, `requirements.txt`, `README.md`, and the `.github` folder

### 3. Add your keys as secrets (NEVER put them in the code)
In your repo: **Settings → Secrets and variables → Actions → New repository secret**
Add two:
- Name `FOOTBALL_DATA_KEY`  → value = your football-data token
- Name `GROQ_API_KEY`       → value = your Groq key

### 4. Turn it on
Go to the **Actions** tab → enable workflows if asked → open **WC2026 Content Agent**
→ click **Run workflow** to test it now. After that it runs itself every 2 hours.

Generated content lands in the **`output/`** folder of your repo, one folder per match.

---

## Run it on your own computer instead (optional)
```bash
pip install -r requirements.txt
export FOOTBALL_DATA_KEY="your_key"
export GROQ_API_KEY="your_key"
python3 wc2026_agent.py          # one pass
python3 wc2026_agent.py --watch  # keep running, poll every 15 min
python3 wc2026_agent.py --demo   # no keys needed, sample output
```

## Cost
| Thing | Cost |
|---|---|
| football-data.org free tier | $0 |
| Groq (Llama 3.3 70B) free tier | $0 |
| GitHub Actions (private repo, runs every 2h, ~1 min each) | $0 (within free 2000 min/mo) |
| **Total** | **$0 / month** |

Tip: a **public** repo gets unlimited Actions minutes — but your draft scripts
would be publicly visible. Private is the safer default.

## Free-tier limits to know
- Scores are **delayed** (fine for post-match analysis, not for live).
- **No xG / no player stats** on the free plan — you draw your own charts.
- 10 API calls/minute (the agent stays well under this).

## What's next (Phase 2, not built yet)
Free voiceover (Piper TTS) + auto-generated charts + n8n to glue voice→video→upload.
Ask when you're ready and it gets built.
