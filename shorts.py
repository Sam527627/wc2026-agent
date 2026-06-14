#!/usr/bin/env python3
"""
SHORTS ENGINE
=============
Takes the main video's best insight and auto-generates:
  - YouTube Short (60s, 9:16, 1080x1920)
  - Instagram Reel compatible
  - TikTok compatible

All three from one script. Runs automatically after the main video is built.
"""

import os, re, subprocess, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from PIL import Image, ImageDraw, ImageFont
import voice   # reuse the voice engine

W, H = 1080, 1920   # vertical 9:16
BG   = "#0a0a0a"
GOLD = "#f5c518"
TEAL = "#00b4d8"
RED  = "#e63946"

def log(msg): print(f"  [shorts] {msg}", flush=True)

def _font(size):
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        try: return ImageFont.truetype(path, size)
        except: pass
    return ImageFont.load_default()

def shorts_frame(home, away, hg, ag, hook_text, stat_text, out_path):
    """Generate a single vertical frame for the Short."""
    img  = Image.new("RGB", (W, H), color="#0a0a0a")
    draw = ImageDraw.Draw(img)

    # Top bar
    draw.rectangle([0, 0, W, 120], fill=TEAL)
    draw.text((W//2, 60), "WC2026 · DAILY ANALYSIS",
              font=_font(36), fill="#0a0a0a", anchor="mm")

    # Score card
    draw.rectangle([80, 160, W-80, 420], fill="#111111", outline=GOLD, width=5)
    draw.text((W//2, 250), f"{hg}  –  {ag}",
              font=_font(130), fill="white", anchor="mm")
    draw.text((200, 380), home[:10], font=_font(42), fill=TEAL, anchor="mm")
    draw.text((W-200, 380), away[:10], font=_font(42), fill=RED, anchor="mm")

    # Hook text
    y = 460
    for line in _wrap(hook_text, 24):
        draw.text((W//2, y), line, font=_font(52), fill="white", anchor="mm")
        y += 70

    # Divider
    draw.line([(80, y+20), (W-80, y+20)], fill=TEAL, width=3)
    y += 60

    # Stat text
    for line in _wrap(stat_text, 28):
        draw.text((W//2, y), line, font=_font(44), fill=GOLD, anchor="mm")
        y += 62

    # Subscribe prompt at bottom
    draw.rectangle([0, H-160, W, H], fill=TEAL)
    draw.text((W//2, H-80), "SUBSCRIBE FOR DAILY WC ANALYSIS ⚽",
              font=_font(34), fill="#0a0a0a", anchor="mm")

    img.save(out_path, "JPEG", quality=95)

def _wrap(text, width):
    words = text.split()
    lines, cur = [], []
    for w in words:
        if sum(len(x)+1 for x in cur) + len(w) > width:
            lines.append(" ".join(cur)); cur = [w]
        else:
            cur.append(w)
    if cur: lines.append(" ".join(cur))
    return lines[:6]   # max 6 lines on screen

def build_short(match, hook, script_text, out_dir, index=1):
    """Build one Short MP4."""
    home = match["home"]; away = match["away"]
    hg   = match.get("home_goals",0); ag = match.get("away_goals",0)

    shorts_dir = os.path.join(out_dir, "shorts")
    os.makedirs(shorts_dir, exist_ok=True)

    frame_path = os.path.join(shorts_dir, f"short{index}_frame.jpg")
    audio_path = os.path.join(shorts_dir, f"short{index}_voice.mp3")
    out_path   = os.path.join(shorts_dir, f"short{index}_final.mp4")

    # Frame
    stat_line = f"{home} {hg}-{ag} {away}  |  Group {match.get('group','')}"
    shorts_frame(home, away, hg, ag, hook, stat_line, frame_path)

    # Voice
    full_text = f"{hook}. {script_text}"
    voice.generate_voiceover(full_text, audio_path)

    # Get audio duration
    res = subprocess.run(
        ["ffprobe","-v","quiet","-show_entries","format=duration",
         "-of","default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True)
    try:    dur = min(float(res.stdout.strip()), 59.5)
    except: dur = 45.0

    # Assemble vertical video
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", frame_path,
        "-i", audio_path,
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-vf", f"scale={W}:{H},fps=30",
        "-t", str(dur + 0.3),
        out_path
    ], check=True, capture_output=True)

    log(f"Short {index} → {out_path}  ({dur:.0f}s)")
    return out_path

def generate_all_shorts(match, shorts_data, out_dir):
    """shorts_data = list of {hook, script} dicts from the package."""
    paths = []
    for i, s in enumerate(shorts_data[:3], 1):
        try:
            p = build_short(match, s.get("hook",""), s.get("script",""), out_dir, i)
            paths.append(p)
        except Exception as e:
            log(f"Short {i} error: {e}")
    return paths

if __name__ == "__main__":
    # Quick test
    m = {"id":"test","home":"Germany","away":"Curacao",
         "home_goals":4,"away_goals":0,"stage":"GROUP_STAGE","group":"E"}
    shorts = [
        {"hook":"Germany scored 4 and STILL haven't shown their best.",
         "script":"Here is what every team in this World Cup just learned about Germany. Their second midfielder never broke a sweat. That means there is a whole gear they have not used yet. The real Germany shows up in the knockouts."},
        {"hook":"The one stat from Germany vs Curacao that changes everything.",
         "script":"Germany had the ball 71 percent of the time. But here is the thing — Curacao barely got out of their own half in the first 20 minutes. Germany's press was suffocating before the first goal even went in."},
        {"hook":"Why France and Spain should be VERY worried right now.",
         "script":"Germany just scored four. Clean sheet. And their best player, Musiala, only played 60 minutes. This is a team that is warming up. The tournament does not start until the knockouts."},
    ]
    paths = generate_all_shorts(m, shorts, "test_shorts_out")
    print("Done:", paths)
