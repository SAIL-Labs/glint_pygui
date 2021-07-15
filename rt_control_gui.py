# %%
import os
import sys
sys.path.append(os.path.abspath('mems/'))
from PyQt5.QtCore import Qt
from PyQt5 import uic
from PyQt5 import QtWidgets, QtCore, QtGui
import IrisAO_PythonAPI as IrisAO_API

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
                        'The GUI will open without MEMS features.'
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
        path = 'mems/'
        mirror_num = 'FSC37-01-11-1614'
        driver_num = '05160023'
        self.nb_segments = 37  # 37 for PTT111, 169 for PTT489
        # Stay True if there is no issue with the MEMS connection and library
        self.mems_fuse = True

        try:
            self.mirror = IrisAO_API.MirrorConnect(
                path + mirror_num, path + driver_num, disableHW)
            print("Connection to the mirror: ", self.mirror)    
        except Exception as e:
            error_message = str(e)
            error_message += "\n\nErr M1: There was a problem connecting to the mirror.\n"+\
                             "Check the error message above."
            print(error_message)
            self.mems_fuse = False
            self.mirror = None
     

disableHw = True
# resp = input("\nDisable hardware? [Y/n]\n")
# if resp in ['n', 'N']:
#     disableHw = False
warmup_mems = WarmUpMems(disableHw)

import numpy as np
from matplotlib.backends.backend_qt5agg import (
    NavigationToolbar2QT as NavigationToolbar)
import matplotlib.pyplot as plt
import pyqtgraph as pg
from astropy.io import fits

MEMS_MAX = 2.5
MEMS_MIN = -2.5
TARGET_FPS = 1394.

class TableModel(QtCore.QAbstractTableModel):
    """
    The methods are a compilation of what was found on the internet, I don't know how they work but they do.
    """

    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data

    def data(self, index, role):
        """
        This method displays the table
        """
        if role == Qt.DisplayRole:
            # Note: self._data[index.row()][index.column()] will also work
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
            except ValueError:  # If cell is blank, string cnnot be converted in float so we pass
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

        :param segment_list: list of segments to move
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

        # Init presets and segments variables
        self.mems_on = np.zeros((self.nb_segments, 3))
        self.mems_off = np.zeros((self.nb_segments, 3))
        self.mems_flat = np.zeros((self.nb_segments, 3))

        self.step_seg = 0
        self.segment_id = 0

        # Init fields
        self.segment_selection.setText(str(self.segment_id))
        self.mems_step.setText(str(self.step_seg))
        self.scan_wait.setText('0.1')
        self.num_loops.setText('1')
        self.seg_to_move.setText('1')
        self.null_to_scan.setText('1')
        self.null_scan_range_min.setText("-2.5")
        self.null_scan_range_step.setText("0.5")
        self.null_scan_range_max.setText("2.5")

        # Init MEMS table
        self.mems_values = np.zeros((self.nb_segments, 3))
        self.model = TableModel(self.mems_values)
        self.table_mems.setModel(self.model)

        # Resize it to fit the attributed area
        header = self.table_mems.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.table_mems.verticalHeader().setDefaultSectionSize(21)

        # Init RT display
        self.dk = np.zeros((344, 96), dtype=float)
        self.rtd = np.zeros((344, 96), dtype=float)

        self.plots_refwg.setText("1")
        self.plots_average.setText("1")
        self.plots_width.setText("100")
        self.time_flux_min.setText("-inf")
        self.time_flux_max.setText("inf")
        self.spectral_flux_min.setText("-inf")
        self.spectral_flux_max.setText("inf")

        self.rt_img_view.hideAxis('left')
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

        # Timing - monitor fps and trigger refresh
        self.timer_active = False
        self.timer = QtCore.QTimer()


        # Set the buttons
        self.pushButton_exit.clicked.connect(self.exitapp)
        self.pushButton_dark.clicked.connect(self.click_grab_dark)
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
        print(self.count)
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
            msg = DisplayPopUp('Error', 'Error M4: Mirror was not successfully released.\n'+
                                'The GUI will close, check error messages in the terminal.')
        self.timer.stop()
        self.close()

    def addHistoryItem(self, text, colortext=True):
        """Display feedback on the actions made through the GUI.

        :param text: text to add in the history
        :type text: string
        :param colortext: color the text in red if `False`, defaults to True
        :type colortext: bool, optional
        """
        if self.qlist_history.count() > 23:
            self.qlist_history.takeItem(0)
        item = QtWidgets.QListWidgetItem(text)
        if not colortext:
            item.setForeground(QtGui.QColor("red"))
        self.qlist_history.addItem(item)

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

    # =============================================================================
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
        self.mems_values[:] = positions
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

        self.mems_values = self._foolproof(self.mems_values)

        self.addHistoryItem(
                'Piston Up (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')

        self._move_mems()
        self.updateTable(self.segment_id, 0)

    def clickPistonDown(self):
        """Decrease the piston of the selected segment (field *Segment*) by the value in the field *Step*.

        If the segment ID is 0, the pistons of all the segments are incremented.
        """        
        self._getStepAndId()
        if self.segment_id == 0:
            self.mems_values[:, 0] -= self.step
        else:
            self.mems_values[self.segment_id-1, 0] -= self.step

        self.mems_values = self._foolproof(self.mems_values)

        self.addHistoryItem(
            'Piston Down (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')

        self._move_mems()
        self.updateTable(self.segment_id, 0)

    def clickTipUp(self):
        """Increase the tip of the selected segment (field *Segment*) by the value in the field *Step*.

        If the segment ID is 0, the tips of all the segments are incremented.
        """           
        self._getStepAndId()
        if self.segment_id == 0:
            self.mems_values[:, 1] += self.step
        else:
            self.mems_values[self.segment_id-1, 1] += self.step

        self.mems_values = self._foolproof(self.mems_values)

        self.addHistoryItem(
            'Tip Up (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')
        self._move_mems()
        self.updateTable(self.segment_id, 1)

    def clickTipDown(self):
        """Decrease the tip of the selected segment (field *Segment*) by the value in the field *Step*.

        If the segment ID is 0, the tips of all the segments are incremented.
        """                   
        self._getStepAndId()
        if self.segment_id == 0:
            self.mems_values[:, 1] -= self.step
        else:
            self.mems_values[self.segment_id-1, 1] -= self.step

        self.mems_values = self._foolproof(self.mems_values)

        self.addHistoryItem(
            'Tip Down (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')
        self._move_mems()
        self.updateTable(self.segment_id, 1)

    def clickTiltUp(self):
        """Increase the tilt of the selected segment (field *Segment*) by the value in the field *Step*.

        If the segment ID is 0, the tips of all the segments are incremented.
        """                   
        self._getStepAndId()
        if self.segment_id == 0:
            self.mems_values[:, 2] += self.step
        else:
            self.mems_values[self.segment_id-1, 2] += self.step

        self.mems_values = self._foolproof(self.mems_values)

        self.addHistoryItem(
            'Tilt Up (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')
        self._move_mems()
        self.updateTable(self.segment_id, 2)

    def clickTiltDown(self):
        """Decrease the tilt of the selected segment (field *Segment*) by the value in the field *Step*.

        If the segment ID is 0, the tips of all the segments are incremented.
        """           
        self._getStepAndId()
        if self.segment_id == 0:
            self.mems_values[:, 2] -= self.step
        else:
            self.mems_values[self.segment_id-1, 2] -= self.step

        self.mems_values = self._foolproof(self.mems_values)

        self.addHistoryItem(
            'Tilt Down (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')
        self._move_mems()
        self.updateTable(self.segment_id, 2)

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
        self.mems_values[:] = self.mems_off[:]
        self.updateTable(self.segment_id, 0)
        self.updateTable(self.segment_id, 1)
        self.updateTable(self.segment_id, 2)
        self.addHistoryItem("Profile 'Off' restored")

    def clickOnRestore(self):
        """Restore the positions of the mirror from a *npz* file in the *On* preset.
        """        
        self.mems_values[:] = self.mems_on[:]
        self.updateTable(self.segment_id, 0)
        self.updateTable(self.segment_id, 1)
        self.updateTable(self.segment_id, 2)
        self.addHistoryItem("Profile 'On' restored")

    def clickFlatRestore(self):
        """Restore the positions of the mirror from a *npz* file in the *Flat* preset.
        """        
        self.mems_values[:] = self.mems_flat[:]
        self.updateTable(self.segment_id, 0)
        self.updateTable(self.segment_id, 1)
        self.updateTable(self.segment_id, 2)
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
        if self.timer_active:
            self.timer_active = False
            self.pushButton_startstop.setText('Start video')
            self.timer.stop()
        else:
            self.timer_active = True
            self.pushButton_startstop.setText('Stop video')
            try:
                self.target_fps = float(self.refresh_rate.text())
                if self.target_fps > 0:
                    self.addHistoryItem('Refresh rate = %s Hz'%self.target_fps)
                else:
                    self.target_fps = 1
                    self.addHistoryItem('Refresh forces to %s Hz'%self.target_fps, False)
                    self.refresh_rate.setText(str(self.target_fps))
            except ValueError:
                self.target_fps = TARGET_FPS
                self.addHistoryItem('Refresh forces to %s Hz'%self.target_fps, False)
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


    def click_grab_dark(self):
        path_to_dk = '/mnt/96980F95980F72D3/glintData/rt_test/dark.fits'
        try:
            self.dk = fits.open(path_to_dk)[0].data.astype(float)
            self.addHistoryItem('Dark loaded')
        except FileNotFoundError:
            self.addHistoryItem('Dark not found', False)

    def refresh(self):
        self.img_data = np.zeros_like(self.rtd)
        if self.checkBox_update_display.isChecked():
            for k in range(int(self.plots_average.text())):
                path_to_rtd = '/mnt/96980F95980F72D3/glintData/rt_test/new.fits'
                self.rtd = fits.open(path_to_rtd)[0].data.astype(float)
                if np.any(self.rtd >= 2**14):
                    self.label_saturation.setText("Saturation")
                    self.label_saturation.setStyleSheet("background-color: red;\
                                                        border: 1px solid black;\
                                                        color: white;")                                                  

                if self.checkBox_dark.isChecked():
                    self.rtd -= self.dk
                # self.rtd = np.random.normal(0, 100, self.rtd.shape)
                self.img_data += self.rtd

            self.img_data /= max(1., int(self.plots_average.text()))
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
    # Nulling optimisation
    # =============================================================================
    def clickNullScan(self):
        self.opti_waiting = float(self.scan_wait.text())
        self.nloops = int(self.num_loops.text())
        self.segment_to_move = int(self.seg_to_move.text())
        self.scan_null = int(self.null_to_scan.text())
        self.scan_read = self.null_scan_range.text().split(':')
        self.scan_begin = float(self.scan_read[0])
        self.scan_end = float(self.scan_read[1])
        self.scan_step = float(self.scan_read[2])

        if self.segment_to_move == 2:
            self.segment_id = 35
        elif self.segment_to_move == 3:
            self.segment_id = 26
        elif self.segment_to_move == 4:
            self.segment_id = 24
        else:  # By default, segment 29 is scanned
            self.segment_id = 29

        self.addHistoryItem("Scan N%s (Seg %s)" %
                            (self.scan_null, self.segment_id))

    # =============================================================================
    # TT opti
    # =============================================================================
    def clickTtOpti(self):
        self.opti_waiting = float(self.scan_wait.text())
        self.nloops = int(self.num_loops.text())
        self.addHistoryItem("TT Opti")

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
