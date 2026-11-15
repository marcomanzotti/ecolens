"""Original background music for the EcoLens demo, synthesised from scratch (no samples, no AI).

Ambient pad + arpeggio + sub bass + soft kick, A minor, 8 chords over 29.2 s. Writes music.wav.
"""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

SR = 48_000
DURATION = 29.2
CHORD_LEN = DURATION / 8
BEAT = CHORD_LEN / 8  # 8 beats per chord (about 131 BPM)
KICK_FROM, KICK_TO = 9.0, 26.2
ARP_FROM = 2.5

# (bass, pad notes) as MIDI numbers: Am9, Fmaj7, C(add9), G(add9), twice
CHORDS = [
    (45, [57, 60, 64, 71]), (41, [53, 57, 60, 64]),
    (48, [55, 60, 64, 67]), (43, [55, 59, 62, 69]),
] * 2

t_all = np.arange(int(SR * DURATION)) / SR


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def lowpass(x, cutoff):
    return sosfilt(butter(2, cutoff, fs=SR, output="sos"), x)


def saw(freq, t):
    return 2 * ((freq * t) % 1.0) - 1


def pad_layer():
    out = np.zeros_like(t_all)
    for i, (_, notes) in enumerate(CHORDS):
        start, length = i * CHORD_LEN, CHORD_LEN + 1.2
        n = int(length * SR)
        t = np.arange(n) / SR
        env = np.minimum(1, t / 0.9) * np.clip((length - t) / 1.2, 0, 1)
        voice = sum(saw(hz(m) * d, t) for m in notes for d in (0.996, 1.0, 1.004))
        voice = lowpass(voice, 1400) * env / (len(notes) * 3)
        a = int(start * SR)
        end = min(a + n, len(out))
        out[a:end] += voice[: end - a]
    return out


def arp_layer():
    out = np.zeros_like(t_all)
    step = BEAT / 2
    k = 0
    t_note = ARP_FROM
    while t_note < DURATION - 1.5:
        chord = CHORDS[int(t_note // CHORD_LEN)][1]
        pattern = [chord[0], chord[1], chord[2], chord[3], chord[2], chord[1]]
        midi = pattern[k % len(pattern)] + 12
        n = int(0.6 * SR)
        t = np.arange(n) / SR
        tone = np.sin(2 * np.pi * hz(midi) * t) + 0.3 * np.sin(4 * np.pi * hz(midi) * t)
        note = tone * np.exp(-t * 7) * np.minimum(1, t / 0.004)
        a = int(t_note * SR)
        end = min(a + n, len(out))
        out[a:end] += note[: end - a]
        t_note += step
        k += 1
    return out


def bass_layer():
    out = np.zeros_like(t_all)
    for i, (root, _) in enumerate(CHORDS):
        a, b = int(i * CHORD_LEN * SR), int((i + 1) * CHORD_LEN * SR)
        t = np.arange(b - a) / SR
        env = np.minimum(1, t / 0.3) * np.clip((CHORD_LEN - t) / 0.3, 0, 1)
        out[a:b] += np.sin(2 * np.pi * hz(root - 12) * t) * env
    return out


def kick_layer():
    out = np.zeros_like(t_all)
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    freq = 45 + 75 * np.exp(-t * 30)
    kick = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 9)
    beat = KICK_FROM
    while beat < KICK_TO:
        a = int(beat * SR)
        end = min(a + n, len(out))
        out[a:end] += kick[: end - a]
        beat += BEAT
    return out


def reverb(x, seconds=2.4, wet=0.35):
    rng = np.random.default_rng(7)
    n = int(seconds * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 3.2)
    ir = lowpass(ir, 5000)
    tail = fftconvolve(x, ir)[: len(x)]
    tail /= np.max(np.abs(tail)) + 1e-9
    return (1 - wet) * x / (np.max(np.abs(x)) + 1e-9) + wet * tail


def main():
    pad, arp, bass, kick = pad_layer(), arp_layer(), bass_layer(), kick_layer()
    music = reverb(0.55 * pad / np.max(np.abs(pad)) + 0.22 * arp / np.max(np.abs(arp)))
    music = music + 0.30 * bass / np.max(np.abs(bass)) + 0.38 * kick / np.max(np.abs(kick))
    fade_in = np.minimum(1, t_all / 0.6)
    fade_out = np.clip((DURATION - t_all) / 2.2, 0, 1)
    music *= fade_in * fade_out
    music = music / np.max(np.abs(music)) * 0.89  # about -1 dBFS peak
    stereo = np.stack([music, np.roll(music, int(0.012 * SR))], axis=1)
    wavfile.write("music.wav", SR, (stereo * 32767).astype(np.int16))
    print("music.wav", len(music) / SR, "s")


if __name__ == "__main__":
    main()
