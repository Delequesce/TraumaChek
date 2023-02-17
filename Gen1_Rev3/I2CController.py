import libm2k

class I2CController:
    
    TOGGLEHEAT = bytearray([0x01]);
    
    def __init__(self, appController):
        self.appController = appController;
        self.ctx = self.appController.ctx;
        self.i2c_desc = self.initInterface();
        
    def i2c_read(self, nBytes):
        nBytes = 1;
        data_read_config = bytearray(2);
        a = [0]*nBytes;
        for i in range(nBytes):
            if libm2k.i2c_read(self.i2c_desc, data_read_config, libm2k.i2c_general_call) == -1:
                #print("fWhoops {a}")
                return a
            else:
                #print(data_read_config)
                #print(data_read_config)
                #a[i] = data_read_config[0];
                a = [x for x in data_read_config];
        #print(a)
        return a

    def i2c_write(self, dataToWrite):
        if libm2k.i2c_write(self.i2c_desc, dataToWrite, libm2k.i2c_general_call) == -1:
            return 0
        else:
            return 1
            
    def toggleHeat(self):
        return self.i2c_write(self.TOGGLEHEAT);
    
    def readTemp(self, nBytes):
        return self.i2c_read(nBytes)
    
    def initInterface(self):
        # I2C Initialization
        m2k_i2c_init = libm2k.m2k_i2c_init()
        m2k_i2c_init.scl = 4 # Switch for old board
        m2k_i2c_init.sda = 3
        m2k_i2c_init.context = self.ctx

        i2c_init_param = libm2k.i2c_init_param()
        i2c_init_param.max_speed_hz = 20000
        i2c_init_param.slave_address = 0x4B
        i2c_init_param.extra = m2k_i2c_init
        
        i2c_desc = libm2k.i2c_init(i2c_init_param)
        return i2c_desc
    
    def onClose(self):
        libm2k.i2c_remove(self.i2c_desc)
            
