<p align="center">
  <img src="https://github.com/user-attachments/assets/cf12bd10-4fd1-459d-9427-c5c1ff778266#gh-light-mode-only" width="500" align="center" alt="Aurora cycler manager">
  <img src="https://github.com/user-attachments/assets/40be68c8-9de0-42cb-9be4-8388fe5965a0#gh-dark-mode-only" width="500" align="center" alt="Aurora cycler manager">
</p>

<br>

Enhancing the Aurora battery assembly robot at Empa.

The Aurora battery assembly robot is based on the Chemspeed Swing SP system. This Python module has a command line interface which can be used within Chemspeed Autosuite Editor to provide additional functions beyond what is possible within AutoSuite, such as electrode balancing and data management.

## Installation

Clone and pip install the repo in a Python environment (tested on 3.12).
```
git clone https://github.com/empaeconversion/aurora-robot-tools
cd aurora-robot-tools
pip install .
```

Ensure that the database location in the `config.py` matches the database location used by Autosuite.

## Usage

### From command line
You can run from the command line with `aurora-rt`, to see possible functions run
```
aurora-rt --help
```

### From Autosuite
Find the executable `aurora-rt.exe`, for a virtual environment it will be located in .venv/Scripts.
Reference this executable from the "Run Executable" command in Autosuite Editor Task View. In the command line arguments give the other arguements required, e.g. `balance` to run electrode balancing. See `aurora-rt --help` for the options available.

## Contributors

- [Graham Kimbell](https://github.com/g-kimbell)
- [Lina Scholz](https://github.com/linasofie/)

## Acknowledgements

This software was developed at the Materials for Energy Conversion Lab at the Swiss Federal Laboratories for Materials Science and Technology (Empa).
