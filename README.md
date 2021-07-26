# glint_pygui
## Python GUI of GLINT

The goal is to create a GUI of GINT in python and replace the existing one in Matlab.
This GUI reproduce the features of the Matlab version: the real time control GUI and the Camera control GUI.
These GUI will communicate with at least the camera and the MEMS.
Main features from Matlab GUI will be:
- streaming camera flux
- scanning injection and null
- saving segment positions profiles (piston, tip and tilt)
- saving data
- RT view of the camera with a time-plot of the flux in the selected output
- averaging functionnality in RT plots

Bonus:
- RT view of the spectrum in the selected output to chase wiggles

## Update: 2021-07-26
The GUI is packaged.
The installing process has not been tested.

## Update: 2021-07-21
The GUI is ready to be tested in real condition.
Python script started: execute ``rt_control_gui`` in your favorite way.
**NOTE: change in the code the MEMS file with regard to the plugged one**

## Update: 2021-01-22
Interface is created.
Python script started: execute ``rt_control_gui`` in your favorite way.

## Installation
To build on local machine

	git clone https://github.com/SydneyAstrophotonicInstrumentationLab/glint_pygui
	Optional: Create a new environment
	python -m pip install glint_pygui

To install the MEMS driver

 	Unzip `mems_setup_kit`
	Follow the instructions in `readme.txt`

Edit the variables in `rt_control_gui.py` between the beacons `Must be customized` and `End of customization`.

## Screenshot
![gui_screenshot](https://user-images.githubusercontent.com/4233805/126922016-d92ac731-087b-4d4c-a2ca-153bbb0d931d.png)

