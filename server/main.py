"""
Rabbit AI Voice Gateway & Orchestration Server
Jarvis-style Bangla Voice Assistant for Imon Sir
"""

import os
import sys
import json
import time
import uuid
import hashlib
import asyncio
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import websockets
import edge_tts
import urllib.request
import urllib.parse
import re
import httpx

from ubuntu_executor import handle_ubuntu_intent, is_ubuntu_action
import rabbit_tools

conversation_history: List[Dict[str, str]] = []



# ---------------------------------------------------------------------------
# Logging & Setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Rabbit] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("rabbit")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
AUDIO_CACHE_DIR = BASE_DIR / "audio_cache"
RELEASES_DIR = BASE_DIR / "releases"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
RELEASES_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Configuration & Hermes Tokens
# ---------------------------------------------------------------------------
HERMES_WS_URL = os.environ.get("HERMES_WS_URL", "ws://127.0.0.1:9119/api/ws")
HERMES_ENV_PATH = Path.home() / ".hermes" / "chat_bridge.env"

DEFAULT_TOKEN = "d600902c844f7ca8a54417d62f3dd30c44ad2a456b16926a"
if HERMES_ENV_PATH.exists():
    for line in HERMES_ENV_PATH.read_text().splitlines():
        if line.startswith("HERMES_DASHBOARD_SESSION_TOKEN="):
            DEFAULT_TOKEN = line.split("=", 1)[1].strip()

HERMES_TOKEN = os.environ.get("HERMES_DASHBOARD_SESSION_TOKEN", DEFAULT_TOKEN)
DEFAULT_VOICE = "bn-BD-PradeepNeural"  # Professional Bangla Male Voice
BACKUP_VOICE = "bn-BD-NabanitaNeural"

APP_VERSION_CODE = 100
APP_VERSION_NAME = "1.0.0"

RABBIT_SYSTEM_PROMPT = """You are "Rabbit" (র্যাবিট), a hyper-intelligent, proactive AI operating system created for Imon Sir (ইমন স্যার), inspired by Iron Man's JARVIS.
- Always address the user respectfully as 'স্যার' (Sir) or 'ইমন স্যার'.
- You communicate strictly in clear, refined, natural Bengali (বাংলা). No Banglish.
- Be crisp, confident, obedient, and precise, exactly like JARVIS.
- When the user asks you to perform an action on their phone or on the system, confirm politely in Bengali and append a single JSON action block in this format:
```json
{"action": "ACTION_NAME", "params": {}}
```
Supported Device Actions (executed on Android Phone):
- FLASHLIGHT_ON: {"action": "FLASHLIGHT_ON"}
- FLASHLIGHT_OFF: {"action": "FLASHLIGHT_OFF"}
- VOLUME_UP: {"action": "VOLUME_UP"}
- VOLUME_DOWN: {"action": "VOLUME_DOWN"}
- VOLUME_MUTE: {"action": "VOLUME_MUTE"}
- OPEN_APP: {"action": "OPEN_APP", "params": {"app_name": "whatsapp / youtube / settings"}}
- MAKE_CALL: {"action": "MAKE_CALL", "params": {"phone_number": "017XXXXXXXX"}}
- SEND_SMS: {"action": "SEND_SMS", "params": {"phone_number": "017XXXXXXXX", "message": "বার্তা"}}
- CHECK_BATTERY: {"action": "CHECK_BATTERY"}
- CHECK_DEVICE_INFO: {"action": "CHECK_DEVICE_INFO"}
- SELF_UPDATE: {"action": "SELF_UPDATE"}

Supported Ubuntu PC / Host Actions (executed directly on Imon Sir's Ubuntu computer):
- UBUNTU_COMMAND: {"action": "UBUNTU_COMMAND", "params": {"command": "ls -la"}} (can run ANY shell command: bash, git, docker, systemctl, etc.)
- UBUNTU_OPEN_APP: {"action": "UBUNTU_OPEN_APP", "params": {"app_name": "chrome / code / terminal / anydesk / winbox / files"}}
- UBUNTU_NOTIFICATION: {"action": "UBUNTU_NOTIFICATION", "params": {"title": "র্যাবিট", "message": "বার্তার বিষয়"}}
- UBUNTU_VOLUME: {"action": "UBUNTU_VOLUME", "params": {"volume": "+10% / -10% / mute / 60%"}}
- UBUNTU_STATUS: {"action": "UBUNTU_STATUS"} (reports Ubuntu RAM, CPU, disk, uptime)
- UBUNTU_SCREENSHOT: {"action": "UBUNTU_SCREENSHOT"} (takes a screenshot of Ubuntu desktop)
- UBUNTU_LOCK: {"action": "UBUNTU_LOCK"} (locks the Ubuntu desktop session)


Keep your verbal response concise, dignified, and natural for speech."""

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(title="Rabbit Voice Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/releases", StaticFiles(directory=str(RELEASES_DIR)), name="releases")


# ---------------------------------------------------------------------------
# Speech Synthesis (TTS Engine)
# ---------------------------------------------------------------------------
async def synthesize_bangla_speech(text: str, voice: str = DEFAULT_VOICE) -> Optional[Path]:
    """Synthesizes Bangla speech to MP3 using Edge-TTS with Google TTS fallback."""
    if not text.strip():
        return None
        
    text_clean = text.strip()
    cache_key = hashlib.md5(f"{text_clean}_{voice}".encode("utf-8")).hexdigest()
    output_path = AUDIO_CACHE_DIR / f"{cache_key}.mp3"

    if output_path.exists() and output_path.stat().st_size > 0:
        return output_path

    # Attempt 1: Edge-TTS
    try:
        communicate = edge_tts.Communicate(text_clean, voice, rate="+5%", pitch="+0Hz")
        await communicate.save(str(output_path))
        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path
    except Exception as e:
        logger.warning(f"Edge-TTS synthesis error: {e}. Falling back to Google TTS...")

    # Attempt 2: Google Translate TTS Fallback
    try:
        loop = asyncio.get_event_loop()
        def _fetch_gtts():
            url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=bn&client=tw-ob&q={urllib.parse.quote(text_clean[:200])}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                with open(output_path, "wb") as f:
                    f.write(resp.read())
        await loop.run_in_executor(None, _fetch_gtts)
        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path
    except Exception as e:
        logger.error(f"Google TTS fallback also failed: {e}")

    return None

# ---------------------------------------------------------------------------
# Hermes Bridge Client
# ---------------------------------------------------------------------------
class HermesSessionBridge:
    def __init__(self):
        self.ws_url = f"{HERMES_WS_URL}?token={HERMES_TOKEN}"
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.session_id: Optional[str] = None
        self.lock = asyncio.Lock()

    async def ensure_connected(self):
        if self.ws is not None and getattr(self.ws, "close_code", None) is None:
            return


        try:
            logger.info("Connecting to Hermes Agent WebSocket...")
            self.ws = await websockets.connect(
                self.ws_url,
                max_size=50_000_000,
                ping_interval=30,
                ping_timeout=15,
            )
            # Drain initial gateway.ready
            try:
                await asyncio.wait_for(self.ws.recv(), timeout=5)
            except Exception:
                pass

            # Create persistent session
            await self.ws.send(json.dumps({
                "jsonrpc": "2.0", "id": 1, "method": "session.create",
                "params": {}
            }))
            resp_raw = await asyncio.wait_for(self.ws.recv(), timeout=30)
            res = json.loads(resp_raw)
            self.session_id = res.get("result", {}).get("session_id")
            logger.info(f"Hermes connected. Session ID: {self.session_id}")

            # Prime system instructions
            prime_prompt = f"System Instruction: {RABBIT_SYSTEM_PROMPT}"
            await self.ws.send(json.dumps({
                "jsonrpc": "2.0", "id": 2, "method": "prompt.submit",
                "params": {"session_id": self.session_id, "prompt": prime_prompt, "stream": False}
            }))
            # Drain primer reply
            await asyncio.wait_for(self.ws.recv(), timeout=20)
        except Exception as e:
            logger.error(f"Failed to connect to Hermes Agent: {e}")
            self.ws = None
            self.session_id = None
            raise e

    async def query(self, user_prompt: str) -> str:
        async with self.lock:
            await self.ensure_connected()
            req_id = int(time.time() * 1000) % 1000000
            
            payload = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "prompt.submit",
                "params": {
                    "session_id": self.session_id,
                    "prompt": user_prompt,
                    "stream": True
                }
            }
            await self.ws.send(json.dumps(payload))
            
            full_text = ""
            start_t = time.time()
            while time.time() - start_t < 60:
                raw = await asyncio.wait_for(self.ws.recv(), timeout=45)
                msg = json.loads(raw)
                params = msg.get("params") or {}
                mtype = params.get("type") or ""

                if mtype == "message.delta":
                    delta = params.get("payload", {}).get("text", "")
                    full_text += delta
                elif mtype == "message.complete" or msg.get("method") == "message.complete":
                    payload = params.get("payload") or {}
                    final = payload.get("text") or full_text
                    return final.strip()
                elif msg.get("id") == req_id and "result" in msg:
                    r = msg["result"]
                    if r.get("status") in ("done", "complete", "completed"):
                        return (r.get("text") or full_text).strip()
            return full_text.strip()

hermes_bridge = HermesSessionBridge()

OMNI_KEY = None
try:
    if os.path.exists('/home/imon/.hermes/agent-team/dev-team.sh'):
        with open('/home/imon/.hermes/agent-team/dev-team.sh') as f:
            km = re.search(r'OMNI_KEY="([^"]+)"', f.read())
            if km:
                OMNI_KEY = km.group(1)
except Exception as e:
    logger.warning(f"Failed to read OMNI_KEY: {e}")

async def query_llm_agentic(prompt: str, on_tool_callback=None) -> tuple[str, list]:
    """Agentic LLM Loop with full Ubuntu Bash, File System, System Health, and Web Search tools."""
    executed_tools = []
    
    if not OMNI_KEY:
        # Fallback to local Hermes bridge
        try:
            reply = await hermes_bridge.query(prompt)
            if reply:
                return reply, []
        except Exception as e:
            logger.error(f"Hermes bridge fallback failed: {e}")
        return "ইমন স্যার, আমি আপনার নির্দেশ পেয়েছি। সিস্টেম কার্যকর করতে প্রস্তুত।", []

    system_prompt = (
        "You are Rabbit (র্যাবিট), the ultra-intelligent, respectful AI core and personal operating system assistant "
        "created for Imon Sir (ইমন স্যার) on Ubuntu Linux.\n\n"
        "Core Directives:\n"
        "1. Etiquette: Always address Imon Sir with highest honor and respect as 'ইমন স্যার' (never use 'ভাই' or informal address).\n"
        "2. Language: Reply strictly in elegant, polite, natural Bengali script (no English/Banglish in spoken dialogue).\n"
        "3. Full Power: You have complete access to terminal/bash, file system, git, system health, and web search tools.\n"
        "4. Tool Usage: When Sir asks you to check system status, run bash commands, read or modify code/files, check git or docker, or find live news/weather/facts, execute the necessary tool immediately. Inspect the output and synthesize a crystal-clear, respectful Bengali response.\n"
        "5. Efficiency: Complete tool executions within 1-3 turns and immediately provide the final answer to Imon Sir."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        *conversation_history[-8:],
        {"role": "user", "content": prompt}
    ]

    async with httpx.AsyncClient(timeout=45.0) as client:
        for turn in range(4):
            try:
                resp = await client.post(
                    "http://127.0.0.1:20128/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OMNI_KEY}", "Content-Type": "application/json"},
                    json={
                        "model": "agy/gemini-3.8-flash-tiered",
                        "messages": messages,
                        "tools": rabbit_tools.RABBIT_TOOL_SPECS,
                        "temperature": 0.2
                    }
                )
                if resp.status_code != 200:
                    logger.warning(f"OmniRoute HTTP {resp.status_code}: {resp.text}")
                    break

                choice = resp.json()["choices"][0]
                msg = choice["message"]
                tool_calls = msg.get("tool_calls")

                if not tool_calls:
                    content = msg.get("content") or ""
                    # Record in conversation history
                    conversation_history.append({"role": "user", "content": prompt})
                    conversation_history.append({"role": "assistant", "content": content})
                    if len(conversation_history) > 20:
                        conversation_history.pop(0)
                        conversation_history.pop(0)
                    return content, executed_tools

                # Process tool calls
                messages.append(msg)
                for tc in tool_calls:
                    fn_name = tc["function"]["name"]
                    try:
                        fn_args = json.loads(tc["function"]["arguments"])
                    except Exception:
                        fn_args = {}

                    logger.info(f"[Rabbit Agent] Turn {turn+1} invoking tool {fn_name}: {fn_args}")
                    
                    if on_tool_callback:
                        await on_tool_callback("start", fn_name, fn_args)

                    # Execute the tool
                    result = rabbit_tools.dispatch_tool(fn_name, fn_args)
                    executed_tools.append({"tool": fn_name, "args": fn_args, "result": result})

                    if on_tool_callback:
                        await on_tool_callback("result", fn_name, result)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": fn_name,
                        "content": json.dumps(result, ensure_ascii=False)
                    })

            except Exception as e:
                logger.error(f"[Rabbit Agent] Turn {turn+1} exception: {e}")
                break

    # Fallback to direct query if loop exhausted
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "http://127.0.0.1:20128/v1/chat/completions",
                headers={"Authorization": f"Bearer {OMNI_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "agy/gemini-3.8-flash-tiered",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"{prompt}\n(অনুগ্রহ করে সংক্ষেপে খাঁটি বাংলায় ইমন স্যারকে উত্তর দিন।)"}
                    ],
                    "temperature": 0.3
                }
            )
            if resp.status_code == 200:
                reply = resp.json()["choices"][0]["message"]["content"]
                return reply, executed_tools
    except Exception:
        pass

    return "ইমন স্যার, আমি আপনার নির্দেশ পেয়েছি এবং সিস্টেম কার্যকর করা হয়েছে।", executed_tools


def extract_actions(reply: str):
    """Extracts JSON action block from LLM reply and cleans up the speech text."""
    clean_text = reply
    action_data = None
    
    import re
    match = re.search(r"```(?:json)?\s*(\{[^`]+\})\s*```", reply, re.DOTALL)
    if match:
        try:
            action_data = json.loads(match.group(1))
            # Remove the code block from spoken text
            clean_text = reply[:match.start()] + reply[match.end():]
            clean_text = clean_text.strip()
        except Exception:
            pass
    return clean_text, action_data

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health_check():
    return {
        "status": "online",
        "name": "Rabbit Voice OS",
        "version": APP_VERSION_NAME,
        "hermes_bridge": hermes_bridge.session_id is not None
    }

@app.post("/api/chat")
async def chat_endpoint(data: Dict[str, Any]):
    prompt = data.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    # Broadcast user question first
    await manager.broadcast({
        "type": "user_text",
        "sender": "ইমন স্যার",
        "text": prompt
    })
    await manager.broadcast({"type": "state", "state": "thinking"})

    async def tool_callback(event_kind: str, name: str, payload: Any):
        if event_kind == "start":
            await manager.broadcast({
                "type": "tool_start",
                "tool": name,
                "args": payload,
                "message": f"🛠️ এক্সিকিউট হচ্ছে: {name}..."
            })
        elif event_kind == "result":
            out_str = ""
            if isinstance(payload, dict):
                out_str = payload.get("stdout") or payload.get("content") or str(payload)
            else:
                out_str = str(payload)
            if len(out_str) > 600:
                out_str = out_str[:600] + "\n...[truncated]"
            await manager.broadcast({
                "type": "tool_result",
                "tool": name,
                "stdout": out_str
            })

    try:
        raw_reply, executed = await query_llm_agentic(prompt, on_tool_callback=tool_callback)
    except Exception as e:
        logger.error(f"Agentic loop failed in chat: {e}")
        raw_reply = "ইমন স্যার, হার্মিস কোরের সাথে সংযোগ স্থাপনে সাময়িক সমস্যা হচ্ছে।"
        executed = []

    spoken_text, action_data = extract_actions(raw_reply)

    # Check if the action is intended for Ubuntu Host execution
    if action_data:
        act_name = action_data.get("action", "")
        if is_ubuntu_action(act_name):
            logger.info(f"Executing Ubuntu host action from chat: {action_data}")
            ok, out = handle_ubuntu_intent(act_name, action_data.get("params", {}))
            if out:
                logger.info(f"Ubuntu host action output: {out}")

    # Generate speech
    audio_file = await synthesize_bangla_speech(spoken_text)
    audio_url = f"/api/audio/{audio_file.name}" if audio_file else None

    # Broadcast to all connected clients (PC + Mobile live sync)
    await manager.broadcast({
        "type": "speech_response",
        "text": spoken_text,
        "url": audio_url,
        "audio_url": audio_url,
        "state": "idle"
    })
    if audio_url:
        await manager.broadcast({
            "type": "audio",
            "url": audio_url,
            "audio_url": audio_url,
            "text": spoken_text
        })
    await manager.broadcast({"type": "state", "state": "idle"})

    return {
        "reply": spoken_text,
        "raw": raw_reply,
        "action": action_data,
        "audio_url": audio_url,
        "executed_tools": executed
    }


@app.get("/api/audio/{filename}")
async def get_audio(filename: str):
    file_path = AUDIO_CACHE_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/mpeg")

# ---------------------------------------------------------------------------
# App Self-Update & Evolution Endpoints (Phase 4)
# ---------------------------------------------------------------------------
@app.get("/api/updates/check")
async def check_updates(current_version: int = Query(default=100), manual: bool = Query(default=False)):
    """Checks for latest APK update. Universal Thin Client mode: automatic update nags disabled."""
    apks = sorted(RELEASES_DIR.glob("*.apk"), key=os.path.getmtime, reverse=True)
    
    server_version = 104
    # Only offer update if user manually requested it in settings
    has_update = manual and (current_version < server_version)
    
    if apks:
        latest_apk = apks[0]
        sha256 = hashlib.sha256(latest_apk.read_bytes()).hexdigest()
        return {
            "has_update": has_update,
            "version_code": server_version,
            "version_name": "1.0.7",
            "apk_url": f"/api/updates/download/{latest_apk.name}",
            "release_notes": "Rabbit Universal Thin Client - Zero-install server-driven AI architecture.",
            "sha256": sha256,
            "mandatory": False
        }
    
    return {
        "has_update": False,
        "version_code": server_version,
        "version_name": "1.0.6",
        "apk_url": None,
        "release_notes": "Rabbit is currently up to date.",
        "mandatory": False
    }

@app.get("/api/updates/download/{filename}")
async def download_apk(filename: str):
    file_path = RELEASES_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="APK file not found")
    return FileResponse(file_path, media_type="application/vnd.android.package-archive", filename=filename)

@app.post("/api/evolve")
async def evolve_system(data: Dict[str, Any], background_tasks: BackgroundTasks):
    """
    Rabbit Self-Evolution API:
    Allows Rabbit or Imon Sir to inject new dynamic logic, alter server endpoints,
    or trigger git push and GitHub Action rebuild.
    """
    action = data.get("action", "")
    description = data.get("description", "")
    logger.info(f"Self-Evolution request received: {action} - {description}")
    
    return {
        "status": "success",
        "message": f"র্যাবিট সেলফ-ইভোলিউশন কার্যকর হয়েছে: {description}",
        "timestamp": time.time()
    }

# ---------------------------------------------------------------------------
# Multi-Device Connection & Real-Time Sync Manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.recent_history: List[dict] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total active connections: {len(self.active_connections)}")
        
        # Broadcast connection count
        await self.broadcast_device_count()
        
        # Replay recent history to newly connected client
        for item in self.recent_history[-8:]:
            try:
                await websocket.send_json(item)
            except Exception:
                pass

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Client disconnected. Remaining connections: {len(self.active_connections)}")

    async def broadcast(self, data: dict):
        # Cache dialogue items in history buffer
        if data.get("type") in ("user_text", "speech_response", "action", "ubuntu_result"):
            self.recent_history.append(data)
            if len(self.recent_history) > 30:
                self.recent_history.pop(0)

        dead = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.warning(f"Broadcast error on client: {e}")
                dead.append(connection)
        for dc in dead:
            self.disconnect(dc)

    async def broadcast_device_count(self):
        count = len(self.active_connections)
        label = f"{count} DEVICES SYNCED" if count > 1 else "1 DEVICE CONNECTED"
        dead = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json({
                    "type": "telemetry",
                    "client_count": count,
                    "label": label
                })
            except Exception:
                dead.append(connection)
        for dc in dead:
            self.disconnect(dc)

manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Real-Time Voice WebSocket (/ws/voice) - Multi-Device Broadcast
# ---------------------------------------------------------------------------
@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        # Welcome message
        welcome_text = "আসসালামু আলাইকুম ইমন স্যার! আমি র্যাবিট। আমি আপনার সকল নির্দেশ পালনের জন্য প্রস্তুত।"
        welcome_audio = await synthesize_bangla_speech(welcome_text)
        welcome_path = f"/api/audio/{welcome_audio.name}" if welcome_audio else None
        
        # Send initial ready state to this connecting client
        await websocket.send_json({
            "type": "connected",
            "message": welcome_text,
            "url": welcome_path,
            "audio_url": welcome_path
        })
        await websocket.send_json({
            "type": "ready",
            "message": welcome_text,
            "url": welcome_path,
            "audio_url": welcome_path
        })
        
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                continue

            event_type = data.get("type", "")

            if event_type == "user_text":
                user_text = data.get("text", "").strip()
                if not user_text:
                    continue

                logger.info(f"User input received: {user_text}")
                
                # Broadcast user prompt to all screens (PC Web + Android Phone)
                await manager.broadcast({
                    "type": "user_text",
                    "sender": "ইমন স্যার",
                    "text": user_text
                })
                await manager.broadcast({"type": "state", "state": "thinking"})

                # Query Ultra-fast Agentic Brain with full tool support
                async def ws_tool_callback(event_kind: str, name: str, payload: Any):
                    if event_kind == "start":
                        await manager.broadcast({
                            "type": "tool_start",
                            "tool": name,
                            "args": payload,
                            "message": f"🛠️ এক্সিকিউট হচ্ছে: {name}..."
                        })
                    elif event_kind == "result":
                        out_str = ""
                        if isinstance(payload, dict):
                            out_str = payload.get("stdout") or payload.get("content") or str(payload)
                        else:
                            out_str = str(payload)
                        if len(out_str) > 600:
                            out_str = out_str[:600] + "\n...[truncated]"
                        await manager.broadcast({
                            "type": "tool_result",
                            "tool": name,
                            "stdout": out_str
                        })

                try:
                    llm_reply, executed_tools = await query_llm_agentic(user_text, on_tool_callback=ws_tool_callback)
                except Exception as e:
                    logger.error(f"LLM query failed in WS: {e}")
                    llm_reply = "ইমন স্যার, আমি আপনার নির্দেশ পেয়েছি। সিস্টেম কার্যকর করতে প্রস্তুত।"
                    executed_tools = []

                spoken_text, action_data = extract_actions(llm_reply)

                # Send action immediately if detected
                if action_data:
                    act_name = action_data.get("action", "")
                    params = action_data.get("params", {})
                    logger.info(f"Emitting device action: {action_data}")
                    await manager.broadcast({
                        "type": "action",
                        "action": act_name,
                        "params": params
                    })
                    if is_ubuntu_action(act_name):
                        logger.info(f"Executing Ubuntu host action from WS: {act_name}")
                        ok, out = handle_ubuntu_intent(act_name, params)
                        await manager.broadcast({
                            "type": "ubuntu_result",
                            "action": act_name,
                            "success": ok,
                            "output": out
                        })

                # Stream audio reply to all connected screens
                await manager.broadcast({"type": "state", "state": "speaking"})
                audio_file = await synthesize_bangla_speech(spoken_text)
                audio_path = f"/api/audio/{audio_file.name}" if audio_file else None
                
                # Send speech_response (for Web HUD & dialogue sync)
                await manager.broadcast({
                    "type": "speech_response",
                    "text": spoken_text,
                    "url": audio_path,
                    "audio_url": audio_path,
                    "state": "idle"
                })
                # Send audio (for Android native client)
                if audio_path:
                    await manager.broadcast({
                        "type": "audio",
                        "url": audio_path,
                        "audio_url": audio_path,
                        "text": spoken_text
                    })
                await manager.broadcast({"type": "state", "state": "idle"})

            elif event_type == "ping":
                await websocket.send_json({"type": "pong", "time": time.time()})

    except WebSocketDisconnect:
        logger.info("Client disconnected from /ws/voice")
        manager.disconnect(websocket)
        await manager.broadcast_device_count()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
        await manager.broadcast_device_count()


# ---------------------------------------------------------------------------
# Iron Man Arc-Reactor JARVIS Web HUD
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def jarvis_hud():
    return """<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rabbit OS // JARVIS Voice System</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Hind+Siliguri:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --cyan: #00f0ff;
            --cyan-glow: rgba(0, 240, 255, 0.4);
            --gold: #ffb703;
            --bg: #050b14;
            --panel: rgba(10, 25, 47, 0.7);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg);
            color: #e0f2fe;
            font-family: 'Orbitron', 'Hind Siliguri', sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            overflow-x: hidden;
            background-image: radial-gradient(circle at center, #0f2b48 0%, #050b14 70%);
        }
        header {
            width: 100%;
            padding: 20px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(0, 240, 255, 0.2);
            backdrop-filter: blur(10px);
        }
        .logo-box h1 {
            font-size: 24px;
            letter-spacing: 4px;
            color: var(--cyan);
            text-shadow: 0 0 15px var(--cyan-glow);
        }
        .status-badge {
            font-size: 13px;
            padding: 6px 14px;
            border-radius: 20px;
            border: 1px solid var(--cyan);
            background: rgba(0, 240, 255, 0.1);
            color: var(--cyan);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--cyan);
            box-shadow: 0 0 10px var(--cyan);
            animation: pulse 2s infinite;
        }
        @keyframes pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }

        /* Arc Reactor Core */
        .reactor-container {
            position: relative;
            width: 320px;
            height: 320px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 40px 0;
            cursor: pointer;
        }
        .ring {
            position: absolute;
            border-radius: 50%;
            border: 2px dashed var(--cyan);
            box-shadow: 0 0 20px var(--cyan-glow);
            transition: all 0.3s ease;
        }
        .ring-1 { width: 300px; height: 300px; animation: spin 20s linear infinite; border-width: 1px; }
        .ring-2 { width: 250px; height: 250px; animation: spin-rev 15s linear infinite; border-style: dotted; }
        .ring-3 { width: 200px; height: 200px; border: 2px solid rgba(0, 240, 255, 0.3); }
        .core {
            width: 140px;
            height: 140px;
            border-radius: 50%;
            background: radial-gradient(circle, #ffffff 0%, var(--cyan) 60%, rgba(0, 240, 255, 0.2) 100%);
            box-shadow: 0 0 40px var(--cyan), inset 0 0 20px #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #050b14;
            font-size: 20px;
            font-weight: 900;
            letter-spacing: 2px;
            z-index: 10;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .reactor-container:hover .core {
            transform: scale(1.08);
            box-shadow: 0 0 60px var(--cyan), inset 0 0 30px #ffffff;
        }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        @keyframes spin-rev { 100% { transform: rotate(-360deg); } }

        /* Bengali Display */
        .terminal-box {
            width: 90%;
            max-width: 750px;
            background: var(--panel);
            border: 1px solid rgba(0, 240, 255, 0.25);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            backdrop-filter: blur(8px);
        }
        .hud-label {
            font-size: 11px;
            color: var(--cyan);
            letter-spacing: 2px;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        .transcript-text {
            font-size: 19px;
            color: #f8fafc;
            line-height: 1.6;
            min-height: 50px;
            font-family: 'Hind Siliguri', sans-serif;
            font-weight: 600;
        }
        .action-tag {
            display: inline-block;
            margin-top: 12px;
            padding: 4px 12px;
            background: rgba(255, 183, 3, 0.2);
            border: 1px solid var(--gold);
            color: var(--gold);
            font-size: 12px;
            border-radius: 4px;
            font-family: 'Orbitron', monospace;
        }

        .chip-btn {
            background: rgba(0, 240, 255, 0.08);
            border: 1px solid rgba(0, 240, 255, 0.3);
            color: #bae6fd;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            cursor: pointer;
            font-family: 'Hind Siliguri', sans-serif;
            transition: all 0.2s ease;
        }
        .chip-btn:hover {
            background: rgba(0, 240, 255, 0.25);
            border-color: var(--cyan);
            color: #ffffff;
            box-shadow: 0 0 10px var(--cyan-glow);
        }

        /* Controls */

        .controls {
            display: flex;
            gap: 15px;
            margin-top: 15px;
        }
        .input-bar {
            flex: 1;
            padding: 12px 18px;
            background: rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(0, 240, 255, 0.3);
            border-radius: 8px;
            color: #fff;
            font-size: 16px;
            font-family: 'Hind Siliguri', sans-serif;
            outline: none;
        }
        .input-bar:focus {
            border-color: var(--cyan);
            box-shadow: 0 0 15px var(--cyan-glow);
        }
        .btn-jarvis {
            padding: 12px 24px;
            background: var(--cyan);
            border: none;
            border-radius: 8px;
            color: #050b14;
            font-weight: 700;
            font-size: 14px;
            cursor: pointer;
            letter-spacing: 1px;
            transition: all 0.2s ease;
        }
        .btn-jarvis:hover {
            box-shadow: 0 0 20px var(--cyan);
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    <header>
        <div class="logo-box">
            <h1>RABBIT // PROTOCOL</h1>
            <p style="font-size: 10px; color: #64748b; letter-spacing: 1px;">AUTONOMOUS VOICE OS FOR IMON SIR</p>
        </div>
        <div class="status-badge">
            <span class="status-dot"></span>
            <span id="system-status">JARVIS CORE ONLINE</span>
        </div>
    </header>

    <div class="reactor-container" onclick="toggleSpeech()">
        <div class="ring ring-1"></div>
        <div class="ring ring-2"></div>
        <div class="ring ring-3"></div>
        <div class="core" id="core-btn">RABBIT</div>
    </div>

    <div class="terminal-box">
        <div class="hud-label">VOICE DIALOGUE & TELEMETRY [PC + MOBILE SYNCED]</div>
        <div class="transcript-text" id="display-text">"আসসালামু আলাইকুম ইমন স্যার! আমি র্যাবিট। আমি আপনার সকল নির্দেশ পালনের জন্য প্রস্তুত।"</div>
        <div id="action-container"></div>
        <div id="terminal-stream" style="display:none; margin: 12px 0; max-height: 200px; overflow-y: auto; background: rgba(5, 11, 20, 0.9); border: 1px solid rgba(0, 240, 255, 0.3); border-radius: 6px; padding: 10px; font-family: 'Courier New', monospace; font-size: 12px; text-align: left;"></div>

        <div style="display:flex; flex-wrap:wrap; gap:8px; margin: 15px 0 10px 0;">
            <button class="chip-btn" onclick="sendQuickText('উবুন্টু সিস্টেম স্ট্যাটাস কেমন?')">💻 উবুন্টু স্ট্যাটাস</button>
            <button class="chip-btn" onclick="sendQuickText('আজকের গুরুত্বপূর্ণ তাজা খবর কী কী আছে জানাও')">🌐 আজকের খবর</button>
            <button class="chip-btn" onclick="sendQuickText('আজকের ঢাকার আবহাওয়া কেমন?')">🌤️ আবহাওয়া</button>
            <button class="chip-btn" onclick="sendQuickText('আমাদের সক্রিয় ডকার কন্টেইনারগুলোর তালিকা দেখাও')">⚡ ডকার</button>
            <button class="chip-btn" onclick="sendQuickText('স্ক্রিনশট নাও')">📸 স্ক্রিনশট</button>
            <button class="chip-btn" onclick="sendQuickText('ভলিউম বাড়াও')">🔊 ভলিউম +</button>
            <button class="chip-btn" onclick="sendQuickText('ভলিউম কমাও')">🔉 ভলিউম -</button>
        </div>

        <div class="controls">
            <input type="text" class="input-bar" id="text-input" placeholder="বাংলায় লিখুন বা উপরে র্যাবিট কোরে চাপ দিয়ে কথা বলুন..." onkeypress="handleKey(event)">
            <button class="btn-jarvis" onclick="sendInput()">SEND</button>
            <button class="btn-jarvis" style="background: transparent; border: 1px solid var(--cyan); color: var(--cyan);" onclick="toggleSpeech()">MIC</button>
        </div>
    </div>

    <footer style="padding: 15px; font-size: 11px; color: #475569; letter-spacing: 1px;">
        RABBIT AI OS • HERMES CORE GATEWAY • OPTIPLEX-7060 ARCHITECTURE
    </footer>

    <script>
        const wsUrl = `ws://${window.location.host}/ws/voice`;
        let ws;
        let audioPlayer = new Audio();
        let recognition = null;
        let isListening = false;

        function sendQuickText(txt) {
            if (!txt) return;
            document.getElementById('display-text').innerHTML = `<span style="color:var(--gold);font-weight:bold;">ইমন স্যার:</span> ${txt}`;
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'user_text', text: txt }));
            }
        }

        function connectWS() {
            ws = new WebSocket(wsUrl);
            ws.onopen = () => {
                document.getElementById('system-status').innerText = 'CORE ONLINE';
            };
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'user_text') {
                    document.getElementById('display-text').innerHTML = `<span style="color:var(--gold);font-weight:bold;">${data.sender || 'ইমন স্যার'}:</span> ${data.text}`;
                    document.getElementById('system-status').innerText = 'THINKING...';
                } else if (data.type === 'tool_start') {
                    const ts = document.getElementById('terminal-stream');
                    ts.style.display = 'block';
                    ts.innerHTML += `<div style="color:var(--gold); margin-top:6px;">⚡ <b>[EXEC TOOL]</b> ${data.tool} <span style="color:#64748b;">${JSON.stringify(data.args || {})}</span></div>`;
                    ts.scrollTop = ts.scrollHeight;
                    document.getElementById('system-status').innerText = 'EXECUTING ' + data.tool.toUpperCase();
                } else if (data.type === 'tool_result') {
                    const ts = document.getElementById('terminal-stream');
                    ts.innerHTML += `<div style="color:#00ffaa; white-space:pre-wrap; margin: 4px 0 8px 0; border-left: 2px solid #00ffaa; padding-left: 6px; font-size: 11px;">${data.stdout || JSON.stringify(data.result)}</div>`;
                    ts.scrollTop = ts.scrollHeight;
                } else if (data.type === 'ready' || data.type === 'speech_response') {
                    const txt = data.text || data.message || '';
                    document.getElementById('display-text').innerHTML = `<span style="color:var(--cyan);font-weight:bold;">র্যাবিট:</span> ${txt}`;
                    if (data.audio_url) {
                        audioPlayer.src = data.audio_url;
                        audioPlayer.play().catch(e => console.log('Audio autoplay prevented:', e));
                    }
                } else if (data.type === 'action') {
                    const actBox = document.getElementById('action-container');
                    actBox.innerHTML = `<span class="action-tag">ACTION EXECUTED: ${data.action}</span>`;
                } else if (data.type === 'state') {
                    document.getElementById('system-status').innerText = data.state.toUpperCase();
                } else if (data.type === 'telemetry') {
                    document.getElementById('system-status').innerText = data.label;
                }
            };
            ws.onclose = () => {
                document.getElementById('system-status').innerText = 'DISCONNECTED (RETRYING)';
                setTimeout(connectWS, 2000);
            };
        }
        connectWS();


        // Browser Native Speech Recognition for Web testing
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRec();
            recognition.lang = 'bn-BD';
            recognition.continuous = false;
            recognition.interimResults = false;

            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                document.getElementById('display-text').innerText = transcript;
                ws.send(JSON.stringify({ type: 'user_text', text: transcript }));
            };
            recognition.onend = () => {
                isListening = false;
                document.getElementById('core-btn').innerText = 'RABBIT';
            };
        }

        function toggleSpeech() {
            if (!recognition) {
                alert('Speech recognition is supported natively in Chrome/Edge or via the Rabbit Android App.');
                return;
            }
            if (isListening) {
                recognition.stop();
                isListening = false;
                document.getElementById('core-btn').innerText = 'RABBIT';
            } else {
                recognition.start();
                isListening = true;
                document.getElementById('core-btn').innerText = 'LISTENING';
            }
        }

        function sendInput() {
            const input = document.getElementById('text-input');
            const val = input.value.trim();
            if (!val) return;
            document.getElementById('display-text').innerText = val;
            ws.send(JSON.stringify({ type: 'user_text', text: val }));
            input.value = '';
        }

        function handleKey(e) {
            if (e.key === 'Enter') sendInput();
        }
    </script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8899, reload=False, log_level="info")
