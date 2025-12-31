import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os
import json
import tempfile

# Add parent directory to path to import magnet2torrent
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from magnet2torrent import core


class TestExtractInfoHash(unittest.TestCase):
    def test_naked_info_hash(self):
        info_hash = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        result = core.extract_info_hash(info_hash)
        self.assertEqual(result, info_hash.upper())

    def test_magnet_uri_hex_hash(self):
        info_hash = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        magnet = f"magnet:?xt=urn:btih:{info_hash}&dn=Test"
        result = core.extract_info_hash(magnet)
        self.assertEqual(result, info_hash.upper())

    def test_magnet_uri_base32_hash(self):
        # Base32 encoded hash (32 chars)
        magnet = "magnet:?xt=urn:btih:VKJAT5JXVY3OPQKWYQKD6IZT3BE2QQ6V"
        result = core.extract_info_hash(magnet)
        # Should decode to 40-char hex
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 40)

    def test_invalid_scheme(self):
        result = core.extract_info_hash("http://example.com")
        self.assertIsNone(result)


class TestCacheSites(unittest.TestCase):
    def test_load_cache_sites(self):
        sites = core.load_cache_sites()
        self.assertIsInstance(sites, list)
        self.assertGreater(len(sites), 0)

    @patch('magnet2torrent.core.requests.get')
    def test_try_cache_sites_success(self, mock_get):
        # Mock a successful torrent download (starts with 'd' for bencoded dict)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'd8:announce40:http://tracker.example.com/announce7:comment4:test4:infod6:lengthi12345e4:name8:test.txte'
        mock_get.return_value = mock_response

        info_hash = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        result = core.try_cache_sites(info_hash, quiet=True)

        self.assertIsNotNone(result)
        self.assertTrue(result.startswith(b'd'))

    @patch('magnet2torrent.core.requests.get')
    def test_try_cache_sites_not_found(self, mock_get):
        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        info_hash = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        result = core.try_cache_sites(info_hash, quiet=True)

        self.assertIsNone(result)


class TestCore(unittest.TestCase):
    @patch('magnet2torrent.core.lt')
    def test_process_magnet_with_info_hash(self, mock_lt):
        # Setup
        mock_session = MagicMock()
        mock_handle = MagicMock()
        # verify status().has_metadata returns True immediately to avoid loop
        mock_handle.status.return_value.has_metadata = True
        mock_session.add_torrent.return_value = mock_handle
        
        mock_lt.parse_magnet_uri.return_value = MagicMock()
        mock_lt.bencode.return_value = b"mock data" # Mock bencode to return bytes
        
        info_hash = "a" * 40 # 40 hex chars
        expected_magnet = f"magnet:?xt=urn:btih:{info_hash}"
        
        # Execute
        core.process_magnet(mock_session, info_hash, "/tmp", [])
        
        # Verify
        mock_lt.parse_magnet_uri.assert_called_with(expected_magnet)

    @patch('magnet2torrent.core.lt')
    def test_process_magnet_with_regular_magnet(self, mock_lt):
        # Setup
        mock_session = MagicMock()
        mock_handle = MagicMock()
        mock_handle.status.return_value.has_metadata = True
        mock_session.add_torrent.return_value = mock_handle
        
        mock_lt.parse_magnet_uri.return_value = MagicMock()
        mock_lt.bencode.return_value = b"mock data" # Mock bencode to return bytes
        
        magnet = "magnet:?xt=urn:btih:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        
        # Execute
        core.process_magnet(mock_session, magnet, "/tmp", [])
        
        # Verify
        mock_lt.parse_magnet_uri.assert_called_with(magnet)

if __name__ == '__main__':
    unittest.main()
