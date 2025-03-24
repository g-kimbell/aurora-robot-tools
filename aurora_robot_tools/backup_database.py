"""Copyright © 2025, Empa, Graham Kimbell, Enea Svaluto-Ferro, Ruben Kuhnel, Corsin Battaglia.

Script to backup the chemspeedDB database to a folder with the base sample ID as the filename.

"""

import shutil
import sqlite3
from datetime import datetime

import pytz

from aurora_robot_tools.config import DATABASE_BACKUP_DIR, DATABASE_FILEPATH, TIME_ZONE


def main() -> None:
    """Make a backup of the database to the backup folder."""
    value = ""
    try:
        with sqlite3.connect(DATABASE_FILEPATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM Settings_Table WHERE key = 'Base Sample ID'")
            result = cursor.fetchone()
            value = result[0] if result is not None else ""
    except sqlite3.Error as e:
        print("Database error: ", e)

    if value == "":
        tz = pytz.timezone(TIME_ZONE)
        value = datetime.now(tz).strftime("%Y-%m-%d_%H-%M-%S")
        print("Base Sample ID not found in the database. Using current timestamp instead.")

    # copy database file to backup folder with the base sample ID as the filename
    DATABASE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_filepath = DATABASE_BACKUP_DIR / (value + ".db")
    shutil.copy(DATABASE_FILEPATH, backup_filepath)
    print(f"Database backed up to {backup_filepath}.")


if __name__ == "__main__":
    main()
