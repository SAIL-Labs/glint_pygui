# %%
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5 import uic
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import (NavigationToolbar2QT as NavigationToolbar)
import numpy as np
import os

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
            return str(value)

    def rowCount(self, index):
        '''
        This method is called by ``data``.
        '''
        return self._data.shape[0]

    def columnCount(self, index):
        '''
        This method is called by ``data``.
        '''
        return self._data.shape[1]
    
    def setData(self, index, value, role):
        """
        This method makes the table editable
        """
        if role == Qt.EditRole:
            try:
                self._data[index.row(), index.column()] = value
            except ValueError: # If cell is blank, string cnnot be converted in float so we pass
                pass
            return True
    
    def flags(self, index):
        '''
        This method allows the edition of the table
        '''
        return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        '''
        This method changed the titles of the columns
        '''
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return ['Piston', 'Tip', 'Tilt'][section]
        return QtCore.QAbstractTableModel.headerData(self, section, orientation, role)
    
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        QtWidgets.QMainWindow.__init__(self)

        uic.loadUi('rt_control_gui.ui', self) # Load the UI Page
        self.setWindowTitle("GLINT RT Control")
        self.preset_path.setText(os.getcwd()+'/presets.npz')

        self.mems_on = np.zeros((37,3))
        self.mems_off = np.zeros((37,3))
        self.mems_flat = np.zeros((37,3))
        
        self.step_seg = 0
        self.segment_id = 0
        
        # Init fields
        self.segment_selection.setText(str(self.segment_id))
        self.mems_step.setText(str(self.step_seg))
        self.scan_wait.setText('0.1')
        self.num_loops.setText('1')
        self.seg_to_move.setText('1')
        self.null_to_scan.setText('1')
        self.null_scan_range.setText("-2.5:0.5:2.5")
        
        # Init MEMS table
        self.mems_values = np.zeros((37,3))
        self.model = TableModel(self.mems_values)
        self.table_mems.setModel(self.model)
        
        # Resize it to fit the attributed area
        header = self.table_mems.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.table_mems.verticalHeader().setDefaultSectionSize(21)
        
        # Set the buttons
        self.pushButton_exit.clicked.connect(self.exitapp)
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
       
        
        # Debug
        self.count = 0

    # =============================================================================
    #   Global control
    # =============================================================================
    def exitapp(self):
        self.close()
    
    def addHistoryItem(self, text, colortext=True):
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
        if row == 0:
            self.model.dataChanged.emit(self.model.index(0, 0), self.model.index(self.mems_values.shape[0]-1, 0))
        else:
            self.model.dataChanged.emit(self.model.index(row-1, column), self.model.index(row-1, column))
        
    def clickMemsToZero(self):
        self.mems_values[:] = 0.
        self.updateTable(0, 0)
        self.updateTable(0, 1)
        self.updateTable(0, 2)
        self.addHistoryItem("MEMS sets to 0")

            
    # =============================================================================
    #   Move MEMS        
    # =============================================================================
    def _getStepAndId(self):
        self.step = float(self.mems_step.text())
        self.segment_id = int(self.segment_selection.text())
        
    def clickPistonUp(self):
        self._getStepAndId()
        if self.segment_id == 0:
            self.mems_values[:,0] += self.step
        else:
            self.mems_values[self.segment_id-1,0] += self.step
            
        self.updateTable(self.segment_id, 0)
        self.addHistoryItem('Piston Up (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')

    def clickPistonDown(self):
        self._getStepAndId()
        if self.segment_id == 0:
            self.mems_values[:,0] -= self.step
        else:
            self.mems_values[self.segment_id-1,0] -= self.step
            
        self.updateTable(self.segment_id, 0)
        self.addHistoryItem('Piston Down (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')

    def clickTipUp(self):
        self._getStepAndId()
        if self.segment_id == 0:
            self.mems_values[:,1] += self.step
        else:
            self.mems_values[self.segment_id-1,1] += self.step
            
        self.updateTable(self.segment_id, 1)
        self.addHistoryItem('Tip Up (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')

    def clickTipDown(self):
        self._getStepAndId()
        if self.segment_id == 0:
            self.mems_values[:,1] -= self.step
        else:
            self.mems_values[self.segment_id-1,1] -= self.step
            
        self.updateTable(self.segment_id, 1)
        self.addHistoryItem('Tip Down (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')

    def clickTiltUp(self):
        self._getStepAndId()
        if self.segment_id == 0:
            self.mems_values[:,2] += self.step
        else:
            self.mems_values[self.segment_id-1,2] += self.step
            
        self.updateTable(self.segment_id, 2)        
        self.addHistoryItem('Tilt Up (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')

    def clickTiltDown(self):
        self._getStepAndId()
        if self.segment_id == 0:
            self.mems_values[:,2] -= self.step
        else:
            self.mems_values[self.segment_id-1,2] -= self.step
            
        self.updateTable(self.segment_id, 2)        
        self.addHistoryItem('Tilt Down (Seg: '+str(self.segment_id)+'/Step:'+str(self.step)+')')
        
        
    # =============================================================================
    #   Presets        
    # =============================================================================
    def clickOffSet(self):
        self.mems_off = self.mems_values.copy()
        
    def clickOnSet(self):
        self.mems_on = self.mems_values.copy()

    def clickFlatSet(self):
        self.mems_flat = self.mems_values.copy()

    def clickOffRestore(self):
        self.mems_values[:] = self.mems_off[:]
        self.updateTable(self.segment_id, 0)
        self.updateTable(self.segment_id, 1)
        self.updateTable(self.segment_id, 2)
        self.addHistoryItem("Profile 'Off' restored")
        
    def clickOnRestore(self):
        self.mems_values[:] = self.mems_on[:]
        self.updateTable(self.segment_id, 0) 
        self.updateTable(self.segment_id, 1)
        self.updateTable(self.segment_id, 2)
        self.addHistoryItem("Profile 'On' restored")

    def clickFlatRestore(self):
        self.mems_values[:] = self.mems_flat[:]
        self.updateTable(self.segment_id, 0) 
        self.updateTable(self.segment_id, 1)
        self.updateTable(self.segment_id, 2)
        self.addHistoryItem("Profile 'Flat' restored")
        
    def clickSave(self):
        output_path = os.path.dirname(self.preset_path.text())+'/'
        filename = os.path.basename(self.preset_path.text())
        
        if not '.npz' in filename:
            filename = filename+'.npz'
            
        if not os.path.exists(output_path):
            self.addHistoryItem('Path Created')
            os.makedirs(output_path)
            
        np.savez(output_path+filename, on=self.mems_on, off=self.mems_off, flat=self.mems_flat)
        
        if os.path.isfile(output_path+filename):
            self.addHistoryItem('Presets saved')
        else:
            self.addHistoryItem('!!! Presets NOT saved !!!', False)
            
    def clickRestore(self):
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
            self.addHistoryItem('!!! Presets NOT loaded or not found!!!', False)

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
        else: # By default, segment 29 is scanned
            self.segment_id = 29
            
        self.addHistoryItem("Scan N%s (Seg %s)"%(self.scan_null, self.segment_id))
        
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
main = MainWindow()
main.show()
app.exec_()
