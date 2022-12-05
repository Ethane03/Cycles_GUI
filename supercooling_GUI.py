import sys
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker as ticker
import queue
import numpy as np
from supercooling_backend import MeerstetterTEC
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot
import datetime as dt
import csv
import os.path

matplotlib.use('Qt5Agg')

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig=Figure(figsize=(width,height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)

class TestApp(QtWidgets.QMainWindow):
    def __init__(self):
        self._translate = QtCore.QCoreApplication.translate
        QtWidgets.QMainWindow.__init__(self)
        self.ui = uic.loadUi("cycles.ui",self)
        self.resize(888,600)
        #icon = QtGui.QIcon()
        #icon.addPixmap(QtGui.QPixmap("pic.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        #self.setWindowIcon(icon)
        self.threadpool = QtCore.QThreadPool()
        self.canvas = MplCanvas(self, width=5,height=3, dpi=100)
        self.ui.gridLayout.addWidget(self.canvas, 1, 1, 1, 1)
        #MeCom stuff
        self.mc = MeerstetterTEC()
        self.mc.enable(1)

        #Params
        self.window_length = 10000 #data points shown on graph
        self.update_interval = 1000 #ms
        self.sample_interval = 10 #ms
        self.channels = [1]

        self.cooling = 0 #1 is cooling, 0 is heating
        
        self.cool_temp = -20 #C
        self.heat_temp =  30 #C
        self.ramp_rate = 5.0#C/m
        self.heat_time = 60 #S
        self.mode = 0 #{0:Time in Min,1:Cycles,2:Infinite}
        self.run_time = 60 #units depend on mode
        self.file_name = "trial.csv" 
        self.file_num = 0
        self.cycle_status = 0 #{0:stopped,1:running,2:paused}

        self.chn_1_temp = 0.0 #C
        self.chn_1_voltage = 0.0 #V
        self.chn_1_current = 0.0 #A

        self.device_status = bool(self.mc.session)
        self.TEC_connected = False

        self.nucleations = []

        #plot stuff
        self.x_data = [dt.datetime.now() for i in range(self.window_length)]
        self.y_data = [0. for i in range(self.window_length)]
        self.v_data = [0. for i in range(self.window_length)]
        self.reference_plot = None
        self.update_plot()
        self.start_button.clicked.connect(self.start_button_f)
        self.stop_button.clicked.connect(self.stop_button_f)
        self.utimer = QtCore.QTimer()
        self.utimer.setInterval(self.update_interval)
        self.utimer.timeout.connect(self.update_plot)
        self.utimer.start()

        self.dtimer = QtCore.QTimer()
        self.dtimer.setInterval(self.sample_interval)
        self.dtimer.timeout.connect(self.get_data)
        self.dtimer.start()
    def start_button_f(self):
        #{0:stopped,1:running,2:paused}
        if self.cycle_status == 0:
            self.begin_cycle()
            self.start_button.setText("Pause Run")
            self.start_button.setStyleSheet("background-color : yellow")
        elif self.cycle_status == 2:
            self.start_button.setText("Pause Run")
            self.start_button.setStyleSheet("background-color : yellow")
            self.cycle_status = 1
        elif self.cycle_status == 1:
            self.start_button.setText("Start Run")
            self.start_button.setStyleSheet("background-color : yellow")
            self.cycle_status = 2
    def stop_button_f(self):
        self.cycle_status == 0
        self.start_button.setText("Start Run")
        self.start_button.setStyleSheet("background-color : green")
        self.mc.set_temp(20.0,1)
    def begin_cycle(self):
        self.mc.set_ramp_rate(self.ramp_rate*2,1)
        self.cool_temp = float(self.cool_temp_text.text())
        self.heat_temp = float(self.heat_temp_text.text())
        self.heat_time = int(self.heat_time_text.text())
        self.mode = (self.mode_select.currentIndex())
        self.run_time = int(self.run_time_text.text())
        self.file_name = self.export_file_name_text.text()
        self.cooling = False
        self.cycle_status = 1    
        self.mc.set_temp(self.heat_temp,1)
    def check_cycle(self):
        if self.cooling:  
            if self.y_data[-1] < 0 and self.v_data[-1] > 3:
                self.nucleations.append(self.y_data[-2])
                print(f"Nucleation at {self.y_data[-2]}")
                print(f"Avg Nucleation temp: {np.average(self.nucleations):.2f}")
                print(f"Std. Dev: {np.std(self.nucleations):.2f}")
                print(f"beginning heating")
                self.write_data_row(self.nucleations[-1])
                self.cooling = 0
                self.mc.set_ramp_rate(self.ramp_rate*2,1)
                self.mc.set_temp(self.heat_temp,1)
                print("begin heat")
        else:
            if all([x> 15 for x in self.y_data[int(-6000/self.sample_interval):-1]]):
                print("beginning cooling")
                self.cooling = 1
                self.mc.set_ramp_rate(self.ramp_rate,1)
                self.mc.set_temp(self.cool_temp,1)
    def get_data(self):
        x = self.mc.get_temp(1)
        c,v = self.mc.get_electric(1)
        self.y_data = self.y_data[1:] + [x]
        self.x_data = self.x_data[1:] + [dt.datetime.now()]
        self.channel_1_temp_text.setText(QtCore.QCoreApplication.translate("MainWindow", f"{x:.2f} °C"))
        self.channel_1_voltage_text.setText(QtCore.QCoreApplication.translate("MainWindow", f"{v:.2f} V"))
        self.channel_1_current_text.setText(QtCore.QCoreApplication.translate("MainWindow", f"{c:.2f} A"))
        self.v_data = np.clip(np.gradient(self.y_data,self.sample_interval/1000),self.cool_temp -5,self.heat_temp+5)
        #self.a_data = np.clip(np.gradient(self.v_data,self.sample_interval/1000),-50,50)
        if(self.cycle_status == 1 or self.cycle_status == 2): self.check_cycle()
    def update_plot(self):
        # Drop off the first y element, append a new one.
        self.canvas.axes.cla()  # Clear the canvas.
        self.canvas.axes.plot(self.x_data, self.y_data, 'r')
        self.canvas.axes.plot(self.x_data, self.v_data, 'g',alpha=0.5)
        #self.canvas.axes.axhline(y=float(target, color='b', linestyle='-',alpha=0.5)
        #self.canvas.axes.plot(self.x_data, self.a_data, 'b')
        # Trigger the canvas to update and redraw.
        self.canvas.draw()
    def check_end(self):
        if self.mode == 0:
            print()
        elif self.mode == 1 and self.run_time <= len(self.nucleations):
            self.cycle_status = 0
            self.mc.set_temp(20.0,1)
    def check_file(self):
        while os.path.isfile(self.file_name):
            self.file_name = self.file_name[0:-len(str(self.file_num))]
            self.file_num +=1
            self.file_name = self.file_name + str(self.file_num)
    def write_data_row(self,data):
        with open(self.file_name, 'w') as csvfile: 
            # creating a csv writer object 
            csvwriter = csv.writer(csvfile) 
            # writing the fields 
            csvwriter.writerow([data])

app = QtWidgets.QApplication(sys.argv)
mainWindow = TestApp()
mainWindow.mc.set_temp(10.0,1)
mainWindow.show()        
sys.exit(app.exec_())