# Oracle for Mac — INTEL (x86_64) build notes

Built 2026-11-24 for Candice's quad-core Intel Core i5 Mac, which
reported "isn't supported on this Mac" for the arm64 build.

## Confirmed cause

The v1.0.0-mac build was Apple Silicon only: `oracle-mac.spec`
`target_arch='arm64'`, built on GitHub-hosted `macos-15` (arm64).
Rosetta 2 translates x86_64 -> arm64, never the reverse, so an
arm64-only .app can never run on an Intel Mac. Finder says exactly
"isn't supported on this Mac". The DMG and the zip contained the same
arm64 binary, so switching files could not fix it.

## Investigation (verified 2026-11-24, not assumed)

1. **macos-13 is gone.** GitHub retired the `macos-13` / `macos-13-large`
   / `macos-13-xlarge` runner labels on Dec 4, 2025 (GitHub blog,
   "macOS 13 runner image is closing down"). A workflow still using
   `macos-13` is broken.
2. **An Intel runner DOES still exist: `macos-15-intel`.** Standard
   GitHub-hosted runner, x86_64, 4 vCPU / 14 GB, free for public
   repositories (oracle-mac is public), active until ~Aug 2027, after
   which GitHub ends Intel support entirely. `macos-26-intel` also
   exists but is a larger (paid) runner only.
3. **PyInstaller cannot cross-build.** An x86_64 binary needs an
   x86_64 Python interpreter. Setting `target_arch='x86_64'` on an
   arm64 (`macos-15`) runner does not produce a working Intel binary.
   The build must run natively on `macos-15-intel`. A universal2
   build was rejected as the route: it needs a universal2 Python plus
   universal2 wheels for every native dependency (PyAudio, OpenCV,
   Pillow, numpy, Playwright), which is fragile and unverifiable here.
   A native Intel build is the reliable route.

## What changed vs the arm64 folder (~/workspace/oracle-mac/)

- `oracle-mac.spec`: `target_arch='arm64'` -> `'x86_64'`;
  `LSMinimumSystemVersion` set to `10.13` in the bundle Info.plist.
- `.github/workflows/build-macos.yml`: renamed job to
  "Build Oracle for macOS (Intel)", `runs-on: macos-15-intel`,
  `MACOSX_DEPLOYMENT_TARGET: '10.13'`, added a runner-arch check
  (`uname -m` must be `x86_64`), verification now requires `x86_64`
  and rejects `arm64`, plus a sweep of EVERY Mach-O file in the
  bundle (one arm64-only .so would launch and then die on load).
- Artifacts renamed: `Oracle-macos-x86_64.dmg` and
  `Oracle-macos-x86_64-unsigned.zip` (artifact names
  `Oracle-macos-x86_64-dmg` / `Oracle-macos-x86_64-unsigned`).
- Everything else (source, avatar, job-hunting auto-submit, desktop
  accounts file) is identical to the arm64 v3 build.

## Verification

- Local: `python3 -m py_compile *.py` passes on all Python files.
- In CI (GitHub Actions, `macos-15-intel`): `lipo -info` on
  `dist/Oracle.app/Contents/MacOS/Oracle` must show `x86_64` and
  the Mach-O sweep must pass; the run fails otherwise. See the
  workflow run / release links in the delivery report.
- NOT verified: actually launching the .app on a real Intel Mac —
  no Intel Mac is available here. Candice opening it is the first
  real launch test. First launch is right-click -> Open (unsigned,
  ad-hoc signed only).

## Residual risk — Candice's macOS version is unknown

`MACOSX_DEPLOYMENT_TARGET=10.13` and Python 3.12 (which needs
macOS 10.13+) maximise compatibility, but the binary is still built
with the macOS 15 SDK. If Candice's Mac is on macOS 10.12 or older,
or on a macOS too old for some linked library, it can still refuse
to run. Ask her Apple menu -> About This Mac -> macOS version if
it fails again.

## Fallback if the Intel .app still cannot run

Do NOT email Candice plain `.py` source (Lorenza's rule: source
code only to Lorenza). The closest working alternative that respects
that rule is a compiled-bytecode installer: ship `.pyc` files (no
plain `.py`) plus a launcher, with Candice installing Intel Python
3.12 from python.org first. That needs Lorenza's explicit approval
as an exception, because it still exposes the program's logic in
bytecode form and needs Candice to install Python herself. The
plain source-run via `install.sh` is the last resort only, and also
needs Lorenza's approval first.
