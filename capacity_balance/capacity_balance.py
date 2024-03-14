import sys
import sqlite3
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

database_filepath = "C:\\Modules\\Database\\chemspeedDB.db"

# Sorting method. 1 = Cost Matrix, 2 = Sort by weight, 3 = Do not sort
# However, right now there is no way to pass arguments to the script with AutoSuite
if len(sys.argv) >= 2:
    sorting_method = int(sys.argv[1])
else:
    sorting_method = 1

print(f'Reading from database {database_filepath}, using sorting method {sorting_method}')

# Connect to the database and create the Cell_Assembly_Table
with sqlite3.connect(database_filepath) as conn:
    # Read the table Cell_Assembly_Table from the database
    df = pd.read_sql("SELECT * FROM Cell_Assembly_Table", conn)

    # Calculate the capacity of the anodes and cathodes
    df["Anode Capacity (mAh)"] = ((df["Anode Weight (mg)"] - df["Anode Current Collector Weight (mg)"])
        * df["Anode Active Material Weight Fraction"] * df["Anode Practical Capacity (mAh/g)"])
    
    df["Cathode Capacity (mAh)"] = ((df["Cathode Weight (mg)"] - df["Cathode Current Collector Weight (mg)"])
        * df["Cathode Active Material Weight Fraction"] * df["Cathode Practical Capacity (mAh/g)"])

    # Keep an immutable copy of the dataframe for moving rows around
    df_immutable = df.copy()

    # Split the dataframe into sub-dataframes for each batch number
    batch_numbers = df["Batch Number"].unique()
    batch_numbers = batch_numbers[~np.isnan(batch_numbers)]

    print(*[f"Batch number {batch_number} has {len(df[df['Batch Number'] == batch_number])} cells."
            for batch_number in batch_numbers])

    for batch_number in batch_numbers:
        df_batch = df[df["Batch Number"] == batch_number]
        row_indices = np.where(df["Batch Number"] == batch_number)[0]

        # Extract the anode and cathode capacities and target N:P ratios
        anode_capacity = np.array(df_batch["Anode Capacity (mAh)"])
        cathode_capacity = np.array(df_batch["Cathode Capacity (mAh)"])
        target_NP_ratio = np.array(df_batch["Target N:P Ratio"])
        maximum_NP_ratio = np.array(df_batch["Maximum N:P Ratio"])
        minimum_NP_ratio = np.array(df_batch["Minimum N:P Ratio"])

        # Reorder the anode and cathode rack positions based on the sorting method
        match sorting_method:
            case 1:
                ### Cost Matrix ###

                # Calculate all possible N:P ratios
                actual_ratio = np.outer(anode_capacity, 1 / cathode_capacity)

                # Factor by which rejected cells are penalised compared to the worst accepted cell
                # 1 = no penalty for rejecting cells to get better ratios for the accepted
                # 10 = it is better to have more cells with bad ratios if it can avoid rejecting any
                # 2 = compromise, rejecting a cell is bad but worth it if the accepted cells have much better ratios
                rejection_cost_factor = 2

                # Cells outside N:P ratio limits are rejected, given the same cost scaled by rejection_cost_factor
                for i in range(len(actual_ratio)):
                    actual_ratio[i, actual_ratio[i] > maximum_NP_ratio[i]] = (
                        maximum_NP_ratio[i] * rejection_cost_factor
                    )
                    actual_ratio[i, actual_ratio[i] < minimum_NP_ratio[i]] = (
                        minimum_NP_ratio[i] / rejection_cost_factor
                    )

                # Calculate the cost matrix
                cost_matrix = np.abs(actual_ratio - np.outer(target_NP_ratio, np.ones(len(cathode_capacity))))

                # prefer unassigned cathodes to not swap with each other
                # by making nans on the diagonal cost very slightly less
                for i in range(len(cathode_capacity)):
                    if np.isnan(cost_matrix[i, i]):
                        cost_matrix[i, i] = 999.99999999
                # otherwise unassigned cells have the same cost
                cost_matrix = np.nan_to_num(cost_matrix, nan=1000)

                # Find the optimal matching of anodes and cathodes
                anode_ind, cathode_ind = linear_sum_assignment(cost_matrix, maximize=False)

            case 2:
                ### Sort by weight ###

                # I think this is always worse than the cost matrix approach
                anode_ind = np.argsort(anode_capacity)
                cathode_ind = np.argsort(cathode_capacity)

            case 3:
                ### Do not sort ###

                anode_ind = np.arange(len(row_indices))
                cathode_ind = np.arange(len(row_indices))

        # Rearrange the Cathode elements to the positions given by cathode_ind
        anode_columns = [
            "Anode Rack Position",
            "Anode Type",
            "Anode Weight (mg)",
            "Anode Capacity (mAh)",
            "Anode Diameter (mm)",
            "Anode Current Collector Weight (mg)",
            "Anode Active Material Weight Fraction",
            "Anode Practical Capacity (mAh/g)",
        ]
        cathode_columns = [
            "Cathode Rack Position",
            "Cathode Type",
            "Cathode Weight (mg)",
            "Cathode Capacity (mAh)",
            "Cathode Diameter (mm)",
            "Cathode Current Collector Weight (mg)",
            "Cathode Active Material Weight Fraction",
            "Cathode Practical Capacity (mAh/g)",
        ]
        for column in anode_columns:
            df.loc[row_indices, column] = df_immutable.loc[row_indices[anode_ind], column].values
        for column in cathode_columns:
            df.loc[row_indices, column] = df_immutable.loc[row_indices[cathode_ind], column].values

    # Find the accepted and rejected cells
    df["Actual N:P Ratio"] = (df["Anode Capacity (mAh)"] / df["Cathode Capacity (mAh)"])
    cell_meets_criteria = ((df["Actual N:P Ratio"] >= df["Minimum N:P Ratio"]) 
                            & (df["Actual N:P Ratio"] <= df["Maximum N:P Ratio"]))
    accepted_cell_indices = np.where(cell_meets_criteria)[0]
    rejected_cell_indices = np.where(~cell_meets_criteria & ~df["Actual N:P Ratio"].isnull())[0]
    for i in rejected_cell_indices:
        print(f'Rack position {i+1} has an N:P ratio of {df["Actual N:P Ratio"].iloc[i]} '
              f'which is outside the acceptable range of {df["Minimum N:P Ratio"].iloc[i]} '
              f'to {df["Maximum N:P Ratio"].iloc[i]}')

    # Re-write the Cell Number column to only include cells with both anode and cathode
    df["Cell Number"] = None
    for cell_number, cell_index in enumerate(accepted_cell_indices):
        df.loc[cell_index, "Cell Number"] = cell_number + 1

    # Write the updated table back to the database
    print(f'Read and manipulated data from database')
    df.to_sql("Cell_Assembly_Table", conn, index=False, if_exists="replace")
    print('Updated database successfully')