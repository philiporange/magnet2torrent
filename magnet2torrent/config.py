import os
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()

# Defaults
OUTPUT_DIR = os.getenv("OUTPUT_DIR", ".")

# SOCKS5 proxy for BitTorrent peer connections
PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = os.getenv("PROXY_PORT")
if PROXY_PORT:
    PROXY_PORT = int(PROXY_PORT)
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")

# HTTP proxy for cache site requests
HTTP_PROXY = os.getenv("HTTP_PROXY")

TRACKER_LIST_URL = os.getenv("TRACKER_LIST_URL", "https://raw.githubusercontent.com/ngosang/trackerslist/refs/heads/master/trackers_best.txt")
CACHE_DIR = os.getenv("CACHE_DIR", "/tmp/magnet_to_rtorrent")
CACHE_TTL = int(os.getenv("CACHE_TTL", 86400))

# Cache sites JSON file - stores prioritized list of torrent cache site URLs
CACHE_SITES_FILE = os.path.join(os.path.dirname(__file__), "cache_sites.json")

# DHT is off by default since public trackers are faster for metadata retrieval
ENABLE_DHT = os.getenv("ENABLE_DHT", "false").lower() in ("true", "1", "yes")
