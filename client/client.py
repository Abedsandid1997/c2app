"""
client.py

This module handles the client-side communication logic for the application.
It includes functions for SENDING and receiving data from the server, as well as handling
connection setup and management.
"""

import threading
import platform
import time
import tkinter as tk
from tkinter import messagebox, Toplevel, Text
import logging
import subprocess
import os
import sys
import socketio
import requests
from system_info import get_installed_apps, get_geolocation, get_harddisk_serial


# Server URL
SERVER_URL = "http://localhost:5000"
sio = socketio.Client()
DATA = {}

IS_SCHEDULED = False
SENDING = True
CLIENT_DIRECTORY = os.path.join(os.path.expanduser("~"))

LOG_FILE = "client_operations.log"
# Set up logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Function to add a device to the server's watchlist


def add_device():
    """
    Add the current device to the server's watchlist. This function initiates the connection
    to the server using Socket.IO and shows a message box when the device is added.
    """

    messagebox.showinfo("Success", "Device has been added to watchlist")

    # Connect to Socket.IO
    sio.connect(SERVER_URL)


def send_data():
    """
    Gather system information (such as device name, OS, installed apps, geolocation, etc.)
    and send it to the server via a POST request. Logs information about the data sent.
    """
    global DATA
    device_name = platform.node()  # Computer name
    os_name = platform.system()  # OS name
    os_version = platform.version()  # OS version
    installed_apps = str(get_installed_apps(os_name))
    timestamp_online = time.strftime("%Y-%m-%d %H:%M:%S")
    geolocation = str(get_geolocation())  # Get IP-based location
    harddisk_serial = get_harddisk_serial()
    DATA = {
        "device_name": device_name,
        "finger_print": harddisk_serial,
        "os_name": os_name,
        "os_version": os_version,
        "installed_apps": installed_apps,
        "timestamp_online": timestamp_online,
        "geolocation": geolocation,
    }

    try:
        response = requests.post(f"{SERVER_URL}/add_device", json=DATA)
        response.raise_for_status()  # Check if request succeeded
        logging.info("Data has been sent to server.")

    except requests.exceptions.RequestException as error:
        messagebox.showerror("Error", f"Error SENDING data: {error}")


def schedule_add_device():
    """
    Periodically resend the device information to the server every hour.
    Runs continuously while SENDING is set to True.
    """
    while SENDING:
        send_data()  # Send the device to the server's watchlist again
        time.sleep(3600)  # Wait for 1 hour before the next run


def send_heartbeat():
    """
    Send a heartbeat message containing the device's fingerprint to the server via a POST request.
    Used to check the device's connectivity status.
    """
    finger_print = get_harddisk_serial()  # Get device's fingerprint
    data = {"finger_print": finger_print}

    try:
        response = requests.post(f"{SERVER_URL}/heartbeat", json=data)
        response.raise_for_status()
        logging.info("Heartbeat sent.")

    except requests.exceptions.RequestException as error:
        print(f"Error SENDING heartbeat: {error}")


def start_heartbeat():
    """
    Start sending heartbeat messages every 10 seconds to the server to indicate the device's
    online status. Runs continuously while SENDING is set to True.
    """
    while SENDING:
        send_heartbeat()
        time.sleep(10)  # Send heartbeat every 10 seconds


# Socket.IO event handlers


@sio.event
def connect():
    """
    Handles the event when the client successfully connects to the server.
    It registers the device fingerprint and starts background threads to send
    heartbeat and scheduled data to the server.
    """
    global IS_SCHEDULED

    print("Connected to server")
    # Send fingerprint when connecting
    fingerprint = get_harddisk_serial()
    sio.emit("register_fingerprint", {"finger_print": fingerprint})

    # Start threads after connection
    if not IS_SCHEDULED:
        threading.Thread(target=start_heartbeat, daemon=True).start()
        threading.Thread(target=schedule_add_device, daemon=True).start()
        IS_SCHEDULED = True


@sio.event
def device_removed(data):
    """
    Handles the event when the device is removed from the server's watchlist.
    Stops the SENDING process and logs the removal.

    Args:
        data (dict): Information related to the device removal event.
    """
    global SENDING
    SENDING = False
    messagebox.showinfo(
        "Device Removed", f"You have been removed from the watchlist: {data}"
    )
    logging.info("Device Removed: You have been removed from the watchlist: %s", data)


@sio.event
def device_offline(data):
    """
    Handles the event when the server marks the device as offline.
    Displays a message to the user about the offline status.

    Args:
        data (dict): Information about the offline device.
    """
    messagebox.showinfo("Device Offline", f"Device offline: {data['device_name']}")


@sio.event
def disconnect():
    """
    Handles the event when the client is disconnected from the server.
    """
    print("Disconnected from server")


# Event to handle file uploads/downloads based on server's instruction
@sio.event
def file_transfer_event(data):
    """
    Handles the file transfer events triggered by the server, which can include
    downloading or uploading files. Responds based on the 'action' type.

    Args:
        data (dict): Information related to the file transfer event.
    """
    action = data.get("action")
    filename = data.get("filename")
    if action == "download" and filename:
        logging.info("Server requested download of file '%s'.", filename)
        download_file(filename)
    elif action == "upload" and filename:
        logging.info("Server requested upload of file '%s'.", filename)
        upload_file(filename)


# Event handler for command execution requests


@sio.on("command_event")
def handle_command_event(data):
    """
    Handles the execution of server-sent commands. Executes the command locally
    and sends the output back to the server.

    Args:
        data (dict): Contains the command to be executed.
    """
    command = data["command"]
    logging.info("Server requested to execute command: %s", command)
    execute_command(command)


# Socket.IO event to handle the file list request


@sio.on("request_file_list")
def handle_file_list_request():
    """
    Handles the server's request for the list of files in the client's directory.
    Sends the list of files back to the server.

    Args:
        data (dict): Contains information regarding the file list request.
    """
    try:
        # List files in the client's specified directory
        files = os.listdir(CLIENT_DIRECTORY)
        files = [
            f for f in files if os.path.isfile(os.path.join(CLIENT_DIRECTORY, f))
        ]  # Only list files
        logging.info("SENDING file list to server: %s", files)

        # Send the list of files back to the server
        sio.emit("send_file_list", {"files": files, "device_id": get_harddisk_serial()})

    except FileNotFoundError:
        logging.error("Directory not found: %s", CLIENT_DIRECTORY)
    except PermissionError:
        logging.error(
            "Permission denied when accessing the directory: %s", CLIENT_DIRECTORY
        )
    except OSError as error:
        logging.error("OS error occurred while listing files: %s", error)


# Start the GUI for Device Watchlist Manager
def start_gui():
    """
    Starts the Tkinter GUI for managing the device's watchlist.
    Provides options to add the device, show data, and check server status.
    """
    root = tk.Tk()
    root.title("Device Watchlist Manager")

    add_device_button = tk.Button(
        root, text="Add Device to Watchlist", command=add_device
    )
    add_device_button.pack(pady=10)

    show_data_button = tk.Button(root, text="Show Data", command=show_data)
    show_data_button.pack(pady=20)

    check_status_button = tk.Button(
        root, text="Check Server Status", command=check_server_status
    )
    check_status_button.pack(pady=10)

    show_logs_button = tk.Button(root, text="Show Logs", command=show_logs)
    show_logs_button.pack(pady=10)
    # Start GUI loop
    root.mainloop()


# Show data function


def show_data():
    """
    Opens a window to display all gathered device data.
    """
    data_window = Toplevel()
    data_window.title("All Data")
    text_box = Text(data_window, wrap="word", width=60, height=20)
    text_box.pack(pady=10, padx=10)

    for key, value in DATA.items():
        text_box.insert("end", f"{key}: {value}\n\n")

    text_box.config(state="disabled")


# Check server status function


def check_server_status():
    """
    Sends a request to the server to check its status. Displays the server status in a message box.
    """
    try:
        response = requests.get(f"{SERVER_URL}/status")
        response.raise_for_status()
        result = response.json()
        messagebox.showinfo("Server Status", result)
    except requests.exceptions.RequestException as error:
        messagebox.showerror("Error", f"Server is offline: {error}")


# Function to handle file download (server to client)
def download_file(filename):
    """
    Handles downloading a file from the server. Saves the file to the 'client_downloads' directory.

    Args:
        filename (str): Name of the file to download.
    """
    try:
        # Create directory 'client-downloads' if it doesn't exist
        download_directory = "client_downloads"
        if not os.path.exists(download_directory):
            os.makedirs(download_directory)

        # Construct the full file path
        file_path = os.path.join(download_directory, filename)

        # Download the file from the server
        response = requests.get(f"{SERVER_URL}/download/{filename}", stream=True)
        response.raise_for_status()

        # Save the downloaded file in 'client-downloads' directory
        with open(file_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        logging.info(
            "Downloaded file '%s' from the server and saved to '%s'.",
            filename,
            file_path,
        )

    except requests.exceptions.RequestException as error:
        logging.error("Error downloading file: %s", error)


# Function to handle file upload (client to server)


def upload_file(filename):
    """
    Handles uploading a file to the server.

    Args:
        filename (str): Name of the file to upload.
    """
    filepath = os.path.join(CLIENT_DIRECTORY, filename)

    try:
        with open(filepath, "rb") as file:
            files = {"file": file}
            response = requests.post(f"{SERVER_URL}/upload", files=files)
            response.raise_for_status()
        logging.info("Uploaded file '%s' to the server.", filepath)
    except requests.exceptions.RequestException as error:
        logging.error("Error uploading file: %s", error)


# Function to execute commands sent by the server


def execute_command(command):
    """
    Executes a system command sent from the server and returns the result back to the server.

    Args:
        command (str): Command string to execute.
    """
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        device_id = get_harddisk_serial()
        sio.emit(
            "command_output", {"command-output": result.stdout, "device_id": device_id}
        )
        if result.stderr:
            sio.emit("command_output", {"command-output": result.stderr})

        logging.info("Executed command: '%s' with output: '%s'", command, result.stdout)

    except Exception as error:
        logging.error("Command execution failed: %s", str(error))


# Show logs function
def show_logs():
    """
    Opens a new window to display the contents of the log file.
    """
    log_window = Toplevel()
    log_window.title("Client Logs")
    text_box = Text(log_window, wrap="word", width=80, height=20)
    text_box.pack(pady=10, padx=10)

    try:
        with open(LOG_FILE, "r") as log_file:
            log_data = log_file.read()
            text_box.insert("end", log_data)

    except FileNotFoundError:
        text_box.insert("end", "Log file not found.")
    except Exception as error:
        text_box.insert("end", f"Error reading log file: {error}")

    text_box.config(state="disabled")


# Initial mode selection GUI


def select_mode():
    """
    Presents the user with the option to either run the program in background mode or GUI mode.
    """
    mode_window = tk.Tk()
    mode_window.title("Select Mode")

    def start_background_mode():
        mode_window.destroy()

        if os.name == "posix":
            subprocess.Popen(
                ["nohup", sys.executable, "-u"] + sys.argv + ["--background"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                close_fds=True,
            )
        elif os.name == "nt":
            subprocess.Popen(
                [sys.executable, "-u"] + sys.argv + ["--background"],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )

    def start_gui_mode():
        mode_window.destroy()
        start_gui()  # Start the GUI mode

    background_button = tk.Button(
        mode_window, text="Run in Background Mode", command=start_background_mode
    )
    background_button.pack(pady=10)

    gui_button = tk.Button(mode_window, text="Run in GUI Mode", command=start_gui_mode)
    gui_button.pack(pady=10)

    mode_window.mainloop()


if __name__ == "__main__":
    if "--background" in sys.argv:
        # Kör som en bakgrundsprocess utan GUI
        add_device()
        while SENDING:
            time.sleep(1)  # Keep the program running
    else:
        select_mode()  # Visa GUI-läge
