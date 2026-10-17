import os
import subprocess
import shlex
import json
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("ubuntu_executor")

UBUNTU_ACTIONS = {
    "UBUNTU_COMMAND", "RUN_COMMAND",
    "UBUNTU_OPEN_APP", "OPEN_DESKTOP_APP",
    "UBUNTU_NOTIFICATION", "SEND_NOTIFICATION",
    "UBUNTU_VOLUME", "VOLUME_UP", "VOLUME_DOWN", "VOLUME_MUTE",
    "UBUNTU_STATUS", "CHECK_STATUS", "CHECK_SERVICES",
    "UBUNTU_SCREENSHOT", "TAKE_SCREENSHOT",
    "UBUNTU_LOCK", "LOCK_SCREEN"
}

def is_ubuntu_action(action_name: str) -> bool:
    if not action_name:
        return False
    return action_name.startswith("UBUNTU_") or action_name in UBUNTU_ACTIONS


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

    if act == "SEND_NOTIFICATION":
        title = params.get("title", "🐰 Rabbit Assistant")
        body = params.get("message", "হ্যালো ইমন স্যার!")
        cmd = f'notify-send "{shlex.quote(title)}" "{shlex.quote(body)}"'
        return execute_system_command(cmd)

    elif act == "OPEN_BROWSER":
        url = params.get("url", "https://google.com")
        cmd = f'google-chrome "{shlex.quote(url)}" > /dev/null 2>&1 &'
        return execute_system_command(cmd)

    elif act == "TERMINAL_RUN":
        cmd_text = params.get("command", "")
        if not cmd_text:
            return (False, "কোনো কমান্ড পাওয়া যায়নি।")
        return execute_system_command(cmd_text)

    elif act == "SET_VOLUME":
        vol = params.get("volume", "50%")
        cmd = f"amixer -D pulse sset Master {shlex.quote(str(vol))}"
        return execute_system_command(cmd)

    elif act == "LOCK_SCREEN":
        cmd = "loginctl lock-session"
        return execute_system_command(cmd)

    elif act == "RESTART_SERVICE":
        svc = params.get("service", "rabbit-gateway.service")
        cmd = f"systemctl --user restart {shlex.quote(svc)}"
        return execute_system_command(cmd)

    return (False, f"অজানা উবুন্টু অ্যাকশন: {action}")
