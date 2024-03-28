"""
Assigns cell numbers to presses.

Data is read from the Cell_Assembly_Table and Press_Table tables in the chemspeedDB database. The
script identifies the cells and presses that are available for assembly, and assigns the cells to
presses by updating both tables. The AutoSuite software will then use this information to assemble
the appropriate cells.

Usage:
    The script is called from assign_cells_to_press.exe by the AutoSuite software.
    It can also be called from the command line.

    There are two optional parameters that can set with the command line call.

    - `link_rack_pos_to_press` (bool, default False):
        If set, press 1 will only accept cells from rack positions 1, 7, 13, 19, 25, 31. Press 2
        only accepts cells from rack positions 2, 8, 14, 20, 26, 32, and so on.

    - `limit_electrolytes_per_batch` (int, default 0):
        0 - No limit on the number of different electrolytes in a batch of up to 6 cells.
        n (integer) - Limit the number of different electrolytes in a batch of up to 6 cells to n.
            This is useful if the electrolyte is volatile, since the cleaning step between each 
            electrolyte switch is time-consuming.

    e.g. `py assign_cells_to_press.py 1 2`
    This will ensure that rack positions and press positions are linked (rack 1 only goes to press 
    1, rack 2 to press 2, etc.) and limit the number of different electrolytes in each batch to 2.
"""

import sqlite3
import sys
import numpy as np
import pandas as pd

DATABASE_FILEPATH = "C:\\Modules\\Database\\chemspeedDB.db"

if len(sys.argv) >= 2:
    link_rack_pos_to_press = bool(sys.argv[1])
else:
    link_rack_pos_to_press = True
if len(sys.argv) >= 3:
    limit_electrolytes_per_batch = int(sys.argv[2])
else:
    limit_electrolytes_per_batch = 0

RACK_TO_PRESS_ORDER = [1,4,2,5,3,6] # which rack positions should be used for presses 1-6

with sqlite3.connect(DATABASE_FILEPATH) as conn:
    # Read the table Cell_Assembly_Table and Press_Table from the database
    df = pd.read_sql("SELECT * FROM Cell_Assembly_Table", conn)
    df_press = pd.read_sql("SELECT * FROM Press_Table", conn)

    # Check where the cell number loaded is 0 and where the error code is 0 for the presses
    available_press_numbers = np.where((df_press["Current Cell Number Loaded"] == 0)
                                        & (df_press["Error Code"] == 0))[0]+1

    # Find rack positions with cells that are assigned for assembly (Cell Number > 0), have not
    # finished assembly, with no error code, and find their cell numbers and electrolyte positions
    available_rack_pos = np.where((df["Cell Number"]>0)
                                    & (df["Last Completed Step"]<11)
                                    & (df["Error Code"]==0))[0]+1
    available_cell_numbers = df.loc[available_rack_pos-1, "Cell Number"].values.astype(int)
    available_electrolytes = df.loc[available_rack_pos-1, "Electrolyte Position"].values.astype(int)

    # Remove cells that are already loaded into a press
    idx_to_keep = np.isin(available_cell_numbers, df_press["Current Cell Number Loaded"].values, invert=True)
    available_cell_numbers = available_cell_numbers[idx_to_keep]
    available_rack_pos = available_rack_pos[idx_to_keep]
    available_electrolytes = available_electrolytes[idx_to_keep]

    if link_rack_pos_to_press:
        print('Using link_rack_pos_to_press')
    if limit_electrolytes_per_batch:
        print(f'Limiting electrolytes to {limit_electrolytes_per_batch} per batch')

    electrolytes_used = []

    # Loop through presses, check conditions then assign the first available cell to the press
    for press_idx in range(6):
        availability_mask = np.ones(len(available_rack_pos), dtype=bool)

        # If no more cells available, stop
        if available_cell_numbers.size == 0:
            print('No more cells available')
            break

        # If press is not available, skip
        if press_idx+1 not in available_press_numbers:
            # If using link_rack_pos_to_press and press has an error code,
            # add an error code to all rack positions linked to that press
            if link_rack_pos_to_press & (df_press.loc[press_idx, "Error Code"] != 0):
                error_mask = (available_rack_pos-1)%6+1 == RACK_TO_PRESS_ORDER[press_idx]
                if available_cell_numbers[error_mask].size>0:
                    print(f'Press {press_idx+1} has an error, '
                            f'giving error code to cells with rack position {available_cell_numbers[error_mask]}')
                else:
                    print(f'Press {press_idx+1} has an error')
                df.loc[available_rack_pos[error_mask]-1, "Error Code"] = 301

            # Otherwise if a cell is already loaded, ensure the press number is set for that cell
            elif df_press.loc[press_idx, "Current Cell Number Loaded"] != 0:
                print(f'Press {press_idx+1} already has cell '
                        f'{df_press.loc[press_idx, "Current Cell Number Loaded"]} loaded')
                mask = df["Cell Number"]==df_press.loc[press_idx, "Current Cell Number Loaded"]
                df.loc[mask, "Current Press Number"] = press_idx+1

                # If there is no error, add the electrolyte to the list of used electrolytes
                if df_press.loc[press_idx, "Error Code"] == 0:
                    electrolyte = df.loc[mask, "Electrolyte Position"].values[0]
                    electrolytes_used.append(electrolyte)
            continue

        # If using link_rack_pos_to_press, only consider cells in when rack_position%6 == (press_idx+1)%6
        if link_rack_pos_to_press:
            availability_mask = (available_rack_pos-1)%6+1 == RACK_TO_PRESS_ORDER[press_idx]

        # Only allow limit_electrolytes_per_batch different electrolytes to be loaded at once (if > 0)
        if limit_electrolytes_per_batch:
            if len(set(electrolytes_used)) >= limit_electrolytes_per_batch:
                availability_mask &= [electrolyte in electrolytes_used for electrolyte in available_electrolytes]

        # Assign the first available cell to the press
        final_available_cell_numbers = available_cell_numbers[availability_mask]
        if final_available_cell_numbers.size > 0:
            loaded_cell=final_available_cell_numbers[0]
            print(f'For press {press_idx+1} I can load cells {final_available_cell_numbers}, '
                    f'loading cell number {loaded_cell}')
            if limit_electrolytes_per_batch:
                electrolytes_used.append(loaded_cell)
            df_press.loc[press_idx, "Current Cell Number Loaded"] = loaded_cell
            df.loc[df["Cell Number"]==loaded_cell, "Current Press Number"] = press_idx+1
            print(f'Setting Current Press Number to {press_idx+1} for cell {loaded_cell}')

            # Remove the loaded cell from the available cells
            removed_idx = np.where(available_cell_numbers==loaded_cell)[0][0]
            available_cell_numbers = np.delete(available_cell_numbers, removed_idx)
            available_rack_pos = np.delete(available_rack_pos, removed_idx)
            available_electrolytes = np.delete(available_electrolytes, removed_idx)
        else:
            print(f'Press {press_idx+1} has no available cells to load')
            continue

    # Write the updated tables back to the database
    df_press.to_sql("Press_Table", conn, index=False, if_exists="replace")
    df.to_sql("Cell_Assembly_Table", conn, index=False, if_exists="replace")
    print('Successfully updated the database')
