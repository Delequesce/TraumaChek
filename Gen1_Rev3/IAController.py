#! /usr/bin/python3
import libm2k
import math, time, csv, queue
import numpy as np
from Test import *
import os

class IAController:

    #R_OFFSET = np.array([3.8+3j, 3.8+3j, 0+3j, 0+3j], dtype='complex'); # New Mux
    #R_OFFSET = np.array([25.4+2.76j, 3.8+3j, 0+3j, 0+3j], dtype='complex'); # Old Mux
    R_OFFSET = np.array([0+1j, 0+1j, 0+1j, 0+1j], dtype='complex'); # New Board
    CALIBFILEPATH = os.path.join(os.path.dirname(__file__),'Calibration.csv')
    SAMPLESPERMEASUREMENT = 2**17
    SAMPLESFORFFT = 100000;
    REPSPERTP = 5;
    THREADDELAY = 50; #Delay time in processing to allow for threading with heater and GUI.

    def __init__(self, appController):

        self.appController = appController;
        self.root = self.appController.root
        self.impedanceQueue = self.appController.impedanceQueue
        self.statusQueue = self.appController.statusQueue
        self.activeTest = None
        self.currTemp = 0
        self.channelList = [];

        # Connect to ADALM2000
        self.ctx=libm2k.m2kOpen()
        self.ain = None
        self.aout = None
        self.dig = None
        self.pwr = None
        if self.ctx is None:
            self.statusQueue.put("Connection Error: No ADALM2000 device available/connected to your PC.")
        else:
            self.ain, self.aout, self.dig, self.pwr = self.connectDevice(self.ctx);
        self.M_calib = self.loadCalibration()
        #self.M_calib = np.array([1,1,1,1], dtype='complex')
        
        # CSV Write Parameters
        self.output_file = None

        # Flags
        self.testRunning = False
        self.isCalibrating = False
        self.isQC_Running = False
        self.testInitialized = False
        self.FSM_State = 0
        self.currCount = 0
        
        self.runTask = None


    # Connects to ADALM2000
    def connectDevice(self, ctx):
        #recentPlug = False
        #if ctx.getDacCalibrationGain(0) == 1.0:
        #    recentPlug = True
        ctx.calibrateFromContext()
        self.getADALMCalibrationValues(ctx)

        # Get Pointers to peripherals
        ain = ctx.getAnalogIn()
        aout = ctx.getAnalogOut()
        pwr = ctx.getPowerSupply()
        dig = ctx.getDigital()
        
        #if recentPlug:
        for i in range(2):
            dig.setDirection(i, 1)
                #dig.enableChannel(i, True)

        ain.setSampleRate(100e6)
        ain.setOversamplingRatio(1)
        ain.setRange(0, -5,5); ain.setRange(1, -5,5)
        ain.enableChannel(0, True); ain.enableChannel(1, True)
        
        pwr.enableChannel(0,True)
        pwr.pushChannel(0,5)

        aout.setOversamplingRatio(0, 1)
        
        return ain, aout, dig, pwr
    
    # Loads calibration values from file (need to add exception handler for if file not found)
    def loadCalibration(self):
        M_calib = np.array([1, 1, 1, 1], dtype=complex)
        with open(self.CALIBFILEPATH, 'r', newline = '') as input_file:
                csv_reader = csv.reader(input_file, delimiter = ',')
                for row in csv_reader:
                    r = np.asarray(row)
                    M_calib = r.astype(np.complex)
                self.statusQueue.put("Parameters succesfully loaded from file")
        return M_calib

    def initTest(self, testParams, digLevels, saveDataFilePath = None,):
        self.statusQueue.put("Initializing Test...")

        # Create Test
        self.testRunning = True
        self.digLevels = digLevels;
        N_channels = 4;
        activeTest = Test(self, testParams, N_channels)
        self.N_channels = activeTest.N_channels
        self.currCount = 0;

        # Set Output parameters
        self.saveDataFilePath = saveDataFilePath
        if saveDataFilePath:
            self.output_file = open(saveDataFilePath, 'w', newline = '')

        # Enable Power
        self.pwr.enableChannel(0,True)

        # Enable Digital Output
        dig = self.dig;

        # Create Test Signal
        Fs_out = 75e6  # Output Sample Rate
        aout = self.aout
        aout.setOversamplingRatio(0,1)
        aout.setSampleRate(0, Fs_out)

        # Create Buffer size of measurement window
        w = 1e-3; #2e-3
        buff_size = int(w * Fs_out) #1ms
        t_out = np.array(range(buff_size))/Fs_out
        buffer =  1.5+0.05*np.sin(2*np.pi*activeTest.Fc*t_out) # 50mv
        aout.setCyclic(True)
        
        # Write Header Row
        if saveDataFilePath:
            csv_writer = csv.writer(self.output_file, delimiter = ' ')
            csv_writer.writerow(["Time", "Z", "G", "C", "Phi"])
        
        # Store necessary local variables in object
        self.buffer = buffer
        
        aout.enableChannel(0, True);
        aout.push(0, buffer)
        activeTest.isInitialized = True
        self.testInitialized = True
        self.activeTest = activeTest
        self.statusQueue.put("Initialization Complete")

        return N_channels

    def runTest(self, t0):
        FSM_State = self.FSM_State

        # State Machine
        activeTest = self.activeTest
        t_m = time.perf_counter() - t0
        if FSM_State == 0:
#             print(f"State 0 start: {t_m}")
            # Set start time
            self.t_start = t_m
            
            # Get current channel list
            self.channelList = self.appController.channelList;
            
            FSM_State += 1
        if FSM_State == 1:
            #print(f"State 1 start: {t_m}")
            # Determine if samples can be collected
            # If so, collect and store samples
            #if activeTest.delay - 1000 > 1e3*(t_m - self.t_start): #auto-average
            if self.currCount < self.REPSPERTP:
                self.activeTest.rawDataMatrix = self.collectData(activeTest)

                # Save first collection time
                activeTest.t[activeTest.collectedMeasurements] = round(self.t_start, 3)
                # Proceed to data processing 
                FSM_State += 1;
                #print(f"Collected: {time.perf_counter()-t0-self.t_start}")
            else:
                # Move on to storage
                #print(self.currCount)
                self.currCount = 0
                FSM_State += 2;
                

        if FSM_State == 2:
            #print(f"State 2 start: {time.perf_counter() - t0}")
            # Extract parameters from data
            self.processData(activeTest, activeTest.collectedMeasurements, self.currCount)
            self.currCount +=1
            if True: # Change to True implement average
                # Go back to collection state
                self.FSM_State = FSM_State - 1;
            else:
                self.FSM_State = FSM_State + 1;
                self.currCount = 0
            
            # Allow for threading after completing 1 collect-process cycle
            self.runTask = self.root.after(self.THREADDELAY, lambda: self.runTest(t0))
            return
            
        if FSM_State == 3:
            #print(f"State 3 start: {t_m}")
            activeTest.collectedMeasurements += 1
            self.sendAndStore(activeTest, activeTest.collectedMeasurements)
            FSM_State += 1;
        if FSM_State == 4:
            if activeTest.collectedMeasurements < activeTest.N_meas:
                t_adj = round(activeTest.delay - 1e3*(t_m - self.t_start))
                self.FSM_State = 0
                #print(f"Stored: {t_m-self.t_start}")
                self.runTask = self.root.after(t_adj-4, lambda: self.runTest(t0))
            else:
                self.stopTest()

    def collectData(self, activeTest):
        dataOut = []
        channelList = self.channelList;

        ain = self.ain
        dig = self.dig
        # Loop through active channels and collect data for each
        #print(channelList)
        for i in channelList:

            # Set MUX Output Values to Switch Active Channels
            for j in range(2):
                #print(self.digLevels[i])
                dig.setValueRaw(j, bool(self.digLevels[i][j]))
                #print(f"Channel {j}: {dig.getValueRaw(j)}")
            
            # Acquire data from buffer
            ain.startAcquisition(self.SAMPLESPERMEASUREMENT);
            dataOut.append(ain.getSamples(self.SAMPLESPERMEASUREMENT));
            ain.stopAcquisition();
            
        
        return dataOut

    def processData(self, activeTest, n, j):
        i = 0
        for chan in self.channelList:
            vin = np.array(activeTest.rawDataMatrix[i][0]);
            vout = np.array(activeTest.rawDataMatrix[i][1]);
            
            sampNum = self.SAMPLESFORFFT;
            
            vin = vin[0:sampNum];
            vout = vout[0:sampNum];
            
            p = np.zeros(2, dtype=np.int16) # index for max of fft 
        
            FVin = np.fft.rfft(vin); FVout = np.fft.rfft(vout)
            # Find index of FFT Max
            p[0] = 2+np.argmax(np.abs(FVin[2:]))
            p[1] = 2+np.argmax(np.abs(FVout[2:]))
        
            if (p[0] != p[1] or (p[0] == 0 and p[1] == 0)):
                self.statusQueue.put("Error: FFT peaks misaligned")  
            
            fc = p[0]*100e6/sampNum

            # Calculate Output Parameters
            vrat_temp = FVin[p[0]]/FVout[p[1]];
            Z_comp_temp = vrat_temp*self.M_calib[chan] - self.R_OFFSET[chan]; # Complex Impedance
            #print(vrat_temp)
            #print(Z_comp_temp)
            #print(np.imag(1e12/Z_comp_temp)/(2*np.pi*fc))
            #print(fc)
            #print('')
            if j > 0:
                activeTest.Vrat[n][chan] = (vrat_temp + activeTest.Vrat[n][chan]*j)/(j+1)
                activeTest.Z_comp[n][chan] = (Z_comp_temp + activeTest.Z_comp[n][chan]*j)/(j+1)
                activeTest.C[n][chan] = (np.imag(1e12/Z_comp_temp)/(2*np.pi*fc) + activeTest.C[n][chan]*j)/(j+1);
                activeTest.G[n][chan] = (np.real(1000/Z_comp_temp) + activeTest.G[n][chan]*j)/(j+1);
                activeTest.phi[n][chan] = (np.angle(Z_comp_temp) + activeTest.phi[n][chan]*j)/(j+1);
                activeTest.Z[n][chan] = (np.abs(Z_comp_temp) + activeTest.Z[n][chan]*j)/(j+1);
            else:
                activeTest.Vrat[n][chan] = vrat_temp
                activeTest.Z_comp[n][chan] = Z_comp_temp
                activeTest.C[n][chan] = np.imag(1e12/Z_comp_temp)/(2*np.pi*fc)
                activeTest.G[n][chan] = np.real(1000/Z_comp_temp)
                activeTest.phi[n][chan] = np.angle(Z_comp_temp)
                activeTest.Z[n][chan] = np.abs(Z_comp_temp)
                
            i+=1

    def sendAndStore(self, activeTest, n):
        #self.statusQueue.put(f"{activeTest.t[n-1]}s: {activeTest.C[n-1]}pF")

        # Add plot data to data queue
        xdata = np.int_(activeTest.t[0:n]+0.5)
        CData = np.transpose(activeTest.C)[:, 0:n]
        self.impedanceQueue.put((xdata, CData))

        # Write data continuously to file
        output_file = self.output_file
        if output_file:
            output_file = open(output_file.name, 'a')
            csv_writer = csv.writer(output_file, delimiter = ' ')
            csv_writer.writerow([activeTest.t[n-1], activeTest.Z[n-1], activeTest.G[n-1],
                                 activeTest.C[n-1], activeTest.phi[n-1], self.currTemp])
            output_file.close()

    def stopTest(self, reason = None):
        self.FSM_State = 5
        calib = self.isCalibrating
        qc = self.isQC_Running
        self.testRunning = False
        #self.aout.enableChannel(0, False);
        self.appController.stopTest(calib, qc)
        statusQueue = self.statusQueue
        
        if self.testInitialized:
            self.aout.cancelBuffer()
            self.ain.stopAcquisition()
            self.aout.enableChannel(0, False)
            #self.pwr.enableChannel(0,False)

        # Log appropriate status to window
        
        # Default Message for bad connection
        message = "Sensor misaligned or not connected. Please check connection and retry"
        
        if reason == "Canceled":
            message = "Test canceled by user"
        else:
            message = "Unknown Abort"
            if calib:
                message = "Calibration Complete"
                self.calculateStats()
                self.isCalibrating = False
            elif qc:
                message = "QC Complete"
                self.calculateStats()
                self.isQC_Running = False
            else:
                message = "Collection Complete"
                self.calculateStats() # Change to true to get stats
        
        # Log Message
        statusQueue.put(message)
    
    def getADALMCalibrationValues(self, ctx):
        print(ctx.getAdcCalibrationGain(0))
        print(ctx.getAdcCalibrationOffset(0))
        print(ctx.getAdcCalibrationGain(1))
        print(ctx.getAdcCalibrationOffset(1))
        print(ctx.getDacCalibrationGain(0))
        print(ctx.getDacCalibrationOffset(0))

    def calculateStats(self):
        x1 = self.activeTest; t = x1.t; N = x1.C.shape[1];
        # Calibration Stats
        calib = self.isCalibrating
        qc = self.isQC_Running
        
        if calib or qc:
            for i in range(N):
                CMean = round(np.mean(x1.C[:, i]), 3); Cstd = round(np.std(x1.C[:, i]), 3)
                GMean = round(np.mean(x1.G[:, i]), 4); Gstd = round(np.std(x1.G[:, i]), 4)
                ZMean = round(np.mean(x1.Z[:, i]), 4); Zstd = round(np.std(x1.Z[:, i]), 4)
                PhiMean = round(np.mean(x1.phi[:, i]), 4); Phistd = round(np.std(x1.phi[:, i]), 4)
                Z_compMean = np.mean(x1.Z_comp[:, i]); VratMean = np.mean(x1.Vrat[:, i]);
                #self.statusQueue.put('Z = {:.5f}'.format(Z_compMean))
                x1.CMean[i] = CMean; x1.GMean[i] = GMean
                x1.ZMean[i] = ZMean; x1.PhiMean[i] = PhiMean
                x1.Z_compMean[i] = Z_compMean; x1.VratMean[i] = VratMean
                
                # Enable to print stats
                if False:
                    self.statusQueue.put('Vrat = {:.5f}'.format(VratMean))
                    self.statusQueue.put(f" G = {GMean}+{Gstd}, C = {CMean}+{Cstd}, Z = {ZMean}+{Zstd}, Phi = {PhiMean}+{Phistd}")
            if calib:
                self.finishCalibration()
            else:
                self.finishQC()
        else:
            for i in range(N):
                # Calculate Tpeak and Delta Epsilon Max
                ind = np.argmax(x1.C[:, i])
                C_norm = np.divide(x1.C[:, i], x1.C[ind][i]);
                Tpeak = np.round(t[ind], 2);
                DeMax = np.round(1-min(C_norm[ind:]), 4)
                              
                self.statusQueue.put(f"Channel {i}: Tpeak: {Tpeak}s, DeMax = {DeMax}")
                
    
    def runCalibration(self, calibStringZ):
        self.isCalibrating = True
        self.Zc = complex(calibStringZ.get())
        runT = 30
        Fm = 0.2
        # Close Calibration popup
        self.appController.toggleTest((self.Zc, Fm, runT))

    def onClose(self):
        if self.runTask:
            self.appController.root.after_cancel(self.runTask)
        if self.ctx:
            self.pwr.enableChannel(0, False)
            libm2k.contextClose(self.ctx)
    
    def finishQC(self):
        activeTest = self.activeTest
        C_QC = np.asarray([48, 98, 220, 270])
        G_QC = np.asarray([5.56, 2.57, 10.00, 5.57])
        
        # Calculate Normalized Root Mean Squared Deviation across range
        rmsdC = np.sqrt(np.mean((activeTest.CMean - C_QC)**2))/(C_QC[3]-C_QC[0])*100
        rmsdG = np.sqrt(np.mean((activeTest.GMean - G_QC)**2))/(G_QC[2]-G_QC[1])*100
        if rmsdC < 2 and rmsdG < 2:
            self.statusQueue.put(f"QC Passed! \nC Error = {rmsdC}%, \nG Error = {rmsdG}%")
        else:
            self.statusQueue.put(f"QC Failed! \nC Error = {rmsdC}%, \nG Error = {rmsdG}%")
        
        
    def finishCalibration(self):
        activeTest = self.activeTest
        newVal = np.zeros((4, 1), dtype=complex)
        oldVal = self.M_calib
        dist = np.zeros((4, 1))
        distThresh = 9
        # Compute Values and Distances
        for i in self.channelList:
            newVal[i] = (self.Zc+self.R_OFFSET[i])/(activeTest.VratMean[i])
            dist[i] = (np.real(newVal[i]) - np.real(oldVal[i]))**2 + (np.imag(newVal[i]) - np.imag(oldVal[i]))**2
        #print(newVal)
        #print(oldVal)
        #print(dist)
        if (dist > distThresh).any():
            self.statusQueue.put('Calibration Failure. Check connection and try again')
        else:
            self.statusQueue.put('Calibration Sucessful!')
            for i in self.channelList:
                self.M_calib[i] = newVal[i]
                self.statusQueue.put('New Calibration Values: {:.4f}'.format(self.M_calib[i]))
        
            # Write to file
            with open(self.CALIBFILEPATH, 'w', newline = '') as output_file:
                csv_writer = csv.writer(output_file, delimiter = ',')
                csv_writer.writerow(self.M_calib)         
            self.statusQueue.put("Parameters succesfully saved to file");
            