"""
Match cathodes with anodes to achieve the desired N:P ratio.

The script reads the weights measured by the cell assembly robot, along with other input parameters, from the
Cell_Assembly_Table in the chemspeedDB database. The preferred method calculates every possible N:P ratio from all
anodes and cathode combinations, then uses the linear sum assignment algorithm to find the optimal matching of anodes
and cathodes. The script then writes the updated table back to the database, which is used by the AutoSuite software to
assemble the cells.

The electrode matching is done in batches (defined in the input excel table), so only electrodes within the same batch
are switched around. This is useful if there are different cell chemistries within one run of the robot.

Note: currently the script only moves the cathodes and not the anode positions. This means that each anode is tied to
its target N:P ratio, so the sorting is not optimal if the user requires different N:P ratios within one batch of cells.

Usage:
    The script is called from an executable, capacity_balance.exe, which is called from the AutoSuite software.
    It can also be called from the command line.

    There is one additional parameter that can be set:

    - `sorting_method`:
        1 - Use the cost matrix method to match the cathodes with the anodes.
        2 - Sort the anodes and cathodes by weight.
        3 - Do not sort the anodes and cathodes.
    
    The cost matrix method is always the best option, but the other methods are included for legacy, comparison and 
    testing purposes.

TODO:
    - Add a 3D sorting method, in which anodes can also switch positions. This would be useful if the user requires
      different N:P ratios within one batch of cells.
    - Make rejection_cost_factor an argument when AutoSuite supports it.
    - [Long term] Pre-calculate the possible matchings using different rejection_cost_factors and allow the user to
      choose the best one.
"""

import sys
import sqlite3
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

DATABASE_FILEPATH = "C:\\Modules\\Database\\chemspeedDB.db"

def calculate_capacity(df):
    """Calculate the capacity of the anodes and cathodes in-place in the main dataframe, df.

    Args:
        df (pandas.DataFrame): The dataframe containing the cell assembly data.
    """
    df["Anode Capacity (mAh)"] = ((df["Anode Weight (mg)"] - df["Anode Current Collector Weight (mg)"])
        * df["Anode Active Material Weight Fraction"] * df["Anode Practical Capacity (mAh/g)"])
    df["Cathode Capacity (mAh)"] = ((df["Cathode Weight (mg)"] - df["Cathode Current Collector Weight (mg)"])
        * df["Cathode Active Material Weight Fraction"] * df["Cathode Practical Capacity (mAh/g)"])

def cost_matrix_assign(df, rejection_cost_factor = 2):
    """Calculate the cost matrix and find the optimal matching of anodes and cathodes.

    Args:
        df (pandas.DataFrame): The dataframe containing the cell assembly data.
        rejection_cost_factor (float, optional): The factor by which to scale the cost of rejected cells. Defaults to 2.
            1 = more rejected cells, better N:P ratio of accepted cells
            10 = fewer rejected cells, worse N:P ratio of accepted cells
            2 = compromise

    Returns:
        tuple: The indices of the optimal matching of anodes and cathodes.
    """
    # Calculate all possible N:P ratios
    actual_ratio = np.outer(df["Anode Capacity (mAh)"], 1 / df["Cathode Capacity (mAh)"])
    n_batch,_ = actual_ratio.shape

    # Cells outside N:P ratio limits are rejected, given the same cost scaled by rejection_cost_factor
    for i in range(n_batch):
        actual_ratio[i, actual_ratio[i] > df["Maximum N:P Ratio"].loc[i]] = (
            df["Maximum N:P Ratio"].loc[i] * rejection_cost_factor
        )
        actual_ratio[i, actual_ratio[i] < df["Minimum N:P Ratio"].loc[i]] = (
            df["Minimum N:P Ratio"].loc[i] / rejection_cost_factor
        )

    # Calculate the cost matrix
    cost_matrix = np.abs(actual_ratio - np.outer(df["Target N:P Ratio"], np.ones(n_batch)))

    # Prefer unassigned cathodes to not swap with each other
    # by making nans on the diagonal cost very slightly less
    for i in range(n_batch):
        if np.isnan(cost_matrix[i, i]):
            cost_matrix[i, i] = 999.99999999
    # otherwise unassigned cells have the same cost
    cost_matrix = np.nan_to_num(cost_matrix, nan=1000)

    # Find the optimal matching of anodes and cathodes using linear sum assignment
    anode_ind, cathode_ind = linear_sum_assignment(cost_matrix, maximize=False)

    return anode_ind, cathode_ind

def rearrange_electrode_columns(df, row_indices, anode_ind, cathode_ind):
    """Rearrange the anode and cathode columns in-place in the main dataframe, df, 
    based on the indices of the optimal matching.

    Args:
        df (pandas.DataFrame): The dataframe containing the cell assembly data.
        row_indices (numpy.ndarray): The indices for the rows in df being rearrange.
        anode_ind (numpy.ndarray): Anode indices for optimal matching (length = len(row_indices)).
        cathode_ind (numpy.ndarray): Cathode indices for optimal matching (length = len(row_indices)).
    """
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
    df_immutable = df.copy()
    for column in anode_columns:
        df.loc[row_indices, column] = df_immutable.loc[row_indices[anode_ind], column].values
    for column in cathode_columns:
        df.loc[row_indices, column] = df_immutable.loc[row_indices[cathode_ind], column].values

def update_cell_numbers(df):
    """Update the cell numbers in the main dataframe, df, based on the accepted cells.
    
    Args:
        df (pandas.DataFrame): The dataframe containing the cell assembly data.
    """
    df["Actual N:P Ratio"] = df["Anode Capacity (mAh)"] / df["Cathode Capacity (mAh)"]
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

def main():
    """Read the cell assembly data from the database, calculate the capacity of the anodes and cathodes, and match the
    cathodes with the anodes to achieve the desired N:P ratio. Write the updated table back to the database.
    """
    if len(sys.argv) >= 2:
        sorting_method = int(sys.argv[1])
    else:
        sorting_method = 1

    print(f'Reading from database {DATABASE_FILEPATH}, using sorting method {sorting_method}')

    # Connect to the database and create the Cell_Assembly_Table
    with sqlite3.connect(DATABASE_FILEPATH) as conn:
        # Read the table Cell_Assembly_Table from the database
        df = pd.read_sql("SELECT * FROM Cell_Assembly_Table", conn)

        # Calculate the capacity of the anodes and cathodes
        calculate_capacity(df)

        # Split the dataframe into sub-dataframes for each batch number
        batch_numbers = df["Batch Number"].unique()
        batch_numbers = batch_numbers[~np.isnan(batch_numbers)]

        for batch_number in batch_numbers:
            df_batch = df[df["Batch Number"] == batch_number]
            row_indices = np.where(df["Batch Number"] == batch_number)[0]
            print(f"Batch number {batch_number} has {len(row_indices)} cells.")

            # Reorder the anode and cathode rack positions based on the sorting method
            match sorting_method:
                case 1: # Use cost matrix and linear sum assignment
                    anode_ind, cathode_ind = cost_matrix_assign(df_batch)

                case 2: # Sort by weight
                    # I think this is always worse than the cost matrix approach
                    anode_ind = np.argsort(df_batch["Anode Capacity (mAh)"])
                    cathode_ind = np.argsort(df_batch["Cathode Capacity (mAh)"])

                case 3: # Do not sort
                    anode_ind = np.arange(len(row_indices))
                    cathode_ind = np.arange(len(row_indices))

            # Rearrange the electrodes in the main dataframe
            rearrange_electrode_columns(df, row_indices, anode_ind, cathode_ind)

        # Update the actual N:P ratio and accepted cell numbers in the main dataframe
        update_cell_numbers(df)

        # Write the updated table back to the database
        df.to_sql("Cell_Assembly_Table", conn, index=False, if_exists="replace")
        print('Updated database successfully')

if __name__ == "__main__":
    main()
