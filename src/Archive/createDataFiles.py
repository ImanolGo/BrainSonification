

# Standard library imports
import numpy as num
import cPickle as pickle
import os

class createDataFiles():
    def __init__(self):
        self.dir = '/Users/imanolgo/Documents/SMC/Master_Thesis/fMRI_Thesis/FMRI_App/MRData/'
        self.numVoxels = 1000
        
    def start(self):
        
        usersDir = []
        for name in os.listdir(self.dir): 
            if os.path.isdir(os.path.join(self.dir, name)):
                #print name
                usersDir.append(name)
        
        noUserList = ['CBU060474','CBU060506','CBU060662']
        for noUser in noUserList:
            usersDir.remove(noUser)

        for userNum, user in enumerate(usersDir):
            
            print "User Test: ", user
            
            try:
                fi = open("data/" + user + "_hemisphere.dat", 'r')
            except IOError:
                #No such file
                
                data_path  = self.dir + user + '/sess1/'
                fi = open(data_path + "fMRI_Data.dat", 'r')
                print "Reading fMRI Data ..."
                self.Data = pickle.load(fi) 
                fi.close()
                print "Data read"
                
                try:
                    fi = open(data_path + "selectedFeatures.dat", 'r')
                except IOError:
                    #No such file
                    print "Selected features file not found"
                else:
                    self.ttest_ind = pickle.load(fi)
                    self.ANOVA_ind = pickle.load(fi)
                    self.tasks = pickle.load(fi)
                    self.SVMttest_ind = pickle.load(fi)
                    fi.close()
                    
                    (self.numFrames,self.lenZ,self.lenX,self.lenY) = num.shape(self.Data) # 4D axis
                    self.findMaxCoordinate()
                    self.projectToHemisphere()
                    self.readMetaData()
                    self.saveData(user)
                    
                self.Data = []
 
            else:
                fi.close()
           
        print "Data files created successfully!!!"
        
    def saveData(self,_user):
        fi = open("data/" + _user + "_hemisphere.dat","w")
        pickle.dump(self.voxels, fi,protocol= pickle.HIGHEST_PROTOCOL)
        pickle.dump(self.CoordinatesSemisphere, fi,protocol= pickle.HIGHEST_PROTOCOL)
        pickle.dump(self.stimuli, fi,protocol= pickle.HIGHEST_PROTOCOL)
        fi.close()
        print "Data saved"
        return
        
    def readMetaData(self):
        
        # 0 means Idle, then stimuli from 1-4
        self.stimuli = num.zeros(self.numFrames)
        
        for i in range(len(self.tasks)):
           for ind in (self.tasks[i]):
               self.stimuli[ind] = i+1
           
        
    def findMaxCoordinate(self):
         
        meanData = self.Data.mean(axis=0)
        meanData[meanData<350]=0; #Background Filtering
        
        #Find the maximum coordinate
        self.MaxCoord = 0
        for i in range(self.lenZ):        
            for j in range(self.lenX):
                for k in range(self.lenY):
                   if(meanData[i,j,k]>0):
                        #Referencing the coordinates to the center (0,0)
                        iCoord = float(i)- float(self.lenZ)/2.0
                        jCoord = float(j)- float(self.lenX)/2.0
                        kCoord = float(k)- float(self.lenY)/2.0
                        
                        self.MaxCoord = num.maximum(self.MaxCoord,num.abs(iCoord))
                        self.MaxCoord = num.maximum(self.MaxCoord,num.abs(jCoord))
                        self.MaxCoord = num.maximum(self.MaxCoord,num.abs(kCoord))
                        
        print "Maximum coordinate: ", self.MaxCoord
                        
    def projectToHemisphere(self):
        self.CoordinatesSemisphere = []
        self.voxels = []
            
        for n in range(self.numVoxels):
            # To reconstruct from indexes
            ind = self.ANOVA_ind[n]
            k = ind%self.lenY #y axis
            rest = ind/self.lenY 
            j = rest%self.lenY #x axis
            i = rest/self.lenX #z axis
            
            self.voxels.append(self.Data[:,i,j,k])
            
            # To reconstruct from indexes               
            kCoord = float(k) - float(self.lenY)/2.0 #y axis
            kCoord = kCoord/self.MaxCoord #normalize the coordinate to the maximum
            rest = ind/self.lenY
            jCoord = float(j) - float(self.lenX)/2.0 #x axis
            jCoord = jCoord/self.MaxCoord #normalize the coordinate to the maximum
            iCoord = float(i) - float(self.lenZ)/2.0 #z axis   
            iCoord = iCoord/self.MaxCoord #normalize the coordinate to the maximum
            
            #TODO: the inverse tangent must be suitably defined to take the correct quadrant of x,y into account.
            [rho,theta,phi] = self.cartesian2Spherical(jCoord, kCoord, abs(iCoord)) #we force z to be always positive
            [x,y,z] = self.spherical2Cartesian(1.0, theta, phi) #projection to a hemisphere of radius 1
            self.CoordinatesSemisphere.append([x,y,z])
            
        #transform data to numpy arrays
        self.voxels = num.array(self.voxels)
        self.CoordinatesSemisphere = num.array(self.CoordinatesSemisphere)
            
            
    def spherical2Cartesian(self,_rho,_theta,_phi):
        # theta = azimuthal angle
        # phi =  polar angle
        # rho = radius
        _x = _rho*num.cos(_theta)*num.sin(_phi)
        _y = _rho*num.sin(_theta)*num.sin(_phi)
        _z = _rho*num.cos(_phi)
        return _x,_y,_z
    
    def cartesian2Spherical(self,_x,_y,_z):
        # theta = azimuthal angle
        # phi =  polar angle
        # rho = radius
        _rho = num.sqrt(_x**2+_y**2+_z**2) 
        _phi = num.arctan2(num.sqrt(_x**2+_y**2), _z)
        _theta = num.arctan2(_y, _x)
        return _rho,_theta,_phi
                
                
    