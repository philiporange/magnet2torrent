# magnet2torrent

Convert magnet URIs to torrent files using `libtorrent`. This tool downloads the metadata from the swarm (without downloading the file content) and saves it as a `.torrent` file. It also augments the tracker list with a curated list of public trackers.

## Features

*   **Fast Cache Site Lookup:** First attempts to download torrents from cache sites (itorrents.org, hash2torrent.com) via HTTP for near-instant results.
*   **Peer Fallback:** Falls back to swarm-based metadata download if cache sites don't have the torrent.
*   **Proxy Support:** SOCKS5 proxy for peer connections, HTTP proxy for cache site requests.
*   **Public Tracker Augmentation:** Automatically fetches and caches best public trackers to improve connectivity.
*   **Configuration:** Supports `.env` file for default configuration.

## Installation

```bash
pip install .
```

## Usage

```bash
magnet2torrent <magnet_uri_or_info_hash> [options]
```

### Options

*   `--dir`, `-o`: Output directory (default: current directory).
*   `-q`, `--quiet`: Suppress output.
*   `--enable-dht`: Enable DHT for peer discovery (off by default, cannot be used with SOCKS5 proxy).
*   `--http-proxy`: HTTP proxy for cache site requests (e.g., `http://host:port`).
*   `--proxy-host`: SOCKS5 proxy hostname for peer connections.
*   `--proxy-port`: SOCKS5 proxy port.
*   `--proxy-user`: SOCKS5 proxy username (optional).
*   `--proxy-pass`: SOCKS5 proxy password (optional).

### Environment Variables (`.env`)

You can create a `.env` file to set defaults:

```env
OUTPUT_DIR=/path/to/torrents
ENABLE_DHT=false
HTTP_PROXY=http://127.0.0.1:8080
PROXY_HOST=127.0.0.1
PROXY_PORT=9050
PROXY_USER=username
PROXY_PASS=password
```

**Important Notes:**
- The tool first tries to download from torrent cache sites (fast) before falling back to peer connections.
- `HTTP_PROXY` is used for cache site HTTP requests; `PROXY_HOST/PORT` is the SOCKS5 proxy for peer connections.
- DHT and SOCKS5 proxy cannot be used together since SOCKS5 proxies don't support UDP reliably.
- When using a SOCKS5 proxy, the tool uses HTTP/HTTPS trackers only (UDP trackers don't work through proxies).
