"""Control the LED ring light on the camera."""

import serial

# Settings for the serial connection
COM_PORT = "COM7"
BAUD_RATE = 9600

all_modes = {
    "0": "0",
    "off": "0",
    "1": "1",
    "r": "1",
    "red": "1",
    "2": "2",
    "g": "2",
    "green": "2",
    "3": "3",
    "b": "3",
    "blue": "3",
    "4": "4",
    "w": "4",
    "white": "4",
    "on": "4",
    "5": "5",
    "party": "5",
    "6": "6",
    "qr": "6",
}


def set_light(light_mode: str) -> None:
    """Input off, r, g, b, w, on, party, qr."""
    if light_mode not in all_modes:
        msg = f"Invalid input: {input}. Valid inputs are: {', '.join(all_modes.keys())}"
        raise ValueError(msg)
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
    ser.write(all_modes[light_mode].encode())
    ser.readall()
    ser.close()
