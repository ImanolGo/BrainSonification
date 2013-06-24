import OSC

class osc_send():
    def __init__(self,portNum):
        # tupple with ip, port. i dont use the () but maybe you want -> send_address = ('127.0.0.1', 9000)
        self.send_address = ('127.0.0.1', portNum)

        # OSC basic client
        self.c = OSC.OSCClient()
        self.c.connect( self.send_address ) # set the address for all following messages
        
    def set_PortNumber(self,portNum):
        self.send_address = ('127.0.0.1', portNum)
        self.c.connect( self.send_address ) # set the address for all following messages
        
    def send_volume(self,volume):
        # single message
        msg = OSC.OSCMessage()
        msg.setAddress("/volume") # set OSC address
        msg.append(volume) # int
        self.c.send(msg) # send it!
        
    def send_stimulus(self,stimulus):
        # single message
        msg = OSC.OSCMessage()
        msg.setAddress("/stimulus") # set OSC address
        msg.append(stimulus) # int
        self.c.send(msg) # send it!
        
    def send_coordinates(self,coordinates):
        # single message
        msg = OSC.OSCMessage()
        msg.setAddress("/coordinates/x") # set OSC address
        msg.extend(coordinates[:,0]) # float
        self.c.send(msg) # send it!
        msg = OSC.OSCMessage()
        msg.setAddress("/coordinates/y") # set OSC address
        msg.extend(coordinates[:,1]) # float
        self.c.send(msg) # send it!
        msg = OSC.OSCMessage()
        msg.setAddress("/coordinates/z") # set OSC address
        msg.extend(coordinates[:,2]) # float
        self.c.send(msg) # send it!
        
        
    def send_best_voxels(self,best_voxels):
        # single message
        msg = OSC.OSCMessage()
        i = 0
        for voxel in best_voxels:
            msg.setAddress("/voxels") # set OSC address
            msg.append(voxel) # int
        
        msg.append(0) #When erasing number of voxels leave them to zero
        self.c.send(msg) # send it!