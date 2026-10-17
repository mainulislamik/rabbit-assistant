#!/usr/bin/env bash
# Rabbit Assistant // JARVIS Desktop App for Ubuntu
# Author: Imon Sir & Rabbit Voice OS

export WAYLAND_DISPLAY=wayland-0
export XDG_RUNTIME_DIR=/run/user/1000
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus"

# Check if Rabbit Gateway service is running
if ! systemctl --user is-active --quiet rabbit-gateway.service; then
    systemctl --user start rabbit-gateway.service
    sleep 1
fi

APP_URL="http://127.0.0.1:8899/"
PROFILE_DIR="/home/imon/.config/rabbit-assistant-desktop"
mkdir -p "$PROFILE_DIR"

if command -v google-chrome &> /dev/null; then
    exec /usr/bin/google-chrome \
        --ozone-platform=wayland \
        --app="$APP_URL" \
        --user-data-dir="$PROFILE_DIR" \
        --class="rabbit-assistant" \
        --window-size=1100,850 \
        --window-name="Rabbit Assistant // JARVIS" \
        "$@"
elif command -v chromium &> /dev/null; then
    exec /snap/bin/chromium \
        --ozone-platform=wayland \
        --app="$APP_URL" \
        --user-data-dir="$PROFILE_DIR" \
        --class="rabbit-assistant" \
        --window-size=1100,850 \
        "$@"
else
    xdg-open "$APP_URL"
fi
