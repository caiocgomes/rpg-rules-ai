#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/caiocgomes/rpg-rules-ai.git"
INSTALL_DIR="${INSTALL_DIR:-/opt/rpg-rules-ai}"
SERVICE_USER="rpg-rules-ai"
SERVICE_NAME="rpg-rules-ai"
ENV_DIR="/etc/rpg-rules-ai"
ENV_FILE="${ENV_DIR}/env"
UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# --- Root check ---

if [[ $EUID -ne 0 ]]; then
    echo "Error: this script must be run as root (sudo)." >&2
    exit 1
fi

# --- Install uv if missing ---

if ! command -v uv &>/dev/null; then
    echo "uv not found, installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    if ! command -v uv &>/dev/null; then
        echo "Error: uv installation failed." >&2
        exit 1
    fi
fi

echo "Using uv at: $(command -v uv)"

# --- System user ---

if ! id "$SERVICE_USER" &>/dev/null; then
    echo "Creating system user '$SERVICE_USER'..."
    useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

# --- Clone or pull repo ---

if [[ -d "${INSTALL_DIR}/.git" ]]; then
    echo "Repo already exists at ${INSTALL_DIR}, pulling latest..."
    git -C "$INSTALL_DIR" pull --ff-only
else
    echo "Cloning repo to ${INSTALL_DIR}..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

# --- Install dependencies (creates .venv) ---

echo "Running uv sync..."
cd "$INSTALL_DIR"
uv sync --no-dev

# --- Data directories ---

echo "Setting up data directories..."
mkdir -p "${INSTALL_DIR}/data/chroma"
mkdir -p "${INSTALL_DIR}/data/docstore"
mkdir -p "${INSTALL_DIR}/data/sources"
mkdir -p "${INSTALL_DIR}/data/prompts"

# --- Env file ---

mkdir -p "$ENV_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Creating env file from .env.example..."
    cp "${INSTALL_DIR}/.env.example" "$ENV_FILE"
    echo ""
    echo ">>> IMPORTANT: edit ${ENV_FILE} and set OPENAI_API_KEY <<<"
    echo ""
fi

chmod 600 "$ENV_FILE"
chown root:${SERVICE_USER} "$ENV_FILE"
chmod 640 "$ENV_FILE"

# --- Permissions ---

chown -R "${SERVICE_USER}:${SERVICE_USER}" "$INSTALL_DIR"

# --- Systemd unit ---

echo "Installing systemd unit file..."
cat > "$UNIT_FILE" <<EOF
[Unit]
Description=RPG Rules AI - Agentic RAG for RPG rulebooks
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}
Environment=PORT=8100
Environment=WORKERS=1
EnvironmentFile=${ENV_FILE}
ExecStart=${INSTALL_DIR}/.venv/bin/uvicorn rpg_rules_ai.api:app --host 0.0.0.0 --port \${PORT} --workers \${WORKERS}
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=30
StartLimitBurst=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

# --- Check OPENAI_API_KEY before starting ---

if grep -q '^OPENAI_API_KEY=$' "$ENV_FILE" || ! grep -q '^OPENAI_API_KEY=' "$ENV_FILE"; then
    echo ""
    echo "=== RPG Rules AI service installed but NOT started ==="
    echo ""
    echo "OPENAI_API_KEY is not configured in ${ENV_FILE}."
    echo "Set it and then run: systemctl start ${SERVICE_NAME}"
else
    echo "Starting ${SERVICE_NAME}..."
    systemctl start "$SERVICE_NAME"
    echo ""
    echo "=== RPG Rules AI service installed and running ==="
fi

echo ""
echo "Install dir:  ${INSTALL_DIR}"
echo "Env file:     ${ENV_FILE}"
echo "Unit file:    ${UNIT_FILE}"
echo "Service user: ${SERVICE_USER}"
echo ""
echo "Useful commands:"
echo "  systemctl status ${SERVICE_NAME}"
echo "  journalctl -u ${SERVICE_NAME} -f"
echo "  systemctl restart ${SERVICE_NAME}"
