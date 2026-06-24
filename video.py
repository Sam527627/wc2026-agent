"""
VIDEO ENGINE v3 — BEAST LEVEL
Combines beast-level animated visuals with neural voiceover.
"""
import os, re, subprocess
import beast_visuals as bv
import voice

SECTION_ORDER = ["HOOK","CONFLICT","BREAKDOWN","BIG INSIGHT",
                 "TOURNAMENT IMPACT","PREDICTION","CTA"]

def parse_sections(script):
    sections = {}
    current = "HOOK"
    buf = []
    for line in script.splitlines():
        s = line.strip()
        if s in SECTION_ORDER:
            if buf: sections[current] = "\n".join(buf).strip()
            current = s; buf = []
        else: buf.append(line)
    if buf: sections[current] = "\n".join(buf).strip()
    return sections

def clean_text(text):
    text = re.sub(r"\[.*?\]","",text)
    text = re.sub(r"\*+|#{1,6}\s*","",text)
    return text.strip()

def duration_of(path):
    for cmd in [
        ["ffprobe","-v","quiet","-show_entries","format=duration",
         "-of","default=noprint_wrappers=1:nokey=1",path],
        ["ffmpeg","-i",path,"-f","null","-"],
    ]:
        try:
            r = subprocess.run(cmd,capture_output=True,text=True)
            out = r.stdout.strip() or r.stderr
            for tok in out.split():
                try:
                    v = float(tok)
                    if 0.1 < v < 600: return v
                except: pass
        except FileNotFoundError: continue
    return 5.0

def generate_video(match, script, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    sections = parse_sections(script)

    hook    = clean_text(sections.get("HOOK",""))[:120]
    insight = clean_text(sections.get("BIG INSIGHT",""))[:120]

    # Build beast visuals
    print("[video] Building Beast-level animated visuals...")
    vis_dir = os.path.join(out_dir, "beast_segs")
    visual_path, thumb_path = bv.build_beast_visuals(
        match, hook, insight, vis_dir)

    # Generate voiceover
    print("[video] Generating voiceover...")
    audio_dir = os.path.join(out_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    audio_parts = []

    for sec in SECTION_ORDER:
        text = sections.get(sec,"")
        if not text: continue
        mp3 = os.path.join(audio_dir, f"{sec.replace(' ','_').lower()}.mp3")
        voice.generate_voiceover(text, mp3)
        dur = duration_of(mp3)
        print(f"  {sec}: {dur:.1f}s")
        audio_parts.append(mp3)

    # Combine audio
    audio_list = os.path.join(out_dir, "audio_list.txt")
    with open(audio_list,"w") as f:
        for ap in audio_parts:
            f.write(f"file '{os.path.abspath(ap)}'\n")
    combined_audio = os.path.join(out_dir,"combined_voice.mp3")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0",
                    "-i",audio_list,"-c","copy",combined_audio],
                   check=True,capture_output=True)

    voice_dur   = duration_of(combined_audio)
    visual_dur  = duration_of(visual_path)
    print(f"[video] Voice: {voice_dur:.1f}s | Visuals: {visual_dur:.1f}s")

    # Combine visuals + voice
    final_mp4 = os.path.join(out_dir,"final_video.mp4")
    if visual_dur < voice_dur:
        subprocess.run([
            "ffmpeg","-y",
            "-stream_loop","-1","-i",visual_path,
            "-i",combined_audio,
            "-c:v","libx264","-c:a","aac","-b:a","192k",
            "-pix_fmt","yuv420p",
            "-t",str(voice_dur+0.5),"-shortest",final_mp4
        ],check=True,capture_output=True)
    else:
        subprocess.run([
            "ffmpeg","-y",
            "-i",visual_path,"-i",combined_audio,
            "-c:v","libx264","-c:a","aac","-b:a","192k",
            "-pix_fmt","yuv420p",
            "-t",str(voice_dur+0.5),
            "-map","0:v:0","-map","1:a:0",final_mp4
        ],check=True,capture_output=True)

    # Copy thumbnail
    thumb_dest = os.path.join(out_dir,"thumbnail.jpg")
    if os.path.exists(thumb_path) and thumb_path != thumb_dest:
        import shutil; shutil.copy(thumb_path, thumb_dest)

    size = os.path.getsize(final_mp4)/1024/1024
    dur  = duration_of(final_mp4)
    print(f"[video] ✅ Done! {final_mp4}  ({dur:.0f}s, {size:.1f}MB)")
    return final_mp4
