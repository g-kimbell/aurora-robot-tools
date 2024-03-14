import sqlite3
import numpy as np
import pandas as pd

database_filepath = "C:\\Modules\\Database\\chemspeedDB.db"

# TODO make these arguments when AutoSuite supports it
link_rack_pos_to_press = False
limit_electrolytes_per_batch = 0

with sqlite3.connect(database_filepath) as conn:
    # Read the table Cell_Assembly_Table from the database
    df = pd.read_sql("SELECT * FROM Cell_Assembly_Table", conn)
    df_press = pd.read_sql("SELECT * FROM Press_Table", conn)

    # Check where the cell number loaded is 0 and where the error code is 0
    available_press_numbers = np.where((df_press["Current Cell Number Loaded"] == 0) 
                                        & (df_press["Error Code"] == 0))[0]+1
    available_rack_pos = np.where((df["Cell Number"]>0) 
                                    & (df["Last Completed Step"]==0) 
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

    for press_idx in range(6):
        availability_mask = np.ones(len(available_rack_pos), dtype=bool)
        # If no more cells available, stop
        if available_cell_numbers.size == 0:
            print('No more cells available')
            break

        # If press is not available, skip
        if press_idx+1 not in available_press_numbers:
            # If using link_rack_pos_to_press and press has an error code, 
            # add an error code to cells with available_rack_pos%6 == (press_idx+1)%6
            if link_rack_pos_to_press & (df_press.loc[press_idx, "Error Code"] != 0):
                error_mask = available_rack_pos%6 == (press_idx+1)%6
                if available_cell_numbers[error_mask].size>0:
                    print(f'Press {press_idx+1} has an error, '
                            f'giving error code to cells with rack position {available_cell_numbers[error_mask]}')
                else:
                    print(f'Press {press_idx+1} has an error')
                df.loc[available_rack_pos[error_mask]-1, "Error Code"] = 301
            elif df_press.loc[press_idx, "Current Cell Number Loaded"] != 0:
                print(f'Press {press_idx+1} already has cell '
                        f'{df_press.loc[press_idx, "Current Cell Number Loaded"]} loaded')
                
                mask = df["Cell Number"]==df_press.loc[press_idx, "Current Cell Number Loaded"]
                df.loc[mask, "Current Press Number"] = press_idx+1
                if df_press.loc[press_idx, "Error Code"] == 0:
                    electrolyte = df.loc[mask, "Electrolyte Position"].values[0]
                    electrolytes_used.append(electrolyte)
            continue

        # If using link_rack_pos_to_press, only consider cells in when rack_position%6 == (press_idx+1)%6
        if link_rack_pos_to_press:
            availability_mask = available_rack_pos%6 == (press_idx+1)%6
        
        # Only allow limit_electrolytes_per_batch different electrolytes to be loaded at once (if > 0)
        if limit_electrolytes_per_batch:
            if len(set(electrolytes_used)) >= limit_electrolytes_per_batch:
                availability_mask &= [electrolyte in electrolytes_used for electrolyte in available_electrolytes]

        # Assign the first available cell to the press
        final_available_cell_numbers = available_cell_numbers[availability_mask]
        loaded_cell=final_available_cell_numbers[0]
        if final_available_cell_numbers.size > 0:
            print(f'For press {press_idx+1} I can load cells {final_available_cell_numbers}, '
                    f'loading cell number {loaded_cell}')
            if limit_electrolytes_per_batch:
                electrolytes_used.append(loaded_cell)
            df_press.loc[press_idx, "Current Cell Number Loaded"] = loaded_cell
            df.loc[loaded_cell-1, "Current Press Number"] = press_idx+1
            print(f'Setting Current Press Number to {press_idx+1} for cell {loaded_cell}')
            
            # Remove the loaded cell from the available cells
            removed_idx = np.where(available_cell_numbers==loaded_cell)[0][0]
            available_cell_numbers = np.delete(available_cell_numbers, removed_idx)
            available_rack_pos = np.delete(available_rack_pos, removed_idx)
            available_electrolytes = np.delete(available_electrolytes, removed_idx)
        else:
            print(f'Press {press_idx+1} has no available cells to load')
            continue
    
    df_press.to_sql("Press_Table", conn, index=False, if_exists="replace")
    df.to_sql("Cell_Assembly_Table", conn, index=False, if_exists="replace")
    print('Successfully updated the database')