"""Copyright © 2024, Empa, Graham Kimbell, Enea Svaluto-Ferro, Ruben Kuhnel, Corsin Battaglia.

Read the user input Excel file and write the data to a SQL database.

Users should use the prepared Excel file, "Input with electrode table.xlsx", to input all of the
parameters of the cells to be assembled. The script reads the file, does some simple manipulation,
and writes the data to the "Cell_Assembly_Table" in the chemspeedDB database, which is used by the
AutoSuite software to assemble the cells.

Usage:
    The script is called from import_excel.exe by the AutoSuite software.
    It can also be called from the command line.
"""

import sqlite3
import sys
import warnings
from pathlib import Path
from tkinter import Tk, filedialog

import pandas as pd

# Ignore the pandas data validation warning
warnings.filterwarnings("ignore", ".*extension is not supported and will be removed.*")

DATABASE_FILEPATH = "C:\\Modules\\Database\\chemspeedDB.db"

# Open dialog to select the input file
DEFAULT_INPUT_FILEPATH = "%userprofile%\\Desktop\\Inputs"
Tk().withdraw()  # to hide the main window
input_filepath = Path(
    filedialog.askopenfilename(
        initialdir = DEFAULT_INPUT_FILEPATH,
        title = "Select the input Excel file",
        filetypes = [("Excel files", "*.xlsx")],
    ),
)

exit_code=0

if not input_filepath:
    print("No input file selected - not updating the database.")

if input_filepath:
    print(f"Reading {input_filepath}")

    # Read the excel file
    try:
        df = pd.read_excel(input_filepath, sheet_name="Input Table")
        df_components = pd.read_excel(input_filepath, sheet_name="Component Properties")
        df_electrolyte = pd.read_excel(input_filepath, sheet_name="Electrolyte Properties", skiprows=1)
    except ValueError:
        print("CRITICAL: Excel file format not correct. Check your input file and try again.")
        raise

    # Create the empty Press_Table
    df_press = pd.DataFrame()
    df_press["Press Number"] = [1, 2, 3, 4, 5, 6]
    df_press["Current Cell Number Loaded"] = 0
    df_press["Error Code"] = 0
    df_press["Last Completed Step"] = 0

    # Create the settings table
    df_settings = pd.DataFrame()
    df_settings["key"] = ["Input Filepath","Base Sample ID"]
    df_settings["value"] = [str(input_filepath),str(input_filepath.stem)]

    # Create the timestamp table
    df_timestamp = pd.DataFrame(columns = ["Cell Number","Step Number","Timestamp"])

    # Fill the details for electrolyte properties
    df["Electrolyte Name"] = df["Electrolyte Position"].map(
        df_electrolyte.set_index("Electrolyte Position")["Name"],
    )
    df["Electrolyte Description"] = df["Electrolyte Position"].map(
        df_electrolyte.set_index("Electrolyte Position")["Description"],
    )
    df["Electrolyte Amount Before Separator (uL)"] = df["Electrolyte Amount (uL)"] * (
        (df["Electrolyte Dispense Order"]=="Before") + 0.5*(df["Electrolyte Dispense Order"]=="Both")
    )
    df["Electrolyte Amount After Separator (uL)"] = df["Electrolyte Amount (uL)"] * (
        (df["Electrolyte Dispense Order"]=="After") + 0.5*(df["Electrolyte Dispense Order"]=="Both")
    )

    # Fill the details for electrode properties
    # df_anode is df_electrodes where 'anode' is in the column name
    df_anode = df_components[[col for col in df_components.columns if "Anode" in col]]
    df_anode = df_anode.dropna(subset=["Anode Type"])
    # if diameter is missing or 0, set to 15 mm
    df_anode["Anode Diameter (mm)"] = df_anode["Anode Diameter (mm)"].fillna(15).replace(0, 15)

    # df_cathode is df_electrodes where 'cathode' is in the column name
    df_cathode = df_components[[col for col in df_components.columns if "Cathode" in col]]
    df_cathode = df_cathode.dropna(subset=["Cathode Type"])
    # if diameter is missing or 0, set to 14 mm
    df_cathode["Cathode Diameter (mm)"] = df_cathode["Cathode Diameter (mm)"].fillna(14).replace(0, 14)

    # If Anode Type or Cathode Type contains duplicates, raise an error
    if df_anode["Anode Type"].duplicated().any() or df_cathode["Cathode Type"].duplicated().any():
        print(
            "CRITICAL: Anode Type or Cathode Type in electrode properties table contains "
            "duplicates. Check the input file.",
        )
        sys.exit(1)

    # Merge Anode and Cathode into table
    df = df.merge(df_anode, on="Anode Type", how="left")
    df = df.merge(df_cathode, on="Cathode Type", how="left")

    # Merge separator into table
    df_separator = df_components[[col for col in df_components.columns if "Separator" in col]]
    df = df.merge(df_separator, on="Separator Type", how="left")

    # Merge casing into table
    df_casing = df_components[[col for col in df_components.columns if "Casing" in col]]
    df = df.merge(df_casing, on="Casing Type", how="left")

    # Merge spacer into table
    df_spacer = df_components[[col for col in df_components.columns if "Spacer" in col]]
    for spacer_pos in ["Top", "Bottom"]:
        df_spacer_specific = df_spacer.rename(columns={col: f"{spacer_pos} {col}" for col in df_spacer.columns})
        df = df.merge(df_spacer_specific, on=f"{spacer_pos} Spacer Type", how="left")
        df[f"{spacer_pos} Spacer Thickness (mm)"] = df[f"{spacer_pos} Spacer Thickness (mm)"].fillna(0)

    # Add columns which will be filled in later
    df["Anode Mass (mg)"] = 0
    df["Anode Active Material Mass (mg)"] = 0
    df["Anode Balancing Capacity (mAh)"] = 0
    df["Anode Rack Position"] = 0
    df["Cathode Mass (mg)"] = 0
    df["Cathode Active Material Mass (mg)"] = 0
    df["Cathode Balancing Capacity (mAh)"] = 0
    df["Cathode Rack Position"] = 0
    df["N:P ratio overlap factor"] = 0
    df["N:P Ratio"] = 0
    df["Cell Number"] = 0
    df["Last Completed Step"] = 0
    df["Current Press Number"] = 0
    df["Error Code"] = 0
    df["Barcode"] = ""
    df["Sample ID"] = ""

    # First filling of anode and cathode positions
    df.loc[df["Anode Type"].notna(), "Anode Rack Position"] = df["Rack Position"]
    df.loc[df["Cathode Type"].notna(), "Cathode Rack Position"] = df["Rack Position"]
    df.loc[df["Anode Type"].notna(), "Anode Mass (mg)"] = 0
    df.loc[df["Cathode Type"].notna(), "Cathode Mass (mg)"] = 0

    # Set the first few columns, the rest in alphabetical order
    columns = df.columns.tolist()
    first_cols = [
        "Rack Position",
        "Cell Number",
        "Current Press Number",
        "Last Completed Step",
        "Error Code",
        "Comments",
    ]
    for f in first_cols:
        columns.remove(f)
    columns = first_cols + sorted(columns)
    df = df[columns]
    print("Successfully read and manipulated the Excel file.")

    # Warnings to the user
    columns_to_check = [
        "Anode Type",
        "Anode Balancing Specific Capacity (mAh/g)",
        "Anode C-rate Definition Specific Capacity (mAh/g)",
        "Anode C-rate Definition Areal Capacity (mAh/cm2)",
        "Cathode Type",
        "Cathode Balancing Specific Capacity (mAh/g)",
        "Cathode C-rate Definition Specific Capacity (mAh/g)",
        "Cathode C-rate Definition Areal Capacity (mAh/cm2)",
        "N:P Ratio Target",
        "N:P Ratio Minimum",
        "N:P Ratio Maximum",
        "Separator Type",
        "Electrolyte Position",
        "Electrolyte Amount (uL)",
        "Electrolyte Dispense Order",
        "Batch Number",
    ]
    missing_columns = set(columns_to_check) - set(df.columns)
    if missing_columns:
        exit_code=1
        print("CRITICAL: these columns are missing from the input:", missing_columns)

    used_rows = df["Anode Type"].notna() | df["Cathode Type"].notna()

    if (~df["Electrolyte Dispense Order"].loc[used_rows].isin(["Before", "After", "Both"])).any():
        exit_code=1
        print('CRITICAL: electrolyte dispense order must be "Before", "After" or "Both".')
    if (df["Electrolyte Amount (uL)"]>500).any():
        exit_code=1
        print(
            "CRITICAL: your input has electrolyte volumes "
            f"({max(df["Electrolyte Amount (uL)"])} uL) that are too large.",
        )
    elif (df["Electrolyte Amount (uL)"]>150).any():
        print(f'WARNING: your input has large electrolyte volumes up {max(df["Electrolyte Amount (uL)"])} uL.')
    if (df["Rack Position"] != pd.Series(range(1, 37))).any():
        exit_code=1
        print("CRITICAL: rack positions must be sequential 1-36. Check the input file.")

    if exit_code:
        print("Critical problems: did not update database.")
        sys.exit(1)

    # Connect to the database and create the Cell_Assembly_Table
    with sqlite3.connect(DATABASE_FILEPATH) as conn:
        df.to_sql(
            "Cell_Assembly_Table",
            conn,
            index=False,
            if_exists="replace",
            dtype={
                "Anode Rack Position": "INTEGER",
                "Cathode Rack Position": "INTEGER",
                "Cell Number": "INTEGER",
                "Last Completed Step": "INTEGER",
                "Current Press Number": "INTEGER",
                "Error Code": "INTEGER",
                "Casing Type": "TEXT",
                "Barcode": "TEXT",
                "Batch Number": "INTEGER",
            },
        )
        df_press.to_sql(
            "Press_Table",
            conn,
            index=False,
            if_exists="replace",
            dtype={col: "INTEGER" for col in df_press.columns},
        )
        electrolyte_dtype={col: "REAL" for col in df_electrolyte.columns}
        electrolyte_dtype["Electrolyte Position"] = "INTEGER"
        electrolyte_dtype["Name"] = "TEXT"
        electrolyte_dtype["Description"] = "TEXT"
        df_electrolyte.to_sql(
            "Electrolyte_Table",
            conn,
            index = False,
            if_exists = "replace",
            dtype = electrolyte_dtype,
        )
        df_settings.to_sql(
            "Settings_Table",
            conn,
            index = False,
            if_exists = "replace",
            dtype = {"key": "TEXT", "value": "TEXT"},
        )
        df_timestamp.to_sql(
            "Timestamp_Table",
            conn,
            index = False,
            if_exists = "replace",
            dtype = {
                "Cell Number": "INTEGER",
                "Step Number": "INTEGER",
                "Timestamp": "VARCHAR(255)",
            },
        )

    print("Successfully updated the database.")
