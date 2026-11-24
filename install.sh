#!/bin/bash
# Oracle for macOS — one-command installer.
# Run from the Oracle folder:   cd ~/Oracle && bash install.sh
# What it does:
#   1. Installs Homebrew if missing (asks for your Mac password).
#   2. Installs portaudio (needed for PyAudio / microphone input).
#   3. Installs the Python packages from requirements.txt.
#   4. Installs Playwright's Chromium (Oracle's own browser).
#   5. Offers to install the launchd jobs (start at login + daily check).
# What it does NOT do:
#   * It does NOT set your OPENAI_API_KEY — do that by hand (see
#     ORACLE_SETUP_MAC.md Step 4) so the key never goes in a shared file.
#   * It does NOT fill in your job profile — run the agent once and use
#     save_job_profile() for name / email / phone / resume path.
set -e
cd "$(dirname "$0")"

echo "== Oracle for macOS — installer =="

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew not found — installing it (you will be asked for your Mac password)..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if [ -x /opt/homebrew/bin/brew ]; then eval "$(/opt/homebrew/bin/brew shellenv)"; fi
  if [ -x /usr/local/bin/brew ]; then eval "$(/usr/local/bin/brew shellenv)"; fi
else
  echo "Homebrew already installed."
fi

echo "Installing portaudio (for PyAudio)..."
brew install portaudio || echo "portaudio install reported a problem — voice listening may fail; text chat still works."

echo "Checking python3..."
python3 --version

echo "Installing Python packages from requirements.txt..."
pip3 install -r requirements.txt

echo "Installing Playwright Chromium (Oracle's own browser)..."
pip3 install playwright
playwright install chromium || echo "Chromium install reported a problem — web search/fetch still work; the real-browser tools will say Playwright is not installed."

echo ""
echo "Core install done. Next steps (see ORACLE_SETUP_MAC.md):"
echo "  1. Set your OpenAI key:  echo 'export OPENAI_API_KEY=YOUR-KEY-HERE' >> ~/.zshrc && source ~/.zshrc"
echo "  2. Test it:  python3 agent.py"
echo "  3. GUI:  python3 gui.py"
echo ""
read -r -p "Install the launchd jobs now (start Oracle at login + daily improvement check)? [y/N] " answer
case "$answer" in
  y|Y)
    cp com.oracle.agent.plist ~/Library/LaunchAgents/ 2>/dev/null || echo "com.oracle.agent.plist not found — skipping."
    launchctl load ~/Library/LaunchAgents/com.oracle.agent.plist 2>/dev/null || echo "Could not load the login job — check the plist path / key (see ORACLE_SETUP_MAC.md Step 7)."
    cp com.oracle.monitor.plist ~/Library/LaunchAgents/ 2>/dev/null || echo "com.oracle.monitor.plist not found — skipping."
    launchctl load ~/Library/LaunchAgents/com.oracle.monitor.plist 2>/dev/null || echo "Could not load the monitor job."
    echo "Launchd jobs installed."
    ;;
  *)
    echo "Launchd jobs skipped. You can install them later (ORACLE_SETUP_MAC.md Step 7)."
    ;;
esac
echo "Done."
