"""Controls for ring light of camera."""

import serial

allowed_settings = {
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


def set_light(setting: str) -> None:
    """Set camera light.

    Args:
        setting (str): Input string to set the light, e.g. "r", "b", "g", "off"

    """
    if setting not in allowed_settings:
        msg = f"Invalid input: {input}. Valid inputs are: {', '.join(allowed_settings.keys())}"
        raise ValueError(msg)
    ser = serial.Serial("COM7", 9600, timeout=1)
    ser.write(allowed_settings[setting].encode())
    ser.readall()
    ser.close()
