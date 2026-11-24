# Oracle for Mac — GitHub setup (build the .app in the cloud)

You do **not** need a Mac to do this. GitHub's own Mac computers build
`Oracle.app` for you, free on the free GitHub plan (public repos get
generous free macOS minutes; private repos get a smaller free allowance
— check the Actions usage page if a run ever says you are out of minutes).

Nothing has been pushed anywhere yet — there is no GitHub login in Muse,
and no repo exists. These are the steps **you** need to do, in order.

## 1. Create a GitHub account (if you do not have one)

Go to https://github.com and sign up. You will need an email address
and a password you choose. Turn on two-factor authentication when GitHub
asks — it will ask for a code from an authenticator app or text message.

## 2. Create a new repository

1. On GitHub, click the **+** at the top right, then **New repository**.
2. Repository name: `oracle-mac` (suggested — any name works).
3. Leave it **Public** or set it to **Private** — either works for the
   build. Public is free-est for macOS minutes; Private keeps the code
   out of public view.
4. Do **not** tick "Add a README" — the folder already has one.
5. Click **Create repository**. GitHub will show you a page with the
   repo's web address. It will look like
   `https://github.com/<your-username>/oracle-mac` — that is *your*
   address; do not use anyone else's.

## 3. Push this folder to the repo

You need the files in `~/workspace/oracle-mac/` on your computer first.
They are already emailed to you as `oracle-mac-full-v3.zip` — unzip that
on your Windows PC, or copy the folder from this workspace.

On your PC, in a terminal (Git must be installed — https://git-scm.com
if it is not), from inside the unzipped `oracle-mac` folder:

```bash
git init
git add .
git commit -m "Oracle for Mac v3 with avatar"
git branch -M main
git remote add origin https://github.com/<your-username>/oracle-mac.git
git push -u origin main
```

Replace `<your-username>` with your own GitHub username. GitHub will ask
for your username and a personal access token (not your password) the
first time you push — GitHub's site explains how to create one under
Settings → Developer settings → Personal access tokens.

## 4. Run the build

1. On GitHub, open your `oracle-mac` repo.
2. Click the **Actions** tab at the top.
3. In the left sidebar, click **Build Oracle for macOS**.
4. Click **Run workflow** (top right), then **Run workflow** again.
5. Wait a few minutes. The run will show a green tick when it finishes.
   If it goes red, click into it — the failing step's log says what
   went wrong (usually a missing dependency or a typo in the spec).

You can also trigger a build by pushing a tag:

```bash
git tag v1.0.0
git push --tags
```

## 5. Download the finished .app

1. When the run is green, click into it.
2. Scroll to the bottom, to **Artifacts**. Download:
   - `Oracle-macos-arm64-unsigned` — contains
     `Oracle-macos-arm64-unsigned.zip` (the `.app`, zipped)
   - `Oracle-macos-arm64-dmg` — contains `Oracle-macos-arm64.dmg`
3. On a Mac, open the DMG, drag `Oracle.app` to Applications, or unzip
   the `.app` zip. **First launch: right-click Oracle.app and choose
   Open, then confirm** — this build is unsigned (no Apple Developer
   signing), so a plain double-click will be blocked by Gatekeeper.
   That is expected for this build, not a broken app.

## What the build does (short version)

`macos-15` (Apple Silicon Mac in the cloud) → installs Python 3.12,
portaudio, the requirements, and PyInstaller → compile-checks every
`.py` file → runs `pyinstaller oracle-mac.spec` → checks the binary is
arm64 and the avatar image was bundled → ad-hoc signs it
(`codesign --sign -`) → makes a DMG with an Applications link → uploads
the `.app` zip and the DMG as artifacts. No signing secrets, no Apple ID,
no notarization. See the comments at the top of
`.github/workflows/build-macos.yml` for the full explanation.

## After the build

The .app still needs a human test on a real Mac: open it, check the
avatar animates, voice replies work, and the camera starts. The workflow
only proves the app *builds* — it does not click through the GUI.
