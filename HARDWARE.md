# Oracle for Mac — Hardware (v1.0.8, in progress)

How Oracle is tuned to the Mac it runs on, and what it is NOT tuned to.
Concise: what each part is for, and what not to assume about it.

## The plain fact first

**There is no single verified Mac for this build.** Lorenza has no Mac
of her own — only a Windows PC — so no Mac hardware has been
verified live with Oracle yet, and the Mac builds are untested on a
real Mac. Oracle for Mac targets Apple Silicon (arm64) and Intel
(x86_64) Macs generally; the Mac it runs on is whatever Mac the user
installs it on.

**The Mac's hardware is that Mac's own CPU and GPU — NOT Lorenza's
Windows PC.** The Windows PC's parts (Ryzen 9 9950X3D, RTX 4080
Super 16 GB VRAM with CUDA, 64 GB DDR5-6000, 2 TB SSD + 3 TB HDD)
belong to the Windows build only (see the Windows `HARDWARE.md`).
Do not size, tune, or describe the Mac build as if it had them:
there is no RTX 4080 Super on a Mac, no CUDA on Apple Silicon, and
no 64 GB RAM guarantee. Anything in the Windows hardware doc does
not carry over unless this file says so.

## Hardware Oracle runs on (per Mac, not per spec sheet)

| Part | What Oracle assumes | Role in Oracle |
| --- | --- | --- |
| CPU | The Mac's own CPU — Apple Silicon (M-series) or Intel, whatever that Mac has | Parallel work: listening, camera, tools, UI |
| GPU | The Mac's own GPU — Apple Silicon integrated GPU, or that Intel Mac's GPU | Smooth avatar animation; local frame work. No CUDA, no NVIDIA assumptions |
| RAM | Whatever the Mac has — do not assume 64 GB | Context + memory cache, camera frame buffers, local models |
| Storage | The Mac's internal drive; memory lives next to Oracle.app, not inside the bundle | Program, models, workspace, prints, alerts |
| Camera | EMEET PIXY Dual-Camera AI PTZ 4K (USB UVC) | Watch, repair assistance |

## CPU: run things in parallel, keep the GUI on the main thread

- Whatever the Mac's CPU is, Oracle's shape is the same: **one
  thread each** for listening (speech recognition), camera watcher
  (motion detection), tool/LLM work, and the self-improvement check.
  None of those may block the GUI.
- **GUI on the main thread only.** Tkinter is not thread-safe: worker
  threads never call widget methods or `root.after()` directly — they
  put callables on the main-thread UI queue (`self._ui_queue`,
  drained every 50 ms by `_drain_ui_queue`; see `AI_DESIGN.md` §7).
  This is the rule that stops the "thinking forever" hang, and the
  120-second watchdog in `_tick_clock` is the backstop if a reply
  thread still sticks.
- Do not assume a slow serial step will be saved by the CPU. Split
  work across threads, or accept the wait and show it (busy indicator
  + watchdog, not silence).

## GPU: use what the Mac has, don't assume a discrete card

- **Local vision and frame work use the Mac's own GPU path**
  (Apple Silicon integrated GPU / Metal, or the Intel Mac's GPU
  through OpenCV). There is no CUDA path on macOS — do not write
  one, and do not leave the Mac's GPU idle while the CPU does vision
  work if an accelerated path is available.
- **Avatar animation should render smoothly** (blink, look-around,
  nod, mouth moving with speech) on any modern Mac; a choppy avatar
  means the rendering path is wrong, not that the hardware is short.
- The cloud LLM (OpenAI) and cloud TTS still do the thinking and
  speaking — the local GPU is for seeing and animating, not for
  replacing the brain.
- Keep one local vision model loaded at a time where possible, and
  release it when the watcher is off.

## RAM: size everything to fit the Mac it's on, no paging

- Oracle must fit comfortably in whatever RAM the Mac has — **do
  not size for 64 GB**, which is the Windows PC's figure, not the
  Mac's. Size these to fit together without paging:
  - **Context / memory cache:** the live conversation history plus
    the running summary (§2 of `AI_DESIGN.md`). Cap it; summarise
    older turns instead of keeping an unbounded history in RAM.
  - **Camera frame buffers:** 1080p frames for motion detection,
    plus the shared `latest_frame` for the GUI preview. 4K frames
    are much heavier — 1080p is the default for motion + vision
    for a reason. Do not hold multiple 4K frames in memory.
  - **Local models:** face-recognition / local vision models and
    any offline speech model. Keep one loaded at a time; unload
    when not in use.
- If Oracle ever starts paging on a Mac, something is sized wrong
  (unbounded history, unreleased frames, or two big models loaded
  at once) — fix the sizing, don't assume more RAM as the answer.
- Workspace files (memory, goals, tasks, tools, prints) are small
  JSON/text; they live next to Oracle.app and are not a RAM concern.

## Camera — EMEET PIXY (USB UVC, macOS)

- `camera.py` enumerates indexes 0–3 with backends
  `CAP_AVFOUNDATION` / `CAP_ANY` (macOS has no DirectShow/MSMF),
  trying resolutions 1920×1080 / 1280×720 / 640×480. A candidate
  counts only if a real frame is read — `isOpened()` alone can lie
  on macOS.
- **Do not carry the Windows finding over as a Mac fact:** on
  Lorenza's Windows PC the PIXY was on index 1 at 1280×720. The
  Mac's index must be found by enumeration on that Mac and recorded
  in `camera.py`'s `open_info` — verify live before claiming it.

## Storage

- The app bundle (`Oracle.app`) plus the folder containing it: the
  program and models live in the bundle; memory, workspace,
  `memory_import/`, prints, and `alerts/` live next to Oracle.app
  so they survive reinstalls.
- Do not write live data inside the bundle — that path is read-only
  in spirit and wiped on reinstall.

## What not to do

- Do not assume the Windows PC's CPU, GPU, VRAM, or RAM on a Mac.
- Do not run vision on the CPU while the Mac's GPU sits idle.
- Do not grow conversation history, frame buffers, or loaded models
  without a cap.
- Do not block the main (GUI) thread with listening, camera, LLM,
  or tool work. Ever. That is what the UI queue and the 120-second
  watchdog exist to prevent.
- No API key or credential is in this file. Keys live in the macOS
  Keychain on the user's Mac only (see `gui.py`).
