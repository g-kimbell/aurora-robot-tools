"""Copyright © 2025, Empa, Graham Kimbell, Enea Svaluto-Ferro, Ruben Kuhnel, Corsin Battaglia.

Capture an image from the camera and save as png and raw 12-bit numpy array.

"""
import sqlite3
from time import sleep

import h5py
import numpy as np
from PIL import Image

import aurora_robot_tools.camera.gxipy as gx
from aurora_robot_tools.config import DATABASE_FILEPATH, IMAGE_DIR


def main() -> None:
    """Connect to camera, capture image, and save as png and raw 12-bit numpy array."""
    # Connect to camera
    device_manager = gx.DeviceManager()
    dev_num, dev_info_list = device_manager.update_device_list()
    print(f"Number of enumerated devices is {dev_num}")
    if dev_num == 0:
        msg = "Cannot connect to camera."
        raise ValueError(msg)

    try:
        cam = device_manager.open_device_by_index(1)  # connect to first camera
        cam.PixelFormat.set(gx.GxPixelFormatEntry.MONO12)  # 12-bit
        cam.TriggerMode.set(gx.GxSwitchEntry.OFF)  # continuous trigger
        cam.AcquisitionMode.set(gx.GxAcquisitionModeEntry.CONTINUOUS)  # continuous acquisition
        cam.ExposureAuto.set(gx.GxAutoEntry.CONTINUOUS)  # continuous auto exposure
        cam.stream_on()  # start data acquisition

        # grab images until exposure is stable
        avg_brightness = 0
        prev_avg_brightness = 0
        stable = 0
        failed = 0
        for _ in range(500):
            raw_image = cam.data_stream[0].get_image()
            if raw_image:
                numpy_image = raw_image.get_numpy_array()
                prev_avg_brightness = avg_brightness
                avg_brightness = np.mean(numpy_image)
                diff = avg_brightness - prev_avg_brightness
                if abs(diff) < 50:
                    stable += 1
                else:
                    stable = 0
                if stable > 20:
                    break
            else:
                print("didn't get anything")
                failed += 1
                if failed >= 10:
                    raise ValueError
                sleep(1)
    finally:
        cam.stream_off()
        cam.close_device()

    # Save last image
    # Convert 12-bit image to 8-bit for saving as PNG
    numpy_image_8bit = (numpy_image >> 4).astype(np.uint8)
    im = Image.fromarray(numpy_image_8bit)

    # Get Run ID from database and cell/press numbers from database
    with sqlite3.connect(DATABASE_FILEPATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT `value` FROM Settings_Table WHERE `key` = 'Base Sample ID'")
        run_id = cursor.fetchone()[0]
        cursor.execute(
            "SELECT `Current Press Number`, `Cell Number`, `Last Completed Step` "
            "FROM Cell_Assembly_Table "
            "WHERE `Current Press Number` > 0 AND `Error Code` = 0 "
            "ORDER BY `Current Press Number` ASC",
        )
        press_cell_steps = cursor.fetchall()

    # Make filename from press/cell/step numbers
    folderpath = IMAGE_DIR/run_id
    folderpath.mkdir(parents=True, exist_ok=True)
    filename = "_".join([f"p{p}c{c}s{s}" for p,c,s in press_cell_steps])

    # Save lossy compressed png image, make sure filename doesn't already exist
    if (folderpath/filename).with_suffix(".png").exists():
        i = 1
        while (folderpath/(filename+f"_{i}")).with_suffix(".png").exists():
            i += 1
        filename += f"_{i}"
    im.save((folderpath/filename).with_suffix(".png"), compress_level=9)
    with h5py.File((folderpath/filename).with_suffix(".h5"), "w") as f:
        f.create_dataset("image", data=numpy_image, compression="gzip", compression_opts=9)

if __name__ == "__main__":
    main()
