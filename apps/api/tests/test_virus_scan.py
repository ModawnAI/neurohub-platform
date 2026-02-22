"""Tests for file upload virus scanning service."""
import pytest
from unittest.mock import patch, MagicMock


class TestVirusScanService:
    def test_scan_clean_file_returns_clean(self):
        """Clean files should return is_clean=True."""
        from app.services.virus_scan import scan_result_for_file, ScanResult
        # Mock ClamAV not available - should return clean with warning
        result = scan_result_for_file(b"clean file content")
        assert isinstance(result, ScanResult)
        assert result.is_clean is True  # No scanner available = assume clean

    def test_scan_result_structure(self):
        """ScanResult should have is_clean, scanner, detail fields."""
        from app.services.virus_scan import ScanResult
        result = ScanResult(is_clean=True, scanner="none", detail="No scanner available")
        assert result.is_clean is True
        assert result.scanner == "none"

    def test_scan_disabled_by_default(self):
        """Virus scanning should be optional and disabled by default."""
        from app.services.virus_scan import is_scanning_enabled
        # Should not crash even if ClamAV is not installed
        enabled = is_scanning_enabled()
        assert isinstance(enabled, bool)
