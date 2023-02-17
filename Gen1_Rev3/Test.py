#! /usr/bin/python3
# Contains variables and parameters related to the actual experiment, including test frequency, run time, and any recorded data
import numpy as np

class Test: 

    #R_OFFSET = np.array([20.3, 20.3, 20.6, 20.3]);
    #R_OFFSET = np.zeros((1, 4)); 

    def __init__(self, IAController, testParams, N_channels):

        self.manager = IAController

        # Test setup parameters
        self.Fc = testParams[0]
        self.Fm = testParams[1]
        self.runT = testParams[2]
        self.delay = int(1000/self.Fm)
        self.N_meas = int(self.runT*self.Fm) + 1
        self.collectedMeasurements = 0
        self.N_channels = N_channels

     # Test data output parameters
        self.N_channels = N_channels
        self.rawDataMatrix = []
        self.Z = np.empty((self.N_meas, N_channels))
        self.Z.fill(np.nan)
        self.G = np.empty((self.N_meas, N_channels))
        self.G.fill(np.nan)
        self.C = np.empty((self.N_meas, N_channels))
        self.C.fill(np.nan)
        self.phi = np.empty((self.N_meas, N_channels))
        self.phi.fill(np.nan)
        self.Z_comp = np.empty((self.N_meas, N_channels), dtype=complex)
        self.Z_comp.fill(np.nan)
        self.Vrat = np.empty((self.N_meas, N_channels), dtype=complex)
        self.Vrat.fill(np.nan)
        self.t = np.zeros(self.N_meas)

        self.GMean = np.zeros(N_channels)
        self.CMean = np.zeros(N_channels)
        self.ZMean = np.zeros(N_channels)
        self.PhiMean = np.zeros(N_channels)
        self.Z_compMean = np.zeros((N_channels,), dtype=complex)
        self.VratMean = np.zeros((N_channels,), dtype=complex)

        # Flags
        self.isInitialized = False

        # Calibration Data
        self.M_calib = np.zeros((1, 4));
