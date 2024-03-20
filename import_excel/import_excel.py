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

import sys
import os
import sqlite3
import warnings
import numpy as np
import pandas as pd

# Ignore the pandas data validation warning
warnings.filterwarnings('ignore', '.*extension is not supported and will be removed.*')

DATABASE_FILEPATH = "C:\\Modules\\Database\\chemspeedDB.db"

if len(sys.argv) >= 2:
    input_filepath = sys.argv[1]
else:
    input_filepath = "%userprofile%\\Desktop\\Inputs\\Input with electrode table.xlsx"
if input_filepath.lower().startswith("%userprofile%"):
    input_filepath = os.path.expandvars(input_filepath)

print(f'Input Excel file: {input_filepath}')
print(f'Output database: {DATABASE_FILEPATH}')

# Read the excel file
df = pd.read_excel(input_filepath, sheet_name="Input Table")
df_electrodes = pd.read_excel(input_filepath, sheet_name="Electrode Properties")
df_electrolyte = pd.read_excel(input_filepath, sheet_name="Electrolyte Properties", skiprows=1)

# Create the empty Press_Table
df_press = pd.DataFrame()
df_press["Press Number"] = [1, 2, 3, 4, 5, 6]
df_press["Current Cell Number Loaded"] = 0
df_press["Error Code"] = 0
df_press["Last Completed Step"] = 0

# Fill the details for electrode properties
anode_columns = [col for col in df.columns if "Anode" in col and col != "Anode Type"]
cathode_columns = [col for col in df.columns if "Cathode" in col and col != "Cathode Type"]
for column in anode_columns:
    df[column] = df["Anode Type"].map(df_electrodes.set_index("Anode Type")[column])
for column in cathode_columns:
    df[column] = df["Cathode Type"].map(df_electrodes.set_index("Cathode Type")[column])

# Add columns which will be filled in later
df["Anode Weight (mg)"] = np.nan
df["Anode Capacity (mAh)"] = np.nan
df["Anode Rack Position"] = np.nan
df["Cathode Weight (mg)"] = np.nan
df["Cathode Capacity (mAh)"] = np.nan
df["Cathode Rack Position"] = np.nan
df["Actual N:P Ratio"] = np.nan
df["Cell Number"] = 0
df["Last Completed Step"] = 0
df["Current Press Number"] = 0
df["Error Code"] = 0
df["Barcode"] = ""

# First filling of anode and cathode positions
df.loc[df["Anode Type"].notnull(), "Anode Rack Position"] = df["Rack Position"]
df.loc[df["Cathode Type"].notnull(), "Cathode Rack Position"] = df["Rack Position"]
df.loc[df["Anode Type"].notnull(), "Anode Weight (mg)"] = 0
df.loc[df["Cathode Type"].notnull(), "Cathode Weight (mg)"] = 0

print('Successfully read and manipulated the Excel file.')

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
              }
    )
    df_press.to_sql("Press_Table", conn, index=False, if_exists="replace",
                    dtype={col: "INTEGER" for col in df_press.columns})
    electrolyte_dtype={col: "REAL" for col in df_electrolyte.columns}
    electrolyte_dtype["Electrolyte Position"] = "INTEGER"
    electrolyte_dtype["Electrolyte Name"] = "TEXT"
    df_electrolyte.to_sql("Electrolyte_Table", conn, index=False, if_exists="replace",
                          dtype=electrolyte_dtype)

print('Successfully updated the database.')
