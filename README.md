# Cycles GUI
The Cycles GUI runs basic nucleation experiments on the meecom temperature controller for the Public Thermodynamics Lab.

## Usage
Download the python code and run supercooling_GUI.py
##Dependencies
The mecom library is required
Once it is downloaded, you have to modify its commands library. 
Locate the commands.py file and add the line
{"id": 3003, "name":"","format": "FLOAT32"},

