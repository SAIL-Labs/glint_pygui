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

## Update 2021-12-15
Adding new instructions in the readme.md of the mems_setup_kit.

The zip archive mems_setup_kit is replaced by the full folder to ease updates of the files inside

Change in the error message of the GUI if the HW driver is not seen.

New realease 1.0.2.

## Update: 2021-12-07
The installation process has been tested and corrected accordingly.
Use the release 1.0.1.

## Update: 2021-07-26
The GUI is packaged.
The installing process has not been tested.

## Update: 2021-07-21
The GUI is ready to be tested in real condition.
Python script started: execute ``rt_control_gui`` in your favorite way.
**NOTE: change in the code the MEMS file with regard to the plugged one or you may BREAK your MEMS**

## Update: 2021-01-22
Interface is created.
Python script started: execute ``rt_control_gui`` in your favorite way.

## Compatibility
Python >= 3.8.5.

PyQT5 or later.

It has been developed for linux and tested Ubuntu 18.04.
The `mems_setup_kit` contains the MEMS driver for linux.

If you have the MEMS driver for Windows or MAC, the GUI may work even if it
has never been tested on such systems.

For linux OS: every python package using a C-based code **must** be imported **after** the MEMS python library.
A segment fault is raised otherwise.
This explains why the `import` are scattered in the code.

## Installation
To build on local machine

- `git clone https://github.com/SydneyAstrophotonicInstrumentationLab/glint_pygui` or download the realease

- Optional: Create a new environment

- Go to the directory `glint_pygui`

- type `python -m pip install setup.py`

To install the MEMS driver

- Unzip `mems_setup_kit`
- Follow the instructions in `readme.txt`

Edit the variables in `rt_control_gui.py` between the beacons `Must be customized` and `End of customization`.

## Screenshot
![gui_screenshot](https://user-images.githubusercontent.com/4233805/126922016-d92ac731-087b-4d4c-a2ca-153bbb0d931d.png)

