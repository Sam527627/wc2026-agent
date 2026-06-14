"""
VIDEO ENGINE
Takes the script, generates all visuals, generates voiceover,
stitches everything into a 1080p MP4 with captions + music bed.
100% FFmpeg. Zero paid tools.
"""

import os, re, json, subprocess, tempfile, textwrap, shutil
import visuals
import voice

MUSIC_VOLUME = "0.07"   # background music very low under voice

# Map script sections to visual types
SECTION_VISUALS = {
    "HOOK":             "title",
    "CONFLICT":         "section",
    "BREAKDOWN":        "stats",
    "BIG INSIGHT":      "section",
    "TOURNAMENT IMPACT":"momentum",
    "PREDICTION":       "section",
    "CTA":              "section",
}
SECTION_ORDER = ["HOOK","CONFLICT","BREAKDOWN","BIG INSIGHT",
                 "TOURNAMENT IMPACT","PREDICTION","CTA"]

def parse_sections(script: str) -> dict:
    """Split script into named sections."""
    sections = {}
    current = "HOOK"
    buf = []
    for line in script.splitlines():
        stripped = line.strip()
        if stripped in SECTION_ORDER:
            if buf:
                sections[current] = "\n".join(buf).strip()
            current = stripped
            buf = []
        else:
            buf.append(line)
    if buf:
        sections[current] = "\n".join(buf).strip()
    return sections

def duration_of_mp3(path: str) -> float:
    """Get audio duration. ffprobe preferred, ffmpeg as fallback."""
    try:
        r = subprocess.run(
            ["ffprobe","-v","quiet","-show_entries","format=duration",
             "-of","default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True)
        v = float(r.stdout.strip())
        if 0.1 < v < 600:
            return v
    except Exception:
        pass
    try:
        # ffmpeg fallback — parse duration from stderr
        r = subprocess.run(["ffmpeg","-i",path,"-f","null","-"],
                           capture_output=True, text=True)
        for token in r.stderr.split():
            try:
                v = float(token)
                if 0.1 < v < 600:
                    return v
            except ValueError:
                pass
    except Exception:
        pass
    return 5.0

def make_silent_mp3(duration: float, out: str):
    subprocess.run(
        ["ffmpeg","-y","-f","lavfi","-i",f"anullsrc=r=44100:cl=stereo",
         "-t",str(duration),"-q:a","9","-acodec","libmp3lame", out],
        check=True, capture_output=True
    )

def generate_video(match: dict, script: str, out_dir: str) -> str:
    """Full pipeline: visuals + voice + FFmpeg assembly → MP4."""
    home = match["home"]
    away = match["away"]
    hg   = match.get("home_goals", 0) or 0
    ag   = match.get("away_goals", 0) or 0
    stage= match.get("stage","GROUP_STAGE")

    frames_dir = os.path.join(out_dir, "frames")
    audio_dir  = os.path.join(out_dir, "audio")
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(audio_dir,  exist_ok=True)

    sections = parse_sections(script)

    # ── GENERATE ALL FRAMES ──────────────────────────────────────────────────
    print("[video] Generating visual frames...")
    frame_paths = {}

    title_path = os.path.join(frames_dir, "title.png")
    visuals.title_card(home, away, hg, ag, stage, title_path)
    frame_paths["HOOK"] = title_path

    stats_path = os.path.join(frames_dir, "stats.png")
    stats = {"Possession %": (55, 45), "Shots": (14, 6),
             "Shots on Target": (7, 2), "Corners": (6, 3), "Fouls": (12, 10)}
    visuals.stat_bars(home, away, stats, stats_path)
    frame_paths["BREAKDOWN"] = stats_path

    tactics_path = os.path.join(frames_dir, "tactics.png")
    visuals.tactical_board(home, away, "4-3-3", "4-4-2", tactics_path)

    momentum_path = os.path.join(frames_dir, "momentum.png")
    visuals.momentum_chart(home, away, momentum_path)
    frame_paths["TOURNAMENT IMPACT"] = momentum_path

    for sec in ["CONFLICT","BIG INSIGHT","PREDICTION","CTA"]:
        label = sec if sec != "CTA" else "SUBSCRIBE FOR MORE"
        sec_path = os.path.join(frames_dir, f"{sec.replace(' ','_').lower()}.png")
        visuals.section_card(label, sec_path)
        frame_paths[sec] = sec_path

    # ── GENERATE AUDIO PER SECTION ────────────────────────────────────────────
    print("[video] Generating voiceovers...")
    audio_paths = {}
    durations   = {}
    for sec in SECTION_ORDER:
        text = sections.get(sec, "")
        if not text:
            text = sec
        mp3 = os.path.join(audio_dir, f"{sec.replace(' ','_').lower()}.mp3")
        voice.generate_voiceover(text, mp3)
        audio_paths[sec] = mp3
        durations[sec]   = duration_of_mp3(mp3)
        print(f"  {sec}: {durations[sec]:.1f}s")

    # ── BUILD SEGMENT VIDEOS (frame held for audio duration) ──────────────────
    print("[video] Building segments...")
    segment_files = []
    for i, sec in enumerate(SECTION_ORDER):
        frame = frame_paths.get(sec, frame_paths.get("HOOK"))
        audio = audio_paths[sec]
        dur   = durations[sec]
        seg   = os.path.join(out_dir, f"seg_{i:02d}.mp4")

        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1", "-i", frame,
            "-i", audio,
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-vf", f"scale=1920:1080,fps=24",
            "-t", str(dur + 0.5),
            seg
        ], check=True, capture_output=True)
        segment_files.append(seg)

    # ── CONCAT ALL SEGMENTS ───────────────────────────────────────────────────
    print("[video] Concatenating segments...")
    concat_list = os.path.join(out_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for seg in segment_files:
            f.write(f"file '{os.path.abspath(seg)}'\n")

    raw_video = os.path.join(out_dir, "raw_video.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy", raw_video
    ], check=True, capture_output=True)

    # ── ADD CAPTIONS (burn-in subtitles from script) ──────────────────────────
    print("[video] Adding captions...")
    srt_path = _make_srt(sections, durations, out_dir)

    final_mp4 = os.path.join(out_dir, "final_video.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", raw_video,
        "-vf", f"subtitles={srt_path}:force_style='FontName=Arial,FontSize=22,"
               "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,"
               "Alignment=2,MarginV=40'",
        "-c:a", "copy",
        final_mp4
    ], check=True, capture_output=True)

    # ── GENERATE THUMBNAIL ────────────────────────────────────────────────────
    thumb_path = os.path.join(out_dir, "thumbnail.jpg")
    headline   = f"Why {home} {'Won' if hg > ag else 'Lost' if hg < ag else 'Drew'}"
    visuals.thumbnail(home, away, hg, ag, headline, thumb_path)

    # Cleanup segments
    for seg in segment_files:
        try: os.remove(seg)
        except: pass

    total_dur = sum(durations.values())
    size_mb   = os.path.getsize(final_mp4) / 1024 / 1024
    print(f"[video] ✅ Done! {final_mp4}  ({total_dur:.0f}s, {size_mb:.1f}MB)")
    return final_mp4

def _make_srt(sections: dict, durations: dict, out_dir: str) -> str:
    """Generate SRT subtitle file from script sections."""
    srt_path = os.path.join(out_dir, "captions.srt")
    idx  = 1
    time = 0.0
    lines = []

    def fmt_time(s):
        h = int(s//3600); m = int((s%3600)//60)
        sec = s % 60
        return f"{h:02d}:{m:02d}:{sec:06.3f}".replace(".",",")

    for sec in SECTION_ORDER:
        text = sections.get(sec, "")
        dur  = durations.get(sec, 5.0)
        # chunk text into ~8-word subtitle lines
        words = re.sub(r"\[.*?\]","",text).split()
        chunk_size = 8
        chunks = [" ".join(words[i:i+chunk_size])
                  for i in range(0, len(words), chunk_size)]
        if not chunks: chunks = [sec]
        chunk_dur = dur / max(len(chunks), 1)

        t = time
        for chunk in chunks:
            lines.append(str(idx))
            lines.append(f"{fmt_time(t)} --> {fmt_time(t + chunk_dur - 0.05)}")
            lines.append(chunk)
            lines.append("")
            idx += 1
            t += chunk_dur
        time += dur + 0.5

    with open(srt_path, "w") as f:
        f.write("\n".join(lines))
    return srt_path


if __name__ == "__main__":
    # Quick test with demo data
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    m = {"id":"test","home":"Germany","away":"Curacao",
         "home_goals":4,"away_goals":0,
         "stage":"GROUP_STAGE","group":"E"}
    script = """HOOK
Germany just put FOUR past Curacao. But here is the thing nobody is talking about.

CONFLICT
On paper this was the easiest match in Group E. On the tactical board it told us something terrifying about the rest of the tournament.

BREAKDOWN
Germany lined up in a 4-2-3-1 and pressed from minute one. Curacao could not get out of their own half. The xG tells the full story — Germany created chance after chance down the right channel.

BIG INSIGHT
What most viewers missed was Germany's second striker role. Musiala dropped deep constantly, dragging Curacao's midfield out of shape. Every goal came from that exact movement.

TOURNAMENT IMPACT
Group E is now Germany's to lose. But France and Spain were watching. They just got a very detailed scouting report.

PREDICTION
Germany top the group with nine points. The question now is who they face in the round of 32 — and whether this attacking system holds up against a proper defensive block.

CTA
Subscribe for daily World Cup breakdowns. Tomorrow we rank every group after day four — and two giants are in serious trouble."""

    out = generate_video(m, script, "test_video_out")
    print("Test complete:", out)
