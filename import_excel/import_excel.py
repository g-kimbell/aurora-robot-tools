"""
Read the user input Excel file and write the data to a SQL database.

Users should use the prepared Excel file, "Input with electrode table.xlsx", to input all of the
parameters of the cells to be assembled. The script reads the file, does some simple manipulation,
and writes the data to the "Cell_Assembly_Table" in the chemspeedDB database, which is used by the
AutoSuite software to assemble the cells.

Usage:
    The script is called from import_excel.exe by the AutoSuite software.
    It can also be called from the command line.
"""

import os
import sqlite3
import warnings
from tkinter import Tk, filedialog
import pandas as pd

# Ignore the pandas data validation warning
warnings.filterwarnings('ignore', '.*extension is not supported and will be removed.*')

DATABASE_FILEPATH = "C:\\Modules\\Database\\chemspeedDB.db"

DEFAULT_INPUT_FILEPATH = "%userprofile%\\Desktop\\Inputs"
Tk().withdraw()  # to hide the main window
input_filepath = filedialog.askopenfilename(
    initialdir = DEFAULT_INPUT_FILEPATH,
    title = "Select the input Excel file",
    filetypes = [("Excel files", "*.xlsx")]
)

exit_code=0

if not input_filepath:
    print('No input file selected - not updating the database.')

if input_filepath:
    print(f'Reading {input_filepath}')

    # Read the excel file
    df = pd.read_excel(input_filepath, sheet_name="Input Table", dtype={"Casing Type": str})
    df_electrodes = pd.read_excel(input_filepath, sheet_name="Electrode Properties")
    df_electrolyte = pd.read_excel(input_filepath, sheet_name="Electrolyte Properties", skiprows=1)

    # Create the empty Press_Table
    df_press = pd.DataFrame()
    df_press["Press Number"] = [1, 2, 3, 4, 5, 6]
    df_press["Current Cell Number Loaded"] = 0
    df_press["Error Code"] = 0
    df_press["Last Completed Step"] = 0

    # Create the settings table
    df_settings = pd.DataFrame()
    filename_without_ext, _ = os.path.splitext(os.path.basename(input_filepath))
    df_settings["key"] = ["Input Filepath","Base Sample ID"]
    df_settings["value"] = [input_filepath,filename_without_ext]

    # Create the timestamp table
    df_timestamp = pd.DataFrame(columns = ["Cell Number","Step Number","Timestamp"])

    # Fill the details for electrolyte properties
    df["Electrolyte Name"] = df["Electrolyte Position"].map(
        df_electrolyte.set_index("Electrolyte Position")["Name"]
        )
    df["Electrolyte Description"] = df["Electrolyte Position"].map(
        df_electrolyte.set_index("Electrolyte Position")["Description"]
        )
    df["Electrolyte Amount Before Seperator (uL)"] = df["Electrolyte Amount (uL)"] * (
        (df["Electrolyte Dispense Order"]=="Before") + 0.5*(df["Electrolyte Dispense Order"]=="Both")
        )
    df["Electrolyte Amount After Seperator (uL)"] = df["Electrolyte Amount (uL)"] * (
        (df["Electrolyte Dispense Order"]=="After") + 0.5*(df["Electrolyte Dispense Order"]=="Both")
        )

    # Fill the details for electrode properties
    anode_columns = [col for col in df_electrodes.columns if "Anode" in col and col != "Anode Type"]
    cathode_columns = [col for col in df_electrodes.columns if "Cathode" in col and col != "Cathode Type"]
    for column in anode_columns:
        df[column] = df["Anode Type"].map(df_electrodes.set_index("Anode Type")[column])
    for column in cathode_columns:
        df[column] = df["Cathode Type"].map(df_electrodes.set_index("Cathode Type")[column])

    # Add columns which will be filled in later
    df["Anode Weight (mg)"] = 0
    df["Anode Active Material Weight (mg)"] = 0
    df["Anode Capacity (mAh)"] = 0
    df["Anode Rack Position"] = 0
    df["Cathode Weight (mg)"] = 0
    df["Cathode Active Material Weight (mg)"] = 0
    df["Cathode Capacity (mAh)"] = 0
    df["Cathode Rack Position"] = 0
    df["N:P ratio overlap factor"] = df["Cathode Diameter (mm)"]**2 / df["Anode Diameter (mm)"]**2
    df["Actual N:P Ratio"] = 0
    df["Cell Number"] = 0
    df["Last Completed Step"] = 0
    df["Current Press Number"] = 0
    df["Error Code"] = 0
    df["Barcode"] = ""
    df["Sample ID"] = ""

    # First filling of anode and cathode positions
    df.loc[df["Anode Type"].notnull(), "Anode Rack Position"] = df["Rack Position"]
    df.loc[df["Cathode Type"].notnull(), "Cathode Rack Position"] = df["Rack Position"]
    df.loc[df["Anode Type"].notnull(), "Anode Weight (mg)"] = 0
    df.loc[df["Cathode Type"].notnull(), "Cathode Weight (mg)"] = 0

    print('Successfully read and manipulated the Excel file.')

    # Warnings to the user
    columns_to_check = [
        'Anode Type',
        'Cathode Type',
        'Target N:P Ratio',
        'Minimum N:P Ratio',
        'Maximum N:P Ratio',
        'Separator',
        'Electrolyte Position',
        'Electrolyte Amount (uL)',
        'Electrolyte Dispense Order',
        'Batch Number',
    ]
    missing_columns = set(columns_to_check) - set(df.columns)
    if missing_columns:
        exit_code=1
        print("CRITICAL: these columns are missing from the input:", missing_columns)

    used_rows = df["Anode Type"].notnull() | df["Cathode Type"].notnull()

    if (~df["Electrolyte Dispense Order"].loc[used_rows].isin(["Before", "After", "Both"])).any():
        exit_code=1
        print('CRITICAL: electrolyte dispense order must be "Before", "After" or "Both".')
    if (df["Electrolyte Amount (uL)"]>500).any():
        exit_code=1
        print(f'CRITICAL: your input has electrolyte volumes ({max(df["Electrolyte Amount (uL)"])} uL) that are too large.')
    elif (df["Electrolyte Amount (uL)"]>150).any():
        print(f'WARNING: your input has large electrolyte volumes up {max(df["Electrolyte Amount (uL)"])} uL.')
    if (~df["Separator"].loc[used_rows].isin(["Whatman","Celgard"])).any():
        print('WARNING: separator type not recognised. Check the input file.')
    if (df["Rack Position"] != pd.Series(range(1, 37))).any():
        exit_code=1
        print('CRITICAL: rack positions must be sequential 1-36. Check the input file.')

    if exit_code:
        print('Critical problems: did not update database.')
        exit(1)

    # Connect to the database and create the Cell_Assembly_Table
    with sqlite3.connect(DATABASE_FILEPATH) as conn:
        df.to_sql("Cell_Assembly_Table", conn, index=False, if_exists="replace",
                dtype={"Anode Rack Position": "INTEGER",
                        "Cathode Rack Position": "INTEGER",
                        "Cell Number": "INTEGER",
                        "Last Completed Step": "INTEGER",
                        "Current Press Number": "INTEGER",
                        "Error Code": "INTEGER",
                        "Casing Type": "TEXT",
                        "Barcode": "TEXT",
                        "Batch Number": "INTEGER",
                }
        )
        df_press.to_sql("Press_Table", conn, index=False, if_exists="replace",
                        dtype={col: "INTEGER" for col in df_press.columns})
        electrolyte_dtype={col: "REAL" for col in df_electrolyte.columns}
        electrolyte_dtype["Electrolyte Position"] = "INTEGER"
        electrolyte_dtype["Name"] = "TEXT"
        electrolyte_dtype["Description"] = "TEXT"
        df_electrolyte.to_sql("Electrolyte_Table", conn, index=False, if_exists="replace",
                            dtype=electrolyte_dtype)
        df_settings.to_sql("Settings_Table", conn, index=False, if_exists="replace",
                           dtype={"key": "TEXT", "value": "TEXT"})
        df_timestamp.to_sql("Timestamp_Table", conn, index=False, if_exists="replace",
                            dtype={"Cell Number": "INTEGER", "Step Number": "INTEGER", "Timestamp": "VARCHAR(255)"})

    print(f'Successfully updated the database.')
