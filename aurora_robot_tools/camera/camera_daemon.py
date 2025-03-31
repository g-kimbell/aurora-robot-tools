"""Daemon for live view of bottom-up camera, listens for capture command."""

import socket
import sqlite3
import threading
from pathlib import Path

import cv2

from aurora_robot_tools.config import CAMERA_PORT, DATABASE_FILEPATH

PHOTO_PATH = Path("C:/Aurora_webcam_images/")

step_radius = {
    1: 10,
    2: 10,
    30: 7.5,
    40: 7,
    60: 8,
    80: 7.5,
    90: 7,
    100: 8,
    120: 9.5,
}
radius_mm = 10

def socket_listener() -> None:
    """Listen for capture message on socket."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("127.0.0.1", CAMERA_PORT))  # Bind to any interface, port 12345
    server_socket.listen(1)
    print("Listening for connections...")
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")

        data = client_socket.recv(1024).decode().strip()
        if data == "capturebottom" and latest_frame is not None:
            # get current cell, press, step numbers from database
            with sqlite3.connect(DATABASE_FILEPATH) as conn:
                cursor = conn.cursor()
                # get LATEST value from Timestamp_table where `Complete` = 0
                cursor.execute("SELECT `value` from Settings_Table WHERE `key` = 'Base Sample ID'")
                result = cursor.fetchone()
                run_id = result[0]
                cursor.execute(
                    "SELECT `Cell Number`, `Step Number`, `Timestamp` from Timestamp_Table WHERE `Complete` = 0 ORDER BY `Timestamp` DESC LIMIT 1"
                )
                result = cursor.fetchone()
                label = f"cell_{result[0]}_step_{result[1]}"
            global radius_mm
            radius_mm = step_radius.get(int(result[1]),10)
            photo_path = PHOTO_PATH / run_id / f"{label!s}.png"
            if not photo_path.parent.exists():
                photo_path.parent.mkdir(parents=True)
            cv2.imwrite(str(photo_path), latest_frame)
            print(f"Frame saved as {photo_path!s}")

        client_socket.close()


def main() -> None:
    """Start webcam, show in window, listen for capture command."""
    global latest_frame
    global radius_mm
    print("Starting webcam, press q to quit.")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Use DirectShow
    latest_frame = None  # Global variable to store the latest frame
    thread = threading.Thread(target=socket_listener, daemon=True)
    thread.start()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        latest_frame = frame.copy()  # Update the latest frame
        frame = cv2.circle(frame, (320,240), int(radius_mm*375/20), (0,0,255))
        frame = cv2.line(frame,(320,0),(320,480), (0,0,255))
        frame = cv2.line(frame,(0,240),(640,240), (0,0,255))
        cv2.imshow("Webcam Feed", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
