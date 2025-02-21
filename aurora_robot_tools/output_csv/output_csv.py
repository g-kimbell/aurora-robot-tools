"""Copyright © 2024, Empa, Graham Kimbell, Enea Svaluto-Ferro, Ruben Kuhnel, Corsin Battaglia.

Convert the finished database to a csv file that can be read by Aurora and AiiDA.
"""
import sqlite3
import sys
from datetime import datetime
from tkinter import Tk, filedialog

import pandas as pd
import pytz

DATABASE_FILEPATH = "C:\\Modules\\Database\\chemspeedDB.db"

TIME_ZONE = "Europe/Zurich"

DEFAULT_OUTPUT_FILEPATH = "%userprofile%\\Desktop\\Outputs"

STEP_DEFINITION = {
    10: {
        "Step": "Bottom",
        "Description": "Place bottom casing",
    },
    20: {
        "Step": "Spacer",
        "Description": "Place bottom spacer",
    },
    30: {
        "Step": "Anode",
        "Description": "Place anode face up",
    },
    40: {
        "Step": "Cathode",
        "Description": "Place cathode face up",
    },
    50: {
        "Step": "Electrolyte",
        "Description": "Add electrolyte before separator",
    },
    60: {
        "Step": "Separator",
        "Description": "Place separator",
    },
    70: {
        "Step": "Electrolyte",
        "Description": "Add electrolyte after separator",
    },
    80: {
        "Step": "Anode",
        "Description": "Place anode face down",
    },
    90: {
        "Step": "Cathode",
        "Description": "Place cathode face down",
    },
    100: {
        "Step": "Spacer",
        "Description": "Place top spacer",
    },
    110: {
        "Step": "Spring",
        "Description": "Place spring",
    },
    120: {
        "Step": "Top",
        "Description": "Place top casing",
    },
    130: {
        "Step": "Press",
        "Description": "Press cell using 7.8 kN hydraulic press",
    },
    140: {
        "Step": "Return",
        "Description": "Return completed cell to rack",
    },
}

PRESS_STEP = next(k for k, v in STEP_DEFINITION.items() if v["Step"] == "Press")

# Get Run ID from the settings table
with sqlite3.connect(DATABASE_FILEPATH) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT `value` FROM Settings_Table WHERE `key` = 'Base Sample ID'")
    run_id = cursor.fetchone()[0]

# Open file dialog to set the output file path
Tk().withdraw()  # to hide the main window
output_filepath = filedialog.asksaveasfilename(
    title = "Export chemspeed.db to .json",
    filetypes = [("json files", "*.json")],
    initialdir=DEFAULT_OUTPUT_FILEPATH,
    initialfile=f"{run_id}.json",
)
if not output_filepath:
    print("No output file selected - not updating the database.")
    sys.exit()
if not output_filepath.endswith(".json"):
    output_filepath += ".json"

with sqlite3.connect(DATABASE_FILEPATH) as conn:
    # Get cell assembly table for finished cells
    df = pd.read_sql(
        f"SELECT * FROM Cell_Assembly_Table WHERE `Last Completed Step` >= {PRESS_STEP} AND `Error Code` = 0",
        conn,
    )
    df_timestamp = pd.read_sql(
        "SELECT * FROM Timestamp_Table",
        conn,
    )

# If df is empty (no finished cells), exit
if df.empty:
    print("No finished cells found in database.")
    print("No output file created.")
    sys.exit()

# Add Run ID to dataframe
df["Run ID"] = run_id

# Remove certain columns, these are either unnecessary or will be recalculated
columns_to_drop = [
    "Last Completed Step",
    "Current Press Number",
    "Error Code",
    "Anode Balancing Capacity (mAh)",
    "Cathode Balancing Capacity (mAh)",
    "N:P ratio overlap factor",
    "N:P Ratio",
    "N:P Ratio Maximum",
    "N:P Ratio Minimum",
    "N:P Ratio Target",
]
df = df.drop(columns=columns_to_drop)

# Generate a sample history from timestamp table
# Drop nans, cast to int, sort by timestamp, drop duplicates
df_timestamp = df_timestamp.dropna()
df_timestamp["Step Number"] = df_timestamp["Step Number"].astype(int)
df_timestamp["Cell Number"] = df_timestamp["Cell Number"].astype(int)
df_timestamp = df_timestamp.sort_values("Timestamp",ascending=False)
df_timestamp = df_timestamp.drop_duplicates(["Cell Number", "Step Number"])
# Pivot the table so that each step number is a column
df_timestamp = df_timestamp.pivot_table(
    index="Cell Number",
    columns="Step Number",
    values="Timestamp",
    aggfunc="last",
)
# Create a Assembly history column for each cell number
def _generate_assembly_history(timestamps: pd.Series) -> list:
    """Take a row of timestamps, turn into a list of dicts describing assembly history."""
    history = []
    timestamp_dict = timestamps.to_dict()
    for i in STEP_DEFINITION:
        # check if key exists
        step: dict[str,str|int] = {}
        ts = timestamp_dict.get(i)
        if ts and isinstance(ts, str):
            try:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S %z")
            except ValueError:
                try:
                    dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")  # noqa: DTZ007
                except ValueError:
                    dt = datetime.strptime(ts, "%d.%m.%Y %H:%M")  # noqa: DTZ007
            dt = pytz.timezone(TIME_ZONE).localize(dt)
            step["Step"] = STEP_DEFINITION[i]["Step"]
            step["Description"] = STEP_DEFINITION[i]["Description"]
            step["Timestamp"] = dt.strftime("%Y-%m-%d %H:%M:%S %z")
            step["uts"] = int(dt.timestamp())
            history.append(step)
    return history
print(df_timestamp)
df_timestamp["Assembly History"] = df_timestamp.apply(_generate_assembly_history, axis=1)

# Merge assembly history into the cell assembly table on cell number
df = df.merge(df_timestamp["Assembly History"], on="Cell Number")

df.to_json(output_filepath, orient="records", indent=4)
