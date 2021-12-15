import os
import sys
from PyQt5.QtCore import Qt
from PyQt5 import uic
from PyQt5 import QtWidgets, QtCore, QtGui, QtTest

"""
Must be customized
"""
MIRROR_NUM = 'FSC37-01-11-1614' # Configuration file name
DRIVER_NUM = '05160023' # Hardware driver file name
MEMS_PATH = 'mems/' # Path where the hardware driver and the configuration files are located
MEMS_NB_SEGMENT = 37 # 37 for PTT111, 169 for PTT489
PATH_TO_FRAMES = '/mnt/96980F95980F72D3/glintData/rt_test/new.fits'
sys.path.append(os.path.abspath(MEMS_PATH))
"""
End of customization
"""
import IrisAO_PythonAPI as IrisAO_API

MEMS_MAX = 2.5
MEMS_MIN = -2.5
TARGET_FPS = 10.
SCAN_WAIT = 0.1
TTX_MIN, TTX_MAX = -2.5, 2.5
TTY_MIN, TTY_MAX = -2.5, 2.5
NUM_LOOPS = 1
SEG_TO_MOVE = 1
NULL_TO_SCAN = 1
NULL_RANGE_MIN = -2.5
NULL_RANGE_MAX = 2.5
NULL_RANGE_STEP = 0.5
WAVELENGTH = 1.6
NUM_DARK_FRAMES = 1
STEP_SEG = 0
SEGMENT_ID = 0

def display_error(err_code):
    """Gather all the hand-made error code which may rise because of MEMS or camera.

    Hand-made error codes to help debugging the software if any issue with the Camera
    or the MEMS raise.
    The syntax for the error code for the mirror is MX: M for *mirror* and X the ID of the error.

    Similarly, the syntax for the error code for the camera is CX with C for *Camera*.

    :param err_code: Code of the error.
    :type err_code: string
    :return: tuple of messages to return respectively in the history in the GUI and
            in the terminal.
    :rtype: tuple
    """
    prefix = 'Err '+err_code+': '
    if err_code == 'M1':
        history_msg = prefix + 'MEMS connection error'
        terminal_msg = prefix + 'MEMS initialization failed.'+\
                        'Restart the GUI and choose to disable HW.'
    elif err_code == 'M2':
        history_msg = prefix + 'Flattening failed'
        terminal_msg = prefix + 'There was an error while'+\
                        'flattenning the mirror'
    elif err_code == 'M3':
        history_msg = prefix + "Error reading position"
        terminal_msg = prefix + "There was an error reading from the mirror"
    elif err_code == 'M4':
        history_msg = prefix + 'Mirror not released'
        terminal_msg = prefix + 'There was a problem releasing the connection with the mirror'
    elif err_code == 'M5':
        history_msg = prefix + 'Error sending positions'
        terminal_msg = prefix + 'There was a problem sending positions.'
    else:
        history_msg = terminal_msg = 'No error code!'

    return (history_msg, terminal_msg)

class WarmUpMems(object):
    def __init__(self, disableHW):
        """Dedicated to initialize connection with the hardware.

        The IrisAO library has segfault conflict with any python library using C.
        The function `MirrorConnect` must be called before such libraries to avoid
        the segfault. 
        Hence this class in the import part of the scripts.

        :param disableHW: if `True`, it is a *simulation* mode. 
                            Commands are not sent to the MEMS and response are got
                            from the calibration file.
        :type disableHW: bool
        """
        path = MEMS_PATH
        mirror_num = MIRROR_NUM
        driver_num = DRIVER_NUM
        self.nb_segments = MEMS_NB_SEGMENT
        # Stay True if there is no issue with the MEMS connection and library
        self.mems_fuse = True

        try:
            self.mirror = IrisAO_API.MirrorConnect(
                path + mirror_num, path + driver_num, disableHW)
            print("Connection to the mirror: ", self.mirror)    
        except Exception as e:
            error_message = str(e)
            error_message += "\n\nErr M1: There was a problem connecting to the mirror.\n"+\
                             "Check the popup message above."
            print(error_message)
            self.mems_fuse = False
            self.mirror = None
     

disableHw = True
resp = input("\nDisable hardware? [Y/n]\n")
if resp in ['n', 'N']:
    disableHw = False
warmup_mems = WarmUpMems(disableHw)

import numpy as np
from matplotlib.backends.backend_qt5agg import (
    NavigationToolbar2QT as NavigationToolbar)
import matplotlib.pyplot as plt
from scipy.interpolate import interp2d
from scipy.optimize import curve_fit
import pyqtgraph as pg
from astropy.io import fits
import datetime

plt.ion()

class TableModel(QtCore.QAbstractTableModel):
    """
    The methods are a compilation of what was found on the internet, I don't know how they work but they do.
    """

    def __init__(self, data, mems_comm):
        super(TableModel, self).__init__()
        self._data = data
        self._mems = mems_comm

    def data(self, index, role):
        """
        This method displays the table
        """
        if role == Qt.DisplayRole:
            value = self._data[index.row(), index.column()]
            # return str(value)
            return '{:.4f}'.format(round(value, 4))

    def rowCount(self, index):
        """
        This method is called by ``data``.
        """
        return self._data.shape[0]

    def columnCount(self, index):
        """
        This method is called by ``data``.
        """
        return self._data.shape[1]

    def setData(self, index, value, role):
        """
        This method makes the table editable
        """
        if role == Qt.EditRole:
            try:
                self._data[index.row(), index.column()] = value
                self._comm_with_mems(index.row())
            except ValueError:  # If cell is blank, string cannot be converted in float so we pass
                pass
            return True

    def flags(self, index):
        """
        This method allows the edition of the table
        """
        return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """
        This method changed the titles of the columns
        """
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return ['Piston', 'Tip', 'Tilt'][section]
        return QtCore.QAbstractTableModel.headerData(self, section, orientation, role)

    def _comm_with_mems(self, row):
        seg_list = [row + 1]
        pos_list = [list(self._data[row])]
        
        fuse_send = self._mems.send_command(seg_list, pos_list)

        if fuse_send == False:
            msg = display_error('M5')
            popup = DisplayPopUp('Error', msg[1])
        positions, fuse_get_positions = self._mems.get_positions(seg_list)
        self._data[row] = positions
        if fuse_get_positions == False:
            popup = DisplayPopUp('Error', display_error('M3')[1])    


class MemsControl(object):
    """Control the MEMS

    This class regroups command to send command to the mirror and receive its feedback.
    """
    def __init__(self, mirror_handle):
        self.mirror = mirror_handle

    def flatten_mirror(self):
        """Flatten the mirror
        """
        print( "*** Flatten the mirror")
        try:
            IrisAO_API.MirrorCommand(self.mirror, IrisAO_API.MirrorInitSettings)
            fuse_flatten = True
        except Exception as e:
            print(e)
            print(display_error('M2')[1])
            fuse_flatten = False
        return fuse_flatten

    def send_command(self, segment_list, pos_list):
        """Send a list of positions to the mirror

        Send a command to move a list of segments to a given position (piston, tip and tilt).

        :param segment_list: list of segments to move. Segment ID starst at 1.
        :type segment_list: list
        :param pos_list: list of list/tuple of piston/tip/tilt in um/mrad/mrad.
        :type pos_list: list
        :return: if `False`, triggers an error message depending on the success of sending the command.
        :rtype: bool
        """
        print("*** Set mirror position")
        segment_list = list(segment_list)
        try:
            IrisAO_API.SetMirrorPosition(self.mirror, segment_list, pos_list)
            IrisAO_API.MirrorCommand(self.mirror, IrisAO_API.MirrorSendSettings)
            fuse_send = True
        except Exception as e:
            print(e)
            print(display_error('M5')[1])
            fuse_send = False

        return fuse_send


    def get_positions(self, segments_list):
        """Get positions of a list of segments

        :param segments_list: segments one wants to know the position.
        :type segments_list: list
        :return: tuple of the list of positions (piston/tip/tilt) and the error-message trigger.
        :rtype: tuple
        """
        segments_list = list(segments_list)
        try:
            positions, locked, reachable = \
                IrisAO_API.GetMirrorPosition(self.mirror, segments_list)
            positions = np.array(positions)
            fuse_get_positions = True
        except Exception as e:
            print(e)
            print(display_error('M3')[1])
            positions = np.zeros((len(segments_list), 3))
            fuse_get_positions = False
            
        return positions, fuse_get_positions

    def release_mirror(self):
        """Terminate connection with the mirror.

        :return: equal to 0 if the termination is successfull, it throws an error otherwise.
        :rtype: int
        """
        try:
            released = IrisAO_API.MirrorRelease(self.mirror)
            print("*** Mirror released")
        except Exception as e:
            print(e)
            print(display_error('M4')[1])
            released = self.mirror
        
        return released


class DisplayPopUp():
    """Generate pop-up messages for import errors.
    """
    def __init__(self, title, text):
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle(title)
        msg.setText(text)
        x = msg.exec_()  # this will show our messagebox

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, mirror_handle, mems_fuse, mems_nb_segments, *args, **kwargs):
        """Initialize the fields of the GUI and its interaction with hardware.

        :param mirror_handle: object containing the features to communicate with the mirror
        :type mirror_handle: long
        :param mems_fuse: If `False`, the GUI starts without the mirror features, a pop-up is raised.
        :type mems_fuse: bool
        :param mems_nb_segments: number of segments of the mirror.
        :type mems_nb_segments: int
        """
        QtWidgets.QMainWindow.__init__(self)

        uic.loadUi('rt_control_gui.ui', self)  # Load the UI Page
        self.setWindowTitle("GLINT RT Control")
        self.preset_path.setText(os.getcwd()+'/presets.npz')

        # Init MEMS hardware
        self.nb_segments = mems_nb_segments
        if mems_fuse:
            self.mems = MemsControl(mirror_handle)
            self.addHistoryItem("Mirror connected")
        else:
            msgs = display_error('M1')
            self.addHistoryItem(msgs[0], False)
            msg = DisplayPopUp('Error', msgs[1])
            sys.exit()

        # Init presets and segments variables
        self.mems_on = np.zeros((self.nb_segments, 3))
        self.mems_off = np.zeros((self.nb_segments, 3))
        self.mems_flat = np.zeros((self.nb_segments, 3))

        self.step_seg = STEP_SEG
        self.segment_id = SEGMENT_ID

        # Init fields
        self.segment_selection.setText(str(self.segment_id)) # is created in *.ui file
        self.mems_step.setText(str(self.step_seg)) # is created in *.ui file
        self.scan_wait.setText(str(SCAN_WAIT)) # is created in *.ui file
        self.num_loops.setText(str(NUM_LOOPS)) # is created in *.ui file
        self.seg_to_move.setText(str(SEG_TO_MOVE)) # is created in *.ui file
        self.null_to_scan.setText(str(NULL_TO_SCAN)) # is created in *.ui file
        self.null_scan_range_min.setText(str(NULL_RANGE_MIN)) # is created in *.ui file
        self.null_scan_range_step.setText(str(NULL_RANGE_STEP)) # is created in *.ui file
        self.null_scan_range_max.setText(str(NULL_RANGE_MAX)) # is created in *.ui file
        self.num_dark_frames.setText(str(NUM_DARK_FRAMES)) # is created in *.ui file

        # Init MEMS table
        self.mems_values = np.zeros((self.nb_segments, 3))
        self.model = TableModel(self.mems_values, self.mems)
        self.table_mems.setModel(self.model) # is created in *.ui file


        ## Resize it to fit the attributed area
        header = self.table_mems.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.table_mems.verticalHeader().setDefaultSectionSize(21)


        # Init RT display
        self.dk = np.zeros((344, 96), dtype=float)
        self.rtd = np.zeros((344, 96), dtype=float)

        self.plots_refwg.setText("1") # is created in *.ui file
        self.plots_average.setText("1") # is created in *.ui file
        self.plots_width.setText("100") # is created in *.ui file
        self.time_flux_min.setText("-inf") # is created in *.ui file
        self.time_flux_max.setText("inf") # is created in *.ui file
        self.spectral_flux_min.setText("-inf") # is created in *.ui file
        self.spectral_flux_max.setText("inf") # is created in *.ui file

        self.rt_img_view.hideAxis('left') # is created in *.ui file
        self.rt_img_view.hideAxis('bottom')
        self.rt_img_view.setAspectLocked(False)
        self.rt_img_view.setRange(xRange=[0,96], yRange=[0,344], padding=0)
        self.rt_img_view.invertY(True)

        ## Build RT image view
        self.imv_data = pg.ImageItem()

        ### build lookup table
        pos = np.array([0.0, 0.5, 1.0])
        color = np.array([[0,0,0,255], [255,128,0,255], [255,255,0,255]], dtype=np.ubyte)
        map = pg.ColorMap(pos, color)
        lut = map.getLookupTable(0.0, 1.0, 256)
        self.imv_data.setLookupTable(lut)

        self.rt_img_view.addItem(self.imv_data)

        self.rois = self.define_rois()
        for elt in self.rois:
            self.rt_img_view.addItem(elt)

        ## Built RT spectral flux plot
        self.time_width = int(self.plots_width.text())
        self.time_width_old = int(self.plots_width.text())
        self.time_flux = np.zeros(self.time_width)

        # Init TT map display
        self.tt_map_display.setAspectLocked(False)
        self.tt_map_display.setRange(xRange=[-2.5, 2.5], yRange=[-2.5, 2.5], padding=0)
        self.imv_tt = pg.ImageItem()
        self.imv_tt.setLookupTable(lut)
        self.tt_map_display.addItem(self.imv_tt)
        

        # Init TT other stuff
        self.tt_max = []

        # Timing - monitor fps and trigger refresh
        self.timer_active = False
        self.timer = QtCore.QTimer()


        # Set the buttons
        self.pushButton_exit.clicked.connect(self.exitapp)
        self.pushButton_dark.clicked.connect(self.click_dark_button)
        self.piston_up.clicked.connect(self.clickPistonUp)
        self.piston_down.clicked.connect(self.clickPistonDown)
        self.tip_up.clicked.connect(self.clickTipUp)
        self.tip_down.clicked.connect(self.clickTipDown)
        self.tilt_up.clicked.connect(self.clickTiltUp)
        self.tilt_down.clicked.connect(self.clickTiltDown)
        self.preset_save.clicked.connect(self.clickSave)
        self.preset_restore.clicked.connect(self.clickRestore)
        self.off_set.clicked.connect(self.clickOffSet)
        self.on_set.clicked.connect(self.clickOnSet)
        self.flat_set.clicked.connect(self.clickFlatSet)
        self.off_restore.clicked.connect(self.clickOffRestore)
        self.on_restore.clicked.connect(self.clickOnRestore)
        self.flat_restore.clicked.connect(self.clickFlatRestore)
        self.button_mems_to_zero.clicked.connect(self.clickMemsToZero)
        self.null_opti.clicked.connect(self.clickNullScan)
        self.tt_opt.clicked.connect(self.clickTtOpti)
        self.camera_command.returnPressed.connect(self.send_camera_command)
        self.push_button_save_dir.clicked.connect(self.browse_save_dir)
        self.pushButton_startstop.clicked.connect(self.startstop_refresh)
        self.buttonDev.clicked.connect(self.debug)

        # Init label
        self.label_saturation.setText("")

        # Alarm system preventing the flooding of the History
        self.alarm_refwg = False

        # Debug
        self.count = 0

    # =============================================================================
    #   Global control
    # =============================================================================
    def debug(self):
        print('Do development things here')
        self.count += 1
        pass

    def exitapp(self):
        """Close the GUI and the connection with the mirror.
        """
        release = self.mems.release_mirror()
        if release == 0:
            self.addHistoryItem('Mirror released')
        else:
            self.addHistoryItem(display_error('M4')[0], False)
            msg = DisplayPopUp('Error', display_error('M4')[1])
        self.timer.stop()
        plt.close('all')
        self.close()

    def addHistoryItem(self, text, colortext=True):
        """Display feedback on the actions made through the GUI.

        :param text: text to add in the history
        :type text: string
        :param colortext: color the text in red if `False`, defaults to True
        :type colortext: bool, optional
        """
        if self.qlist_history.count() > 200:
            self.qlist_history.takeItem(0)
        item = QtWidgets.QListWidgetItem(text)
        if not colortext:
            item.setForeground(QtGui.QColor("red"))
        self.qlist_history.addItem(item)
        self.qlist_history.scrollToBottom()

    def str2float(self, text, default_val):
        try:
            return float(text)
        except ValueError:
            self.addHistoryItem('Wrong format number', False)
            return default_val

    # =============================================================================
    # MEMS Table
    # =============================================================================
    def updateTable(self, row, column):
        """Update the table of the segment positions.

        Update the table of the segment positions when using the *Move MEMS* group of buttons.

        :param row: row matching the segment ID, if 0 all the segments are updated.
        :type row: int
        :param column: changed positions among *piston, tip, tilt*.
        :type column: int
        """
        if row == 0:
            self.model.dataChanged.emit(self.model.index(
                0, 0), self.model.index(self.mems_values.shape[0]-1, 0))
        else:
            self.model.dataChanged.emit(self.model.index(
                row-1, column), self.model.index(row-1, column))

    def clickMemsToZero(self):
        """Flatten the mirror
        """
        fuse_flatten = self.mems.flatten_mirror()
        if fuse_flatten:
            self.addHistoryItem("MEMS sets to 0")
            positions, fuse_get_positions = self.mems.get_positions(np.arange(self.nb_segments)+1)
            self.mems_values[:] = positions
            self.updateTable(0, 0)
            self.updateTable(0, 1)
            self.updateTable(0, 2)
            if fuse_get_positions == False:
                self.addHistoryItem(display_error('M3')[0], False)
        else:
            self.addHistoryItem(display_error('M2')[0], False)

    def move_mems_and_updateTable(self, column):
        self._move_mems()

        if column not in [0, 1, 2]:
            for it in range(3):
                self.updateTable(self.segment_id, it)
        else:
            self.updateTable(self.segment_id, column)

    # ===========================================================================
    #   Move MEMS
    # =============================================================================
    def _foolproof(self, arr):
        arr[arr >= MEMS_MAX] = MEMS_MAX
        arr[arr <= MEMS_MIN] = MEMS_MIN
        
        return arr

    def _getStepAndId(self):
        self.step = float(self.mems_step.text())
        self.segment_id = int(self.segment_selection.text())

    def _move_mems(self):
        self.mems_values = self._foolproof(self.mems_values)
        if self.segment_id == 0:
            seg_list = list(np.arange(self.nb_segments) + 1)
            pos_list = [list(elt) for elt in self.mems_values]
        else:
            seg_list = [self.segment_id]
            pos_list = [self.mems_values[self.segment_id-1]]
        
        fuse_send = self.mems.send_command(seg_list, pos_list)

        if fuse_send == False:
            self.addHistoryItem(display_error('M5')[0], False)        
        positions, fuse_get_positions = self.mems.get_positions(seg_list)
        seg_list = list(np.array(seg_list) - 1)
        self.mems_values[seg_list, :] = positions
        if fuse_get_positions == False:
            self.addHistoryItem(display_error('M3')[0], False)

    def clickPistonUp(self):
        """Increase the piston of the selected segment (field *Segment*) by the value in the field *Step*.

        If the segment ID is 0, the pistons of all the segments are incremented.
        """
        self._getStepAndId()
        if self.segment_id == 0:
            self.mems_values[:, 0] += self.step
        else:
            self.mems_values[self.segment_id-1, 0] += self.step

        # self.mems_values = self._foolproof(self.mems_values)

        self.addHistoryItem(
                'Piston Up (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')

        self.move_mems_and_updateTable(0)

    def clickPistonDown(self):
        """Decrease the piston of the selected segment (field *Segment*) by the value in the field *Step*.

        If the segment ID is 0, the pistons of all the segments are incremented.
        """        
        self._getStepAndId()
        if self.segment_id == 0:
            self.mems_values[:, 0] -= self.step
        else:
            self.mems_values[self.segment_id-1, 0] -= self.step

        # self.mems_values = self._foolproof(self.mems_values)

        self.addHistoryItem(
            'Piston Down (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')
        
        self.move_mems_and_updateTable(0)

    def clickTipUp(self):
        """Increase the tip of the selected segment (field *Segment*) by the value in the field *Step*.

        If the segment ID is 0, the tips of all the segments are incremented.
        """           
        self._getStepAndId()
        if self.segment_id == 0:
            self.mems_values[:, 1] += self.step
        else:
            self.mems_values[self.segment_id-1, 1] += self.step

        # self.mems_values = self._foolproof(self.mems_values)

        self.addHistoryItem(
            'Tip Up (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')

        self.move_mems_and_updateTable(1)

    def clickTipDown(self):
        """Decrease the tip of the selected segment (field *Segment*) by the value in the field *Step*.

        If the segment ID is 0, the tips of all the segments are incremented.
        """                   
        self._getStepAndId()
        if self.segment_id == 0:
            self.mems_values[:, 1] -= self.step
        else:
            self.mems_values[self.segment_id-1, 1] -= self.step

        self.addHistoryItem(
            'Tip Down (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')

        self.move_mems_and_updateTable(1)

    def clickTiltUp(self):
        """Increase the tilt of the selected segment (field *Segment*) by the value in the field *Step*.

        If the segment ID is 0, the tips of all the segments are incremented.
        """                   
        self._getStepAndId()
        if self.segment_id == 0:
            self.mems_values[:, 2] += self.step
        else:
            self.mems_values[self.segment_id-1, 2] += self.step

        # self.mems_values = self._foolproof(self.mems_values)

        self.addHistoryItem(
            'Tilt Up (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')

        self.move_mems_and_updateTable(2)

    def clickTiltDown(self):
        """Decrease the tilt of the selected segment (field *Segment*) by the value in the field *Step*.

        If the segment ID is 0, the tips of all the segments are incremented.
        """           
        self._getStepAndId()
        if self.segment_id == 0:
            self.mems_values[:, 2] -= self.step
        else:
            self.mems_values[self.segment_id-1, 2] -= self.step

        # self.mems_values = self._foolproof(self.mems_values)

        self.addHistoryItem(
            'Tilt Down (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')

        self.move_mems_and_updateTable(2)

    # =============================================================================
    #   Presets
    # =============================================================================

    def clickOffSet(self):
        """Save the current positions of the mirror in the *Off* preset.
        """
        self.mems_off = self.mems_values.copy()

    def clickOnSet(self):
        """Save the current positions of the mirror in the *On* preset.
        """        
        self.mems_on = self.mems_values.copy()

    def clickFlatSet(self):
        """Save the current positions of the mirror in the *On* preset.
        """        
        self.mems_flat = self.mems_values.copy()

    def clickOffRestore(self):
        """Restore the positions of the mirror from a *npz* file in the *Off* preset.
        """
        self.mems_values[:] = self.mems_off[:].copy()
        self.move_mems_and_updateTable('all')
        self.addHistoryItem("Profile 'Off' restored")

    def clickOnRestore(self):
        """Restore the positions of the mirror from a *npz* file in the *On* preset.
        """        
        self.mems_values[:] = self.mems_on[:].copy()
        self.move_mems_and_updateTable('all')
        self.addHistoryItem("Profile 'On' restored")

    def clickFlatRestore(self):
        """Restore the positions of the mirror from a *npz* file in the *Flat* preset.
        """        
        self.mems_values[:] = self.mems_flat[:].copy()
        self.move_mems_and_updateTable('all')
        self.addHistoryItem("Profile 'Flat' restored")

    def clickSave(self):
        """Save the preset

        Save the presets *On*, *Off*, *Flat* in the file which path is written in the *Preset* field.
        The presets are saved in a *npz* file.
        """
        output_path = os.path.dirname(self.preset_path.text())+'/'
        filename = os.path.basename(self.preset_path.text())

        if not '.npz' in filename:
            filename = filename+'.npz'

        if not os.path.exists(output_path):
            self.addHistoryItem('Path Created')
            os.makedirs(output_path)

        np.savez(output_path+filename, on=self.mems_on,
                 off=self.mems_off, flat=self.mems_flat)

        if os.path.isfile(output_path+filename):
            self.addHistoryItem('Presets saved')
        else:
            self.addHistoryItem('!!! Presets NOT saved !!!', False)

    def clickRestore(self):
        """Restore the preset

        Restore the presets *On*, *Off*, *Flat* from the *npz* the file written in the *Preset* field.
        To apply the loaded presets, it is required to click on the *Restore* button of the considered preset.
        """        
        output_path = os.path.dirname(self.preset_path.text())+'/'
        filename = os.path.basename(self.preset_path.text())

        if os.path.isfile(output_path+filename):
            preset = np.load(output_path+filename)
            self.mems_on = preset['on']
            self.mems_off = preset['off']
            self.mems_flat = preset['flat']
            self.addHistoryItem('Presets loaded')
            del preset
        else:
            self.addHistoryItem(
                '!!! Presets NOT loaded or not found!!!', False)

    # =============================================================================
    # RT images and plots
    # =============================================================================
    def startstop_refresh(self):
        if self.timer.isActive():
            self.pushButton_startstop.setText('Start video')
            self.timer.stop()
        else:
            self.pushButton_startstop.setText('Stop video')
            self.target_fps = self.str2float(self.refresh_rate.text(), TARGET_FPS)
            self.target_fps = abs(self.target_fps)
            self.addHistoryItem('Refresh rate = %s Hz'%self.target_fps)
            self.refresh_rate.setText(str(self.target_fps))

            self.timer.setInterval(int(np.around(1000. / self.target_fps)))
            self.timer.timeout.connect(self.refresh)
            self.timer.start()        

    def define_rois(self):
        self.roi_p1 = pg.RectROI([35, 323], [61, 15], pen=(255, 0, 0), movable=False, resizable=False, rotatable=False)
        self.roi_n9 = pg.RectROI([35, 303], [61, 15], pen=(255, 0, 0), movable=False, resizable=False, rotatable=False)
        self.roi_p2 = pg.RectROI([35, 283], [61, 15], pen=(255, 0, 0), movable=False, resizable=False, rotatable=False)
        self.roi_n8 = pg.RectROI([35, 263], [61, 15], pen=(255, 0, 0), movable=False, resizable=False, rotatable=False)
        self.roi_n1 = pg.RectROI([35, 244], [61, 15], pen=(255, 0, 0), movable=False, resizable=False, rotatable=False)
        self.roi_n12 = pg.RectROI([35, 224], [61, 15], pen=(255, 0, 0), movable=False, resizable=False, rotatable=False)
        self.roi_n7 = pg.RectROI([35, 204], [61, 15], pen=(255, 0, 0), movable=False, resizable=False, rotatable=False)
        self.roi_n6 = pg.RectROI([35, 184], [61, 15], pen=(255, 0, 0), movable=False, resizable=False, rotatable=False)
        self.roi_n11 = pg.RectROI([35, 165], [61, 15], pen=(255, 0, 0), movable=False, resizable=False, rotatable=False)
        self.roi_n4 = pg.RectROI([35, 145], [61, 15], pen=(255, 0, 0), movable=False, resizable=False, rotatable=False)
        self.roi_n5 = pg.RectROI([35, 125], [61, 15], pen=(255, 0, 0), movable=False, resizable=False, rotatable=False)
        self.roi_n10 = pg.RectROI([35, 105], [61, 15], pen=(255, 0, 0), movable=False, resizable=False, rotatable=False)
        self.roi_n2 = pg.RectROI([35, 85], [61, 15], pen=(255, 0, 0), movable=False, resizable=False, rotatable=False)
        self.roi_p3 = pg.RectROI([35, 66], [61, 15], pen=(255, 0, 0), movable=False, resizable=False, rotatable=False)
        self.roi_n3 = pg.RectROI([35, 46], [61, 15], pen=(255, 0, 0), movable=False, resizable=False, rotatable=False)
        self.roi_p4 = pg.RectROI([35, 26], [61, 15], pen=(255, 0, 0), movable=False, resizable=False, rotatable=False)

        rois = [self.roi_p4, self.roi_n3, self.roi_p3, self.roi_n2,
                self.roi_n10, self.roi_n5, self.roi_n4, self.roi_n11,
                self.roi_n6, self.roi_n7, self.roi_n12, self.roi_n1,
                self.roi_n8, self.roi_p2, self.roi_n9, self.roi_p1]

        idx = np.arange(len(rois))

        for elt in rois:
            elt.setAcceptedMouseButtons(QtCore.Qt.MouseButton.LeftButton)
        

        self.roi_p4.sigClicked.connect(lambda x: self.plots_refwg.setText(str(rois.index(self.roi_p4)+1)))
        self.roi_n3.sigClicked.connect(lambda x: self.plots_refwg.setText(str(rois.index(self.roi_n3)+1)))
        self.roi_p3.sigClicked.connect(lambda x: self.plots_refwg.setText(str(rois.index(self.roi_p3)+1)))
        self.roi_n2.sigClicked.connect(lambda x: self.plots_refwg.setText(str(rois.index(self.roi_n2)+1)))
        self.roi_n10.sigClicked.connect(lambda x: self.plots_refwg.setText(str(rois.index(self.roi_n10)+1)))
        self.roi_n5.sigClicked.connect(lambda x: self.plots_refwg.setText(str(rois.index(self.roi_n5)+1)))
        self.roi_n4.sigClicked.connect(lambda x: self.plots_refwg.setText(str(rois.index(self.roi_n4)+1)))
        self.roi_n11.sigClicked.connect(lambda x: self.plots_refwg.setText(str(rois.index(self.roi_n11)+1)))
        self.roi_n6.sigClicked.connect(lambda x: self.plots_refwg.setText(str(rois.index(self.roi_n6)+1)))
        self.roi_n7.sigClicked.connect(lambda x: self.plots_refwg.setText(str(rois.index(self.roi_n7)+1)))
        self.roi_n12.sigClicked.connect(lambda x: self.plots_refwg.setText(str(rois.index(self.roi_n12)+1)))
        self.roi_n1.sigClicked.connect(lambda x: self.plots_refwg.setText(str(rois.index(self.roi_n1)+1)))
        self.roi_n8.sigClicked.connect(lambda x: self.plots_refwg.setText(str(rois.index(self.roi_n8)+1)))
        self.roi_p2.sigClicked.connect(lambda x: self.plots_refwg.setText(str(rois.index(self.roi_p2)+1)))
        self.roi_n9.sigClicked.connect(lambda x: self.plots_refwg.setText(str(rois.index(self.roi_n9)+1)))
        self.roi_p1.sigClicked.connect(lambda x: self.plots_refwg.setText(str(rois.index(self.roi_p1)+1)))

        return rois

    def click_dark_button(self):
        if self.pushButton_dark.text() == 'Take dark':
            self._grab_dark()
        else:
            self._abort_grab_dark()

    def _grab_dark(self):
        self.abortDark = False
        self.pushButton_dark.setText('Abort Dark')
        self.pushButton_dark.setStyleSheet('color: red')
        self.checkBox_dark.setEnabled(False)
        self.old_dk = self.dk.copy()

        path_to_dk = PATH_TO_FRAMES
        self.dk = []
        nb_dark = int(self.str2float(self.num_dark_frames.text(), NUM_DARK_FRAMES))
        exp_time = 1/self.str2float(self.refresh_rate.text(), TARGET_FPS)

        for k in range(nb_dark):
            if self.abortDark:
                break
            dark_frame = fits.open(path_to_dk)[0].data.astype(float)
            self.addHistoryItem('Acquiring dark %s/%s'%(k+1, nb_dark))
            self.dk.append(dark_frame)
            QtTest.QTest.qWait(int(exp_time * 1000))

        if self.abortDark:
            self.addHistoryItem('Acquiring dark aborted')
            self.dk = self.old_dk.copy()
        else:
            self.addHistoryItem('Acquiring dark done')
            self.dk = np.array(self.dk)
            self.dk = np.mean(self.dk, 0)

        self.checkBox_dark.setEnabled(True)

        if not self.abortDark:
            self.pushButton_dark.setText('Take dark')
            self.pushButton_dark.setStyleSheet('color: black')
    
    def _abort_grab_dark(self):
        self.abortDark = True
        self.pushButton_dark.setText('Take dark')
        self.pushButton_dark.setStyleSheet('color: black')

    def refresh(self):
        self.img_data = np.zeros_like(self.rtd)
        for k in range(int(self.plots_average.text())):
            path_to_rtd = PATH_TO_FRAMES
            self.rtd = fits.open(path_to_rtd)[0].data.astype(float)
            if np.any(self.rtd >= 2**14):
                self.label_saturation.setText("Saturation")
                self.label_saturation.setStyleSheet("background-color: red;\
                                                    border: 1px solid black;\
                                                    color: white;")                                                  

            if self.checkBox_dark.isChecked():
                self.rtd -= self.dk
            # self.rtd += np.random.normal(0, 5, self.rtd.shape)
            self.img_data += self.rtd

        self.img_data /= max(1., int(self.plots_average.text()))

        if self.checkBox_update_display.isChecked():
            self.imv_data.setImage(self.img_data.T)
            vmin, vmax = self.change_display_dynamic(self.img_data, self.display_vmin.text(), self.display_vmax.text())
            self.imv_data.setLevels([vmin, vmax])

            self.update_fluxes()

            try:
                int(self.plots_refwg.text())
                if int(self.plots_refwg.text()) >= 1 and int(self.plots_refwg.text()) <= 16:
                    self.plot_spectral_flux()
                    self.plot_time_flux()
                    if self.alarm_refwg:
                        self.addHistoryItem('Ref WG OK')                    
                    self.alarm_refwg = False
                else:
                    if not self.alarm_refwg:
                        self.addHistoryItem('No WG selected', False)
                        self.alarm_refwg = True
            except ValueError:
                if not self.alarm_refwg:
                    self.addHistoryItem('No WG selected', False)
                    self.alarm_refwg = True
                pass

    def change_display_dynamic(self, data, vmin, vmax):
        if vmin == 'inf' or vmin == '-inf' or vmin is None or vmin == '':
            vmin = data.min()
        else:
            try:
                vmin = float(vmin)
            except ValueError:
                vmin = data.min()

        if vmax == 'inf' or vmax == '-inf' or vmax is None or vmax == '':
            vmax = data.max()
        else:
            try:
                vmax = float(vmax)
            except ValueError:
                vmax = data.max()

        return vmin, vmax

    def plot_spectral_flux(self):
        spectral_flux = self.rois[int(self.plots_refwg.text())-1].getArrayRegion(self.img_data, self.imv_data, axes=(1, 0))
        spectral_flux = spectral_flux.mean(1)
        vmin, vmax = self.change_display_dynamic(spectral_flux, self.spectral_flux_min.text(), self.spectral_flux_max.text())
        self.plots_spectralflux.setYRange(vmin, vmax)
        self.plots_spectralflux.plot(spectral_flux, clear=True)

    def plot_time_flux(self):
        instant_flux = self.rois[int(self.plots_refwg.text())-1].getArrayRegion(self.img_data, self.imv_data, axes=(1, 0))
        instant_flux = instant_flux.mean()
        if int(self.plots_width.text()) != self.time_width_old:
            self.time_flux = np.zeros(int(self.plots_width.text()))
            self.time_width_old = int(self.plots_width.text())
        self.time_flux[:-1] = self.time_flux[1:]
        self.time_flux[-1] = instant_flux
        vmin, vmax = self.change_display_dynamic(self.time_flux, self.time_flux_min.text(), self.time_flux_max.text())
        self.plots_time_flux.setYRange(vmin, vmax)
        self.plots_time_flux.plot(self.time_flux, clear=True)

    def update_fluxes(self):
        labels = [self.flux_p4, self.flux_n3, self.flux_p3, self.flux_n2,
                  self.flux_n10, self.flux_n5, self.flux_n4, self.flux_n11,
                  self.flux_n6, self.flux_n7, self.flux_n12, self.flux_n1,
                  self.flux_n8, self.flux_p2, self.flux_n9, self.flux_p1]
        fluxes = [elt.getArrayRegion(self.img_data, self.imv_data, axes=(1, 0)).mean() for elt in self.rois]
        
        for k in range(len(labels)):
            labels[k].setText("%.3f"%fluxes[k])

    # =============================================================================
    # TT opti
    # =============================================================================
    def clickTtOpti(self):
        if self.tt_opt.text() == 'Do TT optimisation':
            self._do_tt_opt()
        else:
            self._abort_tt()

    def _do_tt_opt(self):
        self.abortTT = False
        self.tt_opt.setText('Abort TT')
        self.tt_opt.setStyleSheet('color: red')
        self.pushButton_startstop.setEnabled(False)
        if self.timer.isActive():
            reactivate_timer = True
            self.pushButton_startstop.setText('Start video')
            self.timer.stop()
        else:
            reactivate_timer = False

        self.mems_value_old = self.mems_values.copy()
        self.clickMemsToZero()

        scan_wait = self.str2float(self.scan_wait.text(), SCAN_WAIT)

        num_loops = int(self.str2float(self.num_loops.text(), NUM_LOOPS))

        step = 0.5
        ttx = np.arange(TTX_MIN, TTX_MAX + step, step)
        tty = np.arange(TTY_MIN, TTY_MAX + step, step)
        seg_tt = [[29], [35], [26], [24]]
        wg_table = {29: 16, 35: 14, 26: 3, 24: 1}
        colours = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]

        old_segment_id = self.segment_selection.text()

        for seg in seg_tt:
            if self.abortTT:
                break  
            self.tt_map = []
            self.segment_id = seg[0]
            self.segment_selection.setText(str(self.segment_id)) # Defined in ui file
            for k in range(num_loops):
                self.addHistoryItem('Scanning TT seg %s %s/%s'%(seg[0], k+1, num_loops))
                cum_map = []
                for x in ttx:
                    y_fill = []
                    for y in tty:
                        if self.abortTT:
                            break
                        self.mems_values[self.segment_id-1] = [0, x, y]
                        self.move_mems_and_updateTable('all')
                        QtTest.QTest.qWait(int(scan_wait * 1000))
                        self.refresh()
                        flux = self.rois[wg_table[self.segment_id]-1].getArrayRegion(self.img_data, self.imv_data, axes=(1, 0))
                        flux = flux.mean()
                        y_fill.append(flux)
                    cum_map.append(y_fill)
                self.tt_map.append(cum_map)

            self.mems_values[self.segment_id-1] = self.mems_value_old[self.segment_id-1]
            self.move_mems_and_updateTable('all')

            if not self.abortTT:
                self.addHistoryItem('Scanning TT seg %s done'%(seg[0]))

                self.tt_map = np.array(self.tt_map)
                self.tt_map = np.mean(self.tt_map, 0)
                ttx_interp = np.arange(TTX_MIN, TTX_MAX + step/10, step/10)
                tty_interp = np.arange(TTY_MIN, TTY_MAX + step/10, step/10)
                interp_function = interp2d(ttx, tty, self.tt_map.T, kind='cubic')
                self.tt_map_interp = interp_function(ttx_interp, tty_interp)
                idx_max = np.unravel_index(np.argmax(self.tt_map_interp), self.tt_map_interp.shape)
                coord_max = (ttx_interp[idx_max[1]], tty_interp[idx_max[0]])
                print('TT max seg %s:'%seg[0], coord_max)
                self.tt_max.append(coord_max)
                rect = QtCore.QRectF(ttx_interp[0], tty_interp[0],
                                    (ttx_interp[-1]-ttx_interp[0]), (tty_interp[-1]-tty_interp[0]))
                self.imv_tt.setImage(self.tt_map_interp.T)
                self.imv_tt.setRect(rect)
                try:
                    self.tt_map_display.removeItem(self.tt_crosshair)
                except AttributeError:
                    pass
                self.tt_crosshair = pg.CrosshairROI(coord_max, [0., 0.5], pen=colours[seg_tt.index(seg)], movable=False, resizable=False, rotatable=False)
                self.tt_map_display.addItem(self.tt_crosshair)
                self.mems_values[self.segment_id-1] = [0, coord_max[0], coord_max[1]]
                self.move_mems_and_updateTable('all')
                np.savez('tt_map_seg%s_%s'%(seg[0], datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')),
                            x=ttx_interp, y=tty_interp, z=self.tt_map_interp.T)
                QtTest.QTest.qWait(500)
            else:
                self.addHistoryItem('Scanning TT aborted', False)
                print('Scanning TT aborted')
                # self.mems_values[self.segment_id-1] = self.mems_value_old[self.segment_id-1].copy()
                self.segment_id = 0
                self.move_mems_and_updateTable('all') 

        if reactivate_timer:
            self.timer.start()
            self.pushButton_startstop.setText('Stop video')
        self.pushButton_startstop.setEnabled(True)
        self.segment_selection.setText(old_segment_id)
        self.segment_id = self.str2float(old_segment_id, SEGMENT_ID)

        if not self.abortTT:
            self.tt_opt.setText('Do TT optimisation')
            self.tt_opt.setStyleSheet('color: black')            

    def _abort_tt(self):
        self.abortTT = True
        self.tt_opt.setText('Do TT optimisation')
        self.tt_opt.setStyleSheet('color: black')

    # =============================================================================
    # Nulling optimisation
    # =============================================================================
    def clickNullScan(self):
        if self.null_opti.text() == 'Do Nuller optimisation':
            self._do_null_scan()
        else:
            self._abort_nullscan()

    def _do_null_scan(self):
        self.abortNull = False
        self.null_opti.setText('Abort Null scan')
        self.null_opti.setStyleSheet('color: red')
        self.pushButton_startstop.setEnabled(False)
        if self.timer.isActive():
            reactivate_timer = True
            self.pushButton_startstop.setText('Start video')
            self.timer.stop()
        else:
            reactivate_timer = False

        scan_wait = self.str2float(self.scan_wait.text(), SCAN_WAIT)
        num_loops = int(self.str2float(self.num_loops.text(), NUM_LOOPS))
        self.mems_value_old = self.mems_values.copy()
        old_segment_id = self.segment_selection.text()    

        self.segment_to_move = int(self.str2float(self.seg_to_move.text(), SEG_TO_MOVE))
        self.scanning_null = int(self.str2float(self.null_to_scan.text(), NULL_TO_SCAN))
        self.scan_begin = self.str2float(self.null_scan_range_min.text(), NULL_RANGE_MIN)
        self.scan_end = self.str2float(self.null_scan_range_max.text(), NULL_RANGE_MAX)
        self.scan_step = self.str2float(self.null_scan_range_step.text(), NULL_RANGE_STEP)

        scan_range = np.arange(self.scan_begin, self.scan_end + self.scan_step, self.scan_step)

        if self.segment_to_move == 2:
            self.segment_id = 35
        elif self.segment_to_move == 3:
            self.segment_id = 26
        elif self.segment_to_move == 4:
            self.segment_id = 24
        else:  # By default, segment 29 is scanned
            self.segment_id = 29

        self.segment_selection.setText(str(self.segment_id)) # Defined in ui file

        wg_table = {1: 12, 2: 4, 3: 2, 4: 7, 5: 6, 6: 9}

        tt_pos = self.mems_values[self.segment_id-1, 1:].copy()

        self.scanned_valued = []
        self.real_piston = []
        self.full_frames = []

        for k in range(num_loops):
            if self.abortNull:
                break            
            temp = []
            temp_piston = []
            temp_frame = []
            self.addHistoryItem("Scan N%s (Seg %s) %s/%s" %
                                (self.scanning_null, self.segment_id, k+1, num_loops))
            for piston in scan_range:
                if self.abortNull:
                    break
                self.mems_values[self.segment_id-1] = [piston, *tt_pos]
                self.move_mems_and_updateTable('all')
                QtTest.QTest.qWait(int(scan_wait * 1000))
                self.refresh()
                flux = self.rois[wg_table[self.scanning_null]-1].getArrayRegion(self.img_data, self.imv_data, axes=(1, 0))
                flux = flux.mean()         
                temp.append(flux)
                temp_piston.append(self.mems_values[self.segment_id-1, 0])
                temp_frame.append(self.img_data)
            self.scanned_valued.append(temp)
            self.real_piston.append(temp_piston)
            self.full_frames.append(temp_frame)
            
            if not self.abortNull:
                plt.figure(1)
                plt.clf()
                plt.plot(temp_piston, temp)
                plt.xlabel('Positions of segment %s'%self.segment_id)
                plt.title('Scan of Null %s'%self.scanning_null)

        if not self.abortNull:
            self.scanned_valued = np.array(self.scanned_valued)
            self.scanned_valued = np.mean(self.scanned_valued, 0)
            self.real_piston = np.array(self.real_piston)
            self.real_piston = np.mean(self.real_piston, 0)
            self.full_frames = np.array(self.full_frames)
            self.full_frames = np.transpose(self.full_frames, axes=(2, 3, 1, 0))
            self.addHistoryItem("Scan N%s (Seg %s) done" %
                                (self.scanning_null, self.segment_id))
            null_model = lambda x, amp, freq, phase, offset: amp * np.sin(freq*x + phase) + offset

            init_guess = [(self.scanned_valued.max()-self.scanned_valued.min())/2, 
                            2*np.pi/WAVELENGTH, 0, self.scanned_valued.mean()]
            popt = curve_fit(null_model, self.real_piston, self.scanned_valued, p0=init_guess)[0]
            x = np.arange(self.scan_begin, self.scan_end, self.scan_step/100)
            fit = null_model(x, *popt)
            best_null_pos = x[np.argmin(fit)]

            print('')
            print('Fit results:', popt)
            print('Best null at', best_null_pos)
            print('')
            self.addHistoryItem('Best null for Seg %s at %.3f um'%(self.segment_id, best_null_pos))
            self.mems_values[self.segment_id-1] = [best_null_pos, *tt_pos]
            self.move_mems_and_updateTable('all')
            QtTest.QTest.qWait(int(scan_wait * 1000))
            self.refresh()        

            plt.figure(1)
            plt.clf()
            plt.plot(self.real_piston, self.scanned_valued, 'o')
            plt.plot(x, fit)
            plt.plot(best_null_pos, null_model(best_null_pos, *popt), '+', c='r',
                    markersize=15, markeredgewidth=3, label=r'%.4f $\mu$m'%(best_null_pos))
            plt.xlabel('Real positions of segment %s'%self.segment_id)
            plt.title('Scan of Null %s'%self.scanning_null)
            plt.legend(loc='best')

            self._define_save_name()
            ref_segment_pos = self.mems_values[self.ref_segment-1, 0]
            if ref_segment_pos > 0:
                ref_segment_pos = '%.2f'%ref_segment_pos
            else:
                ref_segment_pos = 'm%.2f'%(abs(ref_segment_pos))

            np.savez('null%s_%sat%s_%s'%(self.scanning_null, self.ref_segment, ref_segment_pos, datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')),
                    x=self.real_piston, y=self.scanned_valued, seg=self.segment_id, nullId=self.scanning_null)
            np.savez('null%s_%sat%s_fullIms_%s'%(self.scanning_null, self.ref_segment, ref_segment_pos, datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')),
                    x=self.real_piston, y=self.scanned_valued, seg=self.segment_id, nullId=self.scanning_null,
                    darkframe=self.dk, fullScanAllImages=self.full_frames)
        else:
            self.addHistoryItem('Scanning Null aborted', False)
            print('Scanning Null aborted')
            self.mems_values[:] = self.mems_value_old
            self.segment_id = 0
            self.move_mems_and_updateTable('all') 

        if reactivate_timer:
            self.timer.start()
            self.pushButton_startstop.setText('Stop video')
        self.pushButton_startstop.setEnabled(True)
        self.segment_selection.setText(old_segment_id)

        if not self.abortNull:
            self.null_opti.setText('Do Nuller optimisation')
            self.null_opti.setStyleSheet('color: black')          

    def _abort_nullscan(self):
        self.abortNull = True
        self.null_opti.setText('Do Nuller optimisation')
        self.null_opti.setStyleSheet('color: black')

    def _define_save_name(self):
        if self.scanning_null == 1:
            if self.segment_to_move == 1:
                self.ref_segment = 35
            else:
                self.ref_segment = 29
        elif self.scanning_null == 2:
            if self.segment_to_move == 2:
                self.ref_segment = 26
            else:
                self.ref_segment = 35
        elif self.scanning_null == 3:
            if self.segment_to_move == 1:
                self.ref_segment = 24
            else:
                self.ref_segment = 29
        elif self.scanning_null == 4:
            if self.segment_to_move == 3:
                self.ref_segment = 24
            else:
                self.ref_segment = 26
        elif self.scanning_null == 5:
            if self.segment_to_move == 3:
                self.ref_segment = 29
            else:
                self.ref_segment = 26
        elif self.scanning_null == 6:
            if self.segment_to_move == 4:
                self.ref_segment = 35
            else:
                self.ref_segment = 24
        else:
            self.addHistoryItem('No null selected', False)
            self.ref_segment = 1

    # =============================================================================
    # Camera Control
    # =============================================================================
    def send_camera_command(self):
        self.addHistoryItem('Cam Com:'+str(self.camera_command.text()))

    def browse_save_dir(self):
        dir_name = QtWidgets.QFileDialog.getExistingDirectory()
        self.line_edit_save_dir.setText(dir_name)

app = QtWidgets.QApplication([])
main = MainWindow(warmup_mems.mirror, warmup_mems.mems_fuse, warmup_mems.nb_segments)
main.show()
app.exec_()
