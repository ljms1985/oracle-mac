"""
Camera watch for Oracle - EMEET PIXY Dual-Camera AI PTZ 4K.

What we verified about the PIXY:
  * It is a USB UVC webcam (4K@30 / 1080p@60, Sony 1/2.55" sensor,
    73° FOV, 310° pan / 180° tilt, AI tracking up to ~6m, palm gesture).
  * Its PTZ, presets, and AI tracking are officially controlled by
    EMEET Studio software (and by the optional remote), not by a
    public EMEET SDK/API that we could find. That matters for code:
    there is NO guaranteed Python API to drive the PIXY motor directly.

So this module uses three layers, in order:
  1. Native AI tracking in the camera itself - leave EMEET Studio's
     AI tracking ON, and the PIXY will already pan/tilt to follow a
     person. Oracle does not need to fight it.
  2. UVC PTZ via OpenCV - many UVC PTZ cameras accept
     CAP_PROP_PAN / TILT / ZOOM through AVFoundation on macOS.
     We TRY this, report success/failure honestly, and fall back if
     the PIXY ignores it (which it may, since EMEET routes PTZ
     through EMEET Studio).
  3. Digital PTZ - crop + zoom inside a 1080p/4K frame. This always
     works for framing, even if the motor does not move. It is not
     the same as physically rotating, and the code says so.

Watch / abnormal alerts:
  * OpenCV motion detection (background subtraction) runs locally.
    Nothing is sent anywhere until motion passes a threshold AND
    the watcher is ARMED.
  * Only then is ONE snapshot sent to OpenAI Vision for a detailed
    description, and only if OPENAI_API_KEY is set and CAMERA_VISION=1.
    That means that snapshot goes to a cloud model - if you do not
    want that, set CAMERA_VISION=0 and you will get motion alerts
    with time + size, but no AI description.
  * An alert is then EMAILED via email_alerts.py (see email_alerts.py)
    with a detailed description, time, and where the snapshot was saved
    locally (alerts/). Alerts go by email, not SMS, per your choice.
    Email cannot carry a local photo file without a public URL, so the
    description is the message.
  * Cooldown (default 5 minutes) stops spam from one long event.
  * Privacy mode: stop the watcher and tilt the camera down if PTZ
    works, matching PIXY's own privacy tilt. The GUI shows a clear
    WATCHING / OFF indicator at all times.

Install on macOS:
  pip3 install opencv-python
  (Use the Mac build of EMEET Studio from EMEET's site for PTZ -
   there is no public EMEET SDK on macOS either.)
  (pip install pillow   # only needed for the GUI live preview)

Run alone for a test:
  python camera.py

Opening a camera (CameraController.open): enumerates indexes 0..3
with backends [CAP_AVFOUNDATION, CAP_ANY] (macOS has no
DirectShow/MSMF), trying resolutions 1920x1080 / 1280x720 /
640x480. A candidate only counts if a REAL frame is read -
isOpened() alone is not enough, it can lie on macOS. What worked
is recorded in controller.open_info (index, backend, width,
height); the last failure is in controller.last_error, which a
successful open clears. On macOS also check System Settings >
Privacy & Security > Camera and allow Terminal / your Python app
to use the camera - a denied permission looks like "no camera".
"""

import base64
import os
import threading
import time
from datetime import datetime
from pathlib import Path

# Auto-tracking + local face recognition (v1.0.8-mac, items 7/9).
# Both are OpenCV-only by default and degrade gracefully if OpenCV
# 5.x is installed (no Haar/HOG there) or face_recognition is absent.
try:
    from tracking import AutoTracker
except Exception:
    AutoTracker = None
try:
    import face_profiles as face_profiles
except Exception:
    face_profiles = None

BASE_DIR = Path(__file__).resolve().parent
ALERTS_DIR = BASE_DIR / "alerts"

# Same no-frame failure seen on Windows (-2147483638 / 0x8000000A):
# the camera "opens" but yields no frames.
NO_FRAME_ERROR = "-2147483638 / 0x8000000A"

CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", "0"))
ARMED = os.environ.get("CAMERA_ARMED", "1") == "1"
VISION_ENABLED = os.environ.get("CAMERA_VISION", "1") == "1"
MOTION_MIN_AREA = int(os.environ.get("CAMERA_MOTION_MIN_AREA", "5000"))
ALERT_COOLDOWN_SEC = int(os.environ.get("CAMERA_ALERT_COOLDOWN", "300"))

latest_frame = None  # shared with the GUI preview, if it is open
_latest_lock = threading.Lock()


def _cv2():
    try:
        import cv2
        return cv2
    except ImportError:
        raise RuntimeError("opencv-python is not installed. Run: pip install opencv-python")


class CameraController:
    def __init__(self, index=CAMERA_INDEX):
        self.index = index
        self.cap = None
        # What actually opened, and the last failure - see open().
        # open_info: {"index": int, "backend": str, "width": int,
        #             "height": int} once a camera is open, {} before.
        # last_error: "" after a successful open, otherwise a short
        # human-readable reason the last candidate failed.
        self.open_info = {}
        self.last_error = ""
        self.pan = 0
        self.tilt = 0
        self.zoom = 1.0
        # Digital crop centre (0.5 = middle of frame)
        self.crop_x = 0.5
        self.crop_y = 0.5

    def open(self, index=None):
        """Open a camera, robustly.

        Tries the requested index first (default: this controller's
        index, from CAMERA_INDEX), then every other index 0..3. For
        each index, tries backends [CAP_AVFOUNDATION, CAP_ANY], and
        for each backend tries resolutions 1920x1080, 1280x720,
        640x480. A candidate only counts if a real frame is read.
        On success sets self.index / self.cap / self.open_info and
        CLEARS self.last_error. On total failure releases everything,
        leaves self.cap None, records the reason in self.last_error,
        and raises RuntimeError with that reason.
        """
        cv2 = _cv2()
        wanted = self.index if index is None else index
        order = [wanted] + [i for i in range(4) if i != wanted]
        backends = []
        if hasattr(cv2, "CAP_AVFOUNDATION"):
            backends.append((cv2.CAP_AVFOUNDATION, "CAP_AVFOUNDATION"))
        backends.append((cv2.CAP_ANY, "CAP_ANY"))
        resolutions = [(1920, 1080), (1280, 720), (640, 480)]
        failures = []
        for idx in order:
            for backend, backend_name in backends:
                for width, height in resolutions:
                    cap = cv2.VideoCapture(idx, backend)
                    try:
                        if not cap.isOpened():
                            failures.append(f"index {idx} {backend_name} {width}x{height}: not opened")
                            cap.release()
                            continue
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                        ok, frame = cap.read()
                        if not ok or frame is None or frame.size == 0:
                            failures.append(f"index {idx} {backend_name} {width}x{height}: opened but no frame")
                            cap.release()
                            continue
                        # Real frame read - this candidate counts.
                        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or width)
                        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or height)
                        self.close()
                        self.index = idx
                        self.cap = cap
                        self.open_info = {"index": idx, "backend": backend_name,
                                          "width": actual_w, "height": actual_h}
                        self.last_error = ""
                        return True
                    except Exception as e:
                        failures.append(f"index {idx} {backend_name} {width}x{height}: {e}")
                        try:
                            cap.release()
                        except Exception:
                            pass
        self.cap = None
        self.open_info = {}
        detail = failures[-1] if failures else "no camera candidate tried"
        self.last_error = (
            f"Could not open any camera (indexes 0..3). Last failure: {detail}. "
            "Check it is plugged in and not in use by EMEET Studio / Zoom / OBS. "
            "On macOS also check System Settings > Privacy & Security > Camera "
            "and allow Terminal / your Python app to use the camera.")
        raise RuntimeError(self.last_error)

    def read(self):
        if self.cap is None:
            self.open()
        ok, frame = self.cap.read()
        if not ok:
            return None
        # Digital PTZ: crop around crop_x/crop_y at the current zoom.
        if self.zoom > 1.0:
            h, w = frame.shape[:2]
            cw, ch = int(w / self.zoom), int(h / self.zoom)
            cx, cy = int(self.crop_x * w), int(self.crop_y * h)
            x1 = max(0, min(w - cw, cx - cw // 2))
            y1 = max(0, min(h - ch, cy - ch // 2))
            import cv2 as _cv
            frame = _cv.resize(frame[y1:y1 + ch, x1:x1 + cw], (w, h))
        global latest_frame
        with _latest_lock:
            latest_frame = frame.copy()
        return frame

    def close(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.open_info = {}

    # -- PTZ: try UVC first, report honestly if it is ignored ------------
    def ptz(self, pan_delta=0, tilt_delta=0, zoom_delta=0.0):
        """Try physical PTZ. Returns a dict of what actually worked."""
        cv2 = _cv2()
        self.pan = max(-155, min(155, self.pan + pan_delta))
        self.tilt = max(-90, min(90, self.tilt + tilt_delta))
        self.zoom = max(1.0, min(1.5, self.zoom + zoom_delta))  # PIXY digital zoom is 1.5x
        result = {"pan": self.pan, "tilt": self.tilt, "zoom": self.zoom,
                  "uvc_pan_ok": False, "uvc_tilt_ok": False, "uvc_zoom_ok": False}
        if self.cap is not None:
            result["uvc_pan_ok"] = bool(self.cap.set(cv2.CAP_PROP_PAN, self.pan))
            result["uvc_tilt_ok"] = bool(self.cap.set(cv2.CAP_PROP_TILT, self.tilt))
            result["uvc_zoom_ok"] = bool(self.cap.set(cv2.CAP_PROP_ZOOM, self.zoom))
        # Digital fallback always applies (see read()).
        result["digital_zoom_applied"] = self.zoom
        result["note"] = ("If uvc_* are False, the PIXY ignored AVFoundation PTZ - "
                          "use EMEET Studio (Mac) presets / remote for motor control, "
                          "and Oracle will use digital framing + the camera's own AI tracking.")
        return result

    def privacy_mode(self):
        """Stop framing on people and tilt down if the motor allows it."""
        try:
            self.ptz(tilt_delta=-90)
        except Exception:
            pass
        return "Privacy mode: watcher should be stopped, camera tilted down if PTZ worked. Unplug the camera for full privacy if you want it guaranteed."


def describe_snapshot(image_path):
    """Send ONE snapshot to OpenAI Vision for a detailed description."""
    if not VISION_ENABLED:
        return "Vision analysis is off (CAMERA_VISION=0). Motion was detected, but no AI description was requested."
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return "Vision analysis skipped - OPENAI_API_KEY is not set."
    import json, urllib.request
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    payload = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": (
                    "Describe in detail what you see in this camera snapshot. "
                    "Say: how many people/animals, what they are doing, where in the room, "
                    "anything unusual, broken, fallen, or out of place, and whether this "
                    "looks like a normal everyday scene or something abnormal that a "
                    "homeowner should check. Be specific, do not guess identities.")},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ],
        }],
        "max_tokens": 300,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


# ----------------------------------------------------------------------
# Pan-and-describe (2026-11-24, Lorenza's request)
#   "When I ask what it sees I need it to describe everything it sees
#    as the camera pans from left to right and right to left."
#
# Before this, "what do you see" had no camera path at all in the GUI:
# the only vision use was a SINGLE still snapshot — describe_snapshot()
# for a motion alert, and RepairSession.look_at_board() for one board
# photo. Nothing panned, nothing combined several views.
#
# pan_and_describe() is a COMMANDED sweep, not auto-tracking:
#   1. Pause auto-tracking (if any is running — the caller passes a
#      pause_tracking callable; on Windows there is no tracker yet,
#      on Mac the Watcher has set_auto_track()). Resume it afterwards.
#   2. Pan left -> right in stops, capturing a frame at each stop.
#   3. Pan right -> left, capturing again at each stop (things move).
#   4. Describe each leg with OpenAI Vision, then merge the two legs
#      into ONE coherent spoken description, in left-to-right order.
#   5. Return the camera to exactly where it started (pan, zoom, crop).
#
# Physical pan: UVC CAP_PROP_PAN via controller.ptz(). The PIXY often
# ignores UVC PTZ (EMEET routes the motor through EMEET Studio),
# so if UVC pan reports False on the first move, the sweep falls back
# to DIGITAL pan: zoom 1.5x and slide the crop window left -> right
# across the wide frame. The result always says honestly which mode
# was used ("physical pan" vs "digital pan"), and if no frames can be
# read at all it says so plainly instead of inventing a description.
# Frames + description are saved under alerts/pan-YYYYMMDD-HHMMSS/.
# ----------------------------------------------------------------------

PAN_SWEEP_DEG = 60          # sweep +/- this many degrees from the start pan
PAN_SWEEP_STOPS = 5         # capture positions per leg (far left..far right)
PAN_SETTLE_SEC = 0.9        # wait after each move for the motor / frame to settle
PAN_VISION_MAX_WIDTH = 960  # frames are downscaled to this width for vision
PAN_POSITION_LABELS = ("far left", "left", "centre", "right", "far right")

# Phrases that mean "pan the camera and describe everything you see".
# Matched by gui.py _ask() (and the CLI) before the LLM is called.
# "Look at board" is NOT in here - that stays on the repair path.
PAN_DESCRIBE_PHRASES = (
    "what do you see", "describe what you see", "what can you see",
    "what do you see in the room", "describe the room",
    "look around", "look around the room", "scan the room",
    "pan and describe", "pan around", "pan the camera",
    "what's around", "what is around", "describe everything you see",
    "tell me what you see",
)


def is_pan_describe_request(text):
    """True if the user is asking Oracle to pan and describe the room."""
    if not text:
        return False
    low = " ".join(str(text).lower().split())
    return any(p in low for p in PAN_DESCRIBE_PHRASES)


def _encode_frame_b64(frame, max_width=PAN_VISION_MAX_WIDTH):
    """Downscale a frame and return it as a base64 JPEG string."""
    cv2 = _cv2()
    h, w = frame.shape[:2]
    if w > max_width:
        frame = cv2.resize(frame, (max_width, int(h * max_width / w)))
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
    if not ok:
        raise RuntimeError("could not JPEG-encode a camera frame")
    return base64.b64encode(buf.tobytes()).decode()


def _openai_chat(payload, timeout=90):
    """One OpenAI chat-completions call. Key comes from the env var only."""
    import json
    import urllib.request
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set on this PC.")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


def _vision_describe_leg(frames, leg_label):
    """Describe one sweep leg (list of (label, b64) frames) with Vision.

    One call, all frames of the leg at once, so the model sees the
    whole leg in order and can say what is where, left to right.
    """
    if not VISION_ENABLED:
        raise RuntimeError("Vision is off (CAMERA_VISION=0).")
    model = os.environ.get("OPENAI_VISION_MODEL",
                           os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    content = [{
        "type": "text",
        "text": (
            f"This is a camera sweep, {leg_label}, of one room. The frames "
            "are in sweep order. Describe EVERYTHING you can see across "
            "all of these frames, in detail and in left-to-right order: "
            "every person (what they are doing, what they are wearing), "
            "every animal, every piece of furniture, objects on tables "
            "and shelves, doors, windows, screens, and anything unusual, "
            "broken, fallen, or out of place. Say which part of the room "
            "(far left / left / centre / right / far right) each thing is "
            "in. Do not guess at identities of people. If a frame is dark "
            "or blurry, say so instead of inventing what is in it."),
    }]
    for label, b64 in frames:
        content.append({"type": "text", "text": f"Frame: {label}."})
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
    return _openai_chat({
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 700,
    })


def _vision_merge(leg_ltr, leg_rtl):
    """Merge the two legs' descriptions into one spoken description."""
    model = os.environ.get("OPENAI_VISION_MODEL",
                           os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    return _openai_chat({
        "model": model,
        "messages": [{
            "role": "user",
            "content": (
                "Merge these two descriptions of the same room into ONE "
                "clear spoken description, in left-to-right order, as if "
                "you are telling the homeowner what the camera saw while "
                "it panned left to right and then right to left. Keep "
                "every distinct object, person, and detail from both "
                "passes; drop exact duplicates. Mention anything that "
                "appeared in only one pass. Write it to be spoken aloud: "
                "natural sentences, contractions, no bullet lists, no "
                "headings. Start with a plain sentence like 'Panning "
                "across the room, from left to right, I can see...'.\n\n"
                f"LEFT-TO-RIGHT PASS:\n{leg_ltr}\n\n"
                f"RIGHT-TO-LEFT PASS:\n{leg_rtl}"),
        }],
        "max_tokens": 800,
    })


def pan_and_describe(controller=None, steps=PAN_SWEEP_STOPS,
                     sweep_deg=PAN_SWEEP_DEG, settle_sec=PAN_SETTLE_SEC,
                     progress=None, pause_tracking=None):
    """Pan left->right then right->left, describe everything seen.

    controller: a CameraController (opened by us if not given, or if
        not already open). If None, one is created and closed at the end.
    progress: optional fn(str) called with plain-English progress lines
        ("Panning left to right...", "Describing what I saw...").
    pause_tracking: optional fn() -> resume fn (or None). Called before
        the sweep and its result called afterwards, so auto-tracking
        does not fight the sweep. On Windows there is no tracker yet,
        so callers may pass None; on Mac pass watcher.set_auto_track.

    Returns a dict: {"ok": bool, "description": str, "pan_mode":
    "uvc"|"digital"|"none", "frames": [paths], "run_dir": str,
    "start_pan": float, "error": str|None}. On failure ok is False and
    "description" is a plain-English explanation, never invented.
    """
    def _say(msg):
        if progress is not None:
            try:
                progress(msg)
            except Exception:
                pass

    own_controller = controller is None
    if controller is None:
        controller = CameraController()
    resume_tracking = None
    if pause_tracking is not None:
        try:
            resume_tracking = pause_tracking()
        except Exception:
            resume_tracking = None
    run_dir = None
    try:
        try:
            if controller.cap is None:
                controller.open()
        except Exception as e:
            return {"ok": False,
                    "description": ("I could not open the camera to look "
                                    f"around: {e}"),
                    "pan_mode": "none", "frames": [], "run_dir": None,
                    "start_pan": getattr(controller, "pan", 0),
                    "error": str(e)}
        start_pan = getattr(controller, "pan", 0)
        start_zoom = getattr(controller, "zoom", 1.0)
        start_crop_x = getattr(controller, "crop_x", 0.5)

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = ALERTS_DIR / f"pan-{stamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # --- Decide physical vs digital pan with one probe move. ---
        _say("Panning the camera to the far left to start the sweep...")
        probe = controller.ptz(pan_delta=-sweep_deg)
        time.sleep(settle_sec)
        physical = bool(probe.get("uvc_pan_ok"))
        pan_mode = "uvc" if physical else "digital"
        if not physical:
            _say("The PIXY ignored the motor pan command, so I am sweeping "
                 "digitally across the wide frame instead.")
            # The probe move above already changed the controller's
            # *logical* pan even though the motor ignored it — reset it,
            # or every later PTZ move would start from a wrong position.
            controller.pan = start_pan
            try:
                controller.ptz(zoom_delta=0.5)  # zoom 1.0 -> 1.5x for cropping
            except Exception:
                pass

        positions = []
        for i in range(steps):
            frac = (i / (steps - 1)) if steps > 1 else 0.5
            positions.append(-sweep_deg + 2 * sweep_deg * frac)
        labels = PAN_POSITION_LABELS if steps == 5 else [
            f"position {i + 1} of {steps}" for i in range(steps)]

        def _capture_at(rel_pan, label, leg, idx):
            """Move to rel_pan (deg from start) and capture one frame."""
            if physical:
                # controller.pan is absolute; move to start_pan + rel_pan.
                target = start_pan + rel_pan
                controller.ptz(pan_delta=target - getattr(controller, "pan", 0))
            else:
                # Digital pan: slide the crop window across the frame.
                controller.crop_x = 0.5 + (rel_pan / sweep_deg) * 0.3 \
                    if sweep_deg else 0.5
            time.sleep(settle_sec)
            frame = controller.read()
            if frame is None:
                return None
            name = f"{leg}-{idx:02d}-{label.replace(' ', '-')}.jpg"
            path = run_dir / name
            cv2 = _cv2()
            if not cv2.imwrite(str(path), frame):
                return None
            return (label, path, frame)

        legs = {}
        for leg, leg_label, order in (
                ("ltr", "left to right", positions),
                ("rtl", "right to left", list(reversed(positions)))):
            _say(f"Panning {leg_label}...")
            shots = []
            # order is positions (ltr) or reversed(positions) (rtl); the
            # label comes from the position's index in `positions`.
            for idx, rel_pan in enumerate(order):
                label = labels[positions.index(rel_pan)]
                shot = _capture_at(rel_pan, label, leg, idx)
                if shot is not None:
                    shots.append(shot)
            legs[leg] = shots

        # --- Return the camera exactly where it started. ---
        try:
            if physical:
                controller.ptz(pan_delta=start_pan - getattr(controller, "pan", 0))
            else:
                # Digital mode never moved the motor; just fix the
                # logical pan the probe move polluted.
                controller.pan = start_pan
            controller.zoom = start_zoom
            controller.crop_x = start_crop_x
        except Exception:
            pass

        frames = [str(p) for leg in ("ltr", "rtl")
                  for (_l, p, _f) in legs[leg]]
        if not frames:
            return {"ok": False,
                    "description": ("The camera panned, but I could not "
                                    "grab any frames during the sweep — the "
                                    "camera may be in use by another app, or "
                                    f"it hit the no-frame error "
                                    f"({NO_FRAME_ERROR}). Try closing EMEET "
                                    "Studio, unplugging and replugging the "
                                    "PIXY, and asking again."),
                    "pan_mode": pan_mode, "frames": [], "run_dir": str(run_dir),
                    "start_pan": start_pan,
                    "error": "no frames captured during sweep"}

        _say("Describing everything I saw across the whole sweep...")
        try:
            leg_texts = {}
            for leg, leg_label in (("ltr", "left to right"),
                                   ("rtl", "right to left")):
                shots = legs[leg]
                if not shots:
                    leg_texts[leg] = "(no frames captured on this pass)"
                    continue
                encoded = [(label, _encode_frame_b64(frame))
                           for (label, _p, frame) in shots]
                leg_texts[leg] = _vision_describe_leg(encoded, leg_label)
            description = _vision_merge(leg_texts["ltr"], leg_texts["rtl"])
        except Exception as e:
            description = (
                "I panned across the room left to right and back, and saved "
                f"{len(frames)} frames under {run_dir}, but the vision "
                f"description failed: {e}. The frames are saved — I can "
                "try describing them again, or you can look at them.")
            (run_dir / "description.txt").write_text(description,
                                                     encoding="utf-8")
            return {"ok": False, "description": description,
                    "pan_mode": pan_mode, "frames": frames,
                    "run_dir": str(run_dir), "start_pan": start_pan,
                    "error": str(e)}

        if pan_mode == "digital":
            description = ("(The camera motor did not respond to the pan "
                           "command, so I swept the view digitally across "
                           "the wide frame instead — same room, same "
                           "left-to-right description.)\n\n" + description)
        (run_dir / "description.txt").write_text(description, encoding="utf-8")
        return {"ok": True, "description": description,
                "pan_mode": pan_mode, "frames": frames,
                "run_dir": str(run_dir), "start_pan": start_pan,
                "error": None}
    finally:
        if resume_tracking is not None:
            try:
                resume_tracking()
            except Exception:
                pass
        if own_controller:
            try:
                controller.close()
            except Exception:
                pass


def describe_what_you_see(controller=None, **kwargs):
    """Convenience alias: pan the camera and describe everything seen."""
    return pan_and_describe(controller=controller, **kwargs)



class Watcher:
    def __init__(self, controller=None, on_alert=None, on_track=None):
        self.controller = controller or CameraController()
        self.on_alert = on_alert  # function(text) - GUI log, etc.
        self.on_track = on_track  # function(status dict) - GUI track label
        self.running = False
        self.armed = ARMED
        self.thread = None
        self.last_alert = 0
        # --- Auto-track + face recognition (v1.0.8-mac) ---
        # Auto-track defaults ON when the camera is on (NEXT_BUILD
        # item 7). The GUI toggle flips self.auto_track via
        # set_auto_track(); the tracker itself is created here so
        # tracking works even without the GUI.
        self.tracker = AutoTracker(self.controller) if AutoTracker else None
        self.auto_track = True
        self.last_tracked_box = None    # (x, y, w, h) or None
        self.last_identified_name = None  # str, or None = unknown / no face
        self.last_confidence = 0.0
        self.last_track_status = "idle"  # tracking|holding|returning|...
        self.unknown_seen_count = 0     # repeats of the current unknown face
        self.frame_callback = None      # optional fn(frame, track_status)
        self._unknown_tracker = None
        if face_profiles is not None:
            try:
                self._unknown_tracker = face_profiles.UnknownTracker()
            except Exception:
                self._unknown_tracker = None
        self._last_frame = None
        self._frame_count = 0
        self._last_track_report = None
        self._last_track_report_at = 0.0
        self._camera_lost_reported = False

    def start(self):
        if self.running:
            return "Watcher is already running."
        self.controller.open()
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        return f"Watcher started. Armed={self.armed}. Camera index {self.controller.index}."

    def stop(self):
        self.running = False
        self.controller.close()
        return "Watcher stopped."

    # -- Auto-track / face recognition (v1.0.8-mac, items 7 + 9) --------
    def set_auto_track(self, enabled):
        """Turn auto-tracking on/off. Returns a short status string."""
        self.auto_track = bool(enabled)
        if self.tracker is not None:
            self.tracker.enabled = self.auto_track
            if not self.auto_track:
                self.tracker.stop()
                self.tracker.enabled = False
                self.last_tracked_box = None
                self.last_track_status = "disabled"
            else:
                self.tracker.enabled = True
                self.last_track_status = "idle"
        return f"Auto-Track: {'ON' if self.auto_track else 'OFF'}."

    def track_me(self, name=None):
        """'Track me' / 'track this person' voice command.

        With a name, the tracker prefers that person's face once
        face recognition knows them; without one it follows the
        largest person in frame. Also (re-)enables auto-track.
        """
        self.set_auto_track(True)
        if self.tracker is not None:
            self.tracker.set_target(name)
        if name:
            return f"Tracking {name} — I'll follow you and keep you centred."
        return "Tracking you — I'll follow the person in frame and keep them centred."

    def stop_tracking(self):
        """'Stop tracking' voice command: hold still, stay watching."""
        if self.tracker is not None:
            self.tracker.stop()
        self.auto_track = False
        self.last_track_status = "disabled"
        return "Auto-tracking is off. The camera will stay where it is."

    def enrol_current(self, name):
        """Enrol the face currently in frame under ``name``.

        Used by the GUI 'Enroll face' button and the 'enrol this
        person as <name>' voice command. Local only — see
        face_profiles.py.
        """
        if face_profiles is None:
            return "Face enrolment is unavailable (face_profiles.py missing)."
        frame = self._last_frame
        if frame is None:
            return "Enrol failed: the camera isn't running — start camera watch first."
        return face_profiles.enrol(name, frame)

    def track_status_text(self):
        """One line for the GUI status/log, e.g. 'Tracking: Lorenza (0.87)'."""
        if self.last_track_status == "camera_lost":
            return "Tracking: camera lost — check the PIXY is plugged in."
        if self.last_track_status in ("disabled",):
            return "Tracking: off"
        if self.last_tracked_box is None:
            if self.last_track_status == "returning":
                return "Tracking: no person in view — returning to centre."
            return "Tracking: no person in view."
        if self.last_identified_name:
            return (f"Tracking: {self.last_identified_name} "
                    f"(confidence {self.last_confidence:.2f})")
        if self.unknown_seen_count >= 5:
            return ("Tracking: unknown person — seen repeatedly. "
                    "Ask who it is, then enrol them.")
        return "Tracking: unknown person"

    def _report_track(self, status):
        """Call on_track when something changed (or every 2s), thread-safe
        for the GUI because the GUI wraps it in root.after(0, ...)."""
        if self.on_track is None:
            return
        key = (status.get("action"), self.last_identified_name,
               self.last_tracked_box is not None)
        now = time.time()
        if key != self._last_track_report or now - self._last_track_report_at > 2.0:
            self._last_track_report = key
            self._last_track_report_at = now
            try:
                self.on_track(dict(status))
            except Exception:
                pass

    def _loop(self):
        cv2 = _cv2()
        back_sub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)
        while self.running:
            frame = self.controller.read()
            if frame is None:
                # Camera lost: tracker must not move or crash.
                if self.tracker is not None and self.auto_track:
                    status = self.tracker.update(None)
                    self.last_track_status = status["action"]
                    self.last_tracked_box = None
                    self._report_track(status)
                if not self._camera_lost_reported:
                    self._camera_lost_reported = True
                    if self.on_alert:
                        try:
                            self.on_alert("Camera lost — no frame from the PIXY. "
                                          "Tracking is holding still; check the camera is plugged in.")
                        except Exception:
                            pass
                time.sleep(0.5)
                continue
            self._camera_lost_reported = False
            self._last_frame = frame
            self._frame_count += 1
            small = cv2.resize(frame, (640, 360))
            mask = back_sub.apply(small)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            motion_area = sum(cv2.contourArea(c) for c in contours if cv2.contourArea(c) > 500)
            # Largest moving blob, scaled back to full-frame pixels,
            # as the tracker's motion fallback (only used when no
            # person detector fires).
            motion_box = None
            if contours:
                big = max(contours, key=cv2.contourArea)
                if cv2.contourArea(big) > 500:
                    x, y, w, h = cv2.boundingRect(big)
                    fh, fw = frame.shape[:2]
                    motion_box = (int(x * fw / 640.0), int(y * fh / 360.0),
                                  int(w * fw / 640.0), int(h * fh / 360.0))
            # --- Auto-track + face identification (v1.0.8-mac) ---
            track_status = {"action": self.last_track_status,
                            "box": self.last_tracked_box,
                            "camera_lost": False,
                            "uvc_ignored": bool(self.tracker.uvc_ignored) if self.tracker else False,
                            "target_name": self.tracker.target_name if self.tracker else None}
            if self.tracker is not None and self.auto_track:
                # Face identification is the expensive step: run it
                # about once a second, not every frame.
                identified = []
                if face_profiles is not None and self._frame_count % 10 == 1:
                    try:
                        name, conf, box = face_profiles.identify(frame)
                        if box is not None:
                            identified = [(box, name, conf)]
                        if name:
                            self.last_identified_name = name
                            self.last_confidence = conf
                        elif box is not None:
                            # A face is in view but matches nobody:
                            # clear any previous identity, count repeats.
                            self.last_identified_name = None
                            self.last_confidence = 0.0
                            if self._unknown_tracker is not None:
                                is_repeat, count, _b = self._unknown_tracker.note_unknown(frame, box)
                                self.unknown_seen_count = count
                                if is_repeat and self.on_alert:
                                    try:
                                        self.on_alert(
                                            "Camera: an unfamiliar face has been seen repeatedly. "
                                            "Ask who it is, then say 'enrol this person as <name>'.")
                                    except Exception:
                                        pass
                    except Exception:
                        pass
                track_status = self.tracker.update(
                    frame, motion_box=motion_box, identified_faces=identified or None)
                self.last_tracked_box = track_status.get("box")
                self.last_track_status = track_status.get("action", "idle")
                if self.last_tracked_box is None:
                    self.last_identified_name = None
                    self.last_confidence = 0.0
                    self.unknown_seen_count = 0
                track_status["name"] = self.last_identified_name
                track_status["confidence"] = self.last_confidence
                track_status["unknown_seen_count"] = self.unknown_seen_count
                self._report_track(track_status)
            if self.frame_callback is not None:
                try:
                    self.frame_callback(frame, track_status)
                except Exception:
                    pass
            now = time.time()
            if (self.armed and motion_area > MOTION_MIN_AREA
                    and now - self.last_alert > ALERT_COOLDOWN_SEC):
                self.last_alert = now
                self._alert(frame, motion_area)
            time.sleep(0.1)

    def _alert(self, frame, motion_area):
        cv2 = _cv2()
        ALERTS_DIR.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = ALERTS_DIR / f"alert-{stamp}.jpg"
        cv2.imwrite(str(path), frame)
        try:
            description = describe_snapshot(path)
        except Exception as e:
            description = f"Vision analysis failed: {e}. Motion area was {int(motion_area)}."
        text = (f"Oracle camera alert - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Motion detected (area {int(motion_area)}).\n"
                f"What Oracle sees: {description}\n"
                f"Snapshot saved locally at: {path}\n"
                "This is from your own EMEET PIXY camera, watched by Oracle on your Mac.")
        if self.on_alert:
            try:
                self.on_alert(text)
            except Exception:
                pass
        # Email step - replaces SMS texting, per user choice.
        # This is an alert, not a request for permission to change code.
        try:
            from email_alerts import send_email
            sent = send_email("Oracle camera alert - motion detected", text)
            if not sent:
                print(f"[camera] Email alert not sent (SMTP not configured):\n{text}")
        except Exception as e:
            print(f"[camera] Email alert failed: {e}")
        print(text)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "pan":
        # python3 camera.py pan — full sweep test: pan left->right then
        # right->left, describe everything seen, return to start.
        result = pan_and_describe(progress=lambda m: print(f"[pan] {m}"))
        print(f"ok={result['ok']} pan_mode={result['pan_mode']} "
              f"frames={len(result['frames'])} run_dir={result['run_dir']}")
        print()
        print(result["description"])
        raise SystemExit(0 if result["ok"] else 1)
    print("Testing camera - press Ctrl+C to stop. Motion alerts will print here.")
    w = Watcher()
    print(w.start())
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(w.stop())
