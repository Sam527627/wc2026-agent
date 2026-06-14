"""
VOICE ENGINE
Priority 1: edge-tts  (neural quality — needs internet, works on GitHub Actions)
Priority 2: espeak-ng (robotic but offline — works everywhere as fallback)
"""
import asyncio, re, os, subprocess, tempfile

def clean_script(text: str) -> str:
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\*+|#{1,6}\s*", "", text)
    text = re.sub(r"HOOK|CONFLICT|BREAKDOWN|BIG INSIGHT|TOURNAMENT IMPACT|PREDICTION|CTA","",text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

async def _edge_speak(text, out_mp3, voice="en-US-AndrewNeural"):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate="+8%", pitch="-3Hz")
    await comm.save(out_mp3)

def generate_voiceover(script_text: str, out_mp3: str) -> str:
    clean = clean_script(script_text)
    # Try neural first
    try:
        asyncio.run(_edge_speak(clean, out_mp3))
        if os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 1000:
            return out_mp3
    except Exception as e:
        print(f"[voice] edge-tts failed ({e}), using espeak-ng fallback")

    # Fallback: espeak-ng -> wav -> mp3
    tmp_wav = out_mp3.replace(".mp3", "_tmp.wav")
    subprocess.run(
        ["espeak-ng", "-v", "en-us+m3", "-s", "155", "-a", "180",
         "-w", tmp_wav, clean],
        check=True, capture_output=True
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", tmp_wav, out_mp3, "-loglevel", "error"],
        check=True
    )
    os.remove(tmp_wav)
    return out_mp3
