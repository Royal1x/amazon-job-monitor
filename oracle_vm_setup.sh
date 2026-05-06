#!/usr/bin/env bash

set -euo pipefail

# This script is meant to run on an Oracle Cloud Linux VM.
# It installs Python tools, creates the virtual environment,
# installs the project packages, and sets up systemd so the
# job monitor starts automatically at boot.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="amazon-job-monitor"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
PYTHON_BIN="${PROJECT_DIR}/.venv/bin/python"
PIP_BIN="${PROJECT_DIR}/.venv/bin/pip"
CURRENT_USER="$(id -un)"

echo "Project directory: ${PROJECT_DIR}"
echo "Linux user: ${CURRENT_USER}"

echo "Installing system packages..."
sudo apt update
sudo apt install -y python3 python3-venv python3-pip

if [ ! -d "${PROJECT_DIR}/.venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv "${PROJECT_DIR}/.venv"
fi

echo "Installing Python packages..."
"${PIP_BIN}" install --upgrade pip
"${PIP_BIN}" install -r "${PROJECT_DIR}/requirements.txt"

if [ ! -f "${PROJECT_DIR}/.env" ]; then
  cp "${PROJECT_DIR}/.env.example" "${PROJECT_DIR}/.env"
  echo
  echo "A new .env file was created from .env.example."
  echo "Add your real Twilio values to ${PROJECT_DIR}/.env, then run this script again."
  exit 0
fi

echo "Writing systemd service..."
sudo tee "${SERVICE_FILE}" > /dev/null <<EOF
[Unit]
Description=Amazon Warehouse Job Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${PROJECT_DIR}
Environment=PYTHONUNBUFFERED=1
ExecStart=${PYTHON_BIN} -u ${PROJECT_DIR}/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "Starting the service..."
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

echo
echo "Setup complete."
echo "Useful commands:"
echo "  sudo systemctl status ${SERVICE_NAME}"
echo "  sudo journalctl -u ${SERVICE_NAME} -f"
echo "  sudo systemctl restart ${SERVICE_NAME}"
