# Oracle for macOS — Build Notes

Source: the Windows agent in `~/workspace/friend-agent/` (agent.py,
gui.py, computer.py, voice.py, camera.py, monitor.py, email_alerts.py,
sms.py, security.py, identity.py, repair.py, design3d.py, README.md,
SETUP_GUIDE.md, ORACLE_SETUP_DETAILED.md, 3D_KNOWLEDGE.md,
SECURITY_KNOWLEDGE.md, prints/*.stl), adapted for macOS on 2026-11-24.
Built in this Linux environment — see "What was tested" below for
exactly what could and could not be verified here.

Same agent, same features: name Oracle, OpenAI brain (default
`gpt-4o-mini`, Ollama optional), Gideon-inspired dark-neon GUI with
the animated head, voice replies + always-listening (no wake word),
EMEET PIXY camera watch, repair partner, 3D STL design (mm + inches),
security knowledge (authorized targets only), self-improvement
monitor (explains, asks first, backs up, rolls back), email alerts
(not SMS), local-only voice/face learning, own computer
(workspace, browser, memory, goals, tasks).

The prompt rule is kept verbatim in `computer.py`:
"Never tell me what it can't do. It just finds a way, even if that
means it creates new tools or scripts." Safety sections were NOT
stripped.

## Windows → Mac changes, per file

### agent.py
- Docstring: Windows → macOS; run command `python agent.py` →
  `python3 agent.py`.
- `DANGEROUS_PATTERNS`: Windows patterns (`del /f`, `reg delete`,
  `rmdir /s`, `Remove-Item`, `Format-Volume`) replaced with macOS /
  Unix ones (`rm -rf`, `sudo rm`, `diskutil eraseDisk`,
  `diskutil eraseVolume`, `shutdown`, `reboot`, `mkfs`, `dd if=`).
- Everything else (personality, tool loop, 3-try self-correction,
  tool creation with approval gate) unchanged.

### computer.py
- Header: Windows Oracle → macOS Oracle; workspace is
  `~/Oracle/workspace` on the Mac.
- `DANGEROUS_PATTERNS`: same macOS replacement as agent.py.
- System prompt: "on my PC" → "on my Mac, at workspace/ under your
  own folder (~/Oracle/workspace)". The verbatim "Never tell me what
  it can't do…" rule is unchanged.
- New: job-application tools (see "Job applications" below) and the
  local credentials store.
- The Windows `ORACLE_SETUP_DETAILED.md` was NOT copied over; the
  Mac tree has `ORACLE_SETUP_MAC.md` instead.

### voice.py
- Install notes: Windows / pipwin → macOS: `brew install portaudio`,
  then `pip3 install pyttsx3 SpeechRecognition PyAudio`.
- `speak()`: pyttsx3 now initialises with the macOS NSSpeech driver
  (`driverName="nsss"` — Apple built-in voices, offline). If pyttsx3
  is missing or fails, it falls back to the built-in macOS `say`
  command (`say -r 175 <text>`), which is always present on a Mac.
  Voice *replies* therefore work even without PyAudio; only
  listening needs PyAudio.
- Listening (`listen_once`) unchanged apart from the install hint.

### camera.py
- Backend: `cv2.CAP_DSHOW` (Windows DirectShow) →
  `cv2.CAP_AVFOUNDATION` (macOS AVFoundation), with a generic
  `VideoCapture(index)` fallback if that constant is unavailable.
- PTZ notes: DirectShow → AVFoundation; EMEET Studio for Mac is the
  official PTZ route; UVC pan/tilt/zoom is tried and honestly
  reported, digital crop + the camera's own AI tracking is the fallback.
- Camera-open error now also tells the user to check System Settings
  > Privacy & Security > Camera.
- Docstring fixed: alerts are EMAILED (email_alerts.py), not texted
  via sms.py — the code already did that; the comment did not.
- "on your PC" → "on your Mac".

### gui.py
- Header: Windows → macOS; environment-variable note → `~/.zshrc` /
  `launchctl` on the Mac.
- Fonts: `Segoe UI` (not on macOS) → `Helvetica Neue` throughout.
- Scroll: kept `<MouseWheel>` and added `<Button-4>` / `<Button-5>`
  bindings for macOS trackpads / mice that send those events.
- Install hints in messages: `pip install …` → `pip3 install …`
  (with `brew install portaudio` for voice).
- The animated head, starfield, waveform, command deck, pills, clock,
  and themes are unchanged — same Gideon-inspired GUI.

### monitor.py
- Scheduling: "use Task Scheduler on Windows" → launchd on macOS
  (see `com.oracle.monitor.plist`, daily 08:00, and
  ORACLE_SETUP_MAC.md Step 7).
- Approval text fixed: "reply YES to the SMS" → "reply YES to the
  email" (alerts are email, not SMS, per Lorenza's choice).

### email_alerts.py / sms.py
- "A Windows script CAN send email…" → "A macOS script CAN…";
  "Set these on YOUR PC" → "on YOUR Mac". Behaviour unchanged:
  alerts by email, not SMS. `sms.py` (Twilio) is still in the folder
  but is not used by default.

### identity.py
- "on your personal PC" → "on your personal Mac"; face-recognition
  install: Windows / dlib note → macOS: `brew install cmake dlib`,
  then `pip3 install face_recognition`. Local-only learning unchanged.

### design3d.py / repair.py / security.py
- design3d.py: "runs on Windows with plain…" → "runs on macOS…".
  No logic change (pure stdlib + math).
- repair.py: no Windows-specific code; "local to your PC" → "local
  to your Mac".
- security.py: lab example "a Windows VM, a Linux VM" → "a VM
  (macOS, Windows, or Linux Kali / Ubuntu)". Safety gate
  (authorization check before any active test) unchanged.

### Docs
- `README.md`: Windows → macOS throughout; `C:\friend-agent` →
  `~/Oracle`; `python`/`pip` → `python3`/`pip3`; OpenAI key via
  `~/.zshrc` / `launchctl setenv` (the Windows "Environment
  Variables" dialog and PowerShell `$env:` lines were removed);
  camera backend DirectShow → AVFoundation; "Windows scheduled
  task" → macOS launchd job.
- `SETUP_GUIDE.md`: same treatment — python.org macOS installer
  (no "Add to PATH" checkbox on macOS), Terminal instead of Command
  Prompt, `brew install portaudio` for PyAudio, `~/.zshrc` for the
  API key, macOS mic/camera permission paths.
- `ORACLE_SETUP_DETAILED.md` (Windows) was REMOVED from the Mac
  tree and replaced by the new `ORACLE_SETUP_MAC.md` — same step
  structure (Steps 1–9, troubleshooting, checklist), rewritten for
  macOS: Homebrew, python.org Python, `~/Oracle`, `~/.zshrc` +
  `launchctl setenv`, AVFoundation + EMEET Studio for Mac, System
  Settings permissions, launchd instead of Task Scheduler / Startup
  folder, Remote Login (built-in macOS SSH) instead of the Windows
  OpenSSH install + `C:\ProgramData\ssh\administrators_authorized_keys`.
- `3D_KNOWLEDGE.md` / `SECURITY_KNOWLEDGE.md`: "Windows" → "macOS /
  Windows" (they describe both platforms' tools).
- New files: `requirements.txt`, `install.sh`,
  `com.oracle.agent.plist`, `com.oracle.monitor.plist`,
  `oracle-mac.spec`, this file.

### Paths / platform replacements (global)
- `C:\Oracle` / `C:\friend-agent\` → `~/Oracle`
- Command Prompt / PowerShell → Terminal (`/bin/zsh`)
- Task Scheduler / Startup folder → launchd
  (`~/Library/LaunchAgents/`, `launchctl load/unload`)
- Windows Registry / `C:\ProgramData\ssh\…` → none on macOS;
  Remote Login + `~/.ssh/authorized_keys` only
- `python` / `pip` → `python3` / `pip3`

## Job applications — auto-submit (added 2026-11-24)

This applies to the Mac build, and to the Windows design too
(Lorenza's rule, set 2026-11-24). Windows/Mac parity: everything
built for the Mac version must also be in the Windows version and
vice versa — a separate Windows parity update was started for
`~/workspace/friend-agent/`; this Mac build is the reference for it.

New tools in `computer.py` (registered in `COMPUTER_TOOLS`, so
`agent.py` can call them):
- `apply_to_job(url, job_title='', company='', field_values=None, resume_path=None)`
- `get_job_profile()` / `save_job_profile(...)`
- `list_job_submissions(limit=20)`
- `list_job_accounts()`

Behaviour — the rule, exactly as Lorenza set it:
- If a site is NOT blocking it, Oracle fills the form, uploads the
  resume, and presses submit — every time, WITHOUT asking first.
  This is deliberately not gated by the usual approval prompt; it is
  the one external action she has pre-approved in advance. Every
  other external action still asks first.
- It only stops and hands the application to Lorenza when a site
  actually blocks it: CAPTCHA, a sign-in code / 2FA step, an
  anti-bot block, or a step that needs a human. Then it logs exactly
  what was blocked and where, and tells her.
- Job boards that redirect: Indeed (and similar) often send you to
  the employer's own site. `apply_to_job()` follows "Apply on
  company site" links and applies on the EMPLOYER site too, under
  the same auto-submit rule. The final (employer) URL is what gets
  logged, not just the board link.
- Account creation: if an employer site needs a NEW account, Oracle
  creates one — username is the email from the job profile, password
  is a freshly generated distinct strong password per site (16
  characters, upper + lower + digits + symbols, via `secrets`).
  It never reuses one password everywhere.
- Existing logins: if a site asks for an EXISTING password (sign-in
  only, no sign-up form), Oracle stops and asks Lorenza. It does NOT
  invent an existing Indeed password or any other existing password.
- Resume details are never invented: the job profile starts as
  placeholders (name, email, phone, resume_path all empty) to be
  filled on first run on her Mac via `save_job_profile()`. If the
  profile is still empty, `apply_to_job()` cannot fill those fields
  and says what is missing instead of guessing.
- Scope stored in the profile: Jacksonville, FL, $25/hour and up,
  customer service / call-center lead-supervisor and
  mortgage/refinance only; collections, marine, and sales excluded.

Logs and stores (all local, on her Mac):
- Submissions log: `workspace/jobs/submissions.json` — job title,
  company, site (final URL), date/time, status
  (`submitted` / `submitted_unconfirmed` / `blocked`), confirmation
  text if shown, blocked reason, fields filled / unfilled, resume
  note, account created (username only).
- Job profile: `workspace/jobs/profile.json` — created on first use
  from placeholders.
- Accounts log: `~/Oracle/credentials/accounts.json` — site,
  username, password, date created. Folder mode 0700, file mode
  0600. Local only — never in chat logs, email, or the cloud.
  `list_job_accounts()` prints site / username / date only, never
  the password.
- Desktop visibility (Lorenza's explicit choice, added 2026-11-24):
  every account created is ALSO appended to
  `~/Desktop/Oracle-Accounts.txt` — append, never overwrite — and
  that file is opened in TextEdit (`open`) and left open on the
  desktop, so she sees it as soon as she looks at the desktop.
  That file is PLAIN TEXT, by design. Anyone who can see the
  desktop / screen will also see those passwords in plain text.
  That is the trade-off she explicitly chose for visibility. The
  secure local store (`credentials/accounts.json`, 0600) is still
  the canonical copy, and the file header says the same. Do not
  email or share `Oracle-Accounts.txt`.

Limits — what this does NOT do:
- It cannot solve CAPTCHAs, pass 2FA / sign-in codes, or defeat
  anti-bot blocks. Those are the defined stop points.
- It cannot apply on a site whose form it cannot understand (no
  fillable fields found, or no submit button found) — that is logged
  as blocked, not faked as submitted.
- A "submitted_unconfirmed" result means the submit button was
  pressed but no confirmation text appeared — check the site / email.
- It does not bypass a site's terms: it fills the site's own form
  in its own browser, as a human would. If a site blocks automated
  browsers, that is a block, and it stops.
- No application was submitted while building this — the tool was
  only smoke-tested for profile/log/credential handling (see below).

## Installer — what was and was not built

- NO real `.app` or `.pkg` was built here. A true macOS
  `.app`/`.pkg` can only be built on a Mac, and this build ran on
  Linux. Do NOT claim one exists.
- What IS provided instead:
  - `install.sh` — one-command installer: Homebrew (if missing),
    `brew install portaudio`, `pip3 install -r requirements.txt`,
    Playwright + Chromium, then offers to install the launchd jobs.
    It does NOT set the OpenAI key.
  - `oracle-mac.spec` — PyInstaller spec. On a Mac:
    `pip3 install pyinstaller && pyinstaller oracle-mac.spec`
    produces `dist/Oracle.app`. The spec bundles the GUI entry
    point, the agent modules as hidden imports, the docs, and the
    macOS mic/camera usage descriptions. PyInstaller was NOT
    available in this Linux environment, so the spec is untested
    until run on a Mac.
  - `com.oracle.agent.plist` — launchd job: start the GUI at login.
    Edit the username (`/Users/lorenza`) and the `OPENAI_API_KEY`
    value before loading it. The Python path in it is
    `/usr/local/bin/python3` (python.org install); if you use
    Homebrew Python, change it to `/opt/homebrew/bin/python3`.
  - `com.oracle.monitor.plist` — launchd job: daily 08:00
    `monitor.py` check.
  - `requirements.txt` — all Python packages, with the macOS notes
    (PortAudio first; face_recognition / pyinstaller optional).

## What was tested (in this Linux environment)

- `python3 -m py_compile` on every `.py` file in the Mac tree:
  ALL 12 PASS — agent.py, camera.py, computer.py, design3d.py,
  email_alerts.py, gui.py, identity.py, monitor.py, repair.py,
  security.py, sms.py, voice.py. (One failure was found and fixed
  during the build: a broken multi-line string in camera.py's
  camera-open error, and one in computer.py's desktop-file header
  — both fixed, then re-compiled clean.)
- `computer.py` smoke test (import + calls, no browser, no network):
  `get_job_profile()` returns the placeholder profile (Jacksonville,
  $25/hr, correct scope/exclusions); `list_job_submissions()` and
  `list_job_accounts()` report empty correctly; `_save_account()`
  writes `credentials/accounts.json` (folder mode 0700) and appends
  to `~/Desktop/Oracle-Accounts.txt` with the warning header, and
  the entry is appended, not overwritten. The `open` call is
  best-effort and does not break the save if TextEdit is unavailable.
- Verbatim rule check: "Never tell me what it can't do. It just
  finds a way, even if that means it creates new tools or scripts."
  is present and unchanged in `computer.py`.
- Grep check: no `C:\`, PowerShell, `CAP_DSHOW`, Segoe UI, Task
  Scheduler, or Command Prompt remains in the `.py` files or in
  README.md / SETUP_GUIDE.md / ORACLE_SETUP_MAC.md (the only
  remaining "Windows" mentions are explanatory: lab VMs in
  security.py, and one note in SETUP_GUIDE.md that the "Add to
  PATH" checkbox is a Windows installer step).
- Runtime-generated folders (`workspace/`, `credentials/`,
  `__pycache__/`) created by the smoke test were removed before
  packaging — they are created fresh on first run on her Mac.

## What still needs testing on a real Mac (not tested here)

- Full first run: `python3 agent.py` and `python3 gui.py` on a Mac
  with a real OpenAI key — GUI animation, themes, chat, and the
  typewriter/speaking flow.
- Voice: pyttsx3 NSSpeech driver + the `say` fallback; microphone
  listening with PyAudio after `brew install portaudio`; always-
  listening toggle and the visible LISTENING indicator.
- Camera: PIXY opening via AVFoundation, UVC PTZ attempt (expect
  it may be ignored — EMEET Studio for Mac is the official route),
  digital PTZ fallback, motion alerts by email.
- Playwright: `playwright install chromium` and `browser_start()`
  on macOS; `apply_to_job()` end-to-end on a real job board and a
  real employer site (including a redirect, a sign-up form, and a
  blocked case — CAPTCHA / sign-in — to confirm it stops and logs).
- Face recognition: `brew install cmake dlib` + `face_recognition`
  build (slow); fallback behaviour if it is not installed.
- `install.sh` end-to-end on a clean Mac; both launchd plists
  (`launchctl load`, login start, daily monitor run, log files).
- PyInstaller: `pyinstaller oracle-mac.spec` on a Mac, then run
  the resulting `Oracle.app` (mic/camera permission prompts,
  `NSMicrophoneUsageDescription` / `NSCameraUsageDescription`).
- The Desktop accounts file opening in TextEdit on a real Mac
  desktop (it is best-effort code; `open` was not runnable here).
- Job profile first run: fill name / email / phone / resume path
  with `save_job_profile()` before the first real application.
