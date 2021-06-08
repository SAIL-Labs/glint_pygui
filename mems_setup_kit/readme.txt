# Procedure to install the IrisAO segmented mirror library for Python

## List of files before any compilation
In current dir:
- `Example_IrisAO_PythonAPI.py` (example file)
- `Flatten_mirror.py` (example file)
- `PWA163-05-04-0405.mcf` (IrisAO related file)
- `12140002.dcf` (IrisAO related file)
- sub-folder `IrisAO_PythonAPI`

In sub-folder IrisAO_PythonAPI:
- `__init__.py`
- `irisao.mirrors.h`
- `IrisAO_Python.pyx`
- `IrisAO_Python_MirrorControl.py`
- `libirisao.devices.1.0.2.5.so` (the library used to control the IrisAO device)
- `raisePythonException.cpp`
- `raisePythonException.h`
- `readme.txt`
- `setup.py`

## Assumptions and Requirements
The test were carried with Anaconda/Miniconda in a dedicated environment with Python 3 installed.
The notice was writtent assuming you use Anaconda, with a dedicated environment or at least the "base" environment.
If the solution is known for other cases, it will be indicated at the relevant step.

I let you transpose to your own case.

For Python: install cython: conda install cython
For your distro: Install gcc and g++

To execute python script with python privilege, you need to force sudo to use the python of
your environment. 
To get the path to the python of the environment: `which python`
To execute the script with sudo: `sudo path/to/python script.py`

## Step-by-step Procedure
1. Place the kit folder where you need it
2. Open a terminal in ./IrisAO_PythonAPI
3. Link the *libirisao.devices.1.0.2.5.so* to your library directory

  a. Create a symbolic link of *libirisao.devices.1.0.2.5.so* to the library folder
of your Python environment. Note, it is recommended to use absolute path otherwise the
symbolink will consider the so file in the library itself.
E.g: `ln -s /path_to_kit/mems_setup_kit/IrisAO_PythonAPI/libirisao.devices.1.0.2.5.so /path_to_python_env/lib/libirisao.devices.so`
  
  b. Check the link is not broken (using navigator, the icon will change or in CL: `ls -l` will return a red line for the broken link)
  
4. Activate the environment in which you want to install the irisAO library: conda activate env_mems
Discard this step is not using Anaconda and go to Step 4b)
  
  a. In the terminal, run the command: `python setup.py build_ext --inplace`
  
  b. If not in an anaconda environment, run the command: `pythonX.X setup.py build_ext --inplace`
Be mindful of the version of python you are using. E.g. `python3.8 setup.py build_ext --inplace`
NOTE: Errors about undefined function may appear but nothing about files not found or skipped step
or clear exit status.

5. If everything goes well (see note above), the following items appeared:
    - IrisAO_Python.cpython-XX-x86_64-linux-gnu.so, XX is the python version
    - IrisAO_Python.cpp
    - folder "build"
Only the first one matters
The library is supposed to be ready

6. In case you need to use the library in another project (in the same environment):
  
  a. Check that your project is in the same environment as where the IrisAOAPI was installed
  
  b. Copy/paste in the project directory the following files:
    - `IrisAO_PythonAPI/IrisAO_Python.cpython-38-x86_64-linux-gnu.so`
    - `IrisAO_PythonAPI/__init__.py`
    - `IrisAO_Python_MirrorControl.py`
    - the mcf file
    - the cdf file

# Run and test
You can test with the script `Example_IrisAO_PythonAPI.py`.
Open the file and check the following:

	- `mirror_num` matches the dcf file's name
	- `driver_num` matches the mcf file's name
	- `nbSegments` matches the number of segments of the MEMS

## Test without the hardware
Open the script and set `disableHW = True` to not look for the hardware.

1. Open a terminal in the current directory;

2. Activate the environment where the driver is installed;

3a. Execute the script with the command: `python Example_IrisAO_PythonAPI.py`;

3b. If root privilege, execute the script with the command: `sudo path/to/python Example_IrisAO_PythonAPI.py`;

4. Hit Y key then hit Enter to continue until the end. No error message should raise.

### Without environment

1. Open a terminal in the current directory;

2. Make sure no conda environment is active;

3. Execute the script with the command: `(sudo) pythonX.X Example_IrisAO_PythonAPI.py`;

4. Hit Y key then hit Enter to continue until the end. No error message should raise.

# Troubleshooting
- It worked on Python 2.7 and Python 3.

- Previous errors were because of poor instructions and errors in
the import of `__init__.py` and `IrisAO_Python_MirrorControl.py`

- If an ImportError raise (like the IrisAO_API is not known):
    - without sudo: check the symbolink link of `IrisAO_PythonAPI/libirisao.devices.1.0.2.5.so` exists in the lib of your python environment.

- Error message:
> Invalid driver type Smart Driver II Legacy USB interface is not supported on 64 bit Linux devices library.

It happens when the script is not executed in sudo mode and `disableHW=False`.
It means the driver is not plugged or the mcf and dcf files set in the script are not the correct ones.
To solve it, plug the driver, check the correct dcf and mcf files are used in the script and launch the script in sudo mode.