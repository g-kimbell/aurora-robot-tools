"""
Convert the finished database to a csv file that can be read by AiiDA.
"""
import sqlite3
from tkinter import Tk, filedialog
import pandas as pd

DATABASE_FILEPATH = "C:\\Modules\\Database\\chemspeedDB.db"

DEFAULT_OUTPUT_FILEPATH = "%userprofile%\\Desktop\\Outputs"

Tk().withdraw()  # to hide the main window
output_filepath = filedialog.asksaveasfilename(
    initialdir = DEFAULT_OUTPUT_FILEPATH,
    title = "Export chemspeed.db to .csv",
    filetypes = [("csv files", "*.csv")]
)
if not output_filepath:
    print('No output file selected - not updating the database.')
    exit()
if not output_filepath.endswith(".csv"):
    output_filepath += ".csv"

# chemspeed database columns : AiiDA csv columns
column_conversion = {
    "Cell Number" : "Battery_Number",
    "Rack Position" : "Rack_Position",
    "Separator" : "Separator",
    "Electrolyte" : "Electrolyte",
    "Electrolyte Position" : "Electrolyte Position",
    "Electrolyte Amount (uL)": "Electrolyte Amount",
    "Anode Rack Position": "Anode Position",
    "Anode Type": "Anode Type",
    "Anode Diameter (mm)": "Anode_Diameter",
    "Anode Weight (mg)": "Anode Weight",
    "Anode Current Collector Weight (mg)": "Anode Current Collector Weight (mg)",
    "Anode Active Material Weight Fraction": "Anode AM Content",
    "Anode Active Material Weight (mg)" : "Anode AM Weight (mg)",
    "Anode Nominal Specific Capacity (mAh/g)" : "Anode Practical Capacity (mAh/g)",
    "Anode Capacity (mAh)" : "Anode Capacity (mAh)",
    "Cathode Rack Position" : "Cathode Position",
    "Cathode Type" : "Cathode Type",
    "Cathode Diameter (mm)" : "Cathode Diameter (mm)",
    "Cathode Weight (mg)" : "Cathode Weight (mg)",
    "Cathode Current Collector Weight (mg)" : "Cathode Current Collector Weight (mg)",
    "Cathode Active Material Weight Fraction" : "Cathode AM Content",
    "Cathode Active Material Weight (mg)" : "Cathode AM Weight (mg)",
    "Cathode Nominal Specific Capacity (mAh/g)" : "Cathode Practical Capacity (mAh/g)",
    "Cathode Capacity (mAh)" : "Cathode Capacity (mAh)",
    "Target N:P Ratio" : "Target N:P Ratio",
    "Actual N:P Ratio" : "Actual N:P Ratio",
    "Casing Type" : "Casing Type",
    "Separator Diameter (mm)" : "Separator Diameter (mm)",
    "Spacer (mm)" : "Spacer (mm)",
    "Comments" : "Comments",
    "Barcode" : "Barcode",
    "Batch Number" : "Subbatch",
}

with sqlite3.connect(DATABASE_FILEPATH) as conn:
    df = pd.read_sql("SELECT * FROM Cell_Assembly_Table", conn)
    for xode in ["Anode", "Cathode"]:
        if f"{xode} Active Material Weight (mg)" not in df.columns:
            df[f"{xode} Active Material Weight (mg)"] = (
                (df[f"{xode} Weight (mg)"] - df[f"{xode} Current Collector Weight (mg)"])
                * df[f"{xode} Active Material Weight Fraction"]
            )

    df = df[column_conversion.keys()]
    df.rename(columns=column_conversion, inplace=True)
    df.to_csv(output_filepath, index=False, sep=";")
