# magnet2torrent

The `magnet2torrent` project is a command-line utility designed to convert magnet URIs into standard `.torrent` files. It first attempts to quickly download torrents from cache sites (itorrents.org, torrage.info, etc.) via HTTP. If cache sites don't have the torrent, it falls back to fetching metadata from the BitTorrent swarm using `libtorrent`. It supports proxy configuration and automatically augments the tracker list with a curated set of public trackers to improve connectivity.

## Configuration Management

The project uses environment variables, potentially loaded from a `.env` file, to configure default settings such as output directory, proxy details, and whether to enable DHT.

### Accessing Configuration Variables

The `magnet2torrent.config` module loads and exposes configuration variables, prioritizing environment variables over hardcoded defaults.

```python
import os
from magnet2torrent import config

# Example of accessing configuration variables
print(f"Default Output Directory: {config.OUTPUT_DIR}")
print(f"Is DHT enabled by default? {config.ENABLE_DHT}")
print(f"SOCKS5 Proxy Host: {config.PROXY_HOST}")
print(f"HTTP Proxy: {config.HTTP_PROXY}")
print(f"Cache Sites File: {config.CACHE_SITES_FILE}")
```

## Cache Sites

The tool maintains a list of torrent cache site URLs in `magnet2torrent/cache_sites.json`. Before connecting to peers, it tries to download the torrent from these sites in order. If a site fails, it's moved to the end of the list to prioritize working sites.

### Viewing and Modifying Cache Sites

```python
from magnet2torrent import core

# Load current cache sites
sites = core.load_cache_sites()
print(f"Cache sites: {sites}")

# The list is automatically reordered when sites fail
# You can also manually modify cache_sites.json
```

### Trying Cache Sites Directly

```python
from magnet2torrent import core

info_hash = "8600000000000000000000000000000000000000"

# Try to download from cache sites (returns bytes or None)
torrent_data = core.try_cache_sites(info_hash, http_proxy="http://proxy:8080")

if torrent_data:
    print("Downloaded from cache site!")
else:
    print("Not found in cache sites, need to use peer download")
```

## Core Functionality

The `magnet2torrent.core` module handles the main logic: fetching public trackers, initializing the libtorrent session, and processing the magnet URI.

### Fetching Public Trackers

The `get_public_trackers` function retrieves a list of public trackers from a remote URL, caching the result locally to reduce network requests. It automatically filters the list to include only HTTP/HTTPS trackers if a proxy is enabled, as UDP trackers (common in public lists) do not reliably work through SOCKS5 proxies.

-   The function checks a local cache file (`CACHE_DIR`) and uses it if it's not expired (`CACHE_TTL`).
-   If a proxy is enabled (`proxy_enabled=True`), it fetches a broader list and filters for `http://` or `https://` schemes.

```python
import os
import time
from magnet2torrent import core

# 1. Fetching trackers without proxy (includes UDP)
trackers_no_proxy = core.get_public_trackers(proxy_enabled=False)
print(f"Fetched {len(trackers_no_proxy)} trackers (including UDP).")

# 2. Fetching trackers optimized for proxy (HTTP/HTTPS only)
# Note: This might trigger a network request if the cache is stale or non-existent.
trackers_with_proxy = core.get_public_trackers(proxy_enabled=True)
print(f"Fetched {len(trackers_with_proxy)} trackers (HTTP/HTTPS only).")
```

### Initializing the libtorrent Session

The `create_session` function sets up the `libtorrent.session` object, configuring user agent, listening interfaces, and optional proxy or DHT settings.

-   It raises a `ValueError` if both DHT and a proxy are configured, as they are incompatible.
-   If a proxy is provided, it configures the session for SOCKS5 (with or without authentication) and disables local discovery features (LSD, UPnP, NAT-PMP) to ensure all traffic is routed through the proxy.

```python
import libtorrent as lt
from magnet2torrent import core

# 1. Create a session with default settings (no proxy, DHT off by default)
session_default = core.create_session()
print(f"Session created. DHT enabled: {session_default.is_dht_running()}")

# 2. Create a session enabling DHT
session_dht = core.create_session(enable_dht=True)
print(f"Session created. DHT enabled: {session_dht.is_dht_running()}")

# 3. Create a session with a mock proxy configuration
# Note: This requires libtorrent to be installed.
try:
    session_proxy = core.create_session(proxy_host="127.0.0.1", proxy_port=9050)
    settings = session_proxy.get_settings()
    print(f"Session created with proxy. Proxy type: {settings['proxy_type']}")
except ValueError as e:
    print(f"Error creating session: {e}")
```

### Processing a Magnet URI

The `process_magnet` function takes a libtorrent session, a magnet URI (or just an info hash), an output directory, and a list of public trackers. It attempts to resolve the metadata and save the resulting `.torrent` file.

-   **Fast path**: First attempts to download from cache sites via HTTP (near-instant if available).
-   **Fallback**: If cache sites fail, falls back to peer-based metadata download.
-   It checks if the input is a naked info hash and converts it to a full magnet URI if necessary.
-   It adds the magnet to the session, setting the `upload_mode` flag to prevent actual file downloading (metadata-only).
-   It augments the magnet's existing trackers with the provided `public_trackers`.
-   It enters a loop, waiting for the metadata to be received (up to a 5-minute timeout).
-   Once metadata is received, it generates the `.torrent` file content, ensures all known and public trackers are included, and saves the file to the specified output directory.

```python
import libtorrent as lt
import os
import tempfile
from magnet2torrent import core

# Setup mock environment
temp_dir = tempfile.mkdtemp()
mock_session = lt.session()
mock_trackers = ["http://tracker.example.com/announce"]
info_hash = "8600000000000000000000000000000000000000"

# Example 1: Processing with HTTP proxy for cache sites
# core.process_magnet(
#     ses=mock_session,
#     magnet_uri=info_hash,
#     output_dir=temp_dir,
#     public_trackers=mock_trackers,
#     http_proxy="http://proxy:8080"  # Optional HTTP proxy for cache site requests
# )

# Example 2: Processing a full magnet URI
# magnet_uri = f"magnet:?xt=urn:btih:{info_hash}&dn=TestFile"
# core.process_magnet(
#     ses=mock_session,
#     magnet_uri=magnet_uri,
#     output_dir=temp_dir,
#     public_trackers=mock_trackers
# )

print(f"If successful, .torrent files would be saved in: {temp_dir}")
```

## Command Line Interface (CLI)

The `magnet2torrent.cli` module provides the entry point for the command-line tool, handling argument parsing and orchestrating the core functions.

### Running the CLI

The `main` function parses command-line arguments, validates the output directory, initializes the session, and iterates through all provided magnet URIs, calling `core.process_magnet` for each.

-   It uses `argparse` to handle inputs like magnet URIs, output directory (`--dir`), and proxy settings.
-   It respects environment variables loaded via `config` as defaults for optional arguments.
-   It ensures the output directory exists before proceeding.

```bash
# Example usage (requires the package to be installed)

# 1. Basic usage: Convert a magnet URI and save the .torrent file in the current directory.
# magnet2torrent "magnet:?xt=urn:btih:..."

# 2. Specify output directory and enable DHT:
# magnet2torrent "magnet:?xt=urn:btih:..." --dir /tmp/torrents --enable-dht

# 3. Use HTTP proxy for cache site requests:
# magnet2torrent "magnet:?xt=urn:btih:..." --http-proxy http://127.0.0.1:8080

# 4. Use a SOCKS5 proxy for peer connections (disables DHT automatically):
# magnet2torrent "magnet:?xt=urn:btih:..." --proxy-host 127.0.0.1 --proxy-port 9050
```