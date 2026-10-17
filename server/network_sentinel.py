"""
Network & MikroTik Sentinel for Rabbit Assistant.
Monitors LAN gateway latency, WAN internet connectivity, and active local subnet devices.
"""

import subprocess
import re
from typing import Dict, Any, List

def check_network_health() -> Dict[str, Any]:
    """Inspects local MikroTik gateway, WAN connectivity, and active LAN clients."""
    result = {
        "gateway_ip": "192.168.0.1",
        "gateway_latency_ms": None,
        "gateway_online": False,
        "wan_latency_ms": None,
        "wan_online": False,
        "active_devices": [],
        "health": "UNKNOWN",
        "summary": ""
    }

    # 1. Ping Local Gateway
    try:
        p1 = subprocess.run(
            ["ping", "-c", "2", "-W", "1", "192.168.0.1"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3
        )
        if p1.returncode == 0:
            result["gateway_online"] = True
            m = re.search(r"rtt min/avg/max/mdev = [\d\.]+/([\d\.]+)/", p1.stdout)
            if m:
                result["gateway_latency_ms"] = float(m.group(1))
    except Exception as e:
        result["gateway_error"] = str(e)

    # 2. Ping WAN (Cloudflare 1.1.1.1)
    try:
        p2 = subprocess.run(
            ["ping", "-c", "2", "-W", "2", "1.1.1.1"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=4
        )
        if p2.returncode == 0:
            result["wan_online"] = True
            m = re.search(r"rtt min/avg/max/mdev = [\d\.]+/([\d\.]+)/", p2.stdout)
            if m:
                result["wan_latency_ms"] = float(m.group(1))
    except Exception as e:
        result["wan_error"] = str(e)

    # 3. Discover Active LAN Devices from ARP / Neighbor Table
    try:
        p3 = subprocess.run(
            ["ip", "neigh", "show", "dev", "eno1"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3
        )
        devices: List[Dict[str, str]] = []
        if p3.returncode == 0:
            for line in p3.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    ip = parts[0]
                    mac = parts[2] if len(parts) > 2 and ":" in parts[2] else "N/A"
                    state = parts[-1]
                    if state in ("REACHABLE", "DELAY", "STALE"):
                        label = "Unknown Client"
                        if ip == "192.168.0.1":
                            label = "MikroTik Gateway Router"
                        elif ip == "192.168.0.152":
                            label = "ইমন স্যারের অ্যান্ড্রয়েড ফোন (Mobile Client)"
                        devices.append({"ip": ip, "mac": mac, "state": state, "name": label})
        result["active_devices"] = devices
    except Exception as e:
        result["devices_error"] = str(e)

    # 4. Synthesize Status
    if result["gateway_online"] and result["wan_online"]:
        result["health"] = "EXCELLENT"
        gw_lat = f"{result['gateway_latency_ms']:.2f} ms" if result['gateway_latency_ms'] else "<1 ms"
        wan_lat = f"{result['wan_latency_ms']:.2f} ms" if result['wan_latency_ms'] else "স্বাভাবিক"
        result["summary"] = (
            f"লোকাল MikroTik গেটওয়ে (192.168.0.1) এবং ইন্টারনেট সম্পূর্ণ স্থিতিশীল। "
            f"ল্যান ল্যাটেন্সি {gw_lat}, ইন্টারনেট ল্যাটেন্সি {wan_lat}। "
            f"লোকাল সাবনেটে {len(result['active_devices'])}টি সক্রিয় ডিভাইস সংযুক্ত রয়েছে।"
        )
    elif result["gateway_online"] and not result["wan_online"]:
        result["health"] = "NO_INTERNET"
        result["summary"] = "লোকাল রাউটার সচল রয়েছে, তবে বাইরের ইন্টারনেট সংযোগ বিচ্ছিন্ন বা স্লো!"
    else:
        result["health"] = "CRITICAL"
        result["summary"] = "সতর্কতা: লোকাল নেটওয়ার্ক গেটওয়ে ড্রপ করেছে!"

    return result
