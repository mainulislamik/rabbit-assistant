"""Rabbit AI Tools Engine
Provides full OS-level, file system, project context, and live web search tools to Rabbit Assistant.
"""

import os
import sys
import subprocess
import shutil
import glob
import re
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional

UBUNTU_ENV = {
    **os.environ,
    "XDG_RUNTIME_DIR": "/run/user/1000",
    "WAYLAND_DISPLAY": "wayland-0",
    "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
    "PATH": f"/home/imon/.hermes/hermes-agent/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:{os.environ.get('PATH', '')}"
}

# ---------------------------------------------------------------------------
# Tool 1: Shell Execution
# ---------------------------------------------------------------------------
def execute_bash(command: str, workdir: str = "/home/imon", timeout: int = 60, **kwargs) -> Dict[str, Any]:
    """Execute a bash shell command on the host."""
    try:
        proc = subprocess.run(
            ["/usr/bin/bash", "-c", command],
            cwd=workdir if os.path.exists(workdir) else "/home/imon",
            env=UBUNTU_ENV,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        stdout = proc.stdout
        stderr = proc.stderr
        
        # Truncate if output exceeds 8000 chars
        if len(stdout) > 8000:
            stdout = stdout[:4000] + "\n...[truncated output]...\n" + stdout[-4000:]
        if len(stderr) > 2000:
            stderr = stderr[:1000] + "\n...[truncated stderr]...\n" + stderr[-1000:]

        return {
            "exit_code": proc.returncode,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "success": proc.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "stdout": "", "stderr": f"Command timed out after {timeout} seconds", "success": False}
    except Exception as e:
        return {"exit_code": -1, "stdout": "", "stderr": str(e), "success": False}

# ---------------------------------------------------------------------------
# Tool 2: File Operations
# ---------------------------------------------------------------------------
def read_file(path: str, offset: int = 1, limit: int = 150, **kwargs) -> Dict[str, Any]:
    """Read a text or code file with 1-based line numbers and pagination."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(abs_path):
        return {"error": f"File not found: {abs_path}", "success": False}
    if os.path.isdir(abs_path):
        return {"error": f"Path is a directory: {abs_path}", "success": False}
    
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        start_idx = max(0, offset - 1)
        end_idx = min(total_lines, start_idx + limit)
        
        selected = lines[start_idx:end_idx]
        formatted = "".join(f"{i + start_idx + 1:4d}| {line}" for i, line in enumerate(selected))
        
        return {
            "path": abs_path,
            "total_lines": total_lines,
            "offset": offset,
            "limit": limit,
            "content": formatted,
            "success": True
        }
    except Exception as e:
        return {"error": str(e), "success": False}

def write_file(path: str, content: str, **kwargs) -> Dict[str, Any]:
    """Write or overwrite content to a file."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    try:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"path": abs_path, "bytes_written": len(content), "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}

def patch_file(path: str, old_string: str, new_string: str, **kwargs) -> Dict[str, Any]:
    """Targeted find and replace in a file."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(abs_path):
        return {"error": f"File not found: {abs_path}", "success": False}
    
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if old_string not in content:
            return {"error": "old_string not found in file", "success": False}
        
        count = content.count(old_string)
        if count > 1:
            return {"error": f"old_string occurs {count} times (not unique). Provide more surrounding context.", "success": False}
        
        updated = content.replace(old_string, new_string, 1)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(updated)
            
        return {"path": abs_path, "replaced": True, "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}

def search_files(pattern: str, path: str = "/home/imon", target: str = "content", limit: int = 30, **kwargs) -> Dict[str, Any]:
    """Search file contents (regex) or find files by name glob."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    try:
        if target == "files":
            cmd = f"find {abs_path} -maxdepth 4 -name '*{pattern}*' | head -n {limit}"
        else:
            cmd = f"grep -rnI --exclude-dir='.git' --exclude-dir='node_modules' --exclude-dir='venv' '{pattern}' {abs_path} 2>/dev/null | head -n {limit}"
        
        res = execute_bash(cmd)
        matches = [line.strip() for line in res.get("stdout", "").split("\n") if line.strip()]
        return {"matches": matches, "total": len(matches), "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}

# ---------------------------------------------------------------------------
# Tool 3: Live Web Search & Scrape
# ---------------------------------------------------------------------------
def web_search(query: str, limit: int = 5, **kwargs) -> Dict[str, Any]:
    """Search DuckDuckGo live for real-time web results."""
    try:
        url = "https://lite.duckduckgo.com/lite/"
        data = urllib.parse.urlencode({"q": query}).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0"}
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        results = []
        for row in re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL):
            link_m = re.search(r'<a[^>]+href=[\"\']([^\"\']+)[\"\'][^>]*class=[\"\']result-link[\"\'][^>]*>(.*?)</a>', row, re.DOTALL)
            if not link_m:
                link_m = re.search(r'<a[^>]+class=[\"\']result-link[\"\'][^>]+href=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a>', row, re.DOTALL)
            snip_m = re.search(r'class=[\"\']result-snippet[\"\'][^>]*>(.*?)</td>', row, re.DOTALL)
            if link_m:
                href = link_m.group(1)
                title = re.sub(r'<[^>]+>', '', link_m.group(2)).strip()
                results.append({"title": title, "url": href, "snippet": ""})
            elif snip_m and results:
                snip = re.sub(r'<[^>]+>', '', snip_m.group(1)).strip()
                results[-1]["snippet"] = snip
                if len(results) >= limit:
                    break

        return {"query": query, "results": results[:limit], "count": len(results[:limit]), "success": True}
    except Exception as e:
        return {"query": query, "error": str(e), "results": [], "success": False}

def web_extract(url: str, char_limit: int = 4000, **kwargs) -> Dict[str, Any]:
    """Extract clean text content from a web URL."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0"}
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        
        # Clean scripts, styles, navigations
        html = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style.*?</style>', '', html, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return {
            "url": url,
            "content": text[:char_limit],
            "total_chars": len(text),
            "truncated": len(text) > char_limit,
            "success": True
        }
    except Exception as e:
        return {"url": url, "error": str(e), "success": False}

# ---------------------------------------------------------------------------
# Tool 4: System Health & Hardware Monitoring
# ---------------------------------------------------------------------------
def get_system_health(**kwargs) -> Dict[str, Any]:
    """Get system health metrics: CPU, RAM, Disk, Uptime, Host IP."""
    try:
        # Memory
        mem_res = execute_bash("free -h | awk 'NR==2{print $2,$3,$7}'")
        mem_parts = mem_res.get("stdout", "").split()
        total_ram = mem_parts[0] if len(mem_parts) > 0 else "Unknown"
        used_ram = mem_parts[1] if len(mem_parts) > 1 else "Unknown"
        avail_ram = mem_parts[2] if len(mem_parts) > 2 else "Unknown"
        
        # Disk
        disk_res = execute_bash("df -h / | awk 'NR==2{print $2,$3,$4,$5}'")
        disk_parts = disk_res.get("stdout", "").split()
        total_disk = disk_parts[0] if len(disk_parts) > 0 else "Unknown"
        used_disk = disk_parts[1] if len(disk_parts) > 1 else "Unknown"
        avail_disk = disk_parts[2] if len(disk_parts) > 2 else "Unknown"
        disk_pct = disk_parts[3] if len(disk_parts) > 3 else "Unknown"
        
        # Uptime
        uptime_res = execute_bash("uptime -p")
        uptime_str = uptime_res.get("stdout", "").strip()
        
        # IP Address
        ip_res = execute_bash("hostname -I | awk '{print $1}'")
        host_ip = ip_res.get("stdout", "").strip()

        return {
            "host": "imon-OptiPlex-7060 (Ubuntu 24.04)",
            "cpu": "Intel Core i7-10th Gen",
            "gpu": "Intel Arc A770 16GB / UHD 630",
            "ip_address": host_ip,
            "ram": {"total": total_ram, "used": used_ram, "available": avail_ram},
            "disk": {"total": total_disk, "used": used_disk, "available": avail_disk, "use_percent": disk_pct},
            "uptime": uptime_str,
            "success": True
        }
    except Exception as e:
        return {"error": str(e), "success": False}

# ---------------------------------------------------------------------------
# Tool 5: Project Context & Knowledge
# ---------------------------------------------------------------------------
def get_project_context(**kwargs) -> Dict[str, Any]:
    """Retrieve active projects portfolio and operational ports for Imon Sir."""
    return {
        "owner": "Imon Khan (ইমন স্যার) - IT Specialist & Lead Architect",
        "primary_server": "OptiPlex-7060 Ubuntu (192.168.0.100)",
        "projects": [
            {
                "name": "StockWhisk SaaS",
                "ip": "163.227.239.114",
                "domain": "stockwhisk.com",
                "stack": "Django Backend (Docker) + Next.js Frontend",
                "modules": "Fashion, Online, Electronics, Universal, Manufacturing (28 modules)"
            },
            {
                "name": "AmarPDF",
                "ports": "Caddy (:80/:443) -> Next.js (:3009) + FastAPI (:8095)",
                "features": "ATS resume score, Office2PDF, Google AdSense (pub-2861472312283458)"
            },
            {
                "name": "Toto Cloud",
                "path": "/home/imon/toto-datacenter",
                "ports": ":3099 Dashboard, Proxmox VE :8006",
                "features": "Enterprise Cloud OS v4.0, Corosync HA, K3s, Serverless PaaS, S3, Docker"
            },
            {
                "name": "Picasa 3D & ERP",
                "ports": ":3095 (Portal), :8000 (ERP), :3090 (Web)",
                "features": "3D photogrammetry portal, HRMS RBAC framework"
            },
            {
                "name": "Arcadex",
                "ports": ":3080 Docker (arcade-hub)",
                "features": "5,500 games, PS2/PSP/PSX/GBA/J2ME WASM emulation"
            },
            {
                "name": "WhatsApp CRM",
                "ports": ":3050 (Next.js), :8050 (FastAPI), :5001 (Baileys WhatsApp)",
                "phone": "01613511887"
            },
            {
                "name": "Rabbit Assistant (This System)",
                "ports": ":8899 (Voice Gateway & HUD)",
                "features": "Ultra-fast Bengali AI assistant, Wayland Ubuntu desktop control, multi-device continuity"
            }
        ],
        "success": True
    }

# ---------------------------------------------------------------------------
# Tool 6: Desktop & Wayland Control
# ---------------------------------------------------------------------------
def control_desktop(action: str, value: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Control Ubuntu Wayland desktop volume, apps, lock, notifications, screenshots."""
    from ubuntu_executor import handle_ubuntu_intent
    
    intent_map = {
        "volume_up": "UBUNTU_VOLUME",
        "volume_down": "UBUNTU_VOLUME",
        "mute": "UBUNTU_VOLUME",
        "lock": "UBUNTU_LOCK",
        "screenshot": "UBUNTU_SCREENSHOT",
        "notify": "UBUNTU_NOTIFICATION",
        "open_app": "UBUNTU_OPEN_APP"
    }
    
    act_type = intent_map.get(action, "UBUNTU_COMMAND")
    params = {}
    if action == "volume_up":
        params = {"direction": "up", "step": 5}
    elif action == "volume_down":
        params = {"direction": "down", "step": 5}
    elif action == "mute":
        params = {"direction": "mute"}
    elif action == "notify":
        params = {"title": "র্যাবিট নোটিফিকেশন", "message": value or "ইমন স্যারের নির্দেশ কার্যকর হয়েছে।"}
    elif action == "open_app":
        params = {"app": value or "terminal"}
        
    ok, out = handle_ubuntu_intent(act_type, params)
    return {"action": action, "output": out, "success": ok}

# ---------------------------------------------------------------------------
# Tool 7: Long-Term Personal Knowledge Memory
# ---------------------------------------------------------------------------
def recall_personal_memory(query: str, **kwargs) -> Dict[str, Any]:
    """Recall verified personal facts, projects, CV details, AdSense IDs, and servers for Imon Sir."""
    try:
        import rabbit_memory
        return rabbit_memory.search_personal_memory(query)
    except Exception as e:
        return {"error": str(e), "found": False}

# ---------------------------------------------------------------------------
# Tool 8: Autonomous Multi-Agent Dev Team Dispatcher
# ---------------------------------------------------------------------------
def dispatch_dev_team(task_description: str, project_name: str = "general", **kwargs) -> Dict[str, Any]:
    """Dispatch a software engineering task to the autonomous 5-member Dev Team (PM, Backend, Frontend, DevOps, QA)."""
    workspace = Path("/home/imon/.hermes/agent-team/workspace")
    workspace.mkdir(parents=True, exist_ok=True)
    script = Path("/home/imon/.hermes/agent-team/dev-team.sh")
    
    task_file = workspace / "current_task.txt"
    task_file.write_text(f"Project: {project_name}\nTask: {task_description}\nClient: Imon Sir\n")
    
    # Launch in background
    cmd = f"nohup bash {script} dev-team '{task_description}' > {workspace}/team_runner.log 2>&1 &"
    proc = subprocess.Popen(cmd, shell=True, cwd="/home/imon")
    
    return {
        "status": "dispatched",
        "message": f"ইমন স্যার, ৫ সদস্যের অটোনোমাস ডেভ টিমকে নির্দেশ দেওয়া হয়েছে। প্রজেক্ট: {project_name}। ব্যাকগ্রাউন্ডে কাজ শুরু হয়েছে।",
        "pid": proc.pid,
        "workspace": str(workspace)
    }

# ---------------------------------------------------------------------------
# Tool 9: Launch Desktop Apps & Media
# ---------------------------------------------------------------------------
def launch_desktop_app(target: str, **kwargs) -> Dict[str, Any]:
    """Launch Ubuntu desktop applications, VS Code workspaces, Chrome URLs, or background music."""
    from ubuntu_executor import handle_ubuntu_intent
    target_lower = target.lower()
    
    if "youtube" in target_lower or "ইউটিউব" in target_lower:
        url = "https://www.youtube.com"
        ok, out = handle_ubuntu_intent("UBUNTU_OPEN_APP", {"url": url})
        return {"target": target, "action": "open_youtube", "success": ok, "message": "গুগল ক্রোমে ইউটিউব ওপেন করা হয়েছে।"}
    elif "music" in target_lower or "lofi" in target_lower or "গান" in target_lower:
        url = "https://www.youtube.com/results?search_query=lofi+coding+music+live"
        ok, out = handle_ubuntu_intent("UBUNTU_OPEN_APP", {"url": url})
        return {"target": target, "action": "open_music", "success": ok, "message": "ইউটিউবে ব্যাকগ্রাউন্ড কোডিং মিউজিক চালু করা হয়েছে।"}
    elif "vscode" in target_lower or "code" in target_lower:
        ok, out = handle_ubuntu_intent("UBUNTU_OPEN_APP", {"app": "code"})
        return {"target": target, "action": "open_vscode", "success": ok, "message": "ভিএস কোড এডিটর লঞ্চ করা হয়েছে।"}
    elif "chrome" in target_lower or "browser" in target_lower or "http" in target_lower:
        ok, out = handle_ubuntu_intent("UBUNTU_OPEN_APP", {"app": "chrome", "url": target if "http" in target else ""})
        return {"target": target, "action": "open_chrome", "success": ok, "message": "গুগল ক্রোম ব্রাউজার ওপেন করা হয়েছে।"}
    else:
        ok, out = handle_ubuntu_intent("UBUNTU_OPEN_APP", {"app": target})
        return {"target": target, "action": "open_app", "success": ok, "output": out}

# ---------------------------------------------------------------------------
# Tool 10: Multimodal Vision Analysis
# ---------------------------------------------------------------------------
def analyze_visual_image(image_base64: str, prompt: str = "Analyze this visual image in detail in Bengali", **kwargs) -> Dict[str, Any]:
    """Analyze an image using Gemini Multimodal Vision and return visual reasoning in Bengali."""
    import httpx
    omni_key = None
    try:
        cfg = json.loads(Path("/home/imon/.hermes/config.json").read_text())
        omni_key = cfg.get("omniroute", {}).get("api_key")
    except Exception:
        pass
    if not omni_key:
        omni_key = os.getenv("OMNI_KEY")
        
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {omni_key}"}
    payload = {
        "model": "agy/gemini-3.8-flash-tiered",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"You are Rabbit Vision AI assisting Imon Sir (ইমন স্যার). {prompt}. Respond in elegant, polite Bengali script."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                ]
            }
        ],
        "temperature": 0.2
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post("http://127.0.0.1:20128/v1/chat/completions", headers=headers, json=payload)
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"]["content"]
                return {"success": True, "analysis": content}
            return {"success": False, "error": f"HTTP {r.status_code}: {r.text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def analyze_image_with_vision(image_base64: str, prompt: str = "এই ছবিটি দেখে বিস্তারিত বলুন", **kwargs) -> str:
    res = analyze_visual_image(image_base64, prompt, **kwargs)
    if res.get("success"):
        return res.get("analysis", "ছবিটি সফলভাবে বিশ্লেষণ করা হয়েছে।")
    return f"ছবিটি বিশ্লেষণ করার সময় সমস্যা হয়েছে: {res.get('error', 'অজানা ত্রুটি')}"

# ---------------------------------------------------------------------------
# Tool 11: Network & MikroTik Sentinel
# ---------------------------------------------------------------------------
def inspect_network_health(**kwargs) -> Dict[str, Any]:
    """Inspect local MikroTik router gateway latency, public internet health, and connected LAN devices."""
    try:
        from network_sentinel import check_network_health
        return check_network_health()
    except Exception as e:
        return {"error": str(e), "health": "UNKNOWN"}

# ---------------------------------------------------------------------------
# Tool 12: Code Sentinel & Project Syntax Auditor
# ---------------------------------------------------------------------------
def audit_project_code(project_path: str = "/home/imon/rabbit-assistant", **kwargs) -> Dict[str, Any]:
    """Audit project code quality, check for Python/syntax errors, and review uncommitted git diffs."""
    try:
        from code_sentinel import run_project_code_audit
        return run_project_code_audit(project_path)
    except Exception as e:
        return {"error": str(e), "healthy": False}

# ---------------------------------------------------------------------------
# Tool 13: Remote Channel Notification & Alert Dispatcher
# ---------------------------------------------------------------------------
def send_remote_notification(message: str, channel: str = "all", level: str = "info", **kwargs) -> Dict[str, Any]:
    """Send an alert or notification to remote channels (Telegram, WhatsApp, Webhooks) and logs."""
    try:
        from rabbit_bridge import dispatch_remote_alert
        return dispatch_remote_alert(message, channel, level)
    except Exception as e:
        return {"error": str(e), "status": "failed"}

# ---------------------------------------------------------------------------
# Tool Specifications for LLM Function Calling (OpenAI / Gemini format)
# ---------------------------------------------------------------------------
RABBIT_TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "execute_bash",
            "description": "Execute any Linux shell / bash command on the Ubuntu host (e.g. systemctl status/restart, docker ps, free -h, df -h, ps aux, git commands, python scripts, curl, network diagnosis). Always returns stdout, stderr, and exit code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact shell command to run in bash."
                    },
                    "workdir": {
                        "type": "string",
                        "description": "Optional working directory (defaults to /home/imon)."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read content of a file on the Ubuntu filesystem with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute file path (e.g. /home/imon/...) to read."},
                    "offset": {"type": "integer", "description": "1-based starting line number (default: 1)."},
                    "limit": {"type": "integer", "description": "Maximum number of lines to read (default: 150)."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite content to a file at an absolute path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute destination file path."},
                    "content": {"type": "string", "description": "Complete text or code content to write."}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "patch_file",
            "description": "Targeted find and replace of unique text in a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to patch."},
                    "old_string": {"type": "string", "description": "Exact text to find and replace."},
                    "new_string": {"type": "string", "description": "Replacement text."}
                },
                "required": ["path", "old_string", "new_string"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search file contents by regex pattern or find files by name glob.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex or glob string to search for."},
                    "path": {"type": "string", "description": "Directory to search in (default: /home/imon)."},
                    "target": {"type": "string", "enum": ["content", "files"], "description": "'content' to grep inside files, 'files' to find files by name."}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the live web using DuckDuckGo for recent news, facts, weather, technical documentation, or real-time information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search keywords or query."},
                    "limit": {"type": "integer", "description": "Maximum results to return (default: 5)."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_extract",
            "description": "Fetch and extract text content from any website URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to extract content from."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_health",
            "description": "Get current host system telemetry: CPU, RAM usage, NVMe disk usage, system uptime, and local IP address.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_project_context",
            "description": "Get full information and port mapping of Imon Sir's projects (StockWhisk, AmarPDF, Toto Cloud, Picasa, Arcadex, WhatsApp CRM).",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_desktop",
            "description": "Control Ubuntu Wayland desktop functions (volume_up, volume_down, mute, notify, open_app, lock, screenshot).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["volume_up", "volume_down", "mute", "notify", "open_app", "lock", "screenshot"],
                        "description": "Desktop action to execute."
                    },
                    "value": {
                        "type": "string",
                        "description": "Optional value (e.g. app name for open_app, or message for notify)."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall_personal_memory",
            "description": "Recall long-term verified facts, career background, CV, AdSense IDs, and infrastructure details for Imon Sir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The concept, project, or detail to look up (e.g. 'AdSense', 'Shopping Zone BD', 'Arcadex', 'StockWhisk', 'OptiPlex specs')."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "dispatch_dev_team",
            "description": "Trigger the autonomous 5-member AI Dev Team (PM, Backend, Frontend, DevOps, QA) to solve a complex coding task or feature.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "Detailed task description for the engineering team."
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Target project name (e.g. 'AmarPDF', 'StockWhisk', 'TryCalc', 'MessSaaS', 'General')."
                    }
                },
                "required": ["task_description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "launch_desktop_app",
            "description": "Launch Ubuntu desktop applications, VS Code workspaces, Chrome browser, or play coding music on YouTube.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Target to open or play: 'vscode', 'chrome', 'music', 'lofi', 'terminal', 'nautilus', etc."
                    }
                },
                "required": ["target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_visual_image",
            "description": "Perform multimodal AI visual inspection and reasoning on an image or screenshot in Bengali.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_base64": {
                        "type": "string",
                        "description": "Base64-encoded image string."
                    },
                    "prompt": {
                        "type": "string",
                        "description": "What to inspect or question about the image."
                    }
                },
                "required": ["image_base64"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_network_health",
            "description": "Inspect local MikroTik router gateway latency, internet connectivity, and connected LAN devices.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "audit_project_code",
            "description": "Run an automated code health audit on a local project (checks Python syntax errors, git modified files, branch).",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Absolute path to project directory, default '/home/imon/rabbit-assistant'."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_remote_notification",
            "description": "Send a notification or alert to remote channels (Telegram, WhatsApp, or local alert journal).",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Alert message to send."
                    },
                    "channel": {
                        "type": "string",
                        "description": "Destination channel ('telegram', 'whatsapp', 'all')."
                    },
                    "level": {
                        "type": "string",
                        "description": "Alert level ('info', 'warning', 'critical')."
                    }
                },
                "required": ["message"]
            }
        }
    }
]

# ---------------------------------------------------------------------------
# Tool Dispatcher
# ---------------------------------------------------------------------------
TOOL_MAP = {
    "execute_bash": execute_bash,
    "read_file": read_file,
    "write_file": write_file,
    "patch_file": patch_file,
    "search_files": search_files,
    "web_search": web_search,
    "web_extract": web_extract,
    "get_system_health": get_system_health,
    "get_project_context": get_project_context,
    "control_desktop": control_desktop,
    "recall_personal_memory": recall_personal_memory,
    "dispatch_dev_team": dispatch_dev_team,
    "launch_desktop_app": launch_desktop_app,
    "analyze_visual_image": analyze_visual_image,
    "inspect_network_health": inspect_network_health,
    "audit_project_code": audit_project_code,
    "send_remote_notification": send_remote_notification,
}

def dispatch_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool by name with arguments and return result."""
    func = TOOL_MAP.get(tool_name)
    if not func:
        return {"error": f"Tool '{tool_name}' not found", "success": False}
    try:
        return func(**arguments)
    except Exception as e:
        return {"error": f"Execution error in '{tool_name}': {str(e)}", "success": False}
