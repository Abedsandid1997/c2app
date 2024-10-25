"""
This module provides system utility functions for retrieving information about
the operating system, installed applications, geolocation, and hard disk serial numbers.

It includes functions to:
- Get a list of installed applications depending on the OS (Windows, Linux, macOS).
- Fetch geolocation based on the device's IP address.
- Retrieve the hard disk serial number for various operating systems.
"""

import platform
import subprocess
import json
import geocoder


def get_installed_apps(os_type):
    """
    Get the list of installed applications based on the operating system type.

    Args:
        os_type (str): The operating system type ('Windows', 'Linux', 'Darwin' for macOS).

    Returns:
        str: A JSON string of installed applications or an error message.
    """
    if os_type == "Windows":
        return get_installed_apps_windows()
    if os_type == "Linux":
        return get_installed_apps_linux()
    if os_type == "Darwin":  # macOS
        return get_installed_apps_macos()

    return ["Unknown OS - Cannot fetch installed apps"]


# Get installed applications on Windows
def get_installed_apps_windows():
    """
    Get a list of installed applications on Windows.

    Returns:
        str: A JSON string of installed applications or an error message.
    """
    try:
        output = subprocess.check_output(
            [
                "powershell",
                "Get-ItemProperty",
                "HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*",
                "|",
                "Select-Object",
                "DisplayName",
            ]
        )
        apps = output.decode("utf-8").split("\r\n")
        apps_list = [app.strip() for app in apps if app.strip()]
        apps_json = json.dumps(apps_list)
        return apps_json
    except Exception as error:
        return [f"Error fetching apps: {error}"]


# Get installed applications on Linux
def get_installed_apps_linux():
    """
    Get a list of installed applications on Linux.

    Returns:
        str: A JSON string of installed applications or an error message.
    """
    try:
        output = subprocess.check_output(["dpkg", "--get-selections"])
        apps = output.decode("utf-8").split("\n")
        apps_list = [app.split()[0] for app in apps if app]

        # Convert the list to a JSON string
        apps_json = json.dumps(apps_list)
        return apps_json
    except Exception as error:
        return [f"Error fetching apps: {error}"]


# Get installed applications on macOS
def get_installed_apps_macos():
    """
    Get a list of installed applications on macOS.

    Returns:
        str: A JSON string of installed applications or an error message.
    """
    try:
        output = subprocess.check_output(["system_profiler", "SPApplicationsDataType"])
        apps = output.decode("utf-8").split("\n")
        apps_list = [line.strip() for line in apps if "Location:" in line]
        apps_json = json.dumps(apps_list)
        return apps_json
        # Simple parse
    except Exception as error:
        return [f"Error fetching apps: {error}"]


def get_geolocation():
    """
    Retrieve geolocation information based on the device's public IP address.

    Returns:
        dict: A dictionary containing IP address, city, state, country, latitude, and longitude.
    """
    geo_loaction = geocoder.ip("me")
    return {
        "ip": geo_loaction.ip,
        "city": geo_loaction.city,
        "state": geo_loaction.state,
        "country": geo_loaction.country,
        "lat": geo_loaction.latlng[0] if geo_loaction.latlng else None,
        "lng": geo_loaction.latlng[1] if geo_loaction.latlng else None,
    }


def get_harddisk_serial():
    """
    Retrieve the hard disk serial number based on the operating system.

    Returns:
        str: The hard disk serial number or an error message.
    """
    system = platform.system()
    harddisk_serial = "Unsupported OS"
    if system == "Windows":
        # Windows Disk Serial
        harddisk_serial = get_harddisk_serial_windows()

    elif system == "Linux":
        # Linux Disk Serial
        harddisk_serial = get_harddisk_serial_linux()

    elif system == "Darwin":
        # macOS Disk Serial
        harddisk_serial = get_harddisk_serial_macos()

    return harddisk_serial


def get_harddisk_serial_windows():
    """
    Retrieve the hard disk serial number for windows.

    Returns:
        str: The hard disk serial number or an error message.
    """
    try:
        output = subprocess.check_output("wmic diskdrive get SerialNumber", shell=True)
        return output.decode().split("\n")[1].strip()
    except Exception as error:
        return f"Error retrieving hard disk serial on Windows: {str(error)}"


def get_harddisk_serial_linux():
    """
    Retrieve the hard disk serial number for linux.

    Returns:
        str: The hard disk serial number or an error message.
    """
    try:
        output = subprocess.check_output(
            "lsblk -o NAME,SERIAL | grep sda | awk '{print $2}'", shell=True
        )
        return output.decode().strip()
    except Exception as error:
        return f"Error retrieving hard disk serial on Linux: {str(error)}"


def get_harddisk_serial_macos():
    """
    Retrieve the hard disk serial number for macos.

    Returns:
        str: The hard disk serial number or an error message.
    """
    try:
        output = subprocess.check_output(
            "system_profiler SPStorageDataType | grep 'Serial Number'", shell=True
        )
        return output.decode().split(":")[1].strip()
    except Exception as error:
        return f"Error retrieving hard disk serial on macOS: {str(error)}"
