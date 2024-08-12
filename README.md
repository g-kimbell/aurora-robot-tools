<p align="center">
  <img src="https://github.com/user-attachments/assets/93ce6402-2a82-4681-8fe6-309664594d0a" width="500" align="center" alt="Aurora robot tools">
</p>

# Aurora robot tools

Scripts to enhance the functionality of the Aurora battery assembly robot at Empa, based on the Chemspeed Swing SP system.

These scripts are used within the Chemspeed AutoSuite Editor program to give additional functions beyond what is possible within AutoSuite, such as electrode balancing and data management.

## Why are there Go and exe files?

The scripts are written in Python, and interact with a SQL database that is read by the AutoSuite program. AutoSuite cannot run Python files direction, instead one can use a "Run Executable" command which currently only works for .exe files, therefore I have written a simple script in Go which runs the Python script from the command line, but can be called from an .exe. I chose this over PyInstaller since this bundles the whole of Python and all the libraries within each exectuable, so we would end up with many very large files that take a long time to load, and there are issues with antivirus for .bat to .exe conversion.

## Installation

Clone the repo to your prefered location, and install the requirements in requirements.txt. Ensure that the AutoSuite database location matches those in the scripts.

To compile the Go scripts, install Go, in the terminal navigate to the script folder, and use the command 'go build <script_name>.go'.

From AutoSuite Editor, use the "Run Executable" command in the Task View and point it to the .exe file you have compiled.
