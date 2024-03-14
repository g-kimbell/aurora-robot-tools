"""
Determine the electrolyte mixing steps required.

The script reads the electrolytes required and their volumes from the Cell_Assembly_Table in the chemspeedDB database.
It then reads the mixing ratios from the Electrolyte_Table and calculates all the of the mixing steps (such as move
100 uL from vial 1 to vial 5, etc.) required to prepare all electrolytes for the cells.

Usage:
    The script is called from an executable, electrolyte_calculation.exe, which is called from the AutoSuite software.
    It can also be called from the command line.

TODO:
    - Add an option to multiply all the volumes by a factor as an error margin and/or to account for evaporation.
"""

import sqlite3
import numpy as np
import pandas as pd

DATABASE_FILEPATH = "C:\\Modules\\Database\\chemspeedDB.db"

with sqlite3.connect(DATABASE_FILEPATH) as conn:
    # Read the tables from the database
    df = pd.read_sql("SELECT * FROM Cell_Assembly_Table", conn)
    df_electrolyte = pd.read_sql("SELECT * FROM Electrolyte_Table", conn)
    df_electrolyte = df_electrolyte.fillna(0).infer_objects(copy=False)

    # number_of_electrolyte_positions is max of column "Electrolyte Position" in df_electrolyte
    number_of_electrolyte_positions = df_electrolyte["Electrolyte Position"].max()

    # Get a square matrix of the mixture fractions
    mix_fractions = np.zeros((number_of_electrolyte_positions, number_of_electrolyte_positions))
    for i in range(number_of_electrolyte_positions):
        mix_fractions[:, i] = df_electrolyte[f"Mix {i+1}"]

    for i in range(number_of_electrolyte_positions):
        if mix_fractions[i].sum() != 0:
            mix_fractions[i] = mix_fractions[i] / mix_fractions[i].sum()  # normalise the row

    # Get a vector for the (final) volumes required
    # Calculate the cumulative volumes required, i.e. the volume required including the amount which will then be used 
    # to mix other electrolytes
    volumes = np.zeros(number_of_electrolyte_positions)
    for i in range(number_of_electrolyte_positions):
        volumes[i] = df.loc[df["Electrolyte Position"] == i + 1, "Electrolyte Amount (uL)"].sum()
    cumulative_volumes = volumes
    remaining_volumes = volumes
    for i in range(5):
        remaining_volumes = np.matmul(remaining_volumes, mix_fractions)
        cumulative_volumes = cumulative_volumes + remaining_volumes

    # Add these to the electrolyte table
    df_electrolyte["Volume Required (uL)"] = volumes
    df_electrolyte["Cumulative Volume Required (uL)"] = cumulative_volumes

    # Write the electrolyte table back to the database
    df_electrolyte.to_sql("Electrolyte_Table", conn, index=False, if_exists="replace")

    # Create a matrix with the volumes required for each source and target vial
    mixing_matrix = mix_fractions * volumes[:, np.newaxis]

    # Write the mixing steps needed to the Mixing_Table
    # The mixing steps are ordered such that each vial must have completed all of its mixing steps before it is used
    # as a source for another vial
    source_positions = []
    target_positions = []
    volumes_to_mix = []
    for i in range(number_of_electrolyte_positions):
        for j in range(number_of_electrolyte_positions):
            if mixing_matrix[i, j] > 0:
                source_positions.append(j + 1)
                target_positions.append(i + 1)
                volumes_to_mix.append(mixing_matrix[i, j])

    # Write the mixing steps to the Mixing_Table and save it to the database
    df_mixing_table = pd.DataFrame(columns=["Source Position", "Target Position", "Volume (uL)"],
                                   data=zip(source_positions, target_positions, volumes_to_mix))
    df_mixing_table.to_sql(
        "Mixing_Table",
        conn,
        index=False,
        if_exists="replace",
        dtype={
            "Target Position": "INTEGER",
               "Source Position": "INTEGER",
               "Volume (uL)": "REAL",
        }
    )
    print('Successfully calculated the electrolyte volumes and wrote the tables back to the database.')
