#!/usr/bin/env bash
# Odoo Agent Runtime - Linux/macOS installer
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/odoo-agent-runtime}"
SERVICE_NAME="odoo-agent-runtime"
BOLD="\033[1m"; GREEN="\033[0;32m"; YELLOW="\033[0;33m"; RED="\033[0;31m"; NC="\033[0m"

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }
info() { echo -e "${BOLD}[i]${NC} $1"; }
ask() {
    local prompt="$1" default="${2:-}" answer
    if [ -n "$default" ]; then
        read -r -p "$prompt [$default]: " answer
        printf '%s' "${answer:-$default}"
    else
        read -r -p "$prompt: " answer
        printf '%s' "$answer"
    fi
}
ask_yes_no() {
    local prompt="$1" default="${2:-no}" answer
    read -r -p "$prompt [$default]: " answer
    answer="${answer:-$default}"
    case "$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')" in
        y|yes) return 0 ;;
        *) return 1 ;;
    esac
}
dotenv_value() {
    local value="$1"
    if [[ "$value" == *$'\n'* || "$value" == *$'\r'* ]]; then
        error "Configuration values cannot contain line breaks."
        exit 1
    fi
    # python-dotenv decodes backslash and double-quote escapes in double quotes.
    # Dollar signs and backticks are already literal, so escaping them corrupts values.
    printf '%s' "$value" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}
write_env_file() {
    {
        printf '%s\n' '# Odoo Agent Runtime Configuration'
        printf 'ODOO_URL="%s"\n' "$(dotenv_value "$ODOO_URL")"
        printf 'ODOO_DATABASE="%s"\n' "$(dotenv_value "$ODOO_DATABASE")"
        printf 'API_KEY="%s"\n' "$(dotenv_value "$API_KEY")"
        printf 'RUNTIME_NAME="%s"\n' "$(dotenv_value "$RUNTIME_NAME")"
        printf 'POLL_INTERVAL="%s"\n' "$(dotenv_value "$POLL_INTERVAL")"
    } > "$ENV_FILE"
}

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

printf '\n'
info "Odoo Agent Runtime Installer ($OS)"
printf '\n'

PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1 && "$cmd" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 8) else 1)
PY
    then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    error "Python 3.8+ not found. Install Python first: https://www.python.org/downloads/"
    exit 1
fi
log "Python found: $($PYTHON --version)"

printf '\n'
info "Configuration"
ODOO_URL="$(ask 'Odoo URL' 'http://localhost:8069')"
ODOO_DATABASE="$(ask 'Odoo database (optional; required for multi-database Odoo)')"
API_KEY="$(ask 'Runtime API key')"
while [ -z "$API_KEY" ]; do
    error "Runtime API key cannot be empty."
    API_KEY="$(ask 'Runtime API key')"
done
RUNTIME_NAME="$(ask 'Runtime name' "$(hostname 2>/dev/null || echo odoo-runtime)")"
POLL_INTERVAL="$(ask 'Poll interval in seconds' '10')"
INSTALL_MODE="$(ask 'Install mode: service or manual' 'manual')"

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

if [ -f "$SCRIPT_DIR/daemon.py" ]; then
    cp "$SCRIPT_DIR/daemon.py" "$INSTALL_DIR/daemon.py"
    cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/requirements.txt" 2>/dev/null || true
    log "Files copied from local source"
else
    BASE_URL="https://raw.githubusercontent.com/nicolasramos/odoo-agent-runtime/main"
    curl -fsSL "$BASE_URL/daemon.py" -o "$INSTALL_DIR/daemon.py"
    curl -fsSL "$BASE_URL/requirements.txt" -o "$INSTALL_DIR/requirements.txt"
    log "Files downloaded"
fi
chmod +x "$INSTALL_DIR/daemon.py"

if "$PYTHON" -m venv "$INSTALL_DIR/venv"; then
    PYTHON="$INSTALL_DIR/venv/bin/python"
    "$PYTHON" -m pip install -q --upgrade pip
    "$PYTHON" -m pip install -q -r "$INSTALL_DIR/requirements.txt"
    log "Virtual environment created"
else
    warn "Could not create a virtual environment. Installing dependencies for the current Python."
    "$PYTHON" -m pip install -q -r "$INSTALL_DIR/requirements.txt"
fi

ENV_FILE="$INSTALL_DIR/.env"
if [ -f "$ENV_FILE" ] && ! ask_yes_no "Existing .env found. Overwrite it?" "no"; then
    ENV_FILE="$INSTALL_DIR/.env.new"
    warn "Keeping existing .env. Writing new configuration to .env.new."
fi

write_env_file
log "$(basename "$ENV_FILE") written"
if [ "$(basename "$ENV_FILE")" != ".env" ]; then
    warn "Background service install skipped because the active .env was not overwritten."
    INSTALL_MODE="manual"
fi

install_systemd() {
    if ! command -v systemctl >/dev/null 2>&1; then
        warn "systemd not found. Use manual mode instead."
        return
    fi
    cat > "/tmp/$SERVICE_NAME.service" <<EOF
[Unit]
Description=Odoo Agent Runtime
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$PYTHON $INSTALL_DIR/daemon.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    sudo mv "/tmp/$SERVICE_NAME.service" "/etc/systemd/system/$SERVICE_NAME.service"
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    sudo systemctl start "$SERVICE_NAME"
    log "systemd service installed and started"
}

install_launchd() {
    mkdir -p "$HOME/Library/LaunchAgents" "$INSTALL_DIR/logs"
    PLIST="$HOME/Library/LaunchAgents/com.odoo.$SERVICE_NAME.plist"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.odoo.$SERVICE_NAME</string>
  <key>ProgramArguments</key>
  <array><string>$PYTHON</string><string>$INSTALL_DIR/daemon.py</string></array>
  <key>WorkingDirectory</key><string>$INSTALL_DIR</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$INSTALL_DIR/logs/stdout.log</string>
  <key>StandardErrorPath</key><string>$INSTALL_DIR/logs/stderr.log</string>
</dict>
</plist>
EOF
    launchctl unload "$PLIST" >/dev/null 2>&1 || true
    launchctl load "$PLIST"
    log "launchd agent installed and started"
}

case "$(printf '%s' "$INSTALL_MODE" | tr '[:upper:]' '[:lower:]')" in
    service|daemon)
        case "$OS" in
            linux) install_systemd ;;
            darwin) install_launchd ;;
            *) warn "Unsupported service manager for $OS. Use manual mode." ;;
        esac
        ;;
    *)
        warn "Manual mode selected. No background service was installed."
        ;;
esac

printf '\n'
log "Installation complete"
info "Config: $INSTALL_DIR/.env"
info "Manual run: $PYTHON $INSTALL_DIR/daemon.py"
