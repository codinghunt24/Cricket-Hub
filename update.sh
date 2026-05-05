#!/bin/bash

PROJECT_DIR="/home/digitalcash24/cricbuzz-score.com"
VENV_DIR="$PROJECT_DIR/venv"

echo "==============================="
echo "  Cricbuzz Score - Updater"
echo "==============================="

# Step 1: Go to project folder
cd "$PROJECT_DIR" || { echo "ERROR: Project folder not found!"; exit 1; }
echo "[1/4] Project folder: $PROJECT_DIR"

# Step 2: Pull latest code from GitHub
echo "[2/4] Pulling latest code from GitHub..."
git pull origin main
if [ $? -ne 0 ]; then
    echo "ERROR: git pull failed! Check your internet or git config."
    exit 1
fi
echo "      Code updated successfully!"

# Step 3: Install/update Python packages in venv
echo "[3/4] Updating Python packages..."
if [ -f "$VENV_DIR/bin/pip" ]; then
    "$VENV_DIR/bin/pip" install -r requirements.txt -q 2>/dev/null || \
    "$VENV_DIR/bin/pip" install -e . -q 2>/dev/null || \
    echo "      (No requirements file found, skipping)"
else
    echo "      (venv pip not found, skipping)"
fi

# Step 4: Restart the app
echo "[4/4] Restarting application..."

# Try systemd first
if systemctl list-units --type=service 2>/dev/null | grep -q "cricbuzz\|gunicorn\|cricket"; then
    SERVICE=$(systemctl list-units --type=service | grep -E "cricbuzz|gunicorn|cricket" | awk '{print $1}' | head -1)
    sudo systemctl restart "$SERVICE"
    echo "      Restarted systemd service: $SERVICE"

# Try supervisor
elif command -v supervisorctl &>/dev/null; then
    sudo supervisorctl restart all
    echo "      Restarted via supervisor"

# Try gunicorn process kill + restart
elif pgrep -f "gunicorn.*main:app" > /dev/null; then
    pkill -f "gunicorn.*main:app"
    sleep 2
    cd "$PROJECT_DIR"
    "$VENV_DIR/bin/gunicorn" --bind 0.0.0.0:5000 --workers 4 --timeout 300 main:app --daemon
    echo "      Gunicorn restarted!"

else
    echo ""
    echo "  WARNING: Could not auto-restart. Please restart manually."
    echo "  Command: cd $PROJECT_DIR && $VENV_DIR/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 300 main:app"
fi

echo ""
echo "==============================="
echo "  Update Complete!"
echo "==============================="
