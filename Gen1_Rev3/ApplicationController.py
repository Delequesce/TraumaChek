#! /usr/bin/python3
from MainGUI import *
from IAController import *
from I2CController import*
import threading, queue
import tkinter as tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
import time
import queue
import libm2k

class ApplicationController:
    # Class sets up GUI and manages variables across tests. After setting everything up, it periodically polls the 
    # temperature and impedance queues and calls any relevant update functions on GUI object 
    
    def __init__(self, root):

        # Create queues 
        self.statusQueue = queue.Queue()
        self.impedanceQueue = queue.Queue()
        
        # Create Main Objects
        self.gui = MainGUI(self, root); # GUI Object
        self.root = root
        self.IAController = IAController(self);
        self.ctx = self.IAController.ctx;
        self.I2CController = I2CController(self); # Sets up temperature read comms (I2C)
        self.IAProc = None
        
        self.saveDataFilePath = None

        # Assign Channels
        self.channels = self.assignChannels();
        self.channelList = [];

        self.pollTask = None
        
        self.isHeating = False
        self.isFinished = False
        self.isQC_Running = False
        self.timerOn = False
        self.tempArray = []

    # Assign Channels
    def assignChannels(self):
        channels = []
        # Old Board
#         channels.aself.isQC_Running = Trueppend(np.array([0, 0], dtype=np.int8)) # Channel 1 (top left)
#         channels.append(np.array([1, 0], dtype=np.int8)) # Channel 2 (top right)
#         channels.append(np.array([0, 1], dtype=np.int8)) # Channel 3 (bottom left)
#         channels.append(np.array([1, 1], dtype=np.int8)) # Channel 4 (bottom right)
        # New Board
        channels.append(np.array([1, 1], dtype=np.int8)) # Channel 1 (top left)
        channels.append(np.array([1, 0], dtype=np.int8)) # Channel 2 (top right)
        channels.append(np.array([0, 1], dtype=np.int8)) # Channel 3 (bottom left)
        channels.append(np.array([0, 0], dtype=np.int8)) # Channel 4 (bottom right)
        return channels
    
    def openSaveDialog(self):
        self.saveDataFilePath = asksaveasfilename(defaultextension=".csv",
                    filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        self.statusQueue.put("Save Path Successfully Set")
        #self.testDialog = TestDialog(self)

    def toggleTest(self, args = None):
        IAController = self.IAController
        #print(f" Test Running?: {IAController.testRunning}")
        if not IAController.testRunning:
            #self.gui.toggleButtonText('btn_start')
            if args is None:
                # Initialize and Run Test
                #saveDataFilePath = asksaveasfilename(defaultextension=".csv",
                    #filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
                if len(self.saveDataFilePath) > 0:
                    N_channels = IAController.initTest(self.gui.getTestParams(),
                                    self.channels, self.saveDataFilePath)
                    if IAController.testInitialized:
                        self.gui.reinitPlot(N_channels)
                        # Run test
                        self.statusQueue.put("Running Test...")
                        self.isFinished = False
                        self.IAController.FSM_State = 0
                        self.IAProc = threading.Thread(target=IAController.runTest, args=[time.perf_counter()])
                        self.IAProc.start()
                    else:
                        IAController.stopTest("Initialization Error Encountered")
                        return
                else:
                    IAController.stopTest("Canceled")
                    return
            else:
                testParams = self.gui.getTestParams()
                testParams[1] = args[1]; testParams[2] = args[2]
                N_channels = IAController.initTest(testParams, self.channels)
                if IAController.testInitialized:
                    self.gui.reinitPlot(N_channels)
                    # Run test
                    # If calibration:
                    if self.isQC_Running:
                        self.statusQueue.put("Running Quality Check...")
                    else:
                        self.statusQueue.put("Running Calibration...")
                        
                    self.isFinished = False
                    self.IAController.FSM_State = 0
                    self.IAProc = threading.Thread(target=IAController.runTest, args=[time.perf_counter()])
                    self.IAProc.start()
                else:
                    IAController.stopTest("Initialization Error Encountered")
                    return
        #else:
            #self.IAController.stopTest("Canceled");

    def stopTest(self, calib, qc):
        if not (calib or qc):
            self.gui.toggleButtonText('btn_start')
        self.isFinished = True
        if self.IAProc:
            self.IAProc.join()
            #print("IA Procedure Finished")
            
    def runQC(self):
        self.isQC_Running = True
        self.IAController.isQC_Running = True
        self.toggleTest((0, 0.2, 30))

    def polling(self, pollState):
        
        # Check for collected Measurements
        while self.impedanceQueue.qsize():
            try:
                dataTuple = self.impedanceQueue.get(0);
                #print(dataTuple)
                self.gui.updatePlot(*dataTuple)
            except queue.Empty:
                pass

        # Check for status messages
        while self.statusQueue.qsize():
            try:
                msg = self.statusQueue.get(0);
                self.gui.writeStatus(msg)
            except queue.Empty:
                pass
        
        # Check checkbox state
        self.setChannels()
        
        # Request new temperature from controller
        
        if pollState == 10:
            nBytes = 2;
            temp = self.I2CController.readTemp(nBytes)
            if len(temp) > nBytes-1:
                a = [0]*nBytes;
                for i in range(nBytes):
                    #temp[i] = temp[i]
                    a[i] = temp[i]*0.125 + 15;
                
                #a[0] = temp[0];
                #a[1] = temp[1]*0.125 + 15;
                self.IAController.currTemp = a[0]
                self.gui.updateTempLabel(a)
                self.tempArray.append(a[0])
            else:
                self.statusQueue.put("Temperature Read Error")
                
            pollState = 0;
            
        # Update Timer
        if self.timerOn:
            temporaryTime = round(time.perf_counter()-self.timer_start)
            self.gui.updateTimer(str(temporaryTime))
            
        pollState += 1

        self.pollTask = self.root.after(100, lambda: self.polling(pollState))

    # Checks states of channel checkboxes 
    def setChannels(self):
        channelList = []
        i = 0
        for var in self.gui.channelVars:
            if var.get() == 1:
                channelList.append(i)  # Append channel identifier to list
            i+=1
        self.channelList = channelList;
    
    def toggleTimer(self):
        self.timer_start = time.perf_counter()
        self.gui.updateTimer("0")
        self.timerOn ^= True
        
    
    # Communicates with MCU through I2C interface to toggle heating
    def toggleHeating(self):
        if self.I2CController.toggleHeat():
            self.isHeating ^= True;
            self.gui.toggleButtonText('btn_heat')
        else:
            self.statusQueue.put("Temperature Control Communication Error")

    def on_close(self):
        if tk.messagebox.askokcancel("Quit", "Do you want to quit the program?"):
            if self.pollTask:
                self.root.after_cancel(self.pollTask)
            if self.isHeating:
                self.toggleHeating()
            self.IAController.onClose()
            self.I2CController.onClose()
            self.gui.onClose()
            self.root.destroy()

    def runCalibration(self, calibStringZ):
        self.gui.cbWindow.destroy()
        self.IAController.runCalibration(calibStringZ)


# Main program execution
if __name__ == "__main__":
    root = tk.Tk()
    app = ApplicationController(root);
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    app.polling(0)
    # Let GUI run in UI mode
    app.root.mainloop()