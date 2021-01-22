from PyQt5 import QtWidgets, QtCore
from PyQt5 import uic

from matplotlib.backends.backend_qt5agg import (NavigationToolbar2QT as NavigationToolbar)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        QtWidgets.QMainWindow.__init__(self)

        uic.loadUi('rt_control_gui.ui', self) # Load the UI Page
        
        self.pushButton_exit.clicked.connect(self.exitapp)

    def exitapp(self):
        self.close()



app = QtWidgets.QApplication([])
window = MainWindow()
window.show()
app.exec_()
