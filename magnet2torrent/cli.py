import argparse
import os
import sys
from . import config
from . import core

def main():
    parser = argparse.ArgumentParser(description="Convert magnet URIs to torrent files using libtorrent.")
    parser.add_argument("magnets", nargs="+", help="Magnet URIs")
    parser.add_argument("--dir", "-o", dest="output_dir", default=config.OUTPUT_DIR, help="Output directory")
    parser.add_argument("--proxy-host", default=config.PROXY_HOST, help="SOCKS5 proxy hostname for peer connections")
    parser.add_argument("--proxy-port", default=config.PROXY_PORT, type=int, help="SOCKS5 proxy port")
    parser.add_argument("--proxy-user", default=config.PROXY_USER, help="SOCKS5 proxy username")
    parser.add_argument("--proxy-pass", default=config.PROXY_PASS, help="SOCKS5 proxy password")
    parser.add_argument("--http-proxy", default=config.HTTP_PROXY, help="HTTP proxy for cache site requests (e.g., http://host:port)")
    parser.add_argument("--enable-dht", action="store_true", default=config.ENABLE_DHT, help="Enable DHT (cannot be used with proxy)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress output")

    args = parser.parse_args()
    
    output_dir = os.path.abspath(args.output_dir)
    if not os.path.isdir(output_dir):
        print(f"Error: Output directory '{output_dir}' does not exist.")
        sys.exit(1)

    proxy_enabled = bool(args.proxy_host)
    public_trackers = core.get_public_trackers(proxy_enabled=proxy_enabled, quiet=args.quiet)
    if not args.quiet:
        print(f"Loaded {len(public_trackers)} {'HTTP/HTTPS' if proxy_enabled else ''} public trackers.")

    ses = core.create_session(
        proxy_host=args.proxy_host,
        proxy_port=args.proxy_port,
        proxy_user=args.proxy_user,
        proxy_pass=args.proxy_pass,
        enable_dht=args.enable_dht,
        quiet=args.quiet
    )

    try:
        for magnet in args.magnets:
            core.process_magnet(ses, magnet, output_dir, public_trackers, quiet=args.quiet, http_proxy=args.http_proxy)
    except KeyboardInterrupt:
        if not args.quiet:
            print("\nInterrupted by user.")
    finally:
        # Pause session? Not strictly necessary as script ends
        pass

if __name__ == "__main__":
    main()
