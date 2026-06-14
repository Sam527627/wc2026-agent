"""
VISUALS ENGINE — generates all on-screen graphics for the video
Produces PNG frames that FFmpeg will stitch into the final video.
No external services. No API calls. Pure Python + matplotlib + Pillow.
"""

import os
import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
from PIL import Image, ImageDraw, ImageFont
import numpy as np

W, H = 1920, 1080          # output resolution
BG   = "#0a0a0a"           # near-black background
GOLD = "#f5c518"
TEAL = "#00b4d8"
RED  = "#e63946"
WHITE= "#ffffff"
GRAY = "#888888"

def _save(fig, path):
    fig.savefig(path, dpi=100, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close(fig)

# ── 1. TITLE CARD ────────────────────────────────────────────────────────────
def title_card(home, away, hg, ag, stage, out_path):
    fig, ax = plt.subplots(figsize=(19.2, 10.8), facecolor=BG)
    ax.set_facecolor(BG); ax.axis("off")

    # top bar
    ax.add_patch(mpatches.Rectangle((0,.88),1,.12,transform=ax.transAxes,
                                     color=TEAL,zorder=0))
    ax.text(.5,.93,"FIFA WORLD CUP 2026  ·  ANALYSIS",
            transform=ax.transAxes,ha="center",va="center",
            fontsize=18,color=BG,fontweight="bold")

    # score
    ax.text(.5,.62,f"{hg}  –  {ag}",transform=ax.transAxes,
            ha="center",va="center",fontsize=120,color=WHITE,fontweight="bold")
    ax.text(.25,.62,home,transform=ax.transAxes,
            ha="center",va="center",fontsize=36,color=GOLD,fontweight="bold")
    ax.text(.75,.62,away,transform=ax.transAxes,
            ha="center",va="center",fontsize=36,color=GOLD,fontweight="bold")

    # divider
    ax.axhline(.52,color=TEAL,linewidth=2,xmin=.1,xmax=.9)
    ax.text(.5,.44,stage.replace("_"," ").upper(),
            transform=ax.transAxes,ha="center",va="center",
            fontsize=22,color=GRAY)

    # brand
    ax.text(.5,.06,"WC2026 ANALYSIS  ·  SUBSCRIBE FOR DAILY BREAKDOWNS",
            transform=ax.transAxes,ha="center",va="center",
            fontsize=14,color=GRAY)

    fig.tight_layout(pad=0)
    _save(fig, out_path)

# ── 2. STAT BAR ──────────────────────────────────────────────────────────────
def stat_bars(home, away, stats_dict, out_path):
    """stats_dict = {"Possession %": (65,35), "Shots": (12,8), ...}"""
    fig, ax = plt.subplots(figsize=(19.2,10.8), facecolor=BG)
    ax.set_facecolor(BG); ax.axis("off")

    ax.text(.5,.93,"MATCH STATISTICS",transform=ax.transAxes,
            ha="center",fontsize=28,color=WHITE,fontweight="bold")
    ax.text(.22,.87,home,transform=ax.transAxes,
            ha="center",fontsize=20,color=TEAL,fontweight="bold")
    ax.text(.78,.87,away,transform=ax.transAxes,
            ha="center",fontsize=20,color=RED,fontweight="bold")

    items = list(stats_dict.items())
    n = len(items)
    for i,(label,(hv,av)) in enumerate(items):
        y = .78 - i*(.68/max(n-1,1))
        total = hv+av or 1
        hw = .35*(hv/total)
        aw = .35*(av/total)

        # home bar (grows left from centre)
        ax.add_patch(mpatches.Rectangle((.5-hw,y-.015),hw,.03,
                                         color=TEAL,transform=ax.transAxes))
        # away bar (grows right)
        ax.add_patch(mpatches.Rectangle((.5,y-.015),aw,.03,
                                         color=RED,transform=ax.transAxes))
        ax.text(.5,y,label,transform=ax.transAxes,
                ha="center",va="center",fontsize=13,color=WHITE,zorder=5)
        ax.text(.5-hw-.01,y,str(hv),transform=ax.transAxes,
                ha="right",va="center",fontsize=15,color=TEAL,fontweight="bold")
        ax.text(.5+aw+.01,y,str(av),transform=ax.transAxes,
                ha="left",va="center",fontsize=15,color=RED,fontweight="bold")

    fig.tight_layout(pad=0)
    _save(fig, out_path)

# ── 3. TACTICAL BOARD ────────────────────────────────────────────────────────
def tactical_board(home, away, home_formation, away_formation, out_path):
    fig, axes = plt.subplots(1,2,figsize=(19.2,10.8),facecolor=BG)
    for ax, team, form, color in zip(axes,[home,away],
                                      [home_formation,away_formation],[TEAL,RED]):
        ax.set_facecolor("#0d3b1e")
        ax.set_xlim(0,10); ax.set_ylim(0,10)
        ax.set_aspect("equal"); ax.axis("off")
        ax.set_title(f"{team}\n{form}",color=color,
                     fontsize=22,fontweight="bold",pad=12)
        # draw pitch lines
        for x in [0,10]: ax.axvline(x,color="#1a5c2e",lw=2)
        for y in [0,10]: ax.axhline(y,color="#1a5c2e",lw=2)
        ax.add_patch(plt.Circle((5,5),.5,fill=False,color="#1a5c2e",lw=1.5))
        # place dots for formation
        try:
            rows = [int(x) for x in form.split("-")]
        except Exception:
            rows = [4,3,3]
        rows = [1] + rows          # add GK
        y_positions = np.linspace(1,9,len(rows))
        for yi, count in zip(y_positions, rows):
            xs = np.linspace(1.5,8.5,count)
            for xi in xs:
                ax.plot(xi,yi,"o",markersize=18,color=color,
                        markeredgecolor=WHITE,markeredgewidth=1.5)

    fig.tight_layout(pad=0)
    _save(fig, out_path)

# ── 4. MOMENTUM CHART ────────────────────────────────────────────────────────
def momentum_chart(home, away, out_path):
    fig, ax = plt.subplots(figsize=(19.2,10.8),facecolor=BG)
    ax.set_facecolor(BG)
    mins = np.linspace(0,90,91)
    np.random.seed(42)
    home_m = np.cumsum(np.random.randn(91)*.3)
    away_m = -home_m*.6 + np.cumsum(np.random.randn(91)*.2)
    home_m = (home_m-home_m.min())/(home_m.max()-home_m.min())*8+1
    away_m = (away_m-away_m.min())/(away_m.max()-away_m.min())*8+1

    ax.fill_between(mins,home_m,alpha=.25,color=TEAL)
    ax.fill_between(mins,away_m,alpha=.25,color=RED)
    ax.plot(mins,home_m,color=TEAL,lw=3,label=home)
    ax.plot(mins,away_m,color=RED,lw=3,label=away)
    ax.axvline(45,color=GRAY,lw=1,linestyle="--",alpha=.5)
    ax.set_xlabel("Minute",color=WHITE,fontsize=16)
    ax.set_ylabel("Momentum",color=WHITE,fontsize=16)
    ax.set_title("MATCH MOMENTUM",color=WHITE,fontsize=28,fontweight="bold",pad=16)
    ax.tick_params(colors=WHITE); ax.spines[:].set_color(GRAY)
    ax.set_facecolor(BG)
    ax.legend(fontsize=16,facecolor=BG,labelcolor=WHITE)
    fig.tight_layout(pad=1)
    _save(fig, out_path)

# ── 5. THUMBNAIL ─────────────────────────────────────────────────────────────
def thumbnail(home, away, hg, ag, headline, out_path):
    img = Image.new("RGB",(1280,720),color="#0a0a0a")
    draw = ImageDraw.Draw(img)

    # gradient-ish side bars
    for x in range(200):
        alpha = int(255*(x/200)**2)
        draw.rectangle([x,0,x+1,720],fill=(0,180,216, alpha if alpha<255 else 255))
    for x in range(200):
        alpha = int(255*(x/200)**2)
        draw.rectangle([1280-x,0,1280-x+1,720],fill=(230,57,70, alpha if alpha<255 else 255))

    # score box
    draw.rectangle([440,260,840,460],fill="#111111",outline=GOLD,width=4)

    try: fnt_big  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",120)
    except: fnt_big = ImageFont.load_default()
    try: fnt_med  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",48)
    except: fnt_med = fnt_big
    try: fnt_sm   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",32)
    except: fnt_sm = fnt_big

    score_txt = f"{hg} - {ag}"
    draw.text((640,360), score_txt, font=fnt_big, fill=WHITE, anchor="mm")
    draw.text((220,360), home[:12], font=fnt_med, fill="#00b4d8", anchor="mm")
    draw.text((1060,360), away[:12], font=fnt_med, fill="#e63946", anchor="mm")

    # headline
    wrapped = textwrap.fill(headline.upper(), width=32)
    draw.text((640,560), wrapped, font=fnt_sm, fill=GOLD, anchor="mm", align="center")
    draw.text((640,80), "WC2026 ANALYSIS", font=fnt_sm, fill=WHITE, anchor="mm")

    img.save(out_path, "JPEG", quality=95)

# ── 6. SECTION CARD (shows between script sections) ──────────────────────────
def section_card(text, out_path):
    fig, ax = plt.subplots(figsize=(19.2,10.8),facecolor=BG)
    ax.set_facecolor(BG); ax.axis("off")
    ax.add_patch(mpatches.Rectangle((.1,.3),.8,.4,
                  transform=ax.transAxes,color="#111111",
                  linewidth=4,edgecolor=TEAL))
    wrapped = "\n".join(textwrap.wrap(text,40))
    ax.text(.5,.5,wrapped,transform=ax.transAxes,
            ha="center",va="center",fontsize=40,
            color=WHITE,fontweight="bold")
    fig.tight_layout(pad=0)
    _save(fig, out_path)

print("visuals.py loaded ok")
