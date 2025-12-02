import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path to import magnet2torrent
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from magnet2torrent import core

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
