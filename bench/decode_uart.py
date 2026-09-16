#!/usr/bin/env python
"""Decode a captured digital line offline, scanning baud rates and framings.

  python decode_uart.py captures/uart-.../digital.csv --channel 2

The Logic 2 analyzer must be told the baud and framing up front, so it will
happily "decode" garbage at the wrong settings and report parity errors. This
works the other way round: it tries many settings against the captured edges
and scores each by whether the STOP BIT lands high, which is what actually
tells you the framing is right.
"""
import argparse

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("csv")
ap.add_argument("--channel", type=int, default=2)
ap.add_argument("--bauds", type=int, nargs="+", default=None)
args = ap.parse_args()

r = np.genfromtxt(args.csv, delimiter=",", names=True, deletechars="",
                  replace_space="_")
cols = list(r.dtype.names)
t = r[cols[0]].astype(float)
col = next(c for c in cols[1:] if c.endswith(str(args.channel)))
v = r[col].astype(int)

# The CSV lists a row per transition; rebuild the piecewise-constant waveform.
keep = np.concatenate(([True], np.diff(v) != 0))
et, ev = t[keep], v[keep]


def level_at(x):
    i = np.searchsorted(et, x, side="right") - 1
    return ev[np.clip(i, 0, len(ev) - 1)]


STANDARD = [9600, 19200, 38400, 57600, 76800, 115200, 230400, 250000, 460800]
bauds = args.bauds or STANDARD


def decode(baud, parity, nbits=8):
    """Return (frames, ok, total) for one candidate setting."""
    bit = 1.0 / baud
    nframe = 1 + nbits + (1 if parity != "N" else 0) + 1
    frames, ok, total = [], 0, 0
    i = 0
    # walk transitions, treating each falling edge on an idle line as a start bit
    while i < len(et):
        if ev[i] != 0:
            i += 1
            continue
        start = et[i]
        # must be idle-high before the start bit
        if level_at(start - bit * 0.5) != 1:
            i += 1
            continue
        centres = start + bit * (np.arange(nframe) + 0.5)
        if centres[-1] > et[-1]:
            break
        bits = np.array([level_at(c) for c in centres])
        total += 1
        stop_ok = bits[-1] == 1
        data = bits[1:1 + nbits]
        byte = int("".join(str(b) for b in data[::-1]), 2)
        par_ok = True
        if parity != "N":
            want = data.sum() % 2
            pbit = bits[1 + nbits]
            par_ok = (pbit == want) if parity == "E" else (pbit != want)
        if stop_ok and par_ok:
            ok += 1
            frames.append((start, byte))
        # advance past this frame
        i = np.searchsorted(et, start + bit * nframe, side="left")
        i = max(i, 1) if i > 0 else 1
    return frames, ok, total


print(f"{col}: {len(et)} edges, {et[-1]-et[0]:.2f} s span\n")
print(f"{'baud':>8} {'framing':>8} {'frames':>8} {'valid':>8} {'rate':>7}")
print("-" * 44)
results = []
for b in bauds:
    for p in ("N", "E", "O"):
        fr, ok, tot = decode(b, p)
        if tot == 0:
            continue
        results.append((ok / tot, ok, tot, b, p, fr))
        print(f"{b:>8} {'8'+p+'1':>8} {tot:>8} {ok:>8} {ok/tot:>6.0%}")

# Rank by how many frames actually validated, not by percentage: a setting
# that finds one frame and validates it is not better evidence than one that
# finds nine and validates five. A short burst yields few frames at slow bauds
# purely because the burst is shorter than a frame, which says nothing.
MIN_FRAMES = 5
usable = [r for r in results if r[2] >= MIN_FRAMES]
usable.sort(key=lambda x: (-x[1], -x[0]))
if usable:
    rate, ok, tot, b, p, fr = usable[0]
    print(f"\nBest with >={MIN_FRAMES} frames: {b} baud 8{p}1 - "
          f"{ok}/{tot} valid ({rate:.0%})")
elif results:
    print(f"\nNo setting produced {MIN_FRAMES}+ frames - too little traffic "
          f"to decide. Capture more.")
    rate, ok, tot, b, p, fr = max(results, key=lambda x: x[1])
    if fr:
        print(f"\nfirst bytes: " +
              " ".join(f"{byte:02X}" for _, byte in fr[:32]))
