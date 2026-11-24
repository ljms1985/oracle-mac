"""
Voice for Oracle on macOS - speak replies and listen continuously, no wake word.

Speech (v1.0.6 design, mirrors the Windows v1.0.6 design):
  * Default when OPENAI_API_KEY is set: OpenAI TTS (model tts-1,
    voice nova, response_format wav), played through PyAudio with a
    real RMS amplitude level (exponentially smoothed) that drives the
    avatar's mouth: speak_async(text, on_level=None, on_done=None),
    get_level(), is_speaking(), stop_speaking().
  * Fallback order on Mac: pyttsx3 / NSSpeech (Apple's built-in
    voices, offline), then the built-in `say` command (always
    present on a Mac, also offline). If the cloud voice is
    unavailable, Oracle still speaks - it just sounds less natural.
  * The API key is read from the environment and is NEVER logged or
    printed. Log lines say only whether a key is set, never its value.

Install on macOS:
  brew install portaudio   # only needed for PyAudio (microphone input
                           # and OpenAI TTS playback)
  pip3 install pyttsx3 SpeechRecognition PyAudio openai
  (If PyAudio still fails: brew install portaudio, then
   pip3 install --global-option=build_ext \
       --global-option="-I$(brew --prefix portaudio)/include" \
       --global-option="-L$(brew --prefix portaudio)/lib" PyAudio.
   Voice replies still work without PyAudio - only listening and the
   OpenAI TTS voice need it; the pyttsx3 / `say` fallbacks do not.)

IMPORTANT - always listening, read this:
  * "Always listening" here means: while this GUI is open and the
    toggle is ON, the microphone is active and speech is transcribed.
    Anyone nearby, a TV, or a podcast can trigger it. That is the
    trade-off of having NO wake word.
  * Transcription in this starter uses Google Speech Recognition over
    the internet by default (SpeechRecognition's recognize_google).
    That means audio snippets go to Google. If you do not want that,
    swap in an offline engine like Vosk - see the TODO in listen_once().
  * There is ALWAYS a visible LISTENING indicator in the GUI, and a
    button to pause listening instantly. Never run this hidden.
  * This is for YOUR own Mac, in YOUR own home, by your choice. Do not
    run always-listening in a shared / public space without telling
    people nearby.

Usage:
  from voice import speak, speak_async, listen_once
  speak("Hello, I'm Oracle.")
  speak_async("Hello, I'm Oracle.", on_level=update_mouth, on_done=done)
  text = listen_once(timeout=5)  # returns "" if nothing heard / error

NOTE: this port is NOT tested on a real Mac yet. The OpenAI TTS path,
the PyAudio playback path, and the fallback order are written to the
spec above but have only been syntax-checked, not run on macOS.
"""

import array
import io
import json
import math
import os
import threading
import urllib.request
import wave

# --- OpenAI TTS defaults (v1.0.6) ---------------------------------------
OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"
OPENAI_TTS_MODEL = os.environ.get("OPENAI_TTS_MODEL", "tts-1")
OPENAI_TTS_VOICE = os.environ.get("OPENAI_TTS_VOICE", "nova")
OPENAI_TTS_FORMAT = "wav"
_TTS_TIMEOUT_SEC = 30
_TTS_MAX_CHARS = 3500  # OpenAI TTS input limit is 4096; stay under it.

_tts_engine = None
_tts_lock = threading.Lock()

# Playback state, shared by speak_async / get_level / is_speaking /
# stop_speaking. Guarded by _state_lock; _level is the smoothed RMS
# amplitude in 0.0..1.0 (0.0 when not speaking).
_state_lock = threading.Lock()
_speaking = False
_level = 0.0
_stop_requested = threading.Event()
_say_proc = None  # subprocess.Popen for the `say` fallback, if running


def get_level():
    """Current smoothed speech amplitude, 0.0 (silent) to 1.0 (loud).

    Drives the avatar's mouth while OpenAI TTS is playing. Returns
    0.0 when nothing is speaking, and for the pyttsx3 / `say`
    fallbacks, which do not expose audio samples.
    """
    with _state_lock:
        return _level


def is_speaking():
    """True while a reply is being spoken (any backend)."""
    with _state_lock:
        return _speaking


def stop_speaking():
    """Stop the current reply as soon as possible, whatever backend
    is playing it. Safe to call when nothing is speaking."""
    global _say_proc
    _stop_requested.set()
    with _state_lock:
        speaking = _speaking
    if not speaking:
        return
    # PyAudio playback checks _stop_requested each chunk (see below).
    # pyttsx3: ask the engine to stop; best effort, never raises.
    try:
        if _tts_engine is not None:
            _tts_engine.stop()
    except Exception:
        pass
    # `say` fallback: terminate the subprocess.
    try:
        proc = _say_proc
        if proc is not None and proc.poll() is None:
            proc.terminate()
    except Exception:
        pass


def _set_speaking(value):
    global _speaking
    with _state_lock:
        _speaking = value
        if not value:
            global _level
            _level = 0.0


def _set_level(value):
    global _level
    with _state_lock:
        # Exponential smoothing: the mouth should move fluidly, not
        # jump with every chunk. 0.65 keeps the previous level, 0.35
        # takes the new chunk - responsive but not jittery.
        _level = 0.65 * _level + 0.35 * max(0.0, min(1.0, value))


def _rms_level(samples):
    """RMS amplitude of 16-bit PCM samples, normalised to 0.0..1.0."""
    if not samples:
        return 0.0
    total = 0
    for s in samples:
        total += s * s
    rms = math.sqrt(total / len(samples))
    # 16-bit full scale is 32768; real speech RMS sits at roughly
    # 0.03-0.15 of full scale, so raw RMS would leave the mouth
    # almost closed. A sqrt curve maps 0.15 -> 1.0, 0.05 -> ~0.58.
    raw = rms / 32768.0
    return max(0.0, min(1.0, math.sqrt(raw / 0.15))) if raw > 0 else 0.0


def _split_text(text):
    """Split long text into chunks under the TTS input limit, on
    sentence boundaries where possible, so a long reply still speaks
    in full instead of being rejected."""
    text = text.strip()
    if len(text) <= _TTS_MAX_CHARS:
        return [text]
    chunks, current = [], ""
    for sentence in text.replace("\n", " ").split(". "):
        piece = sentence if sentence.endswith(".") else sentence + "."
        if len(current) + len(piece) + 1 > _TTS_MAX_CHARS and current:
            chunks.append(current.strip())
            current = piece
        else:
            current = (current + " " + piece).strip()
    if current:
        chunks.append(current.strip())
    return [c for c in chunks if c]


def _fetch_openai_tts_wav(text):
    """Request one TTS chunk from OpenAI and return the WAV bytes.

    Raises on any failure (no key, network error, bad response).
    The key is used only in the Authorization header and is never
    logged - not here, not by callers.
    """
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    payload = {
        "model": OPENAI_TTS_MODEL,
        "input": text,
        "voice": OPENAI_TTS_VOICE,
        "response_format": OPENAI_TTS_FORMAT,
    }
    req = urllib.request.Request(
        OPENAI_TTS_URL,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=_TTS_TIMEOUT_SEC) as resp:
        return resp.read()


def _play_wav_bytes(wav_bytes, on_level=None):
    """Play WAV bytes through PyAudio, reporting a smoothed RMS level
    per chunk. Returns True if played to the end, False if stopped
    early (stop_speaking) or if playback failed."""
    try:
        import pyaudio
    except ImportError:
        print("[voice] PyAudio not installed - cannot play OpenAI TTS audio. "
              "brew install portaudio && pip3 install PyAudio")
        return False
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
            channels = wav.getnchannels()
            rate = wav.getframerate()
            sampwidth = wav.getsampwidth()
            frames = wav.readframes(wav.getnframes())
    except Exception as e:
        print(f"[voice] Could not parse TTS audio: {e}")
        return False
    if sampwidth != 2:
        # OpenAI returns 16-bit PCM WAV; anything else we cannot
        # level-meter reliably, so do not guess - fall back instead.
        print(f"[voice] Unexpected TTS sample width {sampwidth} (expected 2) - falling back.")
        return False
    pa = pyaudio.PyAudio()
    try:
        stream = pa.open(format=pyaudio.paInt16, channels=channels,
                         rate=rate, output=True)
    except Exception as e:
        print(f"[voice] Could not open audio output: {e}")
        pa.terminate()
        return False
    chunk_frames = 1024
    bytes_per_frame = channels * sampwidth
    played = True
    try:
        pos = 0
        total = len(frames)
        while pos < total:
            if _stop_requested.is_set():
                played = False
                break
            chunk = frames[pos:pos + chunk_frames * bytes_per_frame]
            pos += len(chunk)
            # RMS level from this chunk (16-bit samples, all channels).
            samples = array.array("h")
            samples.frombytes(chunk)
            level = _rms_level(samples)
            _set_level(level)
            if on_level is not None:
                try:
                    on_level(get_level())
                except Exception:
                    pass
            try:
                stream.write(chunk)
            except Exception as e:
                print(f"[voice] Audio playback failed: {e}")
                played = False
                break
    finally:
        try:
            stream.stop_stream()
            stream.close()
        except Exception:
            pass
        pa.terminate()
        _set_level(0.0)
    return played


def _speak_openai(text, on_level=None):
    """OpenAI TTS path. Returns True if the whole text was spoken
    this way, False if it could not be (caller falls back)."""
    if not os.environ.get("OPENAI_API_KEY", ""):
        return False
    try:
        for chunk in _split_text(text):
            if _stop_requested.is_set():
                return True  # Stopped on purpose, not a failure.
            wav_bytes = _fetch_openai_tts_wav(chunk)
            if not _play_wav_bytes(wav_bytes, on_level=on_level):
                return False
        return True
    except Exception as e:
        # Never log the key; the exception message here carries no key.
        print(f"[voice] OpenAI TTS failed ({e}) - falling back to local voice.")
        return False


def _speak_pyttsx3(text):
    """pyttsx3 on macOS -> NSSpeech driver (Apple voices, offline).
    Returns True if spoken, False if unavailable/failed."""
    global _tts_engine
    with _tts_lock:
        try:
            import pyttsx3
            if _tts_engine is None:
                try:
                    _tts_engine = pyttsx3.init(driverName="nsss")
                except Exception:
                    _tts_engine = pyttsx3.init()
                _tts_engine.setProperty("rate", 175)
            _tts_engine.say(text)
            _tts_engine.runAndWait()
            return True
        except Exception as e:
            print(f"[voice] pyttsx3 TTS failed ({e}) - falling back to macOS `say`.")
            return False


def _speak_say(text):
    """Built-in macOS `say` command (always present, offline).
    Returns True if spoken, False if it failed."""
    global _say_proc
    try:
        import subprocess
        _say_proc = subprocess.Popen(["say", "-r", "175", text])
        _say_proc.wait()
        return _say_proc.returncode == 0
    except Exception as e:
        print(f"[voice] TTS failed: {e} (install pyttsx3: pip3 install pyttsx3)")
        return False
    finally:
        _say_proc = None


def speak(text, on_level=None, on_done=None):
    """Speak text aloud on macOS (blocking - use speak_async from the GUI).

    Order: OpenAI TTS (tts-1 / nova, via PyAudio with RMS levels)
    when OPENAI_API_KEY is set, then pyttsx3/NSSpeech, then `say`.
    `on_level` is called with the smoothed amplitude (0.0..1.0) while
    OpenAI TTS plays; `on_done` is called once speaking finishes,
    whatever the backend or outcome.
    """
    if not text:
        if on_done is not None:
            try:
                on_done()
            except Exception:
                pass
        return
    _stop_requested.clear()
    _set_speaking(True)
    try:
        if not _speak_openai(text, on_level=on_level):
            if _stop_requested.is_set():
                return
            if not _speak_pyttsx3(text):
                if _stop_requested.is_set():
                    return
                _speak_say(text)
    finally:
        _set_speaking(False)
        if on_done is not None:
            try:
                on_done()
            except Exception:
                pass


def speak_async(text, on_level=None, on_done=None):
    """Speak in the background; the GUI stays responsive.

    Same arguments as speak(), plus: on_level(level) is called with
    the smoothed RMS amplitude while OpenAI TTS plays (drive the
    avatar's mouth with it), and on_done() is called when speaking
    finishes. Safe to call from the GUI thread.
    """
    threading.Thread(target=speak, args=(text,),
                     kwargs={"on_level": on_level, "on_done": on_done},
                     daemon=True).start()


def listen_once(timeout=5, phrase_time_limit=12):
    """
    Listen once from the default microphone and return transcribed text,
    or "" if nothing was heard or transcription failed.
    No wake word is checked - any intelligible speech is returned.
    """
    try:
        import speech_recognition as sr
    except ImportError:
        print("[voice] SpeechRecognition not installed. pip3 install SpeechRecognition PyAudio (and brew install portaudio first)")
        return ""
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True
    try:
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        # TODO: swap this for an offline recogniser (e.g. Vosk) if you
        # do not want audio sent to a cloud speech service.
        return r.recognize_google(audio)
    except Exception:
        # Includes WaitTimeoutError, UnknownValueError, RequestError.
        return ""
