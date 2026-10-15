"""Synthesize the notification sound candidates (no samples, no licences).

    python3 scripts/notification_sounds.py OUT_DIR

The temple bell (1-temple-bell.wav) ships as
ui/android/app/src/main/res/raw/temple_bell.wav.
"""
import math, random, struct, wave, sys, os
SR = 44100
out = sys.argv[1]
random.seed(7)

def write(name, samples):
    peak = max(abs(s) for s in samples) or 1.0
    gain = 0.7 / peak  # about -3 dBFS
    n = len(samples); fade = int(0.08 * SR)
    with wave.open(os.path.join(out, name), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        frames = bytearray()
        for i, s in enumerate(samples):
            f = 1.0 if i < n - fade else (n - i) / fade
            frames += struct.pack("<h", int(max(-1, min(1, s * gain * f)) * 32767))
        w.writeframes(bytes(frames))

def partials(dur, parts, attack=0.002, start=0.0, total=None):
    """parts: (freq, amp, decay_seconds, detune_hz)"""
    total = total or dur
    n = int(total * SR); s0 = int(start * SR)
    buf = [0.0] * n
    for freq, amp, decay, det in parts:
        for k, f in ((0, freq), (1, freq + det)) if det else ((0, freq),):
            a = amp * (0.5 if det else 1.0)
            ph = random.random() * 2 * math.pi
            for i in range(s0, n):
                t = (i - s0) / SR
                env = (min(1.0, t / attack)) * math.exp(-t / decay)
                if env < 1e-4 and t > attack: break
                buf[i] += a * env * math.sin(2 * math.pi * f * t + ph)
    return buf

def add(*bufs):
    n = max(len(b) for b in bufs); out = [0.0] * n
    for b in bufs:
        for i, v in enumerate(b): out[i] += v
    return out

# 1. Temple bell (ghanta): bright strike, inharmonic church-bell ratios, long hum
f = 587.0
bell = partials(2.6, [(f*0.5, 0.35, 1.6, 0.6), (f, 1.0, 1.1, 0.9), (f*1.19, 0.5, 0.8, 0), (f*1.5, 0.45, 0.7, 0),
                      (f*2.0, 0.6, 0.5, 1.3), (f*2.51, 0.3, 0.35, 0), (f*3.01, 0.2, 0.25, 0), (f*4.07, 0.12, 0.15, 0)])
write("1-temple-bell.wav", bell)

# 2. Singing bowl: soft mallet, slow beating partials, calm long tail
f = 392.0
bowl = partials(3.0, [(f, 1.0, 1.6, 0.8), (f*2.71, 0.45, 1.0, 1.4), (f*5.15, 0.18, 0.6, 2.1), (f*8.4, 0.06, 0.3, 0)],
                attack=0.025)
write("2-singing-bowl.wav", bowl)

# 3. Manjira: two small cymbal 'ting-ting' strikes
def ting(start, total):
    base = 2350.0
    return partials(1.4, [(base, 1.0, 0.45, 3.0), (base*1.47, 0.6, 0.35, 0), (base*2.09, 0.4, 0.25, 4.0),
                          (base*2.73, 0.25, 0.18, 0), (base*3.6, 0.12, 0.12, 0)], attack=0.001, start=start, total=total)
manjira = add(ting(0.0, 1.5), [0.8 * v for v in ting(0.32, 1.5)])
write("3-manjira.wav", manjira)

# 4. Tanpura-style pluck: Sa then Pa, warm harmonic strings with a little jawari brightness
def string(f0, start, total, amp=1.0):
    parts = []
    for h in range(1, 14):
        a = amp * (1.0 / h) * (1.25 if h in (5, 6, 7) else 1.0)
        parts.append((f0 * h * (1 + 0.0004 * h), a, 1.3 / (1 + 0.18 * h), 0.4 if h == 1 else 0))
    return partials(total, parts, attack=0.004, start=start, total=total)
sa = 277.18 / 2 * 2  # C#4 region, a common male-voice Sa
tanpura = add(string(sa * 1.5, 0.0, 2.2, 0.8), string(sa, 0.38, 2.2))
write("4-tanpura-pluck.wav", tanpura)
print("ok")
