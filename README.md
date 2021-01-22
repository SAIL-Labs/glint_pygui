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

## Update: 2021-01-22
Interface is created.
Python script started: execute ``rt_control_gui`` in your favorite way.
