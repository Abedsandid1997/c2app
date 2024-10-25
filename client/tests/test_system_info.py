"""
Unit tests for system_info module.

This module contains tests for functions such as get_installed_apps and get_geolocation.
"""
import unittest
from unittest.mock import patch
import json
from system_info import get_installed_apps, get_geolocation

class TestSystemFunctions(unittest.TestCase):
    """
    Test cases for system-related functions.

    This class includes tests for functions that retrieve installed apps and geolocation data.
    """
    @patch('subprocess.check_output')
    def test_get_installed_apps_windows(self, mock_subprocess):
        """
        Test get_installed_apps for Windows.
        Mocks subprocess to return a sample list of installed applications.
        """
        # Mocka utdata från subprocess för Windows
        mock_subprocess.return_value = b"App1\r\nApp2\r\nApp3\r\n"
        os_type = "Windows"
        result = get_installed_apps(os_type)
        expected_apps = json.dumps(['App1', 'App2', 'App3'])  # Förväntad JSON-sträng
        self.assertEqual(result, expected_apps)

    @patch('subprocess.check_output')
    def test_get_installed_apps_linux(self, mock_subprocess):
        """
        Test get_installed_apps for Linux.
        Mocks subprocess to return a sample list of installed packages.
        """
        # Mocka utdata från subprocess för Linux
        mock_subprocess.return_value = b"app1\tinstall\napp2\tinstall\napp3\tinstall\n"
        os_type = "Linux"
        result = get_installed_apps(os_type)
        expected_apps = json.dumps(['app1', 'app2', 'app3'])  # Förväntad JSON-sträng
        self.assertEqual(result, expected_apps)

    @patch('subprocess.check_output')
    def test_get_installed_apps_macos(self, mock_subprocess):
        """
        Test get_installed_apps for macOS.
        Mocks subprocess to return sample application locations.
        """
        # Mocka utdata från subprocess för macOS
        mock_subprocess.return_value = (
            b"Location: /Applications/App1.app\n"
            b"Location: /Applications/App2.app\n"
        )
        os_type = "Darwin"
        result = get_installed_apps(os_type)
        expected_apps = json.dumps(
            ['Location: /Applications/App1.app', 'Location: /Applications/App2.app']
        )
        self.assertEqual(result, expected_apps)

    def test_get_installed_apps_unknown_os(self):
        """
        Test get_installed_apps for an unknown OS.
        Should return a message indicating the OS is not supported.
        """
        # Testa ett okänt OS
        os_type = "UnknownOS"
        result = get_installed_apps(os_type)
        self.assertEqual(result, ["Unknown OS - Cannot fetch installed apps"])

    @patch('geocoder.ip')
    def test_get_geolocation(self, mock_geocoder):
        """
        Test get_geolocation function.
        Mocks geolocation data to return a sample IP address and location.
        """
        # Mocka geolocation data
        mock_geocoder.return_value.ip = "123.45.67.89"
        mock_geocoder.return_value.city = "Stockholm"
        mock_geocoder.return_value.state = "Stockholm"
        mock_geocoder.return_value.country = "Sweden"
        mock_geocoder.return_value.latlng = [59.3293, 18.0686]

        result = get_geolocation()
        expected_result = {
            "ip": "123.45.67.89",
            "city": "Stockholm",
            "state": "Stockholm",
            "country": "Sweden",
            "lat": 59.3293,
            "lng": 18.0686
        }
        self.assertEqual(result, expected_result)
