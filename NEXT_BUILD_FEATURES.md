# Next Build — Default Features Checklist

**Status: DEFERRED — not building now.**
Lorenza, 2026-11-24 18:06 EST: *"We're not going to build it now but when we do make another build all of these changes will be implemented."*

When Lorenza says go, the next build implements **all** of the items below
automatically, by default — not optional, not a plugin, nothing she has to
turn on or ask for again. **Release gate: verify every item is present and
tested in the build. If any item is missing, the build is not complete.**

## Checklist

| # | Feature | Status at deferral |
|---|---------|--------------------|
| 1 | **Fluid lip-sync** driven by real speech-audio amplitude envelope (smoothed, ~30fps eased interpolation, varied mouth shapes: closed / slightly open / wide / narrow-rounded for O,U / wider for A,E; natural closed rest pose, no snap shut) | DONE in v1.0.6 |
| 2 | **Natural voice** — OpenAI TTS (voice `nova`) as default, warm and natural rate/pitch; pyttsx3/SAPI only as fallback, never the default robotic voice | DONE in v1.0.6 |
| 3 | **Full avatar expressions matching Muse** — bob, blink, look-around, nod, mouth moves fluidly while speaking (not a single hole opening/closing) | DONE in v1.0.6 |
| 4 | **Thread-safety / no stuck thinking** — main-thread `_ui_queue`, `busy` always clears, 120s watchdog that auto-resets a stuck THINKING state with a visible timeout message | DONE in v1.0.3+ (Windows). **Mac gap CLOSED in v1.0.8-mac (in progress, uncommitted 2026-11-24):** 120s watchdog in `_tick_clock`, `_ui_queue` + `_post_ui` for `_ask` reply delivery, `busy` clears on every `_ask`/`_typewriter` exit path, visible "Timed out — I got stuck thinking, please try again" message, logged to `oracle-gui.log`. Untested on a real Mac. Follow-up (not a release gate): migrate the remaining `root.after(0, ...)` worker call sites to `_post_ui`. |
| 5 | **Always-listening, no wake word** — mic open, responds to Lorenza speaking directly | DONE (verified in source 2026-11-24; in v1.0.6). **Mac gap fixed in v1.0.8-mac:** Mac GUI previously defaulted `always_listen=False` with no auto-start; now defaults ON and starts listening at launch, parity with Windows. Untested on a real Mac. |
| 6 | **Camera open fix — EMEET PIXY Dual-Camera AI PTZ 4K** — fix the "can't grab frames" / -2147483638 (0x8000000A) failure: enumerate indexes 0–3 × backends DSHOW/MSMF/ANY, resolution fallback, a candidate counts only if a real frame is read; clear on-screen message if in use | DONE in v1.0.6 — PIXY is on **index 1 at 1280×720** (index 0 opens but returns no frames) |
| 7 | **Camera auto-tracking** — detect a person in frame, keep them centred, drive PTZ (pan/tilt, zoom where supported) continuously to follow movement on its own; NOT only manual tilt/pan on command. Use the PIXY's own AI tracking where exposed (SDK / UVC PTZ controls / vendor API first); fall back to software tracking (person detection + frame-centre error → PTZ commands, smoothed, no jitter/hunt). Dead zone so small movements don't cause constant panning; re-acquire after the person leaves and returns; stop safely if the camera is lost (never spin, never crash on a grab failure). On-screen Auto-Track ON/OFF toggle (default ON when camera is on and a person is in view); "track me / track this person" voice command. Tracking data stays local on her PC. **Verify live: a person walks across the room, camera follows and keeps them in frame. Do not claim it works until that live test passes.** | **IMPLEMENTED in code (v1.0.8-mac, live Mac test pending)** — `tracking.py` (new `AutoTracker`: OpenCV-only HOG people detector + Haar face/full-body cascades, motion fallback; dead zone 0.06, exponential smoothing 0.35, max 1 PTZ step per 0.5s, hold >3s with no person, gentle return to centre >15s, camera-lost = hold still, no crash; UVC PTZ via `CameraController.ptz()` first, digital crop-centre/zoom fallback when UVC is ignored) wired into `camera.py` `Watcher` (auto-track default ON, `track me` hook, `last_tracked_box`/`last_identified_name`/`last_confidence` exposed) and `gui.py` (Auto-Track ON/OFF toggle + tracked-person status line + "track me"/"stop tracking" voice commands). NOTE: requires opencv-python 4.11 — 5.x removed HOG/CascadeClassifier, so requirements.txt now pins `opencv-python==4.11.0.86`. **Live test (Mac + PIXY, do on a real Mac):** start camera watch, walk slowly across the room — camera/digital framing must follow and keep you in frame; walk out of frame and back — it must re-acquire, not hunt; unplug the camera mid-track — it must hold still and report "camera lost", not crash or spin. |
| 8 | **Manual tilt/pan on command** still available alongside auto-track | **IMPLEMENTED in code (v1.0.8-mac, live Mac test pending)** — existing Pan/Tilt/Zoom buttons in `gui.py` (`camera_ptz`) unchanged and still work alongside auto-track; auto-track can be toggled OFF and manual PTZ used instead. Same live Mac test as item 7: with Auto-Track OFF, the Pan/Tilt/Zoom buttons must still move framing (UVC if the PIXY accepts it, digital crop otherwise). |
| 9 | **Local face-feature recognition** — no cloud service, no outside database, no face data sent anywhere. Local library on her PC (e.g. OpenCV / face_recognition / InsightFace — pick one that actually runs on Windows with RTX 4080 Super / 64GB and verify live). Detect a face, extract its feature embedding, match against stored local profiles, identify who it is ("that's Lorenza", "that's Asia", …) and store that identity in Oracle's OWN local memory so it remembers people over time and improves matching. Learning flow: unfamiliar face seen repeatedly → ask Lorenza who it is (voice / on screen) → save name + face profile locally. Known face → greet/identify without asking again. Never auto-label when unsure — show a confidence and ask. Works with auto-tracking: as the camera follows a person, it also identifies them. Privacy per her standing rule (personal PC, her home): learning is automatic, no consent dialog; data stored LOCAL ONLY, never uploaded, never in GitHub/email/logs. She can view and delete a stored face profile. **Verify live: enrol Lorenza, have her leave and return, confirm Oracle identifies her correctly. Report library, enrolment steps, match accuracy, storage location. Do not claim it works until that live test passes.** | **IMPLEMENTED in code (v1.0.8-mac, live Mac test pending)** — `face_profiles.py` (new). Library: `face_recognition` (128-d embeddings, threshold 0.6) IF installed, otherwise OpenCV-only fallback — Haar face, aligned 128×128 grayscale crop, normalised feature (HOG gradient orientations + pixel vector + histogram), cosine-distance matching, conservative threshold 0.08 (measured on synthetic faces: same person 0.034, different people 0.109/0.242 — live Mac test must confirm the threshold on real faces); below threshold always returns "unknown", never a guessed name. Profiles in local `faces/<name>/` (profile.json + face crop JPG + vector .npy, never in the repo — `faces/` added to .gitignore; embeddings never logged). Functions: `enrol(name, frame)`, `identify(frame)` → (name\|None, confidence, box), `list_profiles()`, `delete_profile(name)`, plus `UnknownTracker` (repeated unknown face → GUI/watcher prompts to enrol). Wired into `camera.py` `Watcher` (identifies ~once/sec while tracking; exposes `last_identified_name`/`last_confidence`) and `gui.py` (tracked-person status line, "who is that" + "enrol this person as <name>" voice commands, "Enroll face (camera)" button). **Live test (Mac + PIXY, do on a real Mac):** 1) Start camera watch, face the camera, tap "Enroll face (camera)" and enrol as Lorenza. 2) Leave the room and return — Oracle must identify her by name with a confidence shown in the GUI. 3) Have someone NOT enrolled face the camera — Oracle must say "unknown person", never a wrong name. Report match accuracy + storage location (`faces/` next to Oracle.app). |
| 10 | **Left-side API key swap UI** — "API Key / Change API Key" clearly visible on the LEFT side of the main screen on first open, no menu digging; masked (password-style) entry with Save/Cancel; saving validates with a quick OpenAI test call, updates the User env var `OPENAI_API_KEY` on Windows, active immediately; clear "Key updated" / "Key invalid" message; existing key NEVER shown in plain text (only `SET • ****…last 4`); never written into source/GitHub/logs/email | DONE in v1.0.6 |
| 11 | **Minimize-to-avatar-only mode** — minimizing hides the main GUI and leaves a frameless/transparent, draggable, always-on-top avatar alone on the desktop, still listening/talking, mouth animating; click avatar (or Restore / right-click) to restore the full GUI; full GUI remains the default on open | DONE in v1.0.6 |
| 12 | **Muse-level conversational competency** as the benchmark (observable behaviour, NOT Muse source code — that is proprietary and unavailable): natural back-and-forth, remembers context, asks one clear question when info is missing, does not repeat answered questions, admits when unverified, follows through. Replies written to be spoken naturally (conversational, contractions, varied sentence length, natural pauses, no stiff list-reading). Test with a REAL multi-turn conversation on the PC. | DONE in v1.0.6 (Windows `agent.py` PERSONALITY). **Mac gap CLOSED in v1.0.8-mac (in progress, uncommitted 2026-11-24):** Mac `agent.py` PERSONALITY ported from the Windows spoken style — replies written to be heard not read, contractions, varied sentence length, natural pauses, never read out formatting, no bullet lists/headings/markdown/numbered lists spoken aloud, points as flowing sentences, don't spell out URLs/paths/symbols character by character — plus one Mac line (runs on macOS, not Windows). `gui.py` builds its system prompt from the same `PERSONALITY`, so GUI and CLI agent are consistent. Untested on a real Mac. |
| 13 | **AI/ML design + hardware tuning** — `AI_DESIGN.md` and `HARDWARE.md`: LLM reasoning with tool calling, multi-turn context with summarising, persistent memory, local-only voice/face learning, speech/vision, self-improvement that explains and waits for a yes, timeouts/watchdogs; tuned for **Ryzen 9 9950X3D / RTX 4080 Super (16GB VRAM, CUDA) / 64GB RAM** (NOT 128 — she removed two sticks) | DONE in v1.0.6 (Windows hardware). **Mac note:** the Mac `HARDWARE.md` was missing from the Mac repo until v1.0.8-mac (in progress) — added then, adapted for Mac. The Ryzen / RTX 4080 Super / 64 GB tuning in this row is the **Windows PC's** hardware, NOT the Mac's: the Mac doc states plainly that Mac tuning is the Mac's own CPU/GPU, with no RTX 4080 Super and no CUDA on a Mac. |
| 14 | **Muse conversation memory import** — Oracle inherits what Muse did with her on the PC: import path for Muse chat exports (.md/.json/.txt) into Oracle's persistent memory (deduped, dated, sourced); startup auto-import from a `memory_import/` folder; MEMORY card in the left deck (Import / What do you remember?); imported memory prepended to every reply's system prompt so Oracle can reference it naturally ("you told Muse on Nov 20 that…") and continue those open threads. **Muse-to-Oracle sharing via the private Tailscale/SSH tunnel is explicitly authorized by Lorenza 2026-11-24** — scope is Muse→Oracle only, local on her PC; never GitHub, email to anyone but Lorenza, or any public place. Imported memory stays local; log imports without credential values. Transfer the seed only via the SSH tunnel, never GitHub/email. | Code DONE in v1.0.7 (see State below). Seed file: `~/workspace/oracle-memory-seed/muse-memory-seed.md` (85 facts, 15 OPEN, no key values) — **not in any repo, not emailed** |
| 15 | **Job-hunting auto-submit** — submit applications on its own (fill the form, press submit, push through every time a site is NOT blocking it, without asking first); stop and hand to Lorenza only if actually blocked (CAPTCHA, sign-in code/2FA, anti-bot block, step needing a human). Follow through to the employer's own site when Indeed/another job site redirects there. If an account is required, create a username/password, saved locally only, distinct per site, recorded where she can see it, AND opened in Notepad left up on the desktop (`~/Desktop/Oracle-Accounts.txt`, appended not overwritten). | DONE in v1.0.6 (per build record — re-verify at next release) |
| 16 | **Windows/Mac parity** — everything built for one version must also be in the other, same capabilities on both | Ongoing rule. Known Mac gaps to close: items 4 and 12 above; Mac builds are NOT tested on a real Mac — state that plainly |

## State at deferral (2026-11-24 ~18:06 EST)

- **v1.0.6 is the last released/installed version** (Windows installed at `C:\Oracle`, launch-tested; Mac arm64 + Intel released, untested on a real Mac).
- **v1.0.7 (memory import) was committed and tagged before this stop arrived**
  (Windows commit `d574f49`, tag `v1.0.7`; Mac commit `7093689`, tag `v1.0.7-mac`,
  Intel merge `bbc5095`, tag `v1.0.7-intel`; pushes completed ~18:03 EST).
  GitHub Actions: Windows run 45506575577 **success**; Mac arm64 run 45506589976
  **success**; Mac Intel run 45506593394 was still in progress at the stop.
  **No GitHub release was created, no email was sent, nothing was installed
  on the PC, and the source GUI was not restarted.** The v1.0.7 code is on
  GitHub only as commits/tags; it is NOT a release and NOT on her PC.
- **v1.0.8-mac in progress (uncommitted, 2026-11-24 ~18:15 EST):** the
  two known Mac gaps are closed in source, from base v1.0.7-mac
  (commit `7093689`):
  - Item 4 — 120s watchdog + main-thread `_ui_queue` + `busy` always
    clears, ported from Windows into Mac `gui.py` (watchdog message:
    "Timed out — I got stuck thinking, please try again", logged to
    `oracle-gui.log`).
  - Item 12 — spoken-style `PERSONALITY` ported from Windows
    `agent.py` into Mac `agent.py` (macOS line added; `gui.py` uses
    the same `PERSONALITY`, so GUI and CLI stay consistent).
  - Mac `HARDWARE.md` created (was missing from the Mac repo);
    `AI_DESIGN.md` §7 watchdog note updated for the Mac port.
  - **Not committed, not tagged, not built, not released, not
    emailed, not installed, and not tested on a real Mac.** Items 7,
    8, 9 (auto-track, manual PTZ, local face recognition) are still
    NOT YET BUILT and remain deferred.
- **The PC was left exactly as it was** — nothing uninstalled, nothing
  installed, no GUI restarted in this session.
- **ElevenLabs note (for a future voice decision, only if Lorenza asks):**
  `ELEVENLABS_API_KEY` exists as a User env var on her PC (51 chars, value
  never read) but **no Oracle code uses it** — v1.0.5/v1.0.6 use OpenAI TTS.
  Do not treat it as in-use.

## Dictation / STT fix — done in source 2026-11-24 ~18:22 EST (after deferral)

Same fix as Windows (mirrored in Mac `voice.py`): OpenAI Whisper API
(`whisper-1`) primary, Google fallback, explicit mic pick, calibrate
once, silence gate. Verified on the Windows PC only — Mac side is
code-only, NOT tested on a real Mac. See Windows checklist for test
results. Still to do: Lorenza speaking test sentences directly to
the PC.

## When the next build starts

1. Start from v1.0.7 as the base (memory import already in).
2. Implement items 7, 8, 9 (auto-track, manual PTZ, local face recognition)
   in source on the PC first, verify live, then fold into the package builds.
3. Close the Mac gaps in items 4 and 12.
4. Re-verify every DONE item above in the new build — a regression in any
   item fails the release gate.
5. Then commit, tag, build via Actions, verify SHAs, release, email
   (install link + source separately, Lorenza only for source), install on
   the PC, and launch-test in Session 1.
