#! /usr/bin/python3
from matplotlib.figure import Figure 
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  
NavigationToolbar2Tk)
from tkinter.scrolledtext import *
import tkinter as tk
import tkinter.ttk as ttk
import numpy as np

class MainGUI:
    # Class contains variables pertaining to the status window, data plot, and button callbacks. It also contains functions for updating
    # plots and labels which get called by the ApplicationController
    
    btn_start_states = ['NEW TEST', 'BEGIN MEASUREMENT', 'STOP TEST']
    btn_calib_states = ['CALIBRATE', 'CANCEL CALIBRATION']
    btn_heat_states = ['START HEATING', 'STOP HEATING']
    btn_timer_states = ['START TIMER', 'STOP']
    btn_QC_states = ['QUALITY CHECK', 'STOP QC']
    #calibZ = 99.85+0.017j; # Old Board
    calibZ = 179.9+0.1j; #Complex Impedance Standard Reference (series) New

    def __init__(self, appController, root):

        self.appController = appController;
        self.root = root
        self.tempVar = tk.StringVar()
        self.tempVar.set("None")
        self.timerVar = tk.StringVar()
        self.timerVar.set('0')
        self.statusWindow, self.fr_vis, self.btn_start, self.btn_calib, self.btn_heat, self.btn_timer, self.testStrings, self.channelVars = self.createTopWindow();
        self.fig, self.plot1, self.canvas = self.setUpVisualization();
        self.buttonStateIndices = [0,0,0,0,0] # Start, calibrate, heat, timer, QC
    
    def onClose(self):
        return

    # Initializes plot
    def setUpVisualization(self):
        # Plot
        fig = Figure(figsize=(5.7, 2.5), dpi = 100)
        plot1 = fig.add_axes([0.11, 0.3, 0.8, 0.6], autoscale_on = True)
        plot1.set_xlabel("Time (s)")
        plot1.set_ylabel("Capacitance (pF)")

        # Visual Frame
        canvas = FigureCanvasTkAgg(fig, master = self.fr_vis)
        canvas.draw()
        canvas.get_tk_widget().pack()

        return fig, plot1, canvas

    # Creates the main window and all necessary components
    def createTopWindow(self):
        root = self.root
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        root.geometry("%dx%d" % (width, height))
        root.title("TraumaCheck Interface")
        style = ttk.Style(root)
        root.tk.call('source', '../Azure-ttk-theme-main/azure.tcl')
        style.theme_use('azure')
        style.configure("AccentButton", foreground = 'white')

        root.rowconfigure(0, minsize = 100, weight=1)
        root.rowconfigure(1, minsize = 50, weight=1)
        root.rowconfigure(2, minsize = 150, weight=1)
        root.columnconfigure(0, minsize = 400, weight=1)

        # Create Frames
        # Top frame holds parameters and buttons
        # Middle frame holds the timer and temperature readout
        # Bottom Frame holds graph and status window, 
        # The channel select frame is within the parameter frame
        fr_top = tk.Frame(root)
        fr_middle = tk.Frame(root)
        fr_bottom = tk.Frame(root)
        fr_vis = tk.Frame(fr_bottom)
        fr_status = ttk.LabelFrame(fr_bottom, text = "Status Window")
        fr_params = ttk.LabelFrame(fr_top, text = "Test Signal Parameters")
        fr_channelSelect = ttk.LabelFrame(fr_params, text = "Active Channels")
        fr_button = tk.Frame(fr_top)

        # Set up param fields and initial values
        str_Fc = tk.StringVar(value = "1000000.0")
        str_Fm = tk.StringVar(value = "0.2")
        str_runT = tk.StringVar(value = "1800")
        ent_Fc = ttk.Entry(fr_params, textvariable = str_Fc, width = 15)
        lbl_Fc = ttk.Label(fr_params, text = "Test Frequency (Hz)")
        ent_Fm = ttk.Entry(fr_params, textvariable = str_Fm, width = 15)
        lbl_Fm = ttk.Label(fr_params, text = "Collection Frequency (Hz)")
        ent_runT = ttk.Entry(fr_params, textvariable = str_runT, width = 15)
        lbl_runT = ttk.Label(fr_params, text = "Test Run Time (s)")
        testStrings = (str_Fc, str_Fm, str_runT)
        
        # Temperature Label
        lbl_temp = ttk.Label(fr_middle, textvariable = self.tempVar)
        
        # Timer Button and Label
        btn_timer = ttk.Button(fr_middle, text = self.btn_timer_states[0], style = "AccentButton",
                                    command = self.timerButtonCallback)
        lbl_timer = ttk.Label(fr_middle, textvariable = self.timerVar)

        # Create Status Window
        statusWindow = ScrolledText(fr_status, height = 12, width = 25, wrap = 'word', font=("Helvetica", 8))
        statusWindow.bind("<Key>", lambda e: "break") # Make Read-only

        # Create Buttons
        btn_start = ttk.Button(fr_button, text = self.btn_start_states[0], style = "AccentButton",
                                    command = self.startButtonCallback)
        btn_calib = ttk.Button(fr_button, text = self.btn_calib_states[0], style = "AccentButton",
                               command = self.calibrateButtonCallback)
        btn_heat = ttk.Button(fr_button, text = self.btn_heat_states[0], style = "AccentButton",
                              command = self.heatButtonCallback)
        btn_QC = ttk.Button(fr_button, text = self.btn_QC_states[0], style = "AccentButton",
                              command = self.QCButtonCallback)
        
        # Create Channel Selection Panel
        channelVars = []
        for i in range(4):
            tempVar = tk.IntVar(value = 1);
            channelVars.append(tempVar);
            ttk.Checkbutton(fr_channelSelect, text=f"Ch{i+1}",variable=tempVar, 
                onvalue=1, offvalue=0).grid(row = 0, column = i, padx = 2, pady = 1)

        # Organize and Arrange Components
        fr_button.grid(row = 0, column = 1, padx = (10, 2), pady = 3)
        fr_params.grid(row = 0, column = 0, padx = 8, pady = 10, sticky = "nw")
        btn_start.pack()
        btn_calib.pack(pady = 3)
        btn_QC.pack()
        btn_heat.pack(pady = 3)
        lbl_Fc.grid(row = 0, column = 0, padx = 2, pady = 5)
        ent_Fc.grid(row = 0, column = 1, padx = 2, pady = 5)
        lbl_Fm.grid(row = 0, column = 2, padx = 2, pady = 5)
        ent_Fm.grid(row = 0, column = 3, padx = 2, pady = 5)
        lbl_runT.grid(row = 1, column = 0, padx = 2, pady = 5)
        ent_runT.grid(row = 1, column = 1, padx = 2, pady = 5)
        fr_channelSelect.grid(row = 1, column = 2, columnspan = 2, padx = 2, pady = 2)
        fr_top.grid(row = 0, column = 0, padx = (0, 10), pady = (0, 5))
        fr_middle.grid(row = 1, column = 0)
        btn_timer.grid(row = 0, column = 0, padx = 10)
        lbl_timer.grid(row = 0, column = 1, padx = 10)
        lbl_temp.grid(row = 0, column = 2, padx = 10)
        fr_bottom.grid(row = 2, column = 0)
        fr_vis.grid(row = 0, column = 0)
        fr_status.grid(row = 0, column = 1, sticky = 'N')
        statusWindow.grid(row = 0, column = 0)

        return statusWindow, fr_vis, btn_start, btn_calib, btn_heat, btn_timer, testStrings, channelVars
    
    def reinitPlot(self, N_channels):
        self.plot1.cla()
        for i in range(N_channels):
            self.plot1.plot([], [], 'o-', label=f"Channel {i+1}", markersize=4)
        self.lines = self.plot1.get_lines();
        self.plot1.set_xlabel("Time (s)")
        self.plot1.set_ylabel("Capacitance (pF)")
        #self.plot1.set_title("Impedance Measurements")
        self.plot1.legend(loc='upper left')

    # Updates the plot with new data
    def updatePlot(self, xdata, CData):
        # Update the Canvas with the new data 
        q = 0
        for l in self.lines:
            l.set_xdata(xdata)
            l.set_ydata(CData[q])
            q+=1
        
        CData = CData[~np.isnan(CData)];
        self.plot1.set_xlim(-1, np.max(xdata)+1)
        self.plot1.set_ylim(np.min(CData)*0.9 - 10, np.max(CData)*1.3 + 10)
        self.plot1.legend(handles = self.lines, loc='upper left')
        self.canvas.draw()
    
    # Updates the label displaying the current temperature
    def updateTempLabel(self, temp):
        self.tempVar.set(f"Temperature Left: {temp[0]}C\n Temperature Right: {temp[1]}C")
    
    # Updates Timer in window
    def updateTimer(self, time):
        self.timerVar.set(time)
    
    # Writes to status window
    def writeStatus(self, status):
        numLines = int(self.statusWindow.index('end -1 line').split('.')[0])
        self.statusWindow.insert('end', status + '\n')
        self.statusWindow.yview('end')
        
    def openCalibrationWindow(self):
        cbWindow = tk.Toplevel(self.root)
        cbWindow.title("Calibration Window")
        cbWindow.rowconfigure(0, minsize = 100, weight=1)
        cbWindow.columnconfigure(0, minsize = 200, weight=1)

        calibStringZ = tk.StringVar(value = '{:.3f}'.format(self.calibZ))
        
        #fr_calibParams = ttk.LabelFrame(cbWindow, text = "Calibration Parameters")
        #fr_calibValues = ttk.LabelFrame(cbWindow, text = "Current Values")
        btn_calibRun = ttk.Button(cbWindow, text = "Begin Calibration", style = "AccentButton",
                    command = lambda: self.appController.runCalibration(calibStringZ))
        #fr_calibParams.grid(row = 0, column = 0, pady = 2, padx = 2)
        #fr_calibValues.grid(row = 1, column = 0, pady = 2, padx = 2)
        #btn_calibRun.grid(row = 2, column = 0, pady = 2, padx = 2)
        btn_calibRun.grid(row = 1, column = 0, pady = 2, padx = 2)
        lbl_helpText = ttk.Label(cbWindow, text = "Please insert the Calibration Board before continuing")
        lbl_helpText.grid(row = 0, column = 0)
        
        #lbl_Z = ttk.Label(fr_calibParams, text = "Complex\nImpedance (Ohms):") 
        #calibEntryZ = ttk.Entry(fr_calibParams, textvariable = calibStringZ)
        #lbl_Z.grid(row = 0, column = 0, padx = 2, pady = 5)
        #calibEntryZ.grid(row = 0, column = 1, padx = 2, pady = 5)
        
        #lbl_M_calib = ttk.Label(fr_calibValues,
                    #text = f"M_calib: {self.appController.IAController.M_calib}")
        #lbl_M_calib.grid(row = 0, column = 0, pady = 2)
        
        # Center window
        w = cbWindow.winfo_reqwidth()
        h = cbWindow.winfo_reqheight()
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws/2) - (w/2)-150
        y = (hs/2) - (h/2)
        cbWindow.geometry('+%d+%d' % (x, y))
        
        self.cbWindow = cbWindow
        
    # Start Button Callback
    def startButtonCallback(self):
        #self.appController.toggleTest()
        if self.btn_start['text'] == self.btn_start_states[0]:
            self.toggleButtonText('btn_start')
            self.appController.openSaveDialog() # Set file path
        elif self.btn_start['text'] == self.btn_start_states[1]:
            self.toggleButtonText('btn_start')
            self.appController.toggleTest() # Starts Test
        else:
            self.appController.IAController.stopTest("Canceled")
        

    # Calibrate Button Callback
    def calibrateButtonCallback(self):
        self.openCalibrationWindow()
        
    def heatButtonCallback(self):
        self.appController.toggleHeating()
        print('Heater Toggled')
        
    def QCButtonCallback(self):
        #self.openQCWindow()
        self.appController.runQC()
        return
    
    def timerButtonCallback(self):
        self.toggleButtonText('btn_timer')
        self.appController.toggleTimer()

    def getTestParams(self):
        temp = [0, 0, 0]
        i = 0
        for x in self.testStrings:
            temp[i] = float(x.get())
            i+=1
        return temp
    
    def toggleButtonText(self, button):
        if button == 'btn_heat':
            self.buttonStateIndices[2] ^= 1
            self.btn_heat['text'] = self.btn_heat_states[self.buttonStateIndices[2]]
        elif button == 'btn_calib':
            self.buttonStateIndices[1] ^= 1
            self.btn_calib['text'] = self.btn_calib_states[self.buttonStateIndices[1]]
        elif button == 'btn_timer':
            self.buttonStateIndices[3] ^= 1
            self.btn_timer['text'] = self.btn_timer_states[self.buttonStateIndices[3]]
        elif button == 'btn_QC':
            self.buttonStateIndices[4] ^= 1
            self.btn_QC['text'] = self.btn_QC_states[self.buttonStateIndices[4]]
        else:
            x = self.buttonStateIndices[0]
            x += 1 # More than two options
            if x < 3:
                self.buttonStateIndices[0] = x
            else:
                self.buttonStateIndices[0] = 0
            self.btn_start['text'] = self.btn_start_states[self.buttonStateIndices[0]]

        