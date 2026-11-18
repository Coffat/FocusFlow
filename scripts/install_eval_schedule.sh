#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.focusflow.eval7d"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$PLIST_DIR/${LABEL}.plist"
OUT_DIR="$REPO_ROOT/docs/experiments/scheduled_eval_7d"
LOG_PATH="$OUT_DIR/launchd.log"
RUNNER_SCRIPT="$REPO_ROOT/scripts/run_scheduled_eval.py"

resolve_python() {
  if [[ -x "$REPO_ROOT/backend/.venv/bin/python" ]]; then
    printf '%s\n' "$REPO_ROOT/backend/.venv/bin/python"
  elif [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    printf '%s\n' "$REPO_ROOT/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    command -v python3
  else
    echo "Error: no Python interpreter found (.venv/bin/python or python3)." >&2
    exit 1
  fi
}

PYTHON_BIN="$(resolve_python)"

render_plist() {
  cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON_BIN}</string>
    <string>${RUNNER_SCRIPT}</string>
  </array>

  <key>WorkingDirectory</key>
  <string>${REPO_ROOT}</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>PYTHONUNBUFFERED</key>
    <string>1</string>
  </dict>

  <key>StartCalendarInterval</key>
  <array>
    <dict>
      <key>Hour</key>
      <integer>9</integer>
      <key>Minute</key>
      <integer>0</integer>
    </dict>
    <dict>
      <key>Hour</key>
      <integer>14</integer>
      <key>Minute</key>
      <integer>0</integer>
    </dict>
    <dict>
      <key>Hour</key>
      <integer>21</integer>
      <key>Minute</key>
      <integer>0</integer>
    </dict>
  </array>

  <key>StandardOutPath</key>
  <string>${LOG_PATH}</string>

  <key>StandardErrorPath</key>
  <string>${LOG_PATH}</string>

  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
EOF
}

print_crontab() {
  cat <<EOF
# Equivalent crontab entry (daily at 09:00, 14:00, 21:00 local time):
0 9,14,21 * * * cd "${REPO_ROOT}" && "${PYTHON_BIN}" "${RUNNER_SCRIPT}" >> "${LOG_PATH}" 2>&1
EOF
}

usage() {
  cat <<EOF
Usage: $(basename "$0") [--print | --install | --uninstall]

Options:
  --print      Print the launchd plist and equivalent crontab entry without installing (default).
  --install    Write ${PLIST_PATH} and load it with launchctl.
  --uninstall  Unload ${LABEL} from launchctl and remove ${PLIST_PATH}.
  -h, --help   Show this help message.
EOF
}

ACTION="--print"
if [[ "$#" -gt 1 ]]; then
  usage >&2
  exit 2
elif [[ "$#" -eq 1 ]]; then
  ACTION="$1"
fi

case "$ACTION" in
  --print)
    echo "# Target launchd plist path: ${PLIST_PATH}"
    render_plist
    echo ""
    print_crontab
    ;;
  --install)
    mkdir -p "$PLIST_DIR" "$OUT_DIR"
    render_plist > "$PLIST_PATH"
    if command -v plutil >/dev/null 2>&1; then
      plutil -lint "$PLIST_PATH"
    fi
    uid_num="$(id -u)"
    launchctl bootout "gui/${uid_num}/${LABEL}" >/dev/null 2>&1 || launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
    if ! launchctl bootstrap "gui/${uid_num}" "$PLIST_PATH" >/dev/null 2>&1; then
      launchctl load "$PLIST_PATH"
    fi
    echo "Installed and loaded ${PLIST_PATH}"
    echo "Logs: ${LOG_PATH}"
    echo ""
    print_crontab
    ;;
  --uninstall)
    uid_num="$(id -u)"
    launchctl bootout "gui/${uid_num}/${LABEL}" >/dev/null 2>&1 || launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
    if [[ -f "$PLIST_PATH" ]]; then
      rm -f "$PLIST_PATH"
      echo "Unloaded ${LABEL} and removed ${PLIST_PATH}"
    else
      echo "No plist found at ${PLIST_PATH} (already uninstalled)."
    fi
    ;;
  -h|--help)
    usage
    ;;
  *)
    echo "Unknown option: $ACTION" >&2
    usage >&2
    exit 2
    ;;
esac
