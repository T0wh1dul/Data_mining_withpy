"""
proxy_config.py
───────────────
Configuration for rotating IP proxy service.
Edit this file with your proxy service credentials.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Proxy Service Selection ──────────────────────────────────────────────────
# Supported services: "auto", "brightdata", "oxylabs", "smartproxy", "generic", "manual", "none"
PROXY_SERVICE = os.getenv("PROXY_SERVICE", "none").lower()
# If PROXY_SERVICE=auto, manager tries providers in this order.
AUTO_PROVIDER_PRIORITY = [
    p.strip().lower()
    for p in os.getenv(
        "AUTO_PROVIDER_PRIORITY",
        "smartproxy,oxylabs,brightdata,generic,manual,none"
    ).split(",")
    if p.strip()
]

# ── Bright Data (Luminati) ───────────────────────────────────────────────────
# From: https://brightdata.com/proxy-types/residential-proxies
BRIGHTDATA_USERNAME = os.getenv("BRIGHTDATA_USERNAME", "")
BRIGHTDATA_PASSWORD = os.getenv("BRIGHTDATA_PASSWORD", "")
BRIGHTDATA_ZONE = os.getenv("BRIGHTDATA_ZONE", "residential")  # or "static"
# Example: socks5://username-zone:password@proxy.provider.com:port

# ── Oxylabs ─────────────────────────────────────────────────────────────────
# From: https://oxylabs.io/products/rotating-proxy
OXYLABS_USERNAME = os.getenv("OXYLABS_USERNAME", "")
OXYLABS_PASSWORD = os.getenv("OXYLABS_PASSWORD", "")
OXYLABS_PROXY = os.getenv("OXYLABS_PROXY", "pr.oxylabs.io:7777")

# ── SmartProxy ───────────────────────────────────────────────────────────────
# From: https://smartproxy.com
SMARTPROXY_USERNAME = os.getenv("SMARTPROXY_USERNAME", "")
SMARTPROXY_PASSWORD = os.getenv("SMARTPROXY_PASSWORD", "")
SMARTPROXY_PROXY = os.getenv("SMARTPROXY_PROXY", "gate.smartproxy.com:7000")

# ── Manual Proxy List ────────────────────────────────────────────────────────
# PROXY_SERVICE = "manual"
# Add your own proxy URLs (free proxies are unreliable)
MANUAL_PROXIES = [
    # Example format:
    # "http://proxy1.com:8080",
    # "http://proxy2.com:8080",
    # "socks5://proxy3.com:1080",
]

# ── Generic Provider (works with any service URL) ───────────────────────────
# Example:
# GENERIC_PROXY_URL=http://username:password@gateway.provider.com:10000
GENERIC_PROXY_URL = os.getenv("GENERIC_PROXY_URL", "").strip()
# Optional pool (comma separated). Example:
# GENERIC_PROXY_POOL=http://u:p@ip1:port,http://u:p@ip2:port
GENERIC_PROXY_POOL = [
    p.strip() for p in os.getenv("GENERIC_PROXY_POOL", "").split(",") if p.strip()
]

# ── Proxy Settings ───────────────────────────────────────────────────────────
PROXY_TIMEOUT = int(os.getenv("PROXY_TIMEOUT", "15"))  # seconds
PROXY_ROTATION_PER_ROW = os.getenv("PROXY_ROTATION_PER_ROW", "true").lower() == "true"
# If True, changes proxy after each row (recommended)
# If False, changes proxy after X requests (less recommended)

PROXY_RETRY_COUNT = int(os.getenv("PROXY_RETRY_COUNT", "2"))  # Retries on proxy failure
PROXY_FALLBACK_TO_DIRECT = os.getenv("PROXY_FALLBACK_TO_DIRECT", "true").lower() == "true"
# If True, falls back to direct connection if all proxies fail
PROXY_AUTO_SWITCH = os.getenv("PROXY_AUTO_SWITCH", "true").lower() == "true"

# ── Proxy Usage Instructions ─────────────────────────────────────────────────
PROXY_INSTRUCTIONS = """
╔════════════════════════════════════════════════════════════════════════════╗
║                     PROXY SETUP INSTRUCTIONS                              ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  1. BRIGHTDATA (Recommended for reliability)                              ║
║     - Sign up: https://brightdata.com                                     ║
║     - Get zone from: https://dashboard.brightdata.com/zones               ║
║     - Add to .env:                                                        ║
║       PROXY_SERVICE=brightdata                                            ║
║       BRIGHTDATA_USERNAME=your-username                                   ║
║       BRIGHTDATA_PASSWORD=your-password                                   ║
║       BRIGHTDATA_ZONE=your-zone                                           ║
║                                                                            ║
║  2. OXYLABS (Good alternative)                                            ║
║     - Sign up: https://oxylabs.io                                         ║
║     - Add to .env:                                                        ║
║       PROXY_SERVICE=oxylabs                                               ║
║       OXYLABS_USERNAME=your-username                                      ║
║       OXYLABS_PASSWORD=your-password                                      ║
║                                                                            ║
║  3. SMARTPROXY (Budget option)                                            ║
║     - Sign up: https://smartproxy.com                                     ║
║     - Add to .env:                                                        ║
║       PROXY_SERVICE=smartproxy                                            ║
║       SMARTPROXY_USERNAME=your-username                                   ║
║       SMARTPROXY_PASSWORD=your-password                                   ║
║                                                                            ║
║  4. NO PROXY (Default - for testing)                                      ║
║     - PROXY_SERVICE=none                                                  ║
║     - Uses direct connection (may get rate limited)                       ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
"""
