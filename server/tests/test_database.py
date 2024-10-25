"""
Unit tests for the DeviceDatabase class.

This module contains test cases for adding, updating, and retrieving devices
from the database as well as checking device statuses.
"""

import unittest
import datetime
import os
from database import DeviceDatabase


class TestDeviceDatabase(unittest.TestCase):
    """
    Test cases for the DeviceDatabase class.

    This class includes tests for adding, updating, removing, and querying devices in the database.
    """

    def setUp(self):
        """Set up a new database in memory for each test."""
        # Skapa en ny databas i minnet för varje test
        self.database = DeviceDatabase("test.db")
        self.database.create_tables()  # Se till att tabellerna skapas

    def tearDown(self):
        """Remove the test database after each test."""
        # Radera testdatabasen efter varje test
        if os.path.exists("test.db"):
            os.remove("test.db")

    def test_add_device(self):
        """Test adding a device to the database."""
        # Lägg till en enhet i databasen
        self.database.add_device(
            "fingerprint_1",
            "Device1",
            "Android",
            "10",
            "App1, App2",
            "2023-01-01 10:00:00",
            "Location1",
            "2023-01-01 10:00:00",
            "online",
        )
        self.database.add_device(
            "fingerprint_2",
            "Device1",
            "Android",
            "10",
            "App1, App2",
            "2023-01-01 10:00:00",
            "Location1",
            "2023-01-01 10:00:00",
            "online",
        )
        self.database.add_device(
            "fingerprint_3",
            "Device1",
            "Android",
            "10",
            "App1, App2",
            "2023-01-01 10:00:00",
            "Location1",
            "2023-01-01 10:00:00",
            "online",
        )

        # Hämta enheten från databasen
        device = self.database.get_device("fingerprint_1")
        devices = len(self.database.get_all_devices())
        # Kontrollera att enheten har rätt värden
        self.assertIsNotNone(device)
        self.assertEqual(device[1], "fingerprint_1")
        self.assertEqual(3, devices)
        self.assertEqual(device[2], "Device1")
        self.assertEqual(device[3], "Android")

    def test_update_device(self):
        """Test updating a device in the database."""
        # Lägg till en enhet
        self.database.add_device(
            "fingerprint_2",
            "Device2",
            "iOS",
            "14",
            "App1",
            "2023-01-01 11:00:00",
            "Location2",
            "2023-01-01 11:00:00",
            "online",
        )

        # Uppdatera samma enhet
        self.database.add_device(
            "fingerprint_2",
            "Device2_updated",
            "iOS",
            "14.1",
            "App1, App2",
            "2023-01-01 12:00:00",
            "Location3",
            "2023-01-01 12:00:00",
            "offline",
        )

        # Hämta den uppdaterade enheten
        device = self.database.get_device("fingerprint_2")

        # Kontrollera att uppdateringarna stämmer
        self.assertEqual(device[2], "Device2_updated")
        self.assertEqual(device[3], "iOS")
        self.assertEqual(device[9], "offline")

    def test_remove_device(self):
        """Test removing a device from the database."""
        # Lägg till en enhet och ta sedan bort den
        self.database.add_device(
            "fingerprint_3",
            "Device3",
            "Android",
            "11",
            "App1",
            "2023-01-01 13:00:00",
            "Location4",
            "2023-01-01 13:00:00",
            "online",
        )
        removed_fingerprint = self.database.remove_device(1)

        # Kontrollera att enheten togs bort
        self.assertEqual(removed_fingerprint, "fingerprint_3")
        self.assertIsNone(self.database.get_device("fingerprint_3"))

    def test_get_offline_devices(self):
        """Test retrieving offline devices from the database."""
        # Lägg till två enheter, en online och en offline
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        old_time = (datetime.datetime.now() - datetime.timedelta(minutes=2)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        self.database.add_device(
            "fingerprint_4",
            "Device4",
            "Android",
            "12",
            "App1",
            current_time,
            "Location5",
            current_time,
            "online",
        )
        self.database.add_device(
            "fingerprint_5",
            "Device5",
            "Android",
            "12",
            "App1",
            old_time,
            "Location6",
            old_time,
            "online",
        )

        # Hämta enheter som är offline (senast setts för mer än 1 minut sedan)
        offline_devices = self.database.get_offline_devices()

        # Kontrollera att endast den äldre enheten är offline
        self.assertEqual(len(offline_devices), 1)
        self.assertEqual(offline_devices[0][1], "fingerprint_5")

    def test_update_device_status(self):
        """Test updating the status of a device."""
        # Lägg till en enhet
        self.database.add_device(
            "fingerprint_6",
            "Device6",
            "iOS",
            "15",
            "App1",
            "2023-01-01 15:00:00",
            "Location7",
            "2023-01-01 15:00:00",
            "online",
        )

        # Uppdatera enhetens status till offline
        self.database.update_device_status("fingerprint_6")

        # Kontrollera att enhetens status är uppdaterad till offline
        device = self.database.get_device("fingerprint_6")
        self.assertEqual(device[9], "offline")

    def test_update_device_lastseen(self):
        """Test updating the last seen timestamp of a device."""
        # Lägg till en enhet
        self.database.add_device(
            "fingerprint_7",
            "Device7",
            "Android",
            "13",
            "App2",
            "2023-01-01 16:00:00",
            "Location8",
            "2023-01-01 16:00:00",
            "online",
        )

        # Uppdatera enhetens senaste aktivitet
        self.database.update_device_lastseen("fingerprint_7")

        # Kontrollera att senaste aktivitetens tid har uppdaterats
        device = self.database.get_device("fingerprint_7")
        last_seen = device[8]
        self.assertAlmostEqual(
            datetime.datetime.strptime(last_seen, "%Y-%m-%d %H:%M:%S"),
            datetime.datetime.now(),
            delta=datetime.timedelta(seconds=5),
        )
