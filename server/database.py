"""
This module provides a class `DeviceDatabase` for interacting with a SQLite database
to manage device-related information. It includes methods to add, update, remove,
and retrieve devices, as well as to handle device status and activity tracking.
"""

import sqlite3
import datetime


class DeviceDatabase:
    """
    A class to manage devices in the database.
    Provides methods to add, update, remove, and retrieve devices,
    as well as to handle device status and last-seen updates.
    """

    def __init__(self, db_file):
        """
        Initialize the DeviceDatabase with a file path to the SQLite database.

        :param db_file: The database file path.
        """
        self.db_file = db_file

    def _get_connection(self):
        """Return a connection object to the SQLite database."""
        return sqlite3.connect(self.db_file)

    def create_tables(self):
        """Create the devices table if it doesn't already exist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS devices (
                            id INTEGER PRIMARY KEY,
                            finger_print TEXT UNIQUE,
                            device_name TEXT,
                            os_name TEXT,
                            os_version TEXT,
                            installed_apps TEXT,
                            timestamp_online TEXT,
                            geolocation TEXT,
                            last_seen TEXT,
                            status TEXT
                        )"""
        )
        conn.commit()
        conn.close()

    def add_device(
        self,
        finger_print,
        device_name,
        os_name,
        os_version,
        installed_apps,
        timestamp_online,
        geolocation,
        last_seen,
        status,
    ):
        """
        Add or update a device in the database.

        If the device already exists (based on `finger_print`), it will be updated.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO devices
                (
                    finger_print,
                    device_name,
                    os_name, os_version,
                    installed_apps,
                    timestamp_online,
                    geolocation,
                    last_seen,
                    status
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(finger_print) DO UPDATE SET
            device_name=excluded.device_name,
            os_name=excluded.os_name,
            os_version=excluded.os_version,
            installed_apps=excluded.installed_apps,
            timestamp_online=excluded.timestamp_online,
            geolocation=excluded.geolocation,
            last_seen=excluded.last_seen,
            status=excluded.status
        """,
            (
                finger_print,
                device_name,
                os_name,
                os_version,
                installed_apps,
                timestamp_online,
                geolocation,
                last_seen,
                status,
            ),
        )
        conn.commit()
        conn.close()

    def remove_device(self, device_id):
        """
        Remove a device by its ID from the database.

        :param id: The ID of the device to remove.
        :return: The fingerprint of the removed device or None if not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT finger_print FROM devices WHERE id = ?", (device_id,))
        finger_print = cursor.fetchone()
        cursor.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        conn.commit()
        conn.close()
        return finger_print[0] if finger_print else None

    def get_all_devices(self):
        """
        Retrieve all devices from the database.

        :return: A list of all devices.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM devices")
        devices = cursor.fetchall()
        conn.close()
        return devices

    def get_device(self, finger_print):
        """
        Retrieve a device by its fingerprint.

        :param finger_print: The fingerprint of the device.
        :return: The device data or None if not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM devices WHERE finger_print = ?", (finger_print,))
        device = cursor.fetchone()
        conn.close()
        return device

    def update_device_status(self, finger_print):
        """
        Update the status of a device to 'offline' by its fingerprint.

        :param finger_print: The fingerprint of the device to update.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE devices SET status = ? WHERE finger_print = ?",
            ("offline", finger_print),
        )
        conn.commit()
        conn.close()

    def update_device_lastseen(self, finger_print):
        """
        Update the 'last_seen' timestamp of a device to the current time.

        :param finger_print: The fingerprint of the device to update.
        """
        last_seen = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE devices SET last_seen=? WHERE finger_print=?",
            (last_seen, finger_print),
        )
        conn.commit()
        conn.close()

    def get_offline_devices(self):
        """
        Retrieve all devices that are considered offline (last seen more than 1 minute ago).

        :return: A list of offline devices.
        """
        current_time = datetime.datetime.now()
        offline_threshold = current_time - datetime.timedelta(
            minutes=0.5
        )
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM devices WHERE last_seen < ?",
            (offline_threshold.strftime("%Y-%m-%d %H:%M:%S"),),
        )
        offline_devices = cursor.fetchall()
        conn.close()
        return offline_devices
