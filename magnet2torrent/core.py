"""
Core functionality for converting magnet URIs and info hashes to torrent files.

Uses libtorrent to connect to the BitTorrent swarm, fetch metadata only (no file
content), and save the resulting .torrent file. Supports both full magnet URIs
and naked 40-character hex info hashes.

Before connecting to peers, attempts to quickly fetch the torrent from cache
sites (itorrents.org, torrage.info, etc.) via HTTP. Cache sites are tried
sequentially from a JSON config file; failed sites are moved to the end.

Key functions:
- try_cache_sites(): Attempts fast HTTP download from torrent cache sites
- get_public_trackers(): Fetches and caches public tracker lists
- create_session(): Initializes libtorrent with optional proxy/DHT settings
- process_magnet(): Resolves a magnet/info_hash to a .torrent file
"""
import os
import time
import json
import requests
import libtorrent as lt
import re
from urllib.parse import urlparse, parse_qs
from . import config


def load_cache_sites():
    """Load the list of cache site URL templates from JSON file."""
    try:
        with open(config.CACHE_SITES_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_cache_sites(sites):
    """Save the cache site URL templates back to JSON file."""
    with open(config.CACHE_SITES_FILE, 'w') as f:
        json.dump(sites, f, indent=4)


def extract_info_hash(magnet_uri):
    """
    Extract the info hash from a magnet URI or naked info hash.
    Returns uppercase 40-character hex string.
    """
    # Check for naked info hash (40 hex characters)
    if re.match(r'^[a-fA-F0-9]{40}$', magnet_uri):
        return magnet_uri.upper()

    # Parse magnet URI
    parsed = urlparse(magnet_uri)
    if parsed.scheme != 'magnet':
        return None

    params = parse_qs(parsed.query)
    xt_list = params.get('xt', [])

    for xt in xt_list:
        # Format: urn:btih:<info_hash>
        if xt.startswith('urn:btih:'):
            hash_part = xt[9:]  # Remove 'urn:btih:'
            # Handle base32 encoded hashes (32 chars) vs hex (40 chars)
            if len(hash_part) == 32:
                # Base32 encoded, decode to hex
                import base64
                try:
                    decoded = base64.b32decode(hash_part.upper())
                    return decoded.hex().upper()
                except Exception:
                    pass
            elif len(hash_part) == 40:
                return hash_part.upper()

    return None


def try_cache_sites(info_hash, http_proxy=None, quiet=False):
    """
    Attempt to download torrent file from cache sites.

    Tries each site sequentially. If a site fails, it's moved to the end of
    the list and the updated list is saved. Returns the torrent file content
    as bytes if successful, None otherwise.
    """
    sites = load_cache_sites()
    if not sites:
        return None

    proxies = None
    if http_proxy:
        proxies = {'http': http_proxy, 'https': http_proxy}

    info_hash_upper = info_hash.upper()
    info_hash_lower = info_hash.lower()

    failed_sites = []

    for site_template in sites:
        # Try both upper and lower case since different sites may expect different formats
        url = site_template.format(info_hash=info_hash_upper)

        if not quiet:
            print(f"Trying cache site: {urlparse(url).netloc}...")

        try:
            response = requests.get(url, proxies=proxies, timeout=10, allow_redirects=True)

            # Check if we got a valid torrent file
            if response.status_code == 200:
                content = response.content
                # Basic validation: torrent files start with 'd' (bencoded dict)
                if content and content[0:1] == b'd':
                    if not quiet:
                        print(f"Success! Downloaded from {urlparse(url).netloc}")

                    # Move any failed sites to the end
                    if failed_sites:
                        remaining = [s for s in sites if s not in failed_sites]
                        save_cache_sites(remaining + failed_sites)

                    return content

            # Not found or invalid response, try next
            failed_sites.append(site_template)

        except requests.RequestException as e:
            if not quiet:
                print(f"  Failed: {e}")
            failed_sites.append(site_template)

    # All sites failed, reorder the list
    if failed_sites and len(failed_sites) < len(sites):
        remaining = [s for s in sites if s not in failed_sites]
        save_cache_sites(remaining + failed_sites)

    return None


def get_public_trackers(proxy_enabled=False, quiet=False):
    """
    Fetches public trackers from the internet, using a local cache.
    When proxy_enabled=True, only returns HTTP/HTTPS trackers since UDP doesn't work through proxies.
    """
    if not os.path.exists(config.CACHE_DIR):
        os.makedirs(config.CACHE_DIR)

    trackers = []

    # Use different tracker list when proxy is enabled
    if proxy_enabled:
        # Use "all" list which includes HTTP trackers, then filter
        tracker_url = config.TRACKER_LIST_URL.replace("trackers_best.txt", "trackers_all.txt")
        cache_file = os.path.join(config.CACHE_DIR, "trackers_all.txt")
    else:
        tracker_url = config.TRACKER_LIST_URL
        cache_file = os.path.join(config.CACHE_DIR, "trackers_best.txt")

    # Check cache
    is_cached = False
    if os.path.exists(cache_file):
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime < config.CACHE_TTL:
            is_cached = True

    content = ""
    if is_cached:
        if not quiet:
            print(f"Using cached trackers from {cache_file}")
        with open(cache_file, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        if not quiet:
            print(f"Fetching trackers from {tracker_url}")
        try:
            response = requests.get(tracker_url, timeout=10)
            response.raise_for_status()
            content = response.text
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            if not quiet:
                print(f"Failed to fetch trackers: {e}")
            if os.path.exists(cache_file):
                if not quiet:
                    print("Falling back to stale cache.")
                with open(cache_file, 'r', encoding='utf-8') as f:
                    content = f.read()

    # Parse content
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            # Filter by protocol when proxy is enabled
            if proxy_enabled:
                if line.startswith('http://') or line.startswith('https://'):
                    trackers.append(line)
            else:
                trackers.append(line)

    if proxy_enabled and len(trackers) == 0 and not quiet:
        print("Warning: No HTTP/HTTPS trackers found! Proxy will not work with UDP trackers.")

    return trackers


def create_session(proxy_host=None, proxy_port=None, proxy_user=None, proxy_pass=None, enable_dht=False, quiet=False):
    """
    Initializes the libtorrent session with optional DHT and SOCKS5 proxy settings.
    DHT and proxy cannot be used together since SOCKS5 doesn't support UDP reliably.
    Note: Only SOCKS5 proxies are supported. HTTP proxies cannot handle BitTorrent peer connections.
    """
    if enable_dht and proxy_host:
        raise ValueError("Cannot use DHT with a proxy. DHT uses UDP which SOCKS5 proxies don't support reliably.")

    settings = {
        'user_agent': 'magnet2torrent/1.0',
        'listen_interfaces': '0.0.0.0:6881',
    }

    if proxy_host:
        if not quiet:
            print(f"Configuring SOCKS5 proxy: {proxy_host}:{proxy_port}")

        # Disable local network features that bypass proxy
        settings['enable_dht'] = False
        settings['enable_lsd'] = False
        settings['enable_upnp'] = False
        settings['enable_natpmp'] = False

        # Use SOCKS5 with or without authentication
        if proxy_user:
            settings['proxy_type'] = lt.proxy_type_t.socks5_pw
        else:
            settings['proxy_type'] = lt.proxy_type_t.socks5

        settings['proxy_hostname'] = proxy_host
        if proxy_port:
            settings['proxy_port'] = proxy_port
        if proxy_user:
            settings['proxy_username'] = proxy_user
        if proxy_pass:
            settings['proxy_password'] = proxy_pass

        # Ensure all traffic goes through proxy
        settings['proxy_peer_connections'] = True
        settings['proxy_tracker_connections'] = True
        settings['proxy_hostnames'] = True
        settings['anonymous_mode'] = True
    else:
        # No proxy - configure based on DHT setting
        settings['enable_dht'] = enable_dht
        settings['enable_lsd'] = enable_dht
        settings['enable_upnp'] = enable_dht
        settings['enable_natpmp'] = enable_dht

    ses = lt.session(settings)

    if enable_dht:
        if not quiet:
            print("Waiting for DHT nodes...")
        dht_wait_start = time.time()
        while not ses.is_dht_running():
            if time.time() - dht_wait_start > 10:
                if not quiet:
                    print("Warning: DHT initialization timed out (continuing anyway)")
                break
            time.sleep(0.1)

    return ses


def process_magnet(ses, magnet_uri, output_dir, public_trackers, quiet=False, http_proxy=None):
    """
    Resolves a single magnet URI to a .torrent file.

    First attempts to download from torrent cache sites via HTTP (fast path).
    Falls back to peer-based metadata download if cache sites fail.

    Returns:
        Path to the saved .torrent file on success, None on failure.
    """
    # Extract info hash for cache site lookup
    info_hash = extract_info_hash(magnet_uri)

    if not quiet:
        print(f"Processing: {magnet_uri[:60]}...")

    # Try cache sites first (fast path)
    if info_hash:
        if not quiet:
            print("Attempting download from cache sites...")
        torrent_data = try_cache_sites(info_hash, http_proxy=http_proxy, quiet=quiet)

        if torrent_data:
            # Parse the downloaded torrent to get the name
            try:
                torrent_info = lt.torrent_info(lt.bdecode(torrent_data))
                name = torrent_info.name()
            except Exception:
                name = info_hash

            # Sanitize name
            safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c in " ._-"]).strip()
            if not safe_name:
                safe_name = info_hash

            filename = f"{safe_name}.torrent"
            output_path = os.path.join(output_dir, filename)

            if not quiet:
                print(f"Saving to {output_path}")
            with open(output_path, "wb") as f:
                f.write(torrent_data)
            return output_path

        if not quiet:
            print("Cache sites failed, falling back to peer download...")

    # Check for naked info hash (40 hex characters)
    if re.match(r'^[a-fA-F0-9]{40}$', magnet_uri):
        if not quiet:
            print(f"Detected naked info hash: {magnet_uri}")
        magnet_uri = f"magnet:?xt=urn:btih:{magnet_uri}"
    
    # Add magnet
    # We set upload_mode to True to prevent downloading, 
    # effectively making it a metadata-only download initially.
    params = lt.parse_magnet_uri(magnet_uri)
    # Use cache dir for temp storage
    params.save_path = os.path.join(config.CACHE_DIR, "dummy_download") 
    params.flags |= lt.torrent_flags.upload_mode # Don't download payload
    params.flags |= lt.torrent_flags.duplicate_is_error
    
    # Build complete tracker list - params.trackers returns a copy, so we must reassign
    all_trackers = list(params.trackers)
    ct_set = set(all_trackers)
    for t in public_trackers:
        if t not in ct_set:
            all_trackers.append(t)
            ct_set.add(t)
    params.trackers = all_trackers

    handle = ses.add_torrent(params)

    if not quiet:
        print("Downloading metadata...")
    deadline = time.time() + 60 * 5 # 5 minutes timeout
    last_update = time.time()

    while not handle.status().has_metadata:
        if time.time() > deadline:
            if not quiet:
                print("Timeout waiting for metadata.")
            ses.remove_torrent(handle)
            return None

        # Print status every 5 seconds
        if not quiet and time.time() - last_update >= 5:
            status = handle.status()
            print(f"  Peers: {status.num_peers}, Seeds: {status.num_seeds}, Progress: {status.progress*100:.1f}%")
            last_update = time.time()

        time.sleep(1)

    if not quiet:
        print("Metadata received.")
    
    # Get info and create torrent file
    tor_info = handle.torrent_file()
    
    # Create a create_torrent object to generate the file content
    # We use the info we got.
    ct = lt.create_torrent(tor_info)
    
    # Add trackers to the new torrent file
    # We can get the trackers currently known by the handle
    known_trackers = handle.trackers() # returns list of announcer_entry
    
    # Collect all unique tracker URLs
    final_trackers = set()
    
    # From handle (discovered/magnet)
    for t in known_trackers:
        final_trackers.add(t['url'])
        
    # From public list (ensure they are included)
    for t in public_trackers:
        final_trackers.add(t)
        
    # Actually, let's just iterate and add.
    for url in final_trackers:
        ct.add_tracker(url)
        
    # Generate torrent file content
    entry = ct.generate()
    bencoded_data = lt.bencode(entry)
    
    # Determine filename
    name = tor_info.name()
    if not name:
        name = str(handle.info_hash())
    
    # Sanitize name
    safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c in " ._-"]).strip()
    if not safe_name:
        safe_name = str(handle.info_hash())
        
    filename = f"{safe_name}.torrent"
    output_path = os.path.join(output_dir, filename)

    if not quiet:
        print(f"Saving to {output_path}")
    with open(output_path, "wb") as f:
        f.write(bencoded_data)

    # Cleanup
    ses.remove_torrent(handle)

    return output_path
