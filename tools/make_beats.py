"""Sintetiza las bases incluidas en la app (originales, libres de derechos).
Uso: python tools/make_beats.py  ->  src/assets/beats/*.wav"""
import pathlib, wave
import numpy as np

SR = 22050
OUT = pathlib.Path(__file__).resolve().parents[1] / "src/assets/beats"
rng = np.random.default_rng(7)


def env(n, attack=0.002, decay=0.2):
    t = np.arange(n) / SR
    return np.minimum(t / attack, 1) * np.exp(-t / decay)


def kick(dur=0.45):
    n = int(SR * dur); t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, decay=0.18)


def snare(dur=0.3):
    n = int(SR * dur); t = np.arange(n) / SR
    noise = rng.uniform(-1, 1, n)
    noise = noise - np.convolve(noise, np.ones(4) / 4, "same")  # más brillante
    return 0.7 * noise * env(n, decay=0.09) + 0.4 * np.sin(2 * np.pi * 190 * t) * env(n, decay=0.05)


def hat(dur=0.06, open_=False):
    n = int(SR * (0.25 if open_ else dur))
    noise = rng.uniform(-1, 1, n)
    noise = noise - np.convolve(noise, np.ones(2) / 2, "same")
    return 0.25 * noise * env(n, decay=0.08 if open_ else 0.015)


def tone(freq, dur, decay=0.6, harmonics=(1, .5, .25), vol=.2):
    n = int(SR * dur); t = np.arange(n) / SR
    w = sum(a * np.sin(2 * np.pi * freq * (k + 1) * t) for k, a in enumerate(harmonics))
    return vol * w * env(n, attack=0.01, decay=decay)


def place(buf, s, pos):
    i = int(pos * SR)
    j = min(len(buf), i + len(s))
    buf[i:j] += s[: j - i]


def note(m):  # midi -> Hz
    return 440 * 2 ** ((m - 69) / 12)


def save(name, buf):
    buf = buf / (np.abs(buf).max() + 1e-9) * 0.9
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((buf * 32767).astype(np.int16).tobytes())


def boom_bap():
    bpm, bars = 90, 8
    beat = 60 / bpm
    buf = np.zeros(int(SR * beat * 4 * bars) + SR)
    chords = [[57, 60, 64], [53, 57, 60], [55, 59, 62], [52, 55, 59]]  # Am F G Em
    for b in range(bars):
        t0 = b * 4 * beat
        for k in (0, 1.75, 2.5):
            place(buf, kick(), t0 + k * beat)
        for k in (1, 3):
            place(buf, snare(), t0 + k * beat)
        for k in range(8):
            place(buf, hat(open_=(k == 7)), t0 + k * beat / 2 + (0.03 if k % 2 else 0))  # swing
        ch = chords[(b // 2) % 4]
        for m in ch:
            place(buf, tone(note(m), beat * 4, decay=1.2, vol=.07), t0)
        place(buf, tone(note(ch[0] - 24), beat * 1.5, decay=.4, harmonics=(1, .3), vol=.35), t0)
        place(buf, tone(note(ch[0] - 24), beat, decay=.3, harmonics=(1, .3), vol=.3), t0 + 2.5 * beat)
    return buf[: int(SR * beat * 4 * bars)]


def trap():
    bpm, bars = 140, 8
    beat = 60 / bpm
    buf = np.zeros(int(SR * beat * 4 * bars) + SR)
    roots = [45, 45, 41, 43]
    for b in range(bars):
        t0 = b * 4 * beat
        place(buf, snare(), t0 + 2 * beat)
        for k in (0, 0.75, 2.5):
            place(buf, kick(0.3), t0 + k * beat)
        for k in range(16):
            if k in (10, 11) and b % 2:
                place(buf, hat(), t0 + k * beat / 4); place(buf, hat(), t0 + (k + .5) * beat / 4)
            else:
                place(buf, hat(), t0 + k * beat / 4)
        r = roots[(b // 2) % 4]
        place(buf, tone(note(r - 12), beat * 2.5, decay=1.0, harmonics=(1, .15), vol=.5), t0)  # 808
        for i, m in enumerate([r + 12, r + 15, r + 19, r + 15]):
            place(buf, tone(note(m), beat * .9, decay=.25, harmonics=(1, .4, .2), vol=.06), t0 + i * beat)
    return buf[: int(SR * beat * 4 * bars)]


def lofi():
    bpm, bars = 80, 8
    beat = 60 / bpm
    buf = np.zeros(int(SR * beat * 4 * bars) + SR)
    chords = [[62, 65, 69, 72], [55, 59, 62, 65], [60, 64, 67, 71], [57, 60, 64, 67]]  # Dm9 G7 Cmaj7 Am7
    crackle = rng.uniform(-1, 1, len(buf)) * (rng.uniform(0, 1, len(buf)) > 0.9995) * 0.3
    buf += crackle
    for b in range(bars):
        t0 = b * 4 * beat
        for k in (0, 2.5):
            place(buf, kick() * .8, t0 + k * beat)
        for k in (1, 3):
            place(buf, snare() * .6, t0 + k * beat + 0.02)
        for k in range(8):
            place(buf, hat() * .7, t0 + k * beat / 2 + (0.05 if k % 2 else 0))
        for m in chords[b % 4]:
            place(buf, tone(note(m), beat * 4, decay=2.0, harmonics=(1, .2), vol=.06), t0 + 0.01)
        place(buf, tone(note(chords[b % 4][0] - 24), beat * 2, decay=.6, harmonics=(1, .2), vol=.3), t0)
    return buf[: int(SR * beat * 4 * bars)]


def drill():
    bpm, bars = 142, 8
    beat = 60 / bpm
    buf = np.zeros(int(SR * beat * 4 * bars) + SR)
    slide = [44, 44, 47, 42]
    for b in range(bars):
        t0 = b * 4 * beat
        for k in (1, 3.25) if b % 2 else (1.0, 3.0):
            place(buf, snare(), t0 + k * beat)
        for k in (0, 1.75, 2.5):
            place(buf, kick(0.25), t0 + k * beat)
        for k in (0, .75, 1.5, 2, 2.75, 3.25, 3.5):
            place(buf, hat(), t0 + k * beat)
        r = slide[(b // 2) % 4]
        place(buf, tone(note(r - 12), beat * 1.5, decay=.8, harmonics=(1, .25), vol=.5), t0)
        place(buf, tone(note(r - 10), beat * 1.2, decay=.6, harmonics=(1, .25), vol=.45), t0 + 2.5 * beat)
        for i, m in enumerate([r + 24, r + 23, r + 19]):
            place(buf, tone(note(m), beat * .7, decay=.3, harmonics=(1, .5), vol=.05), t0 + (i * 1.33) * beat)
    return buf[: int(SR * beat * 4 * bars)]


OUT.mkdir(parents=True, exist_ok=True)
save("Lo-fi 80 BPM.wav", lofi())
save("Drill 142 BPM.wav", drill())
save("Boom bap 90 BPM.wav", boom_bap())
save("Trap 140 BPM.wav", trap())
