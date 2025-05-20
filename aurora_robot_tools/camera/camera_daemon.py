"""Daemon for live view of bottom-up camera, listens for capture command."""

import socket
import sqlite3
import threading
from pathlib import Path
from time import sleep

import cv2
import gxipy as gx
import numpy as np

from aurora_robot_tools.camera.ringlight import set_light
from aurora_robot_tools.config import CAMERA_PORT, DATABASE_FILEPATH

PHOTO_PATH = Path("C:/Aurora_webcam_images/")

step_radius = {
    1: 10.0,
    2: 10.0,
    30: 7.5,
    40: 7.0,
    60: 8.0,
    100: 8.0,
    120: 9.0,
}
mm_to_px = 1600 / 20
radius_mm = 10.0
coords = (None, None)
last_frame_b = None
last_frame_t = None


def socket_listener() -> None:
    """Capture images when requested by socket connection."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("127.0.0.1", CAMERA_PORT))
    server_socket.listen(1)
    print("Listening for connections...")
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        data = client_socket.recv(1024).decode().strip()
        print(f"Command: {data}")
        if data == "capturebottom" and last_frame_b is not None:
            capture_bottom(client_socket)
        if data == "capturetop" and last_frame_t is not None:
            capture_top(client_socket)
        client_socket.close()


def capture_bottom(client_socket: socket.socket) -> None:
    """Capture an image from the bottom camera."""
    print("Capturing from bottom camera")
    global last_frame_b
    if last_frame_b is None:
        sleep(1)
        if last_frame_b is None:
            print("No frame captured from bottom camera")
            client_socket.sendall(b"1")
            return
    captured_frame = last_frame_b.copy()
    client_socket.sendall(b"0")
    # get current cell, press, step numbers from database
    with sqlite3.connect(DATABASE_FILEPATH) as conn:
        cursor = conn.cursor()
        # get LATEST value from Timestamp_table where `Complete` = 0
        cursor.execute("SELECT `value` from Settings_Table WHERE `key` = 'Base Sample ID'")
        result = cursor.fetchone()
        run_id = result[0]
        cursor.execute(
            "SELECT `Cell Number`, `Step Number` from Timestamp_Table "
            "WHERE `Complete` = 0 ORDER BY `Timestamp` DESC LIMIT 1",
        )
        result = cursor.fetchone()
        result = result if result else (0, 0)
        label = f"cell_{result[0]}_step_{result[1]}"
    radius_mm = step_radius.get(int(result[1]), 10.0)

    # Detect circle in image
    global coords
    coords = detect_circle(captured_frame, radius_mm * mm_to_px)
    if coords[0] is not None:
        y, x, _ = captured_frame.shape
        dx_mm = (x // 2 - coords[0]) / mm_to_px
        dy_mm = (y // 2 - coords[1]) / mm_to_px
        print(f"{dx_mm=}, {dy_mm=}")
        if result[0] > 0:
            write_coords_to_db(result[0], result[1], dx_mm, dy_mm)
    else:
        print("Could not detect circle")
    photo_path = PHOTO_PATH / run_id / "bottom_camera" / f"{label!s}.png"
    if not photo_path.parent.exists():
        photo_path.parent.mkdir(parents=True)
    cv2.imwrite(str(photo_path), captured_frame)
    print(f"Frame saved as {photo_path!s}")


def capture_top(client_socket: socket.socket) -> None:
    """Capture an image from the top camera."""
    print("Capturing from top camera")
    global last_frame_t
    if last_frame_t is None:
        sleep(1)
        if last_frame_t is None:
            print("No frame captured from bottom camera")
            client_socket.sendall(b"1")
            return
    captured_frame_2 = last_frame_t.copy()
    client_socket.sendall(b"0")
    # get current cell, press, step numbers from database
    with sqlite3.connect(DATABASE_FILEPATH) as conn:
        cursor = conn.cursor()
        # get LATEST value from Timestamp_table where `Complete` = 0
        cursor.execute("SELECT `value` from Settings_Table WHERE `key` = 'Base Sample ID'")
        result = cursor.fetchone()
        run_id = result[0]
        cursor.execute(
            "SELECT `Cell Number`, `Last Completed Step`, `Current press number` from Cell_Assembly_Table "
            "WHERE `Current press number` > 0 "
            "ORDER BY `Current press number` ASC",
        )
        results = cursor.fetchall()
        results = results if results else [(0, 0, 0)]
        label = "_".join([f"p{p}c{c}s{s}" for p, c, s in results])
    photo_path = PHOTO_PATH / run_id / "top_camera" / f"{label}.png"
    if not photo_path.parent.exists():
        photo_path.parent.mkdir(parents=True)
    cv2.imwrite(str(photo_path), captured_frame_2)
    print(f"Frame saved as {photo_path!s}")


def write_coords_to_db(cell: int, step: int, dx_mm: float, dy_mm: float) -> None:
    """Write the coordinates to the database."""
    with sqlite3.connect(DATABASE_FILEPATH) as conn:
        cursor = conn.cursor()
        # insert Cell Number, Step Number, dx_mm, dy_mm into Calibration_Table
        cursor.execute(
            "INSERT INTO Calibration_Table (`Cell Number`, `Step Number`, `dx_mm`, `dy_mm`) VALUES (?, ?, ?, ?)",
            (cell, step, dx_mm, dy_mm),
        )
        conn.commit()


def detect_circle(image: np.ndarray, step_radius_px: float) -> tuple:
    """Detect the circle in the image using HoughCircles."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        1,
        50,
        param1=50,
        param2=30,
        minRadius=int(step_radius_px * 0.99),
        maxRadius=int(step_radius_px * 1.01),
    )
    if circles is not None and len(circles) == 1:
        circle = circles[0][0]
        c_x_px = int(circle[0])
        c_y_px = int(circle[1])
        return c_x_px, c_y_px
    return None, None


def shrink_frame(frame: np.ndarray, ratio: float) -> np.ndarray:
    """Shrink the frame by a ratio."""
    y, x, _ = frame.shape
    return cv2.resize(frame, [x // ratio, y // ratio])


def add_target(frame: np.ndarray, coords: tuple, radius_mm: float, ratio: float) -> np.ndarray:
    """Add target circles to the frame."""
    y, x, _ = frame.shape
    frame = cv2.circle(frame, (x // 2, y // 2), int(radius_mm * mm_to_px / ratio), (0, 0, 255))
    frame = cv2.line(frame, (x // 2, 0), (x // 2, y), (0, 0, 255))
    frame = cv2.line(frame, (0, y // 2), (x, y // 2), (0, 0, 255))
    if coords[0] is not None:
        resized_coords = coords[0] // ratio, coords[1] // ratio
        frame = cv2.circle(frame, resized_coords, int(radius_mm * mm_to_px / ratio), (0, 255, 0))
        frame = cv2.line(
            frame,
            (resized_coords[0], resized_coords[1] + 10),
            (resized_coords[0], resized_coords[1] - 10),
            (0, 255, 0),
        )
        frame = cv2.line(
            frame,
            (resized_coords[0] + 10, resized_coords[1]),
            (resized_coords[0] - 10, resized_coords[1]),
            (0, 255, 0),
        )
    return frame


def main() -> None:
    """Start webcam, show in window, listen for capture command."""
    set_light("party")  # Loading light
    global last_frame_b
    global last_frame_t

    print("Starting cameras, press q to quit.")

    # Connect to first USB webcam with DirectShow
    print("Loading bottom camera...")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(3, 10000)  # Set max frame size
    cap.set(4, 10000)
    ret, frame = cap.read()
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    cap.set(28, 1023)  # Set focus to closest distance
    ret, frame = cap.read()

    # Connect to first gxipy camera
    print("Loading top camera...")
    device_manager = gx.DeviceManager()
    dev_num, dev_info_list = device_manager.update_device_list()
    cam = device_manager.open_device_by_index(1)
    cam.PixelFormat.set(gx.GxPixelFormatEntry.MONO8)
    cam.AcquisitionMode.set(gx.GxAcquisitionModeEntry.CONTINUOUS)
    cam.ExposureAuto.set(gx.GxAutoEntry.CONTINUOUS)
    cam.stream_on()

    thread = threading.Thread(target=socket_listener, daemon=True)
    thread.start()
    set_light("b")  # Ready light
    print("Ready to capture images.")
    try:
        while True:
            ret, frame_b = cap.read()
            frame_t = cam.data_stream[0].get_image().get_numpy_array()

            # Update bottom camera frame
            if isinstance(frame_b, np.ndarray):
                last_frame_b = frame_b.copy()
                frame_b = shrink_frame(frame_b, 4)
                frame_b = add_target(frame_b, coords, radius_mm, 4)
                cv2.imshow("Bottom camera", frame_b)

            # Update top camera frame
            if isinstance(frame_t, np.ndarray):
                last_frame_t = frame_t.copy()
                frame_b = shrink_frame(frame_b, 4)
                cv2.imshow("Top camera", frame_t)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        set_light("off")
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
