import os
import subprocess
import shlex
import json
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("ubuntu_executor")

UBUNTU_ACTIONS = {
    "UBUNTU_COMMAND", "RUN_COMMAND", "TERMINAL_RUN",
    "UBUNTU_OPEN_APP", "OPEN_DESKTOP_APP", "OPEN_APP", "OPEN_BROWSER",
    "UBUNTU_NOTIFICATION", "SEND_NOTIFICATION",
    "UBUNTU_VOLUME", "SET_VOLUME", "VOLUME_UP", "VOLUME_DOWN", "VOLUME_MUTE",
    "UBUNTU_STATUS", "CHECK_STATUS", "CHECK_SERVICES",
    "UBUNTU_SCREENSHOT", "TAKE_SCREENSHOT",
    "UBUNTU_LOCK", "LOCK_SCREEN"
}

def is_ubuntu_action(action_name: str) -> bool:
    if not action_name:
        return False
    act = action_name.upper()
    return act.startswith("UBUNTU_") or act in UBUNTU_ACTIONS

# Pre-configured environment variables for GUI & Wayland/X11
USER_ENV = os.environ.copy()
USER_ENV.setdefault("USER", "imon")
USER_ENV.setdefault("HOME", "/home/imon")
USER_ENV.setdefault("XDG_RUNTIME_DIR", "/run/user/1000")
USER_ENV.setdefault("DBUS_SESSION_BUS_ADDRESS", "unix:path=/run/user/1000/bus")
USER_ENV.setdefault("WAYLAND_DISPLAY", "wayland-0")
USER_ENV.setdefault("DISPLAY", ":0")

def execute_system_command(command: str, timeout: int = 25) -> Tuple[bool, str]:
    """Executes a command safely under the user's environment."""
    try:
        res = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=USER_ENV,
            cwd="/home/imon"
        )
        output = (res.stdout or "") + (res.stderr or "")
        return (res.returncode == 0, output.strip())
    except subprocess.TimeoutExpired:
        return (False, "কমান্ড এক্সিকিউশন টাইমআউট হয়েছে (২৫ সেকেন্ড)।")
    except Exception as e:
        return (False, f"কমান্ড ব্যর্থ হয়েছে: {str(e)}")

def handle_ubuntu_intent(action: str, params: Dict[str, Any] = None) -> Tuple[bool, str]:
    params = params or {}
    act = action.upper()

    # 1. Desktop Notification
    if act in ("UBUNTU_NOTIFICATION", "SEND_NOTIFICATION"):
        title = params.get("title", "🐰 Rabbit Assistant")
        body = params.get("message", "ইমন স্যার, নির্দেশ সম্পন্ন হয়েছে।")
        # notify-send with icon
        cmd = f'notify-send -i /home/imon/.local/share/icons/hicolor/256x256/apps/rabbit-assistant.png "{title}" "{body}"'
        return execute_system_command(cmd)

    # 2. Run Shell/Terminal Command
    elif act in ("UBUNTU_COMMAND", "RUN_COMMAND", "TERMINAL_RUN"):
        cmd_text = params.get("command", "")
        if not cmd_text:
            return (False, "কোনো কমান্ড পাওয়া যায়নি।")
        logger.info(f"Running Ubuntu shell command: {cmd_text}")
        return execute_system_command(cmd_text)

    # 3. Open Desktop Applications
    elif act in ("UBUNTU_OPEN_APP", "OPEN_DESKTOP_APP", "OPEN_APP", "OPEN_BROWSER"):
        app_name = params.get("app_name", params.get("app", "")).lower()
        url = params.get("url", "")
        
        if "chrome" in app_name or "browser" in app_name or url:
            target_url = url if url else "https://google.com"
            cmd = f'google-chrome --ozone-platform=wayland "{target_url}" > /dev/null 2>&1 &'
        elif "code" in app_name or "vscode" in app_name:
            cmd = 'code > /dev/null 2>&1 &'
        elif "terminal" in app_name:
            cmd = 'gnome-terminal > /dev/null 2>&1 &'
        elif "anydesk" in app_name:
            cmd = '/home/imon/anydesk.sh > /dev/null 2>&1 &'
        elif "winbox" in app_name:
            cmd = '/home/imon/winbox.sh > /dev/null 2>&1 &'
        elif "file" in app_name or "nautilus" in app_name:
            cmd = 'nautilus /home/imon > /dev/null 2>&1 &'
        elif app_name:
            cmd = f'{shlex.quote(app_name)} > /dev/null 2>&1 &'
        else:
            return (False, "অ্যাপের নাম পাওয়া যায়নি।")
            
        return execute_system_command(cmd)

    # 4. Volume Control
    elif act in ("UBUNTU_VOLUME", "SET_VOLUME", "VOLUME_UP", "VOLUME_DOWN", "VOLUME_MUTE"):
        vol = params.get("volume", "")
        if act == "VOLUME_UP" or vol == "+10%" or vol == "up":
            cmd = "amixer -D pulse sset Master 10%+"
        elif act == "VOLUME_DOWN" or vol == "-10%" or vol == "down":
            cmd = "amixer -D pulse sset Master 10%-"
        elif act == "VOLUME_MUTE" or vol == "mute":
            cmd = "amixer -D pulse sset Master toggle"
        elif vol:
            cmd = f"amixer -D pulse sset Master {shlex.quote(str(vol))}"
        else:
            cmd = "amixer -D pulse sset Master 50%"
        return execute_system_command(cmd)

    # 5. System Health / Status
    elif act in ("UBUNTU_STATUS", "CHECK_STATUS", "CHECK_SERVICES"):
        cmd = "free -h | grep Mem && df -h / | tail -n 1 && uptime -p"
        ok, out = execute_system_command(cmd)
        if ok:
            lines = out.splitlines()
            mem = lines[0] if len(lines) > 0 else ""
            disk = lines[1] if len(lines) > 1 else ""
            up = lines[2] if len(lines) > 2 else ""
            summary = f"সিস্টেম স্ট্যাটাস: আপটাইম {up}। মেমোরি: {mem}। ডিস্ক: {disk}।"
            return (True, summary)
        return (False, out)

    # 6. Lock Desktop Screen
    elif act in ("UBUNTU_LOCK", "LOCK_SCREEN"):
        cmd = "loginctl lock-session"
        return execute_system_command(cmd)

    # 7. Take Screenshot
    elif act in ("UBUNTU_SCREENSHOT", "TAKE_SCREENSHOT"):
        dest = "/home/imon/rabbit-assistant/server/static/screenshots/screenshot.png"
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        # Using Mutter/Xwayland auth
        cmd = f'DISPLAY=:0 XAUTHORITY=$(ls -t /run/user/1000/.mutter-Xwaylandauth* 2>/dev/null | head -n 1) import -window root {dest} 2>/dev/null || grim {dest} 2>/dev/null'
        ok, _ = execute_system_command(cmd)
        if os.path.exists(dest):
            return (True, f"স্ক্রিনশট সফলভাবে সংরক্ষিত হয়েছে: {dest}")
        return (False, "স্ক্রিনশট নেওয়া সম্ভব হয়নি।")

    return (False, f"অজানা উবুন্টু অ্যাকশন: {action}")
