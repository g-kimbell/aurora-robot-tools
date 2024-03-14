import sqlite3
import numpy as np
import pandas as pd

database_filepath = "C:\\Modules\\Database\\chemspeedDB.db"

with sqlite3.connect(database_filepath) as conn:
    # Read the tables from the database
    df = pd.read_sql("SELECT * FROM Cell_Assembly_Table", conn)
    df_electrolyte = pd.read_sql("SELECT * FROM Electrolyte_Table", conn)
    df_electrolyte = df_electrolyte.fillna(0).infer_objects(copy=False)

    # number_of_electrolyte_positions is max of column "Electrolyte Position" in df_electrolyte
    number_of_electrolyte_positions = df_electrolyte["Electrolyte Position"].max()

    # get a square matrix of the mixture fractions
    mix_fractions = np.zeros((number_of_electrolyte_positions, number_of_electrolyte_positions))
    for i in range(number_of_electrolyte_positions):
        mix_fractions[:, i] = df_electrolyte[f"Mix {i+1}"]

    for i in range(number_of_electrolyte_positions):
        if mix_fractions[i].sum() != 0:
            mix_fractions[i] = (mix_fractions[i] / mix_fractions[i].sum())  # normalise the row

    # get a vector for the volumes required
    volumes = np.zeros(number_of_electrolyte_positions)
    for i in range(number_of_electrolyte_positions):
        volumes[i] = df.loc[df["Electrolyte Position"] == i + 1, "Electrolyte Amount (uL)"].sum()

    cumulative_volumes = volumes
    remaining_volumes = volumes
    for i in range(5):
        remaining_volumes = np.matmul(remaining_volumes, mix_fractions)
        cumulative_volumes = cumulative_volumes + remaining_volumes

    # add these to the electrolyte table
    df_electrolyte["Volume Required (uL)"] = volumes
    df_electrolyte["Cumulative Volume Required (uL)"] = cumulative_volumes

    # write the electrolyte table back to the database
    df_electrolyte.to_sql("Electrolyte_Table", conn, index=False, if_exists="replace")

    # create the mixing table with volumes to mix
    mixing_matrix = mix_fractions * volumes[:, np.newaxis]

    df_mixing_table = pd.DataFrame(columns=["Source Position", "Target Position", "Volume (uL)"])
    for i in range(number_of_electrolyte_positions):
        for j in range(number_of_electrolyte_positions):
            if mixing_matrix[i, j] != 0:
                df_mixing_table = df_mixing_table._append(
                    {
                        "Source Position": j + 1,
                        "Target Position": i + 1,
                        "Volume (uL)": mixing_matrix[i, j],
                    },
                    ignore_index=True
                )
                
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