"""Generate recitation audio for every mantra in the corpus.

Each mantra is read in one continuous Google Cloud Text-to-Speech take, with
line start times read from the pauses at each danda, laid over a soft shruti
box drone (18 dB under the voice), and written as mono MP3 plus a manifest of
line timings the app uses to highlight the text as it is recited.

Every mantra gets a male and a female track (Hawk's pick of voices), at
firebase-public/audio/mantras/<id>-<gender>.mp3, and the manifest keys each
mantra's tracks by gender.

Rerun everything (about 10 minutes; overwrites the MP3s and the manifest):
    python3 scripts/make_mantra_audio.py

Usage:
    python3 scripts/make_mantra_audio.py [--only id,id] [--gender male|female]
        [--voice NAME] [--drone-db DB] [--out DIR] [--manifest PATH]

Needs gcloud auth on a project with the Text-to-Speech API enabled, and the
lame encoder (brew install lame).
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "astrospace/core/vedic/mantra_corpus/mantras.json"
DEFAULT_OUT = ROOT / "firebase-public/audio/mantras"
DEFAULT_MANIFEST = ROOT / "astrospace/core/vedic/mantra_corpus/mantra_audio.json"

PROJECT = "gen-lang-client-0058562386"
VOICES = {"male": "hi-IN-Chirp3-HD-Fenrir", "female": "hi-IN-Chirp3-HD-Aoede"}
VOICE = VOICES["male"]
SPEAKING_RATE = 0.8
SR = 24000

INTRO_S = 3.0  # drone alone before the first line, so it settles first
LINE_GAP_S = 0.6  # only for the one-take-per-line fallback
OUTRO_S = 2.5
MUSIC_DB_BELOW_VOICE = 18.0

# Drone tonic per voice register: C#3 under a male voice, G#3 under a female one.
TONICS = {"male": 138.59, "female": 207.65}
TONIC_HZ = TONICS["male"]

LINE_SPLIT = re.compile(r"\s*[।॥]+\s*")


def split_lines(devanagari: str) -> list[str]:
    return [p.strip() for p in LINE_SPLIT.split(devanagari) if p.strip()]


# --- Text-to-Speech --------------------------------------------------------

_token: str | None = None


def _access_token() -> str:
    global _token
    if _token is None:
        _token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    return _token


def tts(text: str, attempts: int = 4) -> np.ndarray:
    """Speak text. The voices now and then return near-silence for a short
    input, so a take that is too quiet or too short is retried."""
    for _ in range(attempts):
        clip = _synthesize(text)
        voiced = np.count_nonzero(np.abs(clip) > 0.05) / SR
        if np.abs(clip).max() > 0.2 and voiced > 0.1:
            return clip
    raise RuntimeError(f"TTS returned silence for {text!r} with {VOICE}")


def _synthesize(text: str) -> np.ndarray:
    body = {
        "input": {"text": text},
        "voice": {"languageCode": "hi-IN", "name": VOICE},
        "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": SR, "speakingRate": SPEAKING_RATE},
    }
    req = urllib.request.Request(
        "https://texttospeech.googleapis.com/v1/text:synthesize",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {_access_token()}",
            "x-goog-user-project": PROJECT,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        audio = base64.b64decode(json.load(resp)["audioContent"])
    with wave.open(io.BytesIO(audio)) as w:
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return trim_silence(pcm.astype(np.float32) / 32768.0)


def trim_silence(x: np.ndarray, rel: float = 0.04, pad_s: float = 0.05) -> np.ndarray:
    """Cut leading and trailing silence or breath, relative to the take's peak."""
    idx = np.flatnonzero(np.abs(x) > max(0.01, rel * float(np.abs(x).max(initial=0))))
    if idx.size == 0:
        return x
    pad = int(pad_s * SR)
    return x[max(0, idx[0] - pad) : min(len(x), idx[-1] + pad)]


def line_starts(take: np.ndarray, n_lines: int) -> list[float] | None:
    """Seconds into a continuous take where each line begins, found from the
    pauses the voice leaves at each danda. None when the pauses don't line up."""
    if n_lines == 1:
        return [0.0]
    env = np.convolve(np.abs(take), np.ones(480) / 480, mode="same")
    quiet = env < 0.04 * env.max()
    gaps, k = [], 0
    while k < len(quiet):
        if quiet[k]:
            g = k
            while k < len(quiet) and quiet[k]:
                k += 1
            if (k - g) / SR >= 0.12 and g > 0 and k < len(quiet):
                gaps.append((k - g, k))
        k += 1
    if len(gaps) < n_lines - 1:
        return None
    ends = sorted(end for _, end in sorted(gaps, reverse=True)[: n_lines - 1])
    return [0.0] + [e / SR for e in ends]


# --- Shruti box drone --------------------------------------------------------


def reed(freq: float, n: int, rng: np.random.Generator) -> np.ndarray:
    """One reed. Its body sits in the harmonics between 100 Hz and 1 kHz, which
    a phone speaker can play; the fundamental alone would vanish on one."""
    t = np.arange(n) / SR
    phase = rng.uniform(0, 2 * np.pi, 16)
    out = np.zeros(n, dtype=np.float64)
    for k in range(1, 17):
        if k * freq > 2500:
            break
        out += np.sin(2 * np.pi * k * freq * t + phase[k - 1]) / k**1.3
    return out


def drone(seconds: float) -> np.ndarray:
    """Sa, Pa and upper Sa held together, with only a slow breath in volume."""
    n = int(seconds * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(3)
    sa = TONIC_HZ
    bed = np.zeros(n, dtype=np.float64)
    for f, amp in [(sa, 1.0), (sa * 1.5, 0.6), (sa * 2, 0.45)]:
        # two reeds per note, a hair apart, for the gentle reed beat
        bed += amp * (reed(f, n, rng) + reed(f * 1.0015, n, rng)) / 2
    bed *= 1 + 0.08 * np.sin(2 * np.pi * 0.12 * t)
    fade_in, fade_out = int(1.8 * SR), int(2.2 * SR)
    bed[:fade_in] *= np.linspace(0, 1, fade_in) ** 2
    bed[-fade_out:] *= np.linspace(1, 0, fade_out) ** 2
    return bed.astype(np.float32)


# --- Assembly ----------------------------------------------------------------


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x**2)) + 1e-9)


def render(mantra: dict) -> tuple[np.ndarray, list[dict]]:
    """One continuous take of the text as written (ॐ glyph and all: Hawk
    preferred how the voice says Om in context), with line times read from
    its pauses. Falls back to one take per line if the pauses don't line up."""
    lines = split_lines(mantra["devanagari"])
    take = tts(mantra["devanagari"])
    starts = line_starts(take, len(lines))
    if starts is None:
        clips = [tts(l + (" ॥" if i == len(lines) - 1 else " ।")) for i, l in enumerate(lines)]
        gap = np.zeros(int(LINE_GAP_S * SR), dtype=np.float32)
        starts, pos = [], 0
        for c in clips:
            starts.append(pos / SR)
            pos += len(c) + len(gap)
        take = np.concatenate([x for c in clips for x in (c, gap)])[: pos - len(gap)]
        print(f"  {mantra['id']}: pauses unclear, used one take per line", flush=True)
    timings = [{"text": l, "start": round(INTRO_S + s, 2)} for l, s in zip(lines, starts)]

    total = INTRO_S + len(take) / SR + OUTRO_S
    voice = np.zeros(int(total * SR), dtype=np.float32)
    s0 = int(INTRO_S * SR)
    voice[s0 : s0 + len(take)] = take
    voice *= 0.12 / rms(take)

    bed = drone(total)
    bed *= (0.12 * 10 ** (-MUSIC_DB_BELOW_VOICE / 20)) / rms(bed)
    mix = voice + bed[: len(voice)]
    mix /= max(1.0, float(np.max(np.abs(mix))) / 0.95)
    return mix, timings


def write_mp3(x: np.ndarray, path: Path) -> None:
    """Encode to a temp name and rename, so an interrupted run leaves no partial file."""
    partial = path.with_name(path.name + ".partial")
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        with wave.open(tmp.name, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
        subprocess.run(
            ["lame", "--quiet", "-m", "m", "-b", "64", tmp.name, str(partial)], check=True
        )
    os.replace(partial, path)


def main() -> int:
    global VOICE, TONIC_HZ, MUSIC_DB_BELOW_VOICE
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated mantra ids")
    ap.add_argument("--gender", choices=sorted(TONICS), help="default: both")
    ap.add_argument("--voice", help="override the voice for --gender")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--drone-db", type=float, default=MUSIC_DB_BELOW_VOICE, help="dB under the voice")
    args = ap.parse_args()
    MUSIC_DB_BELOW_VOICE = args.drone_db
    genders = [args.gender] if args.gender else sorted(TONICS, reverse=True)

    mantras = json.loads(CORPUS.read_text())["mantras"]
    wanted = set(args.only.split(",")) if args.only else None
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(args.manifest.read_text()) if args.manifest.exists() else {}

    for gender in genders:
        VOICE = args.voice if args.voice and args.gender else VOICES[gender]
        TONIC_HZ = TONICS[gender]
        for m in mantras:
            if not m.get("text_in_corpus") or not m.get("devanagari"):
                continue
            if wanted and m["id"] not in wanted:
                continue
            mix, lines = render(m)
            write_mp3(mix, args.out / f"{m['id']}-{gender}.mp3")
            seconds = len(mix) / SR
            manifest.setdefault(m["id"], {})[gender] = {
                "file": f"mantras/{m['id']}-{gender}.mp3",
                "voice": VOICE,
                "voice_start": INTRO_S,
                "voice_seconds": round(seconds - INTRO_S - OUTRO_S, 2),
                "seconds": round(seconds, 2),
                "lines": lines,
            }
            print(f"{gender} {m['id']}: {len(lines)} lines, {seconds:.1f}s", flush=True)

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.manifest.with_name(args.manifest.name + ".partial")
    tmp.write_text(json.dumps(dict(sorted(manifest.items())), ensure_ascii=False, indent=1) + "\n")
    os.replace(tmp, args.manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
