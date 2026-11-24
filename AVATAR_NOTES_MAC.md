# Oracle for macOS — Avatar Notes (v3)

## What was added
Lorenza's chosen Muse avatar is now the face of the Mac Oracle GUI.

- **Avatar:** the red-and-black anime avatar she picked for Muse on
  2026-11-24 — muscular anime male, long spiky black hair, blue eyes,
  light facial stubble, red gi with black trim, black undershirt,
  blue sash.
- **Source image:** `~/workspace/avatars/avatar-1795504357733091975-0.webp`
  (1600x1600). Converted with Pillow to PNG, resized to 512x512, and
  included as `assets/avatar.png` (also copied to top-level
  `avatar.png` — `gui.py` checks `assets/avatar.png` first, then
  `avatar.png`).
- **File changed:** only `gui.py` (plus docs and `requirements.txt`).
  `computer.py` was NOT touched — all job-hunting tools are unchanged.

## How it is animated (tkinter only, no video dependencies)
In `gui.py`, `_load_avatar()` loads the PNG with Pillow/`ImageTk`
and pre-builds two frames: a normal frame (260 px) and a blink frame
(the same image squashed vertically). `animate()` (every 50 ms) then:

- **Idle bob:** slow sine bob, same as the drawn head had.
- **Blink:** every ~62 frames the squashed blink frame is shown
  briefly instead of the normal frame.
- **Look-around:** the image shifts a few pixels left/right (and
  slightly up while thinking), following the existing phase.
- **Nod:** small vertical nod while speaking.
- **Mouth while speaking:** a dark oval overlay is drawn over the
  avatar's mouth area, opening/closing in time with the speaking
  phase (the typewriter / `speak_async` state). Idle shows the
  avatar's own mouth; thinking shows a flat line. The mouth
  position is estimated from this portrait (about 30% below the
  image centre) — see Limits below.
- **Aura / waveform:** the soft glow behind the avatar and the live
  waveform below it are unchanged.

## Fallback
If Pillow is missing, the file is missing, or the image fails to
load, `avatar_photo` stays `None` and `animate()` draws the original
Gideon-inspired vector head in code (blink, look-around, nod, talking
mouth) exactly as before. The GUI never crashes on a missing avatar.

## Setup on the Mac
`pip3 install -r requirements.txt` — Pillow is now listed there.
No other install step. Replace `assets/avatar.png` with any other
square portrait to change the face; restart `gui.py`.

## Testing done here (Linux VM, 2026-11-24)
- `python3 -m py_compile` on all 12 `.py` files in `oracle-mac/`:
  **all pass**.
- Smoke test under Xvfb (virtual display, no real Mac): GUI
  instantiated, `avatar_photo` and `avatar_blink_photo` both loaded,
  `animate()` ran cleanly in speaking, thinking, and idle modes, and
  the drawn-head fallback also animated cleanly after clearing the
  avatar. **No live GUI run on a real Mac was done here.**

## Still needs testing on a real Mac
- Open `python3 gui.py` on a Mac and watch the avatar: check the
  blink timing, that the mouth overlay actually sits on the avatar's
  mouth (not too high/low — adjust the `+38` offset in `animate()`
  if it is off), and that the bob/look-around feel natural.
- Confirm Pillow installs cleanly from `requirements.txt` on the
  Mac Python being used (python.org 3.12 recommended).
- This is a still image animated with transforms + an overlay, not
  a video avatar — it does not lip-sync to real phonemes, it moves
  in time with the speaking state.

## Hi-res update (2026-11-24, source only — not yet in a released package)

Lorenza: "make the Avatar look cleaner, it's not as high res as I would like."

**What was low-res before:** `assets/avatar.png` / `avatar.png` were
only **512x512**, and worse, they were the **whole full-body figure on a
white background** — at the 260 px display size the face itself was only
~70 px wide, and the white box showed on the dark console.

**What changed:**
- Asset replaced with the **head+shoulders crop (740x680, transparent
  background)** cut from the 1600x1600 source — same framing as Windows.
- `gui.py`: avatar render **260 → 420 px**, core canvas **300 → 480 px**,
  face re-centred (cy 138 → 210), aura scaled, waveform moved down,
  sharpening after resize (Sharpness 1.25, Contrast 1.05), mouth overlay
  scaled 1.615x with the same height clamp as Windows, avatar-only
  window enlarged to 440x400.
- Character design unchanged.

**Test:** Xvfb smoke test on Linux — GUI opens, avatar loads at 420x386,
blink frame 420x55, animation runs, no white box. **Not tested on a real
Mac** (same as all Mac work so far).
