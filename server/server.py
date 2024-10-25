"""
This module handles the main server functionality, including device management,
file transfers, and real-time communication using Flask and Flask-SocketIO.
"""

import threading
import time
import logging
import os
import re
import json
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory,
    render_template,
    redirect,
    url_for,
    flash,
)
from database import DeviceDatabase  # Import the new DeviceDatabase class

# Initialize logging
logging.basicConfig(
    filename="server.log", level=logging.INFO, format="%(asctime)s - %(message)s"
)

SERVER_URL = "http://localhost:5000"
app = Flask(__name__)
app.secret_key = re.sub(r"[^a-z\d]", "", os.path.realpath(__file__))
socketio = SocketIO(app, cors_allowed_origins="*")

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["DOWNLOAD_FOLDER"] = DOWNLOAD_FOLDER

# Create an instance of the DeviceDatabase class
db = DeviceDatabase("watchlist.db")
db.create_tables()
connected_clients = {}


@app.route("/")
def main():
    """Renders the main page displaying all devices.

    Returns:
        Rendered HTML page showing the list of devices.
    """
    devices = db.get_all_devices()  # Use the DeviceDatabase method
    return render_template("index.html", devices=devices)


@app.route("/logs")
def view_logs():
    """Displays the server logs.

    Returns:
        Rendered HTML page showing the server logs.
    """
    logs = show_logs()
    return render_template("logs.html", logs=logs)


@app.route("/command")
def send_command():
    """Renders the command interface for a specific device.

    Returns:
        Rendered HTML page with the command interface for the specified device.
    """
    device_id = request.args.get("id")
    device = db.get_device(device_id)  # Use the DeviceDatabase method
    return render_template("command.html", device=device)


@app.route("/command/result", methods=["POST"])
def send_command_post():
    """Handles the command sent to a device.

    Args:
        command (str): The command to be sent to the device.
        device_id (str): The ID of the device to which the command is sent.

    Returns:
        JSON response indicating the status of the command.
    """
    command = request.form["command"]
    device_id = request.form["id"]

    if device_id in connected_clients:
        session_id = connected_clients[device_id]
        socketio.emit("command_event", {"command": command}, room=session_id)
        logging.info("Sent command '%s' to device %s", command, device_id)
        return jsonify({"status": "Command sent"})

    return jsonify({"status": "Device not connected"}), 404


@app.route("/upload")
def upload():
    """Renders the upload interface for a specific device.

    Returns:
        Rendered HTML page showing the upload interface for the specified device.
    """
    device_id = request.args.get("id")
    device = db.get_device(device_id)  # Use the DeviceDatabase method
    files = os.listdir(UPLOAD_FOLDER)
    return render_template("upload.html", device=device, files=files)


@app.route("/upload_file", methods=["POST"])
def upload_file():
    """Handles the file upload from a device.

    Args:
        action (str): The action to perform (e.g., 'download').
        finger_print (str): The fingerprint of the device uploading the file.

    Returns:
        Redirects to the upload page or returns an error response.
    """
    action = "download"
    finger_print = request.form["id"]
    if finger_print in connected_clients:
        session_id = connected_clients.get(finger_print)
    if "file" not in request.files:
        flash("There is no file", "danger")
        return redirect(url_for("upload", id=finger_print))
    file = request.files["file"]
    if file.filename == "":
        flash("There is no file", "danger")

        return redirect(url_for("upload", id=finger_print))

    flash("the file has been uploaded", "success")
    file.save(os.path.join(UPLOAD_FOLDER, file.filename))
    socketio.emit(
        "file_transfer_event",
        {"action": action, "filename": file.filename},
        room=session_id,
    )
    logging.info(
        "Sent file transfer request to device %s: %s %s",
        finger_print,
        action,
        file.filename,
    )
    return redirect(url_for("upload", id=finger_print))


@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    """Handles file download requests.

    Args:
        filename (str): The name of the file to download.

    Returns:
        The requested file if found, otherwise an error response.
    """
    try:
        return send_from_directory(
            app.config["UPLOAD_FOLDER"], filename, as_attachment=True
        )
    except FileNotFoundError:
        return jsonify({"message": "File not found", "status": "fail"}), 404


@socketio.on("command_output")
def handle_command_output(data):
    """Handles the output received from a device command.

    Args:
        data (dict): Contains the command output and device ID.
    """
    command_output = data["command-output"]
    device_id = data["device_id"]
    logging.info("Received output from %s: %s", device_id, command_output)
    socketio.emit("command_result", {"output": command_output, "device_id": device_id})


@app.route("/request_file_list", methods=["POST"])
def request_file_list():
    """Requests the file list from a specific device.

    Returns:
        JSON response indicating the status of the request.
    """
    device_id = request.form["id"]
    if device_id in connected_clients:
        session_id = connected_clients.get(device_id)
        socketio.emit("request_file_list", room=session_id)
        logging.info("Requested file list from device: %s", device_id)
        return jsonify({"status": "Request sent to device"})

    return jsonify({"status": "Device not connected"}), 404


@socketio.on("send_file_list")
def handle_file_list(data):
    """Handles the file list received from a device.

    Args:
        data (dict): Contains the list of files and device ID.
    """
    files = data["files"]
    device_id = data["device_id"]
    logging.info("Received file list from device %s: %s", device_id, files)
    socketio.emit("send_file_result", {"files": files, "device_id": device_id})


@app.route("/show_file_list")
def show_files():
    """Displays the list of files for a specific device.

    Returns:
        Rendered HTML page showing the file list for the specified device.
    """
    device_id = request.args.get("id")
    device = db.get_device(device_id)  # Use the DeviceDatabase method
    return render_template("file_list.html", device=device)


@app.route("/download", methods=["POST"])
def download():
    """Handles the download request for a specific file.

    Returns:
        Redirects to the file list or performs a download action.
    """
    action = "upload"
    finger_print = request.form["id"]
    if finger_print in connected_clients:
        session_id = connected_clients.get(finger_print)
    if "file" not in request.form:
        flash("There is no file", "danger")
        return redirect(url_for("show_files", id=finger_print))
    filename = request.form["file"]
    if filename == "":
        flash("There is no file", "danger")
        return redirect(url_for("show_files", id=finger_print))

    flash("The file has been downloaded", "success")
    socketio.emit(
        "file_transfer_event",
        {"action": action, "filename": filename},
        room=session_id,
    )
    logging.info(
        "Sent file transfer request to device %s: %s %s", finger_print, action, filename
    )
    return redirect(url_for("show_files", id=finger_print))


@app.route("/upload", methods=["POST"])
def upload_file_to_server():
    """Handles the file upload to the server.

    Returns:
        JSON response indicating the status of the upload.
    """
    if "file" not in request.files:
        return jsonify({"message": "No file part", "status": "fail"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"message": "No selected file", "status": "fail"}), 400

    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config["DOWNLOAD_FOLDER"], filename))
    logging.info("File '%s' uploaded successfully.", filename)
    return (
        jsonify(
            {
                "message": f"File {filename} uploaded successfully",
                "status": "success",
            }
        ),
        200,
    )


@app.route("/device/details")
def device_details():
    """Displays detailed information about a specific device.

    Returns:
        Rendered HTML page showing the details of the specified device.
    """
    device_id = request.args.get("id")
    device = db.get_device(device_id)  # Use the DeviceDatabase method
    apps_list = json.loads(device[5])
    return render_template("details.html", device=device, apps_list=apps_list)


@app.route("/add_device", methods=["POST"])
def add_device_route():
    """Handles the addition or update of a device in the database.

    Returns:
        JSON response indicating the status of the addition or update.
    """
    data = request.json
    device_name = data["device_name"]
    os_name = data["os_name"]
    os_version = data["os_version"]
    installed_apps = data.get("installed_apps", "N/A")
    geolocation = data.get("geolocation", "N/A")
    timestamp_online = data["timestamp_online"]
    last_seen = data["timestamp_online"]
    finger_print = data.get("finger_print")
    device_status = "online"

    device = db.get_device(finger_print)  # Use the DeviceDatabase method
    if device:
        db.add_device(
            finger_print,
            device_name,
            os_name,
            os_version,
            installed_apps,
            timestamp_online,
            geolocation,
            last_seen,
            device_status,
        )
        message = "Device updated successfully"
        logging.info("Device %s updated", device_name)
    else:
        db.add_device(
            finger_print,
            device_name,
            os_name,
            os_version,
            installed_apps,
            timestamp_online,
            geolocation,
            last_seen,
            device_status,
        )
        message = "Device added successfully"
        logging.info("Device %s added", device_name)

    return jsonify({"message": message, "status": "success"})


@app.route("/remove_device", methods=["POST"])
def remove_device_route():
    """Handles the removal of a device from the database.

    Returns:
        Redirects to the main page after removal.
    """
    device_id = request.form["id"]
    finger_print = db.remove_device(device_id)  # Use the DeviceDatabase method

    if finger_print in connected_clients:
        session_id = connected_clients.get(finger_print)
        socketio.emit(
            "device_removed",
            {"message": f"Device {finger_print} removed"},
            room=session_id,
        )
        del connected_clients[finger_print]
    logging.info("Device %s removed from watchlist", finger_print)
    return redirect(url_for("main"))


@app.route("/status", methods=["GET"])
def status():
    """Checks the server status.

    Returns:
        JSON response indicating the server status.
    """
    logging.info("Server status requested")
    return jsonify({"status": "Server is running"})


@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    """Handles heartbeat signals from connected devices.

    Returns:
        JSON response confirming receipt of the heartbeat.
    """
    data = request.json
    finger_print = data["finger_print"]
    db.update_device_lastseen(finger_print)  # Use the DeviceDatabase method
    logging.info("Heartbeat received from device: %s", finger_print)
    return jsonify(
        {
            "message": f"Heartbeat received from device:{finger_print}",
            "status": "success",
        }
    )


def show_logs():
    """Reads and returns the server log contents.

    Returns:
        List of log entries or an error message if logs can't be read.
    """
    try:
        with open("server.log", "r", encoding="utf-8") as log_file:
            logs = log_file.readlines()
        return logs
    except FileNotFoundError:
        return ["Log file not found."]
    except IOError as error:
        return [f"Could not read log file: {str(error)}"]


def check_device_status():
    """Checks the status of devices in the database and updates their status if offline.

    Logs the status of offline devices and updates the database accordingly.
    """
    offline_devices = db.get_offline_devices()  # Use the DeviceDatabase method
    devices_list = [
        {
            "device_name": row[2],
            "finger_print": row[1],
            "status": row[9],
            "lastseen": row[8],
        }
        for row in offline_devices
    ]

    for device in devices_list:
        logging.info("Device %s is offline.", device["device_name"])
        db.update_device_status(device["finger_print"])  # Use the DeviceDatabase method


def start_status_check():
    """Continuously checks device status at regular intervals.

    This function runs in a separate thread to avoid blocking the main server.
    """
    while True:
        check_device_status()
        time.sleep(60)


@socketio.on("connect")
def handle_connect():
    """Handles a new client connection.

    Emits a message indicating a successful connection.
    """
    logging.info("Client connected")
    emit("message", {"message": "Connected to server"})


@socketio.on("register_fingerprint")
def handle_register_fingerprint(data):
    """Registers a device fingerprint with its corresponding session ID.

    Args:
        data (dict): Contains the fingerprint of the device.
    """
    finger_print = data["finger_print"]
    session_id = request.sid
    connected_clients[finger_print] = session_id
    logging.info(
        "Device with fingerprint %s registered with session %s",
        finger_print,
        session_id,
    )


@socketio.on("disconnect")
def handle_disconnect():
    """Handles client disconnection.

    Cleans up the connected clients dictionary and logs the disconnection.
    """
    session_id = request.sid
    for fingerprint, sid in list(connected_clients.items()):
        if sid == session_id:
            del connected_clients[fingerprint]
            logging.info("Client with fingerprint %s disconnected", fingerprint)
            break


if __name__ == "__main__":
    server_thread = threading.Thread(
        target=lambda: socketio.run(app, host="0.0.0.0", port=5000, use_reloader=False)
    )

    # Tråd för att kontrollera enheternas status
    status_check_thread = threading.Thread(target=start_status_check)

    # Starta båda trådarna
    server_thread.start()
    status_check_thread.start()

    # Vänta på att båda trådarna ska slutföra
    server_thread.join()
    status_check_thread.join()
