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
    
    btn_start_states = ['NEW TEST', 'STOP TEST']
    btn_calib_states = ['CALIBRATE', 'CANCEL CALIBRATION']
    btn_heat_states = ['START HEATING', 'STOP HEATING']
    #calibZ = 99.85+0.017j; # Old Board
    calibZ = 179.9+0.1j; #Complex Impedance Standard Reference (series) New

    def __init__(self, appController, root):

        self.appController = appController;
        self.root = root
        self.tempVar = tk.StringVar()
        self.tempVar.set("None")
        self.statusWindow, self.fr_vis, self.btn_start, self.btn_calib, self.btn_heat, self.testStrings, self.channelVars = self.createTopWindow();
        self.fig, self.plot1, self.canvas = self.setUpVisualization();
        self.buttonStateIndices = [0,0,0] # Start, calibrate, heat
    
    def onClose(self):
        return

    # Initializes plot
    def setUpVisualization(self):
        # Plot
        fig = Figure(figsize=(5.7, 2.5), dpi = 100)
        plot1 = fig.add_axes([0.1, 0.2, 0.75, 0.65], autoscale_on = True)
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
        root.title("TraumaCheck Interface")
        style = ttk.Style(root)
        root.tk.call('source', '../Azure-ttk-theme-main/azure.tcl')
        style.theme_use('azure')
        style.configure("AccentButton", foreground = 'white')

        root.rowconfigure(0, minsize = 100, weight=1)
        root.rowconfigure(1, minsize = 300, weight=1)
        root.columnconfigure(0, minsize = 400, weight=1)

        # Create Frames
        fr_top = tk.Frame(root)
        fr_bottom = tk.Frame(root)
        fr_vis = tk.Frame(fr_bottom)
        fr_status = ttk.LabelFrame(fr_bottom, text = "Status Window")
        fr_params = ttk.LabelFrame(fr_top, text = "Test Signal Parameters")
        fr_channelSelect = ttk.LabelFrame(fr_params, text = "Active Channels")
        fr_button = tk.Frame(fr_top)

        # Set up param fields and initial values
        str_Fc = tk.StringVar(value = "1000000.0")
        str_Fm = tk.StringVar(value = "0.2")
        str_runT = tk.StringVar(value = "30")
        ent_Fc = ttk.Entry(fr_params, textvariable = str_Fc)
        lbl_Fc = ttk.Label(fr_params, text = "Test Frequency (Hz)")
        ent_Fm = ttk.Entry(fr_params, textvariable = str_Fm)
        lbl_Fm = ttk.Label(fr_params, text = "Collection Frequency (Hz)")
        ent_runT = ttk.Entry(fr_params, textvariable = str_runT)
        lbl_runT = ttk.Label(fr_params, text = "Test Run Time (s)")
        testStrings = (str_Fc, str_Fm, str_runT)
        
        # Temperature Label
        lbl_temp = ttk.Label(fr_bottom, textvariable = self.tempVar)

        # Create Status Window
        statusWindow = ScrolledText(fr_status, height = 13, width = 25, wrap = 'word', font=("Helvetica", 8))
        statusWindow.bind("<Key>", lambda e: "break") # Make Read-only

        # Create Buttons
        btn_start = ttk.Button(fr_button, text = self.btn_start_states[0], style = "AccentButton",
                                    command = self.startButtonCallback)
        btn_calib = ttk.Button(fr_button, text = self.btn_calib_states[0], style = "AccentButton",
                               command = self.calibrateButtonCallback)
        btn_heat = ttk.Button(fr_button, text = self.btn_heat_states[0], style = "AccentButton",
                              command = self.heatButtonCallback)
        

        # Create Channel Selection Panel
        channelVars = []
        for i in range(4):
            tempVar = tk.IntVar();
            channelVars.append(tempVar);
            ttk.Checkbutton(fr_channelSelect, text=f"Ch{i+1}",variable=tempVar, 
                onvalue=1, offvalue=0).grid(row = 0, column = i, padx = 2, pady = 1)

        # Organize and Arrange Components
        fr_button.grid(row = 0, column = 1, padx = 5)
        fr_params.grid(row = 0, column = 0, padx = 5, sticky = "w")
        btn_start.pack()
        btn_calib.pack(pady = 5)
        btn_heat.pack()
        lbl_Fc.grid(row = 0, column = 0, padx = 2, pady = 5)
        ent_Fc.grid(row = 0, column = 1, padx = 2, pady = 5)
        lbl_Fm.grid(row = 0, column = 2, padx = 2, pady = 5)
        ent_Fm.grid(row = 0, column = 3, padx = 2, pady = 5)
        lbl_runT.grid(row = 1, column = 0, padx = 2, pady = 5)
        ent_runT.grid(row = 1, column = 1, padx = 2, pady = 5)
        fr_channelSelect.grid(row = 1, column = 2, columnspan = 2, padx = 2, pady = 2)
        fr_top.grid(row = 0, column = 0)
        lbl_temp.grid(row = 0, column = 0)
        fr_bottom.grid(row = 1, column = 0)
        fr_vis.grid(row = 1, column = 0)
        fr_status.grid(row = 1, column = 1)
        statusWindow.pack()

        return statusWindow, fr_vis, btn_start, btn_calib, btn_heat, testStrings, channelVars
    
    def reinitPlot(self, N_channels):
        self.plot1.cla()
        for i in range(N_channels):
            self.plot1.plot([], [], 'o-', label=f"Channel {i+1}", markersize=4)
        self.lines = self.plot1.get_lines();
        self.plot1.set_xlabel("Time (s)")
        self.plot1.set_ylabel("Capacitance (pF)")
        self.plot1.set_title("Impedance Measurements")
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
        
        fr_calibParams = ttk.LabelFrame(cbWindow, text = "Calibration Parameters")
        fr_calibValues = ttk.LabelFrame(cbWindow, text = "Current Values")
        btn_calibRun = ttk.Button(cbWindow, text = "Begin Calibration", style = "AccentButton",
                    command = lambda: self.appController.runCalibration(calibStringZ))
        fr_calibParams.grid(row = 0, column = 0, pady = 2, padx = 2)
        fr_calibValues.grid(row = 1, column = 0, pady = 2, padx = 2)
        btn_calibRun.grid(row = 2, column = 0, pady = 2, padx = 2)
        
        lbl_Z = ttk.Label(fr_calibParams, text = "Complex\nImpedance (Ohms):") 
        calibEntryZ = ttk.Entry(fr_calibParams, textvariable = calibStringZ)
        lbl_Z.grid(row = 0, column = 0, padx = 2, pady = 5)
        calibEntryZ.grid(row = 0, column = 1, padx = 2, pady = 5)
        
        lbl_M_calib = ttk.Label(fr_calibValues,
                    text = f"M_calib: {self.appController.IAController.M_calib}")
        lbl_M_calib.grid(row = 0, column = 0, pady = 2)
        
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
        self.appController.toggleTest()

    # Calibrate Button Callback
    def calibrateButtonCallback(self):
        self.openCalibrationWindow()
        
    def heatButtonCallback(self):
        self.appController.toggleHeating()

    def getTestParams(self):
        temp = [0, 0, 0]
        i = 0
        for x in self.testStrings:
            temp[i] = float(x.get())
            i+=1
        return temp
    
    def toggleButtonText(self, button):
        if button == 'btn_heat':
            self.buttonStateIndices[2] ^= 1;
            self.btn_heat['text'] = self.btn_heat_states[self.buttonStateIndices[2]]
        elif button == 'btn_calib':
            self.buttonStateIndices[1] ^= 1;
            self.btn_calib['text'] = self.btn_calib_states[self.buttonStateIndices[1]]
        else:
            self.buttonStateIndices[0] ^= 1;
            self.btn_start['text'] = self.btn_start_states[self.buttonStateIndices[0]]

        