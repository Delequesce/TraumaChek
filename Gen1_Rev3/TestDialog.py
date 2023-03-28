import tkinter as tk
import tkinter as ttk
from tkinter.filedialog import askopenfilename, assaveasfilename

class TestDialog:
    
    def __init__(self, appController):
        self.appController = appController
        self.root = appController.root
        
        self.saveDataFilePath = None
        
        self.tdWindow, self.btn_start, self.ent_filePathIndicator = self.createStartWindow(self.root)
        
    def createStartWindow(self, root