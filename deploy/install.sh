#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/caprag}"
SERVICE_USER="caprag"
SERVICE_NAME="caprag"
UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# --- Checks ---

if [[ $EUID -ne 0 ]]; then
    echo "Error: this script must be run as root (sudo)." >&2
    exit 1
fi

if ! command -v uv &>/dev/null; then
    echo "Error: uv is not installed or not in PATH." >&2
    echo "Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

UV_PATH="$(command -v uv)"

# --- User ---

if ! id "$SERVICE_USER" &>/dev/null; then
    echo "Creating system user '$SERVICE_USER'..."
    useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

# --- Directories ---

echo "Setting up directories..."
mkdir -p "${INSTALL_DIR}/data/chroma"
mkdir -p "${INSTALL_DIR}/data/docstore"
mkdir -p "${INSTALL_DIR}/data/sources"
mkdir -p "${INSTALL_DIR}/data/prompts"

chown -R "${SERVICE_USER}:${SERVICE_USER}" "${INSTALL_DIR}/data"

# --- Unit file ---

echo "Installing systemd unit file..."
cat > "$UNIT_FILE" <<EOF
[Unit]
Description=CapaRAG - Agentic RAG for RPG rulebooks
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}
EnvironmentFile=${INSTALL_DIR}/.env
ExecStart=${UV_PATH} run uvicorn caprag.api:app --host 0.0.0.0 --port \${PORT:-8100} --workers \${WORKERS:-1}
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

# --- Done ---

echo ""
echo "=== CapaRAG service installed ==="
echo ""
echo "Install dir:  ${INSTALL_DIR}"
echo "Unit file:    ${UNIT_FILE}"
echo "Service user: ${SERVICE_USER}"
echo ""
echo "Next steps:"
echo "  1. Copy project files to ${INSTALL_DIR}"
echo "  2. Copy .env to ${INSTALL_DIR}/.env (chmod 600)"
echo "  3. Run: cd ${INSTALL_DIR} && uv sync --no-dev"
echo "  4. systemctl enable ${SERVICE_NAME}   # start on boot"
echo "  5. systemctl start ${SERVICE_NAME}    # start now"
echo ""
echo "Useful commands:"
echo "  systemctl status ${SERVICE_NAME}"
echo "  journalctl -u ${SERVICE_NAME} -f"
echo "  systemctl restart ${SERVICE_NAME}"
