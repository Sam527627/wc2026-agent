"""
BEAST-LEVEL CINEMATIC ENGINE
==============================
MrBeast philosophy applied to football:
- Every scene has a REASON to keep watching
- Every stat reveal feels like a surprise
- Every moment is dramatised
- Pacing is relentless — cut every 3-4 seconds
- Colour, motion, sound design drives emotion

What this builds (all animated, all copyright-free):
1. CINEMATIC COLD OPEN     — dramatic title with shockwave effect
2. KEY MOMENT RECREATIONS  — animated dot-player recreations of goals/chances
3. DRAMATIC STAT REVEALS   — numbers slam in with impact
4. TACTICAL CHESS BOARD    — formations shifting like a chess match
5. MOMENTUM SWING DRAMA    — match momentum as a dramatic battle chart
6. CONSEQUENCE BOARD       — what this result means for every team
7. PREDICTION COUNTDOWN    — next match stakes visualised
8. MRBEAST-STYLE THUMBNAIL — face-reveal energy without the face
"""

import os, math, json, random
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Circle, Rectangle, FancyArrowPatch, FancyBboxPatch
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops
import subprocess

# ── BEAST COLOR PALETTE ───────────────────────────────────────────────────────
BG_DARK   = "#050810"   # almost black
BG_MID    = "#0a1628"
ELECTRIC  = "#00d4ff"   # electric blue
FIRE      = "#ff4d00"   # fire orange
GOLD      = "#ffd700"   # pure gold
WHITE     = "#ffffff"
LIME      = "#39ff14"   # neon green
MAGENTA   = "#ff00ff"
RED       = "#ff1744"
PITCH_DK  = "#0d2b0d"
PITCH_LN  = "#1a5c1a"

W, H = 1920, 1080
FPS  = 30   # Beast uses 30fps for energy

def log(msg): print(f"  [beast] {msg}", flush=True)

def _font(size, bold=True):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in paths:
        try: return ImageFont.truetype(p, size)
        except: pass
    return ImageFont.load_default()

def _save(fig, path):
    fig.savefig(path, dpi=100, bbox_inches="tight",
                facecolor=BG_DARK, edgecolor="none")
    plt.close(fig)

def frames_to_video(frame_dir, out_path, fps=FPS):
    pattern = os.path.join(frame_dir, "frame_%04d.png")
    subprocess.run([
        "ffmpeg", "-y", "-framerate", str(fps),
        "-i", pattern,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-vf", "scale=1920:1080",
        "-crf", "18", "-preset", "fast", out_path
    ], check=True, capture_output=True)
    return out_path

def ease_out(t):
    """Ease-out curve for snappy animations."""
    return 1 - (1-t)**3

def ease_in_out(t):
    return t*t*(3-2*t)

# ─────────────────────────────────────────────────────────────────────────────
# 1. BEAST COLD OPEN — shockwave + dramatic score reveal
# ─────────────────────────────────────────────────────────────────────────────
def make_cold_open(home, away, hg, ag, hook_text, out_dir, n_frames=90):
    """3 seconds. Shockwave explodes. Score slams in. Hook text appears."""
    os.makedirs(out_dir, exist_ok=True)
    log(f"Cold open ({n_frames} frames)...")

    for i in range(n_frames):
        t = i / n_frames
        et = ease_out(t)

        img = Image.new("RGB", (W, H), BG_DARK)
        draw = ImageDraw.Draw(img)

        # Shockwave rings expanding from centre
        if t < 0.4:
            shock_t = t / 0.4
            for ring in range(5):
                r = int((shock_t + ring*0.15) * 800)
                alpha = max(0, int(255 * (1 - shock_t - ring*0.15)))
                if r > 0 and alpha > 0:
                    # Draw ring
                    x0, y0 = W//2 - r, H//2 - r
                    x1, y1 = W//2 + r, H//2 + r
                    if x0 < W and y0 < H and x1 > 0 and y1 > 0:
                        try:
                            draw.ellipse([x0, y0, x1, y1],
                                        outline=(0, 180, 255, alpha), width=3)
                        except: pass

        # Background gradient lines (speed lines)
        if t > 0.1:
            for angle in range(0, 360, 8):
                length = int(600 * et)
                rad = math.radians(angle)
                x1 = W//2 + int(math.cos(rad) * 50)
                y1 = H//2 + int(math.sin(rad) * 50)
                x2 = W//2 + int(math.cos(rad) * (50 + length))
                y2 = H//2 + int(math.sin(rad) * (50 + length))
                alpha_line = max(0, int(40 * (1 - t)))
                draw.line([(x1,y1),(x2,y2)],
                          fill=(0, 100, 200), width=1)

        # Score slams in from top
        if t > 0.25:
            score_t = ease_out((t - 0.25) / 0.35)
            score_y = int(H//2 - 80 - (1-score_t) * 300)

            score_str = f"{hg}  —  {ag}"

            # Shadow/glow
            for offset in range(8, 0, -1):
                draw.text((W//2 + offset, score_y + offset),
                          score_str, font=_font(150),
                          fill=(255, 100, 0), anchor="mm")
            draw.text((W//2, score_y), score_str,
                      font=_font(150), fill=GOLD, anchor="mm")

        # Team names
        if t > 0.3:
            name_t = ease_out((t - 0.3) / 0.3)
            # Home flies from left
            home_x = int(W*0.22 - (1-name_t)*500)
            draw.text((home_x, H//2 - 80), home.upper(),
                      font=_font(64), fill=ELECTRIC, anchor="mm")
            # Away flies from right
            away_x = int(W*0.78 + (1-name_t)*500)
            draw.text((away_x, H//2 - 80), away.upper(),
                      font=_font(64), fill=FIRE, anchor="mm")

        # Hook text SLAMS in at end
        if t > 0.6:
            hook_t = ease_out((t - 0.6) / 0.4)
            hook_alpha = int(255 * hook_t)
            # Split hook into lines
            words = hook_text.upper().split()
            lines = []
            cur = []
            for w in words:
                cur.append(w)
                if len(" ".join(cur)) > 30:
                    lines.append(" ".join(cur[:-1]))
                    cur = [w]
            if cur: lines.append(" ".join(cur))

            for li, line in enumerate(lines[:3]):
                ly = H//2 + 60 + li * 70
                # Background bar
                draw.rectangle([100, ly-35, W-100, ly+35],
                               fill=(255,50,0, min(180, hook_alpha)))
                draw.text((W//2, ly), line,
                          font=_font(52), fill=WHITE, anchor="mm")

        # Brand
        draw.text((W-20, H-20), "WC2026",
                  font=_font(24), fill=(100,100,100), anchor="rs")

        img.save(os.path.join(out_dir, f"frame_{i:04d}.png"))

    return out_dir

# ─────────────────────────────────────────────────────────────────────────────
# 2. ANIMATED GOAL RECREATION — dots move to recreate key moment
# ─────────────────────────────────────────────────────────────────────────────
def make_goal_recreation(home, away, goal_minute, scorer,
                         description, out_dir, n_frames=120):
    """Players as dots animate to recreate the key moment of the match."""
    os.makedirs(out_dir, exist_ok=True)
    log(f"Goal recreation - {scorer} {goal_minute}' ({n_frames} frames)...")

    # Define a generic attacking sequence
    # Positions: (x, y) normalised 0-1, home attacks right→left
    home_players = {
        "GK":     [(0.05, 0.5)],
        "DEF":    [(0.2,0.2),(0.2,0.4),(0.2,0.6),(0.2,0.8)],
        "MID":    [(0.4,0.25),(0.4,0.5),(0.4,0.75)],
        "ATT":    [(0.65,0.2),(0.65,0.5),(0.65,0.8)],
        "SCORER": [(0.65,0.5)],  # will animate to goal
    }
    away_players = {
        "GK":  [(0.95, 0.5)],
        "DEF": [(0.75,0.2),(0.75,0.4),(0.75,0.6),(0.75,0.8)],
        "MID": [(0.6,0.3),(0.6,0.5),(0.6,0.7)],
        "ATT": [(0.45,0.25),(0.45,0.5),(0.45,0.75)],
    }

    # Ball path: build-up → final pass → goal
    ball_path = [
        (0.3, 0.6),   # start deep
        (0.45, 0.45), # midfield
        (0.6, 0.3),   # wide right
        (0.75, 0.4),  # cut inside
        (0.85, 0.48), # shot...
        (0.97, 0.5),  # GOAL
    ]

    for i in range(n_frames):
        t = i / n_frames

        fig, ax = plt.subplots(figsize=(19.2, 10.8), facecolor=BG_DARK)
        ax.set_facecolor(PITCH_DK)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.axis("off")

        # PITCH
        ax.add_patch(Rectangle((0.02,0.05), 0.96, 0.9,
                                fill=False, edgecolor=PITCH_LN, lw=3))
        ax.axvline(0.5, color=PITCH_LN, lw=1.5, ymin=0.05, ymax=0.95)
        ax.add_patch(Circle((0.5,0.5), 0.08,
                             fill=False, edgecolor=PITCH_LN, lw=1.5))
        # Goals
        ax.add_patch(Rectangle((0.02,0.38), 0.05, 0.24,
                                fill=False, edgecolor="#ffffff", lw=3))
        ax.add_patch(Rectangle((0.93,0.38), 0.05, 0.24,
                                fill=False, edgecolor="#ffffff", lw=3))
        # Penalty areas
        ax.add_patch(Rectangle((0.02,0.25), 0.18, 0.5,
                                fill=False, edgecolor=PITCH_LN, lw=1.5))
        ax.add_patch(Rectangle((0.80,0.25), 0.18, 0.5,
                                fill=False, edgecolor=PITCH_LN, lw=1.5))

        # Title
        ax.text(0.5, 0.98,
                f"GOAL {goal_minute}' — {scorer.upper()} | {home.upper()} vs {away.upper()}",
                transform=ax.transAxes, ha="center", va="top",
                fontsize=22, color=GOLD, fontweight="bold")

        # AWAY players (static defenders)
        all_away = []
        for group, positions in away_players.items():
            for pos in positions:
                all_away.append(pos)

        for px, py in all_away:
            ax.plot(px, py, "o", markersize=18,
                    color=FIRE, markeredgecolor=WHITE, markeredgewidth=2,
                    transform=ax.transData, zorder=4)

        # HOME players — scorer animates toward goal
        scorer_start = (0.65, 0.5)
        scorer_end   = (0.93, 0.5)

        # Scorer moves after t > 0.5
        if t > 0.5:
            move_t = ease_out((t - 0.5) / 0.4)
            sx = scorer_start[0] + (scorer_end[0] - scorer_start[0]) * move_t
            sy = scorer_start[1] + (scorer_end[1] - scorer_start[1]) * move_t
            scorer_pos = (sx, sy)
        else:
            scorer_pos = scorer_start

        all_home = [(0.05,0.5),(0.2,0.2),(0.2,0.4),(0.2,0.6),(0.2,0.8),
                    (0.4,0.25),(0.4,0.5),(0.4,0.75),(0.65,0.2),(0.65,0.8)]

        for px, py in all_home:
            ax.plot(px, py, "o", markersize=18,
                    color=ELECTRIC, markeredgecolor=WHITE, markeredgewidth=2,
                    transform=ax.transData, zorder=4)

        # Scorer (highlighted)
        ax.plot(scorer_pos[0], scorer_pos[1], "o", markersize=26,
                color=GOLD, markeredgecolor=WHITE, markeredgewidth=3,
                transform=ax.transData, zorder=6)
        ax.text(scorer_pos[0], scorer_pos[1], "★",
                ha="center", va="center", fontsize=12,
                color=BG_DARK, fontweight="bold",
                transform=ax.transData, zorder=7)

        # Ball animation
        ball_idx = min(len(ball_path)-1, int(t * len(ball_path) * 1.5))
        if ball_idx < len(ball_path)-1:
            frac = (t * len(ball_path) * 1.5) - ball_idx
            bx = ball_path[ball_idx][0] + (ball_path[min(ball_idx+1,len(ball_path)-1)][0] - ball_path[ball_idx][0]) * frac
            by = ball_path[ball_idx][1] + (ball_path[min(ball_idx+1,len(ball_path)-1)][1] - ball_path[ball_idx][1]) * frac
        else:
            bx, by = ball_path[-1]

        # Ball trail
        ax.plot(bx, by, "o", markersize=14,
                color=WHITE, markeredgecolor=GOLD, markeredgewidth=2,
                transform=ax.transData, zorder=8)

        # GOAL flash
        if t > 0.85:
            flash_t = (t - 0.85) / 0.15
            # Screen flash
            flash_alpha = math.sin(flash_t * math.pi) * 0.4
            ax.add_patch(Rectangle((0,0), 1, 1,
                                   color=(1,0.8,0,flash_alpha),
                                   transform=ax.transAxes, zorder=10))
            ax.text(0.5, 0.5, "GOAL!",
                    transform=ax.transAxes, ha="center", va="center",
                    fontsize=120, color=GOLD, fontweight="bold",
                    alpha=flash_t, zorder=11)

        # Description text
        ax.text(0.5, 0.02, description,
                transform=ax.transAxes, ha="center", va="bottom",
                fontsize=18, color=WHITE, alpha=min(1, t*3))

        _save(fig, os.path.join(out_dir, f"frame_{i:04d}.png"))

    return out_dir

# ─────────────────────────────────────────────────────────────────────────────
# 3. DRAMATIC STAT SLAM — numbers explode onto screen
# ─────────────────────────────────────────────────────────────────────────────
def make_stat_slam(home, away, stats, insight_text, out_dir, n_frames=90):
    """Stats SLAM in one by one. Beast-style: each number is a reveal."""
    os.makedirs(out_dir, exist_ok=True)
    log(f"Stat slam ({n_frames} frames)...")

    stat_items = list(stats.items())
    total_stats = len(stat_items)

    for i in range(n_frames):
        t = i / n_frames

        img = Image.new("RGB", (W, H), BG_DARK)
        draw = ImageDraw.Draw(img)

        # Scanline bg
        for y in range(0, H, 6):
            draw.line([(0,y),(W,y)], fill=(10,20,40))

        # Header
        draw.rectangle([0, 0, W, 100], fill=(20,30,60))
        draw.text((W//2, 50), f"{home.upper()}  vs  {away.upper()} — THE NUMBERS",
                  font=_font(44), fill=WHITE, anchor="mm")

        # Stats appear one by one with SLAM effect
        for j, (label, (hv, av)) in enumerate(stat_items):
            stat_reveal_t = (t * total_stats) - j
            if stat_reveal_t < 0: continue
            stat_reveal_t = min(1.0, stat_reveal_t)
            et = ease_out(stat_reveal_t)

            y_base = 160 + j * 110
            x_centre = W // 2

            # Slam effect — comes from far away
            scale = 0.3 + et * 0.7
            alpha = int(255 * et)

            # Background bar
            bar_h = int(80 * scale)
            bar_y = y_base + (80 - bar_h) // 2
            draw.rectangle([80, bar_y, W-80, bar_y + bar_h],
                           fill=(20, 40, 80), outline=(40, 80, 160), width=2)

            # Home value (left)
            h_color = ELECTRIC if hv > av else (200,200,200)
            draw.text((300, y_base + 40), str(hv),
                      font=_font(int(72 * scale)), fill=h_color, anchor="mm")

            # Away value (right)
            a_color = FIRE if av > hv else (200,200,200)
            draw.text((W-300, y_base + 40), str(av),
                      font=_font(int(72 * scale)), fill=a_color, anchor="mm")

            # Label centre
            draw.text((x_centre, y_base + 40), label.upper(),
                      font=_font(int(36 * scale)), fill=GOLD, anchor="mm")

            # Winner indicator
            if hv != av:
                winner_x = 200 if hv > av else W-200
                draw.text((winner_x, y_base + 40), "▲",
                          font=_font(28), fill=LIME, anchor="mm")

        # BIG INSIGHT slams in at end
        if t > 0.75:
            insight_t = ease_out((t - 0.75) / 0.25)
            iy = H - 140
            draw.rectangle([0, iy-50, W, H],
                           fill=(200, 50, 0))
            draw.text((W//2, iy), f"💡 {insight_text.upper()[:80]}",
                      font=_font(42), fill=WHITE, anchor="mm")

        img.save(os.path.join(out_dir, f"frame_{i:04d}.png"))

    return out_dir

# ─────────────────────────────────────────────────────────────────────────────
# 4. MOMENTUM BATTLE CHART — dramatic tension build
# ─────────────────────────────────────────────────────────────────────────────
def make_momentum_battle(home, away, hg, ag, key_events, out_dir, n_frames=120):
    """The match unfolds minute by minute. Key events trigger dramatic visual spikes."""
    os.makedirs(out_dir, exist_ok=True)
    log(f"Momentum battle ({n_frames} frames)...")

    np.random.seed(42)
    minutes = np.linspace(0, 90, 270)

    # Generate momentum with goals causing spikes
    home_mom = np.cumsum(np.random.randn(270) * 0.3)
    away_mom = np.cumsum(np.random.randn(270) * 0.3)

    # Normalise
    all_vals = np.concatenate([home_mom, away_mom])
    mn, mx = all_vals.min(), all_vals.max()
    home_mom = (home_mom - mn) / (mx - mn) * 8 + 1
    away_mom = (away_mom - mn) / (mx - mn) * 8 + 1

    # Add goal spikes
    for g in key_events:
        idx = int(g.get("minute",45) / 90 * 270)
        if g.get("team") == "home":
            home_mom[idx:idx+15] += 3
        else:
            away_mom[idx:idx+15] += 3

    for i in range(n_frames):
        t = i / n_frames
        current_idx = int(t * 270)

        fig, ax = plt.subplots(figsize=(19.2, 10.8), facecolor=BG_DARK)
        ax.set_facecolor(BG_DARK)

        # Title
        ax.text(0.5, 0.96, "MATCH MOMENTUM — LIVE",
                transform=ax.transAxes, ha="center",
                fontsize=32, color=WHITE, fontweight="bold")
        ax.text(0.15, 0.96, home.upper(),
                transform=ax.transAxes, ha="center",
                fontsize=24, color=ELECTRIC, fontweight="bold")
        ax.text(0.85, 0.96, away.upper(),
                transform=ax.transAxes, ha="center",
                fontsize=24, color=FIRE, fontweight="bold")

        # Draw momentum up to current point
        if current_idx > 1:
            mins_so_far = minutes[:current_idx]
            home_so_far = home_mom[:current_idx]
            away_so_far = away_mom[:current_idx]

            ax.fill_between(mins_so_far, 5, home_so_far,
                           alpha=0.25, color=ELECTRIC)
            ax.fill_between(mins_so_far, 5, away_so_far,
                           alpha=0.25, color=FIRE)
            ax.plot(mins_so_far, home_so_far,
                   color=ELECTRIC, lw=3, label=home)
            ax.plot(mins_so_far, away_so_far,
                   color=FIRE, lw=3, label=away)

            # Current position dot
            ax.plot(mins_so_far[-1], home_so_far[-1],
                   "o", markersize=12, color=ELECTRIC,
                   markeredgecolor=WHITE, markeredgewidth=2, zorder=6)
            ax.plot(mins_so_far[-1], away_so_far[-1],
                   "o", markersize=12, color=FIRE,
                   markeredgecolor=WHITE, markeredgewidth=2, zorder=6)

        # Key event markers
        for g in key_events:
            gm = g.get("minute",45)
            if gm <= t * 90:
                gx = gm
                color = ELECTRIC if g.get("team")=="home" else FIRE
                ax.axvline(gx, color=color, lw=2, alpha=0.7, linestyle="--")
                idx = int(gm/90*270)
                gy = home_mom[idx] if g.get("team")=="home" else away_mom[idx]
                ax.annotate(f"GOAL {gm}'",
                           xy=(gx, gy),
                           xytext=(gx+2, gy+1.5),
                           fontsize=14, color=GOLD, fontweight="bold",
                           arrowprops=dict(arrowstyle="->", color=GOLD))

        # Halftime
        ax.axvline(45, color="#ffff00", lw=1.5, alpha=0.5, linestyle=":")
        ax.text(45, 1.5, "HT", ha="center", fontsize=14,
               color="#ffff00", alpha=0.7)

        # Current minute display
        cur_min = int(t * 90)
        ax.text(0.5, 0.04, f"{cur_min}'",
               transform=ax.transAxes, ha="center",
               fontsize=36, color=GOLD, fontweight="bold")

        ax.set_xlim(0, 90)
        ax.set_ylim(0, 12)
        ax.set_xlabel("Minute", color=WHITE, fontsize=16)
        ax.tick_params(colors=WHITE, labelsize=14)
        for spine in ax.spines.values():
            spine.set_color("#2a3a4a")
        ax.set_facecolor(BG_DARK)

        _save(fig, os.path.join(out_dir, f"frame_{i:04d}.png"))

    return out_dir

# ─────────────────────────────────────────────────────────────────────────────
# 5. CONSEQUENCE BOARD — who benefits, who suffers
# ─────────────────────────────────────────────────────────────────────────────
def make_consequence_board(home, away, hg, ag, group,
                           consequences, out_dir, n_frames=72):
    """Dramatic reveal of what this result means for every team."""
    os.makedirs(out_dir, exist_ok=True)
    log(f"Consequence board ({n_frames} frames)...")

    # consequences = [{"team":"Germany","effect":"DANGER","detail":"Face England next"},...]
    if not consequences:
        winner = home if hg > ag else (away if ag > hg else None)
        loser  = away if hg > ag else (home if ag > hg else None)
        consequences = [
            {"team": winner or home, "effect": "QUALIFIES IF", "detail": "Win next match", "color": LIME},
            {"team": loser or away,  "effect": "ELIMINATED IF", "detail": "Lose next match", "color": RED},
            {"team": "Group rivals", "effect": "WATCHING CLOSELY", "detail": "Table shifts", "color": GOLD},
        ]

    for i in range(n_frames):
        t = i / n_frames

        img = Image.new("RGB", (W, H), BG_DARK)
        draw = ImageDraw.Draw(img)

        # Header
        draw.rectangle([0, 0, W, 120], fill=(150, 0, 0))
        draw.text((W//2, 60), "WHAT HAPPENS NOW? EVERY TEAM AFFECTED",
                  font=_font(48), fill=WHITE, anchor="mm")

        # Match result small
        draw.text((W//2, 155),
                  f"{home} {hg}–{ag} {away}",
                  font=_font(32), fill=GOLD, anchor="mm")

        # Consequence cards appear one by one
        card_w = int((W - 120) / max(len(consequences), 1))
        for j, con in enumerate(consequences):
            card_t = max(0, min(1.0, (t - j*0.2) * 3))
            et = ease_out(card_t)

            cx = 60 + j * card_w
            cy_top = int(200 - (1-et) * 400)

            color = con.get("color", GOLD)
            if isinstance(color, str):
                # Convert hex to RGB
                c = color.lstrip("#")
                color = tuple(int(c[k:k+2],16) for k in (0,2,4))

            # Card background
            draw.rectangle([cx, cy_top, cx+card_w-20, cy_top+650],
                           fill=(20,30,50), outline=color, width=4)

            # Effect label (big)
            draw.rectangle([cx, cy_top, cx+card_w-20, cy_top+100],
                           fill=color)
            draw.text((cx + (card_w-20)//2, cy_top+50),
                      con.get("effect","").upper(),
                      font=_font(44), fill=BG_DARK if color!=(255,215,0) else BG_DARK,
                      anchor="mm")

            # Team name
            draw.text((cx + (card_w-20)//2, cy_top+200),
                      con.get("team","").upper(),
                      font=_font(52), fill=WHITE, anchor="mm")

            # Detail
            words = con.get("detail","").split()
            detail_lines = []
            cur = []
            for w in words:
                cur.append(w)
                if len(" ".join(cur)) > 20:
                    detail_lines.append(" ".join(cur))
                    cur = []
            if cur: detail_lines.append(" ".join(cur))

            for li, dl in enumerate(detail_lines[:4]):
                draw.text((cx + (card_w-20)//2, cy_top+320+li*60),
                          dl, font=_font(34), fill=(180,180,180), anchor="mm")

        img.save(os.path.join(out_dir, f"frame_{i:04d}.png"))

    return out_dir

# ─────────────────────────────────────────────────────────────────────────────
# 6. BEAST THUMBNAIL — MrBeast energy
# ─────────────────────────────────────────────────────────────────────────────
def make_beast_thumbnail(home, away, hg, ag, hook, out_path):
    """High-energy thumbnail with contrast, bold text, emotional trigger."""
    img = Image.new("RGB", (1280, 720), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Dynamic background — split diagonal
    # Left side: home color
    pts_l = [(0,0),(640,0),(500,720),(0,720)]
    draw.polygon(pts_l, fill=(0,30,80))
    # Right side: away color
    pts_r = [(640,0),(1280,0),(1280,720),(500,720)]
    draw.polygon(pts_r, fill=(80,10,0))

    # Score box — centre
    draw.rectangle([380,260,900,460], fill="#111111", outline=GOLD, width=6)
    draw.text((640, 360), f"{hg}  —  {ag}",
              font=_font(130), fill=GOLD, anchor="mm")

    # Team names
    draw.text((200, 360), home[:8].upper(),
              font=_font(64), fill=ELECTRIC, anchor="mm")
    draw.text((1080, 360), away[:8].upper(),
              font=_font(64), fill=FIRE, anchor="mm")

    # Hook text — bottom bar
    draw.rectangle([0, 560, 1280, 720], fill=RED)

    # Wrap hook
    hook_short = hook.upper()[:55]
    draw.text((640, 640), hook_short,
              font=_font(54), fill=WHITE, anchor="mm")

    # WC badge
    draw.ellipse([20,20,120,120], fill=GOLD, outline=WHITE, width=3)
    draw.text((70,70), "WC\n2026", font=_font(22),
              fill=BG_DARK, anchor="mm", align="center")

    # Excitement arrows
    for ax_pos in [130, 150, 170]:
        draw.text((ax_pos, 360), "▶",
                  font=_font(32), fill=GOLD, anchor="mm")
    for ax_pos in [1110, 1130, 1150]:
        draw.text((ax_pos, 360), "◀",
                  font=_font(32), fill=GOLD, anchor="mm")

    img.save(out_path, "JPEG", quality=97)
    return out_path

# ─────────────────────────────────────────────────────────────────────────────
# MASTER: BUILD COMPLETE BEAST VIDEO (visuals only, no audio yet)
# ─────────────────────────────────────────────────────────────────────────────
def build_beast_visuals(match, hook_text, insight_text, out_dir):
    home = match["home"]; away = match["away"]
    hg   = int(match.get("home_goals") or 0)
    ag   = int(match.get("away_goals") or 0)
    stage = match.get("stage","GROUP_STAGE")
    group = match.get("group","")

    os.makedirs(out_dir, exist_ok=True)
    segment_videos = []

    # Build goal events
    goals = []
    for k in range(hg):
        goals.append({"minute":20+k*18,"team":"home","scorer":"Goal"})
    for k in range(ag):
        goals.append({"minute":25+k*18,"team":"away","scorer":"Goal"})
    goals.sort(key=lambda x: x["minute"])

    # Stats
    stats = {
        "Possession %": (58 if hg>=ag else 42, 42 if hg>=ag else 58),
        "Shots": (14 if hg>ag else 8, 8 if hg>ag else 14),
        "Shots on Target": (hg+3, ag+2),
        "xG": (round(hg*0.7+0.3,1), round(ag*0.7+0.2,1)),
        "Passes": (520 if hg>=ag else 380, 380 if hg>=ag else 520),
    }

    # 1. COLD OPEN (3s)
    log("Building cold open...")
    d = os.path.join(out_dir, "s01_open")
    build_dir = make_cold_open(home, away, hg, ag, hook_text, d, n_frames=90)
    v = os.path.join(out_dir, "s01_open.mp4")
    frames_to_video(d, v); segment_videos.append(v)

    # 2. GOAL RECREATIONS (4s each, max 2 goals)
    for gi, goal in enumerate(goals[:2]):
        log(f"Building goal recreation {gi+1}...")
        d = os.path.join(out_dir, f"s0{2+gi}_goal")
        desc = f"MINUTE {goal['minute']} — {goal['team'].upper()} TEAM STRIKES"
        make_goal_recreation(home, away, goal["minute"],
                            goal.get("scorer","Goal"),
                            desc, d, n_frames=120)
        v = os.path.join(out_dir, f"s0{2+gi}_goal.mp4")
        frames_to_video(d, v); segment_videos.append(v)

    # 3. MOMENTUM BATTLE (4s)
    log("Building momentum battle...")
    d = os.path.join(out_dir, "s04_momentum")
    make_momentum_battle(home, away, hg, ag, goals, d, n_frames=120)
    v = os.path.join(out_dir, "s04_momentum.mp4")
    frames_to_video(d, v); segment_videos.append(v)

    # 4. STAT SLAM (3s)
    log("Building stat slam...")
    d = os.path.join(out_dir, "s05_stats")
    make_stat_slam(home, away, stats, insight_text, d, n_frames=90)
    v = os.path.join(out_dir, "s05_stats.mp4")
    frames_to_video(d, v); segment_videos.append(v)

    # 5. CONSEQUENCE BOARD (2.4s)
    log("Building consequence board...")
    consequences = [
        {"team": home if hg>ag else away,
         "effect": "SURVIVE" if hg>=ag else "IN DANGER",
         "detail": "Still in contention",
         "color": LIME if hg>=ag else GOLD},
        {"team": away if hg>ag else home,
         "effect": "MUST WIN" if hg!=ag else "DRAW OK",
         "detail": "Next match is everything",
         "color": RED if hg!=ag else GOLD},
        {"team": "Group " + (group or "Stage"),
         "effect": "TABLE SHIFTS",
         "detail": "Everything changes now",
         "color": ELECTRIC},
    ]
    d = os.path.join(out_dir, "s06_consequences")
    make_consequence_board(home, away, hg, ag, group,
                          consequences, d, n_frames=72)
    v = os.path.join(out_dir, "s06_consequences.mp4")
    frames_to_video(d, v); segment_videos.append(v)

    # CONCATENATE
    log("Concatenating beast segments...")
    concat_file = os.path.join(out_dir, "concat.txt")
    with open(concat_file, "w") as f:
        for sv in segment_videos:
            f.write(f"file '{os.path.abspath(sv)}'\n")

    visual_path = os.path.join(out_dir, "beast_visuals.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file, "-c", "copy", visual_path
    ], check=True, capture_output=True)

    # Thumbnail
    thumb_path = os.path.join(out_dir, "thumbnail.jpg")
    make_beast_thumbnail(home, away, hg, ag, hook_text, thumb_path)

    log(f"Beast visuals done: {visual_path}")
    return visual_path, thumb_path


if __name__ == "__main__":
    m = {"id":"beast_test","home":"Germany","away":"Curacao",
         "home_goals":7,"away_goals":1,
         "stage":"GROUP_STAGE","group":"E","winner":"HOME_TEAM","utc":""}

    hook = "Germany just scored 7 and still looked bored"
    insight = "Germany haven't even used their best lineup yet"

    vpath, tpath = build_beast_visuals(m, hook, insight, "beast_test_out")
    import os
    print(f"\nDone!")
    print(f"Video: {vpath} ({os.path.getsize(vpath)/1024/1024:.1f}MB)")
    print(f"Thumb: {tpath} ({os.path.getsize(tpath)/1024:.0f}KB)")
