"""Capture a snapshot from the bottom-up camera."""

import socket

from aurora_robot_tools.config import CAMERA_PORT


def main() -> None:
    """Trigger camera to record snapshot."""
    PORT = CAMERA_PORT
    command = "capturebottom"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        try:
            client.connect(("127.0.0.1", PORT))
        except ConnectionRefusedError:
            print("Camera daemon not running - start with 'aurora-rt startcam.")
        client.sendall(command.encode())


if __name__ == "__main__":
    main()
