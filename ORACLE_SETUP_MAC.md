# Oracle for macOS — Very Detailed Setup Guide

This guide gets the macOS Oracle agent up and running from scratch.
Read it in order. Do not skip Step 1, Step 2, or the first-run test in
Step 6 — those are where most setup problems come from.

Oracle here is the Python agent Lorenza built with Muse. It is NOT
Muse itself, and it is NOT truly sentient or conscious. It is a
friend-like agent with an OpenAI brain, its own workspace/computer,
voice, camera, GUI, self-correction, and tool-creation — running on
your own Mac.

This is the macOS version of the Windows agent. Same agent, same
features, same Gideon-inspired GUI — adapted where macOS differs:
Terminal instead of Command Prompt / PowerShell, `~/Oracle` instead
of `C:\Oracle`, `python3` / `pip3` instead of `python` / `pip`,
Homebrew for PortAudio, AVFoundation for the camera, launchd instead
of Task Scheduler, and System Settings for mic/camera permissions.
See `BUILD_NOTES_MAC.md` for the full Windows → Mac change list.

---

## What you are installing

Folder: `~/Oracle/` (after you unzip — see Step 3)

Key files:
- `agent.py` — the chat agent, personality, tool loop, self-correction
- `computer.py` — Oracle's own computer. Workspace, file/command
  tools, web search/fetch, its own Chromium browser, persistent memory,
  goals, and tasks. This is what makes it work like Muse.
- `gui.py` — futuristic dark-neon GUI with animated head, waveform,
  command deck, status pills, clock, theme switcher. The face is
  Lorenza's chosen Muse avatar image (assets/avatar.png, red-and-
  black anime) animated live — bob, blink, look-around, nod, mouth
  moves while speaking; falls back to the drawn head if the image
  is missing. Needs Pillow (`pip3 install Pillow`, in requirements.txt).
  See AVATAR_NOTES_MAC.md.
- `voice.py` — voice replies (pyttsx3 via Apple NSSpeech, with a
  built-in `say` fallback) and always-listening while the GUI is open
- `camera.py` — EMEET PIXY Dual-Camera AI PTZ 4K watching, motion alerts
  (OpenCV AVFoundation backend on macOS)
- `monitor.py` — self-improvement proposals: explains a change, asks
  first, backs up the old version, rolls back on failure
- `email_alerts.py` — alerts by EMAIL (not SMS), via Gmail SMTP
- `identity.py` — local-only voice/face learning, home Mac only
- `security.py` + `SECURITY_KNOWLEDGE.md` — pen-test / hacking knowledge,
  authorized targets only (systems you own or are authorized to test)
- `design3d.py` + `3D_KNOWLEDGE.md` — print-ready STL design, mm + inches
- `repair.py` — electronics / PCB repair partner, pro level
- `tools_generated/` — new tools Oracle writes for itself
- `backups/` — automatic backups before any overwrite
- `workspace/` — Oracle's own computer home, created on first run:
  `files/`, `downloads/`, `memory/`, `logs/`, `goals/`, `tasks/`,
  `browser-profile/`
- `install.sh` — one-command installer (see Step 2 note)
- `com.oracle.agent.plist` / `com.oracle.monitor.plist` — launchd jobs
  for starting Oracle at login and running the daily improvement check
- `oracle-mac.spec` — PyInstaller spec, for building a standalone
  `Oracle.app` on a Mac (see Step 7 note)

---

## Step 1 — Check your Mac (5 minutes)

You need:
- A Mac running macOS 13 Ventura or newer (Apple silicon or Intel)
- At least 4 GB free disk space (more is better for the browser + models)
- An internet connection
- An admin account on the Mac (you only need it once, to install
  Homebrew / Python)

Check your macOS version:
1. Apple menu (top left) > About This Mac.
2. If it says macOS 13 or newer, you are good. Older versions may
   still work, but Python 3.12 and the newest OpenCV expect 13+.

If you already have Python, skip to Step 2, but still check the version
in Step 2 — Oracle needs Python 3.10 or newer.

---

## Step 2 — Install Python and Homebrew (10–15 minutes, one time only)

### 2a. Homebrew (recommended — it makes the voice/microphone parts work)

Homebrew is a package manager for macOS. You need it for PortAudio
(the microphone library PyAudio depends on) and for `cmake`/`dlib`
if you later want face recognition.

1. Open Terminal: Spotlight (Cmd+Space), type `Terminal`, press Enter.
2. Paste this, press Enter, and follow the prompts (it will ask for
   your Mac password — typing it shows nothing on screen, that is normal):
   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
3. When it finishes, run the two lines it prints at the end (they add
   Homebrew to your shell — on Apple silicon they look like
   `echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc`
   and `eval "$(/opt/homebrew/bin/brew shellenv)"`).
4. Verify:
   ```
   brew --version
   ```
   You should see a Homebrew version number.

### 2b. Python

Option A — python.org (simplest, recommended):
1. Go to https://www.python.org/downloads/ in your browser.
2. Click Download Python (3.12 or newer is fine).
3. Run the installer and follow the prompts. The macOS installer
   puts `python3` on PATH for you — there is no "Add to PATH"
   checkbox to tick (that is a Windows installer step).
4. Verify in Terminal:
   ```
   python3 --version
   ```
   You should see something like `Python 3.12.x`.
   Also check pip:
   ```
   pip3 --version
   ```
   You should see a pip version number.

Option B — Homebrew Python (also fine):
```
brew install python@3.12
```
Then `python3 --version` should work. Note: if you use Homebrew
Python and later want the GUI, you may also need `brew install
python-tk` — the python.org installer already includes tkinter.

### 2c. Install the packages Oracle needs

In Terminal, run:
```
brew install portaudio
pip3 install openai pyttsx3 SpeechRecognition pyaudio opencv-python numpy trimesh
pip3 install playwright
playwright install chromium
```

Or, in one go from the Oracle folder (Step 3 first):
```
cd ~/Oracle
pip3 install -r requirements.txt
pip3 install playwright
playwright install chromium
```

Notes:
- `brew install portaudio` first is the macOS fix for PyAudio.
  If `pip3 install PyAudio` still fails, try:
  ```
  pip3 install --global-option=build_ext \
      --global-option="-I$(brew --prefix portaudio)/include" \
      --global-option="-L$(brew --prefix portaudio)/lib" PyAudio
  ```
  If voice still fails, Oracle will still work in text mode — voice is
  optional, text chat is not. Voice *replies* do not need PyAudio at
  all: they use pyttsx3 (Apple NSSpeech) and fall back to the built-in
  macOS `say` command.
- `playwright install chromium` downloads Oracle's own browser. This
  can take several minutes. Let it finish. Without it, Oracle can still
  use web search/fetch, but the real-browser tools will tell you
  Playwright is not installed instead of pretending to work.
- `openai` is needed even if you later switch to Ollama, because the
  default brain is OpenAI (see Step 4).
- Optional, for full face matching: `brew install cmake dlib`, then
  `pip3 install face_recognition`. It is a slow build. If it fails,
  Oracle falls back to OpenCV face detection + voice matching.

### 2d. Shortcut — install.sh

If you would rather not run the steps above one by one, the folder
includes `install.sh`. From Terminal:
```
cd ~/Oracle
bash install.sh
```
It creates `~/Oracle`, installs Homebrew packages and Python
requirements, and offers to install the launchd jobs from Step 7.
Read it first — it is a plain shell script, and it asks before
installing the launchd jobs. It does NOT set your OpenAI key for you
(Step 4 does that, by hand, so the key never goes in a file you share).

---

## Step 3 — Unzip Oracle to ~/Oracle

1. Download / save the zip file attached to the email (or from chat):
   `oracle-mac-full.zip`
2. Double-click it in Finder, or in Terminal:
   ```
   cd ~
   unzip oracle-mac-full.zip
   ```
   That creates `~/Oracle/` with the files directly inside it.
3. Open Finder and check you now have:
   ```
   ~/Oracle/agent.py
   ~/Oracle/computer.py
   ~/Oracle/gui.py
   ~/Oracle/voice.py
   ~/Oracle/camera.py
   ~/Oracle/monitor.py
   ~/Oracle/email_alerts.py
   ```
   If you see `~/Oracle/oracle-mac-full/agent.py` (a folder inside
   a folder), move everything up one level so `agent.py` is directly
   in `~/Oracle/`.

Do NOT put Oracle in a folder with spaces in a long path if you can
avoid it, and do NOT run it from inside the zip file — extract it first.

---

## Step 4 — Set your OpenAI key (do NOT paste it in chat)

Oracle's brain is OpenAI by default, model `gpt-4o-mini` (you can change
it later with the `OPENAI_MODEL` variable).

You need an OpenAI API key. Get one at https://platform.openai.com/
(sign in, API Keys, Create new secret key). Keep it private — never
paste it in chat, email, or a screenshot.

Set it permanently in your shell, so every Terminal and the GUI see it:
1. In Terminal, run (replace YOUR-KEY-HERE with your real key, no
   spaces around the `=`):
   ```
   echo 'export OPENAI_API_KEY=YOUR-KEY-HERE' >> ~/.zshrc
   source ~/.zshrc
   ```
2. **Close any open Terminal windows and open a fresh one** — old
   windows do not pick up the new variable.

Verify in a fresh Terminal window:
```
echo $OPENAI_API_KEY
```
You should see `sk-...` (the start of your key). If it is blank, the
variable was not saved, or you are in an old Terminal window.

For one Terminal session only (good for testing):
```
export OPENAI_API_KEY=YOUR-KEY-HERE
```

For apps launched from Finder / Spotlight (like the GUI, if you
launch it by double-clicking a launcher instead of from Terminal),
Terminal variables do not apply. Run once:
```
launchctl setenv OPENAI_API_KEY YOUR-KEY-HERE
```
That lasts until you restart your Mac. For a permanent Finder-wide
setting, the `launchd` plist in Step 7 includes the variable — edit
`com.oracle.agent.plist` and put your key there, or keep launching
Oracle from Terminal, which is the simplest reliable route.

Optional variables (same `~/.zshrc` process):
- `AGENT_NAME` — default is `Oracle`. Change it only if you want a
  different name.
- `OPENAI_MODEL` — default `gpt-4o-mini`. Use `gpt-4o` only if you
  want the larger, more expensive model.
- `LLM_PROVIDER` — leave this unset for OpenAI. Set it to `ollama`
  only if you want a local model instead (see Troubleshooting).
- `AGENT_AUTO_APPLY` — **leave this unset (OFF) to start.** OFF means
  Oracle asks you before running a command or loading a new tool it
  wrote. Set it to `1` only after you understand the risk, and
  destructive commands are still refused even then.

---

## Step 5 — Camera, email alerts, and voice (optional, in this order)

Do these AFTER the basic text agent works in Step 6. Do not try to
debug everything at once.

### 5a. Camera — EMEET PIXY Dual-Camera AI PTZ 4K
1. Plug the camera in via USB. macOS should recognise it as a webcam
   with no driver install. Test it in FaceTime or Photo Booth first —
   if it works there, Oracle can see it.
2. Install EMEET Studio for Mac from EMEET's site if you want PTZ
   control — there is no public EMEET SDK, so PTZ goes through
   EMEET Studio, UVC (AVFoundation), or digital crop fallback
   (see `camera.py`). On macOS, OpenCV opens the camera with the
   AVFoundation backend (`CAP_AVFOUNDATION`); UVC pan/tilt/zoom is
   tried first and honestly reported — if the PIXY ignores it, Oracle
   uses digital framing plus the camera's own AI tracking.
3. Grant camera permission: the first time Oracle opens the camera,
   macOS asks. Allow it in System Settings > Privacy & Security >
   Camera, for Terminal (and for your Python app, if it asks
   separately). If you deny it, the camera will not open — check
   that setting first.
4. In Oracle, camera watching is for YOUR home Mac only. It learns
   voices and faces locally in `identities/` — nothing is sent to an
   outside database.
5. You still need to tell Oracle what "abnormal" means for your room.
   Example: "Alert me if a person enters the room after 11pm, or if
   the workbench area changes while I'm away." Until you define it,
   it will ask.

### 5b. Email alerts (not SMS)
Oracle alerts by email, not texting.
1. In Gmail, turn on 2-Step Verification, then create an App Password:
   Google Account > Security > 2-Step Verification > App passwords.
   Name it `Oracle`. Copy the 16-character password.
2. In Oracle's email settings (`email_alerts.py` / setup prompts),
   use SMTP `smtp.gmail.com`, port `587`, your Gmail address, and
   that App Password — never your normal Gmail password, and never
   paste either password in chat.
3. Send a test alert from Oracle and check your inbox (and Spam once).

### 5c. Voice
- Voice replies use pyttsx3 on macOS, which uses Apple's NSSpeech
  voices (offline, no key needed). If pyttsx3 fails, Oracle falls
  back to the built-in macOS `say` command. Test it in Terminal:
  `say "Hello, I am Oracle"` — if you hear that, the fallback works.
- Always-listening only works while the GUI is open, with a visible
  red indicator. It does not listen when the GUI is closed.
- If the microphone does not work, check System Settings > Privacy
  & Security > Microphone, and allow Terminal / Python. Also check
  System Settings > Sound > Input is the mic you expect.
- Text chat always works even if voice does not.

---

## Step 6 — First run: text agent (the test that matters)

1. Open a fresh Terminal window.
2. Run:
   ```
   cd ~/Oracle
   python3 agent.py
   ```
3. You should see:
   ```
   Hi, I'm Oracle. Talk to me like a friend - type 'quit' to stop.
   Brain: openai (gpt-4o-mini). Auto-apply new tools: OFF (asks first)
   My computer: workspace at ~/Oracle/workspace
   ```
4. Type a test, for example:
   ```
   Hello, what tools do you have?
   ```
   Oracle should list its tools, including the new computer tools:
   `list_workspace`, `read_workspace_file`, `web_search`, `browser_start`,
   `remember`, `add_task`, and so on.
5. Try a workspace test:
   ```
   Write a file called files/hello.txt that says hello from Oracle, then read it back to me.
   ```
   It should write inside `~/Oracle/workspace/files/hello.txt`, not
   on your Desktop. Check that file in Finder.
6. Try a memory test:
   ```
   Remember that I like detailed answers for technical questions.
   ```
   Then in a new run, ask it what it remembers about you.
7. Type `quit` to stop.

If Step 6 works, the core agent works. Everything else is an add-on.

---

## Step 7 — Run the GUI, and start at login (optional)

From `~/Oracle`, in Terminal:
```
python3 gui.py
```

What you should see:
- Dark neon console, starfield, rotating glowing core
- Animated head (not just a ring) — it blinks, looks around, and its
  mouth moves while it speaks
- Left command deck, pill status indicators, live clock
- Theme switcher: Neon Cyan, Ultraviolet, Solar Amber
- Chat below, with a neon-bordered input

The core pulses while speaking and spins while thinking.

macOS GUI notes:
- Fonts are Helvetica Neue (macOS does not have Segoe UI). The layout
  is the same; text may be very slightly wider/narrower than on Windows.
- tkinter on macOS can be slower to redraw the animated canvas on
  older Intel Macs. If the animation stutters, it is cosmetic — chat
  still works. Use the python.org Python (3.12) for the smoothest GUI.
- If the GUI window opens behind other windows, click the Oracle icon
  in the Dock.

If the GUI does not open:
1. Run `python3 agent.py` first (Step 6). If that fails, the GUI will
   fail for the same reason — fix the agent first.
2. Check the error in Terminal. A missing package error will name the
   package — install it with `pip3 install <package>`. If tkinter
   itself is missing (`No module named '_tkinter'`), reinstall Python
   from python.org, or run `brew install python-tk`.

To run Oracle at login (optional, launchd — the macOS replacement
for Windows Task Scheduler / the Startup folder):
1. Edit `com.oracle.agent.plist` in `~/Oracle` if you need to change
   the path or add your `OPENAI_API_KEY` (see the comments inside it).
2. In Terminal:
   ```
   cp ~/Oracle/com.oracle.agent.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.oracle.agent.plist
   ```
3. Restart your Mac and check Oracle starts. To stop it starting
   automatically:
   ```
   launchctl unload ~/Library/LaunchAgents/com.oracle.agent.plist
   ```

Daily improvement check (optional, launchd):
```
cp ~/Oracle/com.oracle.monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.oracle.monitor.plist
```
That runs `python3 monitor.py` once a day. Proposals still go to
`proposals/` and by email, and nothing applies without your YES.

Building a standalone app (optional, on a Mac only):
- `oracle-mac.spec` is a PyInstaller spec. On your Mac, run
  `pip3 install pyinstaller`, then `pyinstaller oracle-mac.spec`.
  That builds `dist/Oracle.app`. It was NOT built in this package —
  a real `.app` can only be built on a Mac (see `BUILD_NOTES_MAC.md`).
  The source-tree install above is the supported route; the `.app`
  is a convenience, not a requirement.

---

## Step 8 — How to use Oracle like Muse (its own computer)

Talk to it the way you talk to Muse, and let it do the work:

- "Search the web for X and save the results to workspace/files/X.md"
- "List my open tasks" / "Add a task to call the dealer on Saturday"
- "Remember that my Challenger is a 2016 R/T Scat Pack"
- "Open this page in your browser and tell me the price"
- "Write a new tool that does X, test it, and show me the code first"

Rules it follows by default (safe mode):
- Inside `workspace/`: it can read, write, and run things.
- Outside `workspace/`, destructive commands, sending messages/money,
  or changing other people's data: it asks you first.
- Every overwrite is backed up to `backups/` first.
- If a tool fails, the error goes back to the model and it gets up
  to 3 tries to fix its plan before asking you.

Self-improvement (`monitor.py`):
- Proposals go to `proposals/`, with an explanation of what changed
  and why, and a backup of the old version.
- It asks before implementing a change, and rolls back if the new
  code fails a syntax / test check.
- Email alerts go to you (not SMS) for proposals and abnormal
  camera events.

3D design (`design3d.py`):
- Give exact dimensions. If you say "5 inch chest" with no other
  details, it will ask: hinged vs hanging vs treasure, what the
  5 inches measures, other dimensions, lid style, use, and whether
  you want a separate base/lid or a closed model. Answer those first
  — it will not guess.
- Dimensions are shown in both mm and inches (1 in = 25.4 mm).

Security (`security.py`):
- Pen-testing / hacking help is for systems you own or are explicitly
  authorized to test. Otherwise it will point you to a lab (DVWA,
  Juice Shop, Metasploitable) or the official recovery path.

---

## Step 9 — Optional: remote access (Remote Login / SSH) — do this last

Only do this if you want Muse to edit Oracle on your Mac remotely.
It is NOT needed for Oracle to work on your Mac alone.

macOS has SSH built in — no OpenSSH install step like Windows:

1. System Settings > General > Sharing > turn ON "Remote Login".
   That starts the macOS SSH server. Note the address it shows,
   e.g. `ssh username@macbook.local`.
2. Add Muse's public key to `~/.ssh/authorized_keys` on your Mac
   (create the folder/file if needed):
   ```
   mkdir -p ~/.ssh
   chmod 700 ~/.ssh
   ```
   Then add this one line to `~/.ssh/authorized_keys`:
   ```
   ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDUx8X5W2IMPPurXKm5aZLdxfn3X4dPXDsuj9yQqPehI hatch
   ```
   Then:
   ```
   chmod 600 ~/.ssh/authorized_keys
   ```
3. Verify on your Mac:
   ```
   test -f ~/.ssh/authorized_keys && echo YES || echo NO
   ```
   It must say `YES`. If it says `NO`, the key file is missing
   and remote login will not work — do not skip this check.
4. Tell Muse your Mac's address (from System Settings > General >
   Sharing, or `hostname` in Terminal, or your Tailscale IP if you
   use Tailscale on the Mac). Only then can Muse test an actual SSH
   connection. Turning Remote Login on alone does NOT prove remote
   access works.

Note: the Windows guide's `C:\ProgramData\ssh\administrators_authorized_keys`
step does not exist on macOS — `~/.ssh/authorized_keys` is the only
file needed.

---

## Troubleshooting — most common problems, in order

**"python3 is not recognized" / "command not found: python3"**
Python is not on PATH. Reinstall Python from python.org (it puts
`python3` on PATH), close all Terminal windows, open a fresh one.
Do NOT type `python` — on macOS that usually means the old system
Python 2, or nothing at all. Always use `python3` / `pip3`.

**"OPENAI_API_KEY is not set"**
The variable is missing or you are in an old Terminal window. Set it in
Step 4, close all Terminal windows, open a fresh one, run
`echo $OPENAI_API_KEY` to verify. If you launched the GUI from Finder
instead of Terminal, use the `launchctl setenv` line in Step 4, or
launch it from Terminal instead.

**"I hit a problem reaching my brain" / API error**
- Check your internet connection.
- Check your OpenAI account has credit / a valid payment method.
- Check the key has no extra spaces or quotes.
- If you meant to use Ollama, set `LLM_PROVIDER=ollama` and make sure
  `ollama serve` is running, with a model pulled (`ollama pull llama3.1`).

**GUI opens but voice does not work**
Text chat is the fallback — use it. Then check microphone privacy
in System Settings > Privacy & Security > Microphone, and try
`say "test"` in Terminal to check the fallback. For listening, check
PyAudio: `brew install portaudio`, then reinstall PyAudio (Step 2c).

**"No module named '_tkinter'"**
Your Python has no tkinter. Reinstall Python from python.org, or
`brew install python-tk` if you use Homebrew Python.

**Camera not found / PTZ does not move**
Check System Settings > Privacy & Security > Camera and allow
Terminal / Python. Test the camera in FaceTime first. Try a different
USB port, and use EMEET Studio for Mac for PTZ. Oracle's camera module
cannot invent an EMEET SDK that does not exist publicly. On macOS,
UVC PTZ goes through AVFoundation — if the PIXY ignores it, Oracle
says so honestly and uses digital framing + the camera's own AI tracking.

**"Playwright is not installed"**
Run `pip3 install playwright` then `playwright install chromium`
in a fresh Terminal window, then restart Oracle.

**Oracle asks before every command**
That is safe mode, and it is on purpose. Leave it on until you are
comfortable. Only set `AGENT_AUTO_APPLY=1` if you accept that new
tools and commands will run without asking (destructive commands
are still refused).

**A self-change broke something**
Check `backups/` — the previous version is there with a timestamp.
Restore it, restart Oracle, and tell Oracle what broke so it can
try a different fix.

**It says it did something, but nothing changed**
Ask it: "Show me the file / output that proves that." Oracle should
not claim success without verification. If it did, that is a bug to
report in the conversation, with the exact command and output.

**launchd job does not start at login**
Run `launchctl list | grep oracle` in Terminal. If it is not listed,
the plist was not loaded — re-run the `launchctl load` line in
Step 7, and check the plist for a typo in the path. Logs are in
`~/Oracle/logs/` (see the plist's StandardOutPath).

---

## Quick start checklist (tick these off)

- [ ] macOS 13+ on your Mac, Python 3.10+ installed, `python3 --version` works
- [ ] Homebrew + PortAudio installed; packages installed, including Playwright + Chromium
- [ ] Zip extracted to `~/Oracle`, `agent.py` and `computer.py` present
- [ ] `OPENAI_API_KEY` set in `~/.zshrc`, verified in a fresh Terminal window
- [ ] `python3 agent.py` runs, lists computer tools, workspace test passes
- [ ] `python3 gui.py` opens, head animates, chat works
- [ ] (Optional) Camera plugged in, mic/camera permissions allowed, email test alert received
- [ ] (Optional) Remote Login verified: `~/.ssh/authorized_keys` exists

If all the core boxes are ticked, Oracle is up and running on your Mac.
The rest — camera rules, 3D specs, repair help, self-improvement
proposals — you build up by talking to it, and it remembers.

— End of guide —
