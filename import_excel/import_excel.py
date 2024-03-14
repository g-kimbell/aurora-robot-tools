import sys
import os
import sqlite3
import numpy as np
import pandas as pd

database_filepath = "C:\\Modules\\Database\\chemspeedDB.db"

if len(sys.argv) >= 2:
    input_filepath = sys.argv[1]
else:
    input_filepath = os.path.join(
        os.environ["USERPROFILE"],
        "Desktop\\Inputs\\Input with electrode table.xlsx",
        )

print(f'Input Excel file: {input_filepath}')
print(f'Output database: {database_filepath}')

# Read the excel file
df = pd.read_excel(input_filepath, sheet_name="Input Table")
df_electrodes = pd.read_excel(input_filepath, sheet_name="Electrode Properties")
df_press = pd.read_excel(input_filepath, sheet_name="Press Properties")
df_electrolyte = pd.read_excel(input_filepath, sheet_name="Electrolyte Properties", skiprows=1)

# Add a column of NULL for the "Cell Number"
df["Cell Number"] = None
n = 1
for i in range(36):
    # check if the row has more than 5 elements that are not null, if so increment the battery number
    if df.iloc[i].count() > 5:
        df.loc[i, "Cell Number"] = n
        n += 1

# Fill the details for electrode properties
anode_columns = [
    "Anode Diameter (mm)",
    "Anode Current Collector Weight (mg)",
    "Anode Active Material Weight Fraction",
    "Anode Practical Capacity (mAh/g)",
    ]
cathode_columns = [
    "Cathode Diameter (mm)",
    "Cathode Current Collector Weight (mg)",
    "Cathode Active Material Weight Fraction",
    "Cathode Practical Capacity (mAh/g)",
    ]
for column in anode_columns:
    df[column] = df["Anode Type"].map(df_electrodes.set_index("Anode Type")[column])
for column in cathode_columns:
    df[column] = df["Cathode Type"].map(df_electrodes.set_index("Cathode Type")[column])

# Add columns for the anode and cathode weights and capacity
df["Anode Weight (mg)"] = np.nan
df["Anode Capacity (mAh)"] = np.nan
df["Anode Rack Position"] = np.nan
df["Cathode Weight (mg)"] = np.nan
df["Cathode Capacity (mAh)"] = np.nan
df["Cathode Rack Position"] = np.nan
df["Actual N:P Ratio"] = np.nan
df["Last Completed Step"] = 0
df["Current Press Number"] = 0
df["Error Code"] = 0
df["Barcode"] = ""

# First filling of anode and cathode positions
df.loc[df["Anode Type"].notnull(), "Anode Rack Position"] = df["Rack Position"]
df.loc[df["Cathode Type"].notnull(), "Cathode Rack Position"] = df["Rack Position"]
df.loc[df["Anode Type"].notnull(), "Anode Weight (mg)"] = 0
df.loc[df["Cathode Type"].notnull(), "Cathode Weight (mg)"] = 0

print(f'Successfully read and manipulated the Excel file.')

# Connect to the database and create the Cell_Assembly_Table
with sqlite3.connect(database_filepath) as conn:
    df.to_sql("Cell_Assembly_Table", conn, index=False, if_exists="replace")
    df_press.to_sql("Press_Table", conn, index=False, if_exists="replace")
    df_electrolyte.to_sql("Electrolyte_Table", conn, index=False, if_exists="replace")

print('Connected to the database and created the Cell_Assembly_Table')