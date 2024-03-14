# Bender Tools
Scripts for the Aurora battery assembly robot at Empa, also known as Bender.

These scripts are used within the AutoSuite Editor program to give additional functionality beyond what is possible within AutoSuite.

## Why are there Go and exe files?

The scripts are written in Python, and interact with a SQL database that is read by the AutoSuite program. In Autosuite we use a "Run Executable" command which currently only works for .exe files, therefore I have written a simple script in Go which runs the Python script from the command line, but can be called from an .exe. I chose this over PyInstaller since this bundles the whole of Python and all the libraries within each exectuable, so we would end up with many very large files that take a long time to load, and .bat to .exe conversion triggered the Empa antivirus.

## Installation

To compile the Go scripts, install Go, in the terminal navigate to the script folder, and use the command 'go build script_name.go'.

From AutoSuite Editor, use the "Run Executable" command in the Task View to call the .exe file you have compiled.
