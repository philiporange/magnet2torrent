# magnet2torrent

Convert magnet URIs to torrent files using `libtorrent`. This tool downloads the metadata from the swarm (without downloading the file content) and saves it as a `.torrent` file. It also augments the tracker list with a curated list of public trackers.

## Features

*   **Metadata-only download:** Connects to the swarm via trackers (or optionally DHT) to fetch the `.torrent` file.
*   **Proxy Support:** SOCKS5 proxy support (HTTP proxies not supported due to BitTorrent protocol limitations).
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
*   `--enable-dht`: Enable DHT for peer discovery (off by default, cannot be used with proxy).
*   `--proxy-host`: SOCKS5 proxy hostname.
*   `--proxy-port`: SOCKS5 proxy port.
*   `--proxy-user`: SOCKS5 proxy username (optional).
*   `--proxy-pass`: SOCKS5 proxy password (optional).

### Environment Variables (`.env`)

You can create a `.env` file to set defaults:

```env
OUTPUT_DIR=/path/to/torrents
ENABLE_DHT=false
PROXY_HOST=127.0.0.1
PROXY_PORT=9050
PROXY_USER=username
PROXY_PASS=password
```

**Important Notes:**
- Only SOCKS5 proxies are supported. HTTP proxies cannot handle BitTorrent peer connections properly.
- DHT and proxy cannot be used together since SOCKS5 proxies don't support UDP reliably.
- When using a proxy, the tool uses HTTP/HTTPS trackers only (UDP trackers don't work through proxies).
