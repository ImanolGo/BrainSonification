

import nibabel as nib
import osc_send as sn

import utils
import numpy as num
import wx
import os, glob

#from nipy.algorithms.utils.pca import pca
from sklearn.decomposition import PCA

# Enthought library imports
from enthought.chaco.tools.cursor_tool import CursorTool, BaseCursorTool
from enthought.chaco.api import ArrayPlotData, ColorBar, Plot, GridPlotContainer, \
                                 BaseTool, DataRange1D, LinearMapper,GridContainer
from enthought.chaco.default_colormaps import *
from enthought.chaco.tools.api import LineInspector, ZoomTool,PanTool
from enthought.enable.example_support import DemoFrame, demo_main
from enthought.enable.api import Window
from enthought.traits.ui.api import Item, Group, View
from enthought.traits.api import Any, Array, Bool, Callable, CFloat, CInt, \
        Event, Float, HasTraits, Int, Trait, on_trait_change, Instance
from enthought.chaco.example_support import COLOR_PALETTE

MyCOLOR_PALETTE = (num.array([143,89,2,
                         78,154,6,
                         178,223,138,
                         32,74,135,
                         237,212,0,
                         227,26,28,
                         253,191,111,
                         255,127,0,
                         202,178,214,
                         106,61,154], dtype=float)/255).reshape(10,3)
                         
"""                         
color_map_functions = [ jet, autumn, bone, cool, copper, flag, gray, yarg, hot, hsv, pink, prism, 
spring, summer, winter, cw1_004, cw1_005, cw1_006, cw1_028, gmt_drywet, Spectral, RdBu, RdPu, YlGnBu, RdYlBu, GnBu, 
RdYlGn, PuBu, BuGn, Greens, PRGn, BuPu, OrRd, Oranges, PiYG, YlGn, BrBG, Reds, RdGy, PuRd, Blues, Greys, YlOrRd, YlOrBr, 
Purples, PuOr, PuBuGn, gist_earth, gist_gray, gist_heat, gist_ncar, gist_rainbow, gist_stern, gist_yarg ]"""

class ImageIndexTool(BaseTool):
    """ A tool to set the slice of a cube based on the user's mouse movements
    or clicks.
    """

    # This callback will be called with the index into self.component's
    # index and value:
    #     callback(tool, x_index, y_index)
    # where *tool* is a reference to this tool instance.  The callback
    # can then use tool.token.
    callback = Any()

    # This callback (if it exists) will be called with the integer number
    # of mousewheel clicks
    wheel_cb = Any()

    # This token can be used by the callback to decide how to process
    # the event.
    token  = Any()

    # Whether or not to update the slice info; we enter select mode when
    # the left mouse button is pressed and exit it when the mouse button
    # is released
    # FIXME: This is not used right now.
    select_mode = Bool(False)

    def normal_left_down(self, event):
        self._update_slices(event)

    def normal_right_down(self, event):
        self._update_slices(event)

    def normal_mouse_move(self, event):
        if event.left_down or event.right_down:
            self._update_slices(event)

    def _update_slices(self, event):
            plot = self.component
            ndx = plot.map_index((event.x, event.y), 
                                 threshold=5.0, index_only=True)
            if ndx:
                self.callback(self, *ndx)

    def normal_mouse_wheel(self, event):
        if self.wheel_cb is not None:
            self.wheel_cb(self, event.mouse_wheel)    


class BrainFrame(wx.Frame):
    def __init__(self, parent, id):
        self.Window = wx.Frame.__init__(self,parent, id, 'fMRI Player',size=(800, 500))
        self.pnl1 = wx.Panel(self, -1)
        self.pnl1.SetBackgroundColour(wx.BLACK)
        self.pnl2 = wx.Panel(self, -1 )
        self.pnl3 = wx.Panel(self, -1 )
        self.pnl4 = wx.Panel(self, -1)
        self.pnl4.SetBackgroundColour(wx.BLACK)
        self.nb = wx.Notebook(self,-1)
        self.timer = wx.Timer(self, -1)
        self.colormap = Any
        self.colorcube = Any
        self.num_figs = 10
        self.Data = 0
        self.numPC = 50 # number of principal components
        self.pcInd = 0
        self.principalComponent = []
        self.volume_on = False
        self.previous_vol = 0
        self.best_voxels_ind = []
        self.portNum = 9001
        self.osc = sn.osc_send(self.portNum)
        self.T = 2 #The sample period 
        self.Fs = 1.0/self.T #The sample frequency
        self.Fs = 44100 #The sample frequency
        self.cmap = Trait(gmt_drywet, Callable) #gmt_drywet,jet
        self.Voxel = num.zeros(self.num_figs)
        self.FFTVoxel = num.zeros(self.num_figs)
        self.frqs = num.zeros(self.num_figs)
        self.fftPeaks = num.zeros(self.num_figs)
        self.maxtab = num.zeros(shape=(self.num_figs,2))

        self.init_data('../data/s03_epi_snr01_xxx/')
        self.init_panel()
        self.update_panel()
        self.update_voxel_data()
        self.updateOSC()
        self.draw_plot()

    def init_panel(self):
                # initialize menubar
        toolbar = self.CreateToolBar()
       # toolbar.AddLabelTool(wx.ID_EXIT, '', wx.Bitmap('icons/quit.png'))
        toolbar.AddLabelTool(wx.ID_OPEN, '', wx.Bitmap('../icons/Yellow_open.png'))
        toolbar.Realize()
        self.TextVoxelEnergy = wx.StaticText(self.pnl3, -1, 'Voxel Energy: 0.0' )
        self.TextSliceX = wx.StaticText(self.pnl3, -1, 'X: ')
        self.TextSliceY = wx.StaticText(self.pnl3, -1, 'Y: ')
        self.TextSliceZ = wx.StaticText(self.pnl3, -1, 'Z: ')
        self.CtrlSliceX  = wx.SpinCtrl(self.pnl3, -1, '0', min=0, max=64)
        self.CtrlSliceY  = wx.SpinCtrl(self.pnl3, -1, '0', min=0, max=64)
        self.CtrlSliceZ  = wx.SpinCtrl(self.pnl3, -1, '0', min=0, max=36)
        self.PCText = wx.StaticText(self.pnl3, -1, 'Select nth Principal Component')
        self.PCCtrl  = wx.SpinCtrl(self.pnl3, -1, '1', min=1, max=self.numPC)
        self.VAText = wx.StaticText(self.pnl3, -1, 'Voxel Analysis')
       
        # create track counter
        self.trackCounter = wx.StaticText(self.pnl2, label=" 0 / 0")

        self.Bind(wx.EVT_TOOL, self.OnExit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_TOOL, self.OnOpen, id=wx.ID_OPEN)
        self.Bind(wx.EVT_TIMER, self.OnTimer)

        # initialize slider
        # default id = -1 is used, initial value = 0, min value = 0, max value = number of figures
        self.MaxSlider3 = 2000
        self.MinSlider3 = 125
        self.slider1 = wx.Slider(self.pnl2, -1, 0, 0, self.num_figs)
        self.slider2 = wx.Slider(self.pnl2, -1, 0, 0, 100, size=(120, -1))
        self.slider3 = wx.Slider(self.pnl2, -1, (self.MaxSlider3 - self.MinSlider3), self.MinSlider3, self.MaxSlider3, size=(120, -1))
        self.pos_slider1 = self.slider1.GetValue()
        self.pos_slider2 = self.slider2.GetValue()
        self.pos_slider3 = self.slider3.GetValue()
        self.clkFreq = (self.MaxSlider3 + self.MinSlider3) - self.pos_slider3
        #self.osc.send_IVT(self.clkFreq)
        fSpeed = 1000.0/self.clkFreq
        strSpeed = "%.2f Frames/s" % fSpeed
        self.TextSpeed = wx.StaticText(self.pnl2, -1, strSpeed)

        # initialize buttons
        self.pause = wx.BitmapButton(self.pnl2, -1, wx.Bitmap('../icons/stock-media-pause.png'))
        self.play  = wx.BitmapButton(self.pnl2, -1, wx.Bitmap('../icons/stock-media-play.png'))
        self.prev  = wx.BitmapButton(self.pnl2, -1, wx.Bitmap('../icons/stock-media-prev.png'))
        self.next  = wx.BitmapButton(self.pnl2, -1, wx.Bitmap('../icons/stock-media-next.png'))
        self.volume = wx.BitmapButton(self.pnl2, -1, wx.Bitmap('../icons/stock-volume.png'))
        
        #self.nb.AddPage(self.pnl1, "fMRI Slices")
        #self.nb.AddPage(self.pnl4, "Time Voxel")
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox1 = wx.BoxSizer(wx.VERTICAL)
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        self.topsizer= wx.BoxSizer(wx.HORIZONTAL) # left controls, right image output
        # slider controls controls

        ctrlsizer= wx.BoxSizer(wx.VERTICAL)
        ctrlsizer.AddSpacer(30)
        ctrlsizer.Add(self.PCText, 0, wx.ALIGN_CENTER, 5)
        ctrlsizer.AddSpacer(5)
        ctrlsizer.Add(self.PCCtrl,0,wx.ALIGN_CENTER)
        ctrlsizer.AddSpacer(30)
       
        h1= wx.BoxSizer(wx.HORIZONTAL)
        h1.Add(self.TextSliceZ,0,wx.ALIGN_CENTER)
        h1.Add(self.CtrlSliceZ,0,wx.ALIGN_CENTER)
        ctrlsizer.Add(h1,0,wx.ALIGN_CENTER)
        ctrlsizer.AddSpacer(5)
        h2= wx.BoxSizer(wx.HORIZONTAL)
        h2.Add(self.TextSliceX,0,wx.ALIGN_CENTER)
        h2.Add(self.CtrlSliceX,0,wx.ALIGN_CENTER)
        ctrlsizer.Add(h2,0,wx.ALIGN_CENTER)
        ctrlsizer.AddSpacer(5)
        h3= wx.BoxSizer(wx.HORIZONTAL)
        h3.Add(self.TextSliceY,0,wx.ALIGN_CENTER)
        h3.Add(self.CtrlSliceY,0,wx.ALIGN_CENTER)
        ctrlsizer.Add(h3,0,wx.ALIGN_CENTER)
        ctrlsizer.AddSpacer(15)
        ctrlsizer.Add(self.TextVoxelEnergy, 0, wx.ALIGN_CENTER, 5)
        self.pnl3.SetSizer(ctrlsizer)
        
        self.topsizer.Add(self.pnl3, 0, wx.ALL, 10)
        self.topsizer.Add(self.nb, 2, wx.ALL)  

        hbox1.Add(self.slider1, 1, wx.ALL|wx.EXPAND, 20)
        hbox1.Add(self.trackCounter, 0, wx.ALL|wx.CENTER, 20)
        hbox2.Add(self.pause,flag=wx.LEFT,border=10)
        hbox2.Add(self.play, flag=wx.RIGHT, border=10)
        hbox2.Add(self.prev, flag=wx.LEFT, border=10)
        hbox2.Add(self.next)
        hbox2.AddSpacer(35)
        hbox2.Add(self.slider3,flag=wx.ALIGN_RIGHT | wx.TOP | wx.LEFT, border=10)
        hbox2.AddSpacer(10)
        hbox2.Add(self.TextSpeed,wx.ALL|wx.CENTER)
        hbox2.Add((150, -1), 1, flag=wx.EXPAND | wx.ALIGN_RIGHT)
        hbox2.Add(self.volume, flag=wx.ALIGN_RIGHT)
        hbox2.Add(self.slider2, flag=wx.ALIGN_RIGHT | wx.TOP | wx.LEFT, border=10)
        hbox2.AddSpacer(15)
        
        vbox.Add(hbox1, 1, wx.EXPAND | wx.BOTTOM, 10)
        vbox.Add(hbox2, 1, wx.EXPAND)
        self.pnl2.SetSizer(vbox)
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        #sizer.Add(self._create_plot_window(), 1, wx.EXPAND)
        self.sizer.Add(self.topsizer, 1, flag=wx.EXPAND)
        self.sizer.Add(self.pnl2, flag=wx.EXPAND | wx.BOTTOM | wx.TOP, border=5)
   
        self.SetSizer(self.sizer)
        self.Centre()
        self.slider1.Bind(wx.EVT_SLIDER, self.slider1Update)
        self.slider2.Bind(wx.EVT_SLIDER, self.slider2Update)
        self.slider3.Bind(wx.EVT_SLIDER, self.slider3Update)

        # respond to the click of the button
        self.CtrlSliceX.Bind(wx.EVT_SPINCTRL, self.move2SliceX)
        self.CtrlSliceZ.Bind(wx.EVT_SPINCTRL, self.move2SliceZ)
        self.CtrlSliceY.Bind(wx.EVT_SPINCTRL, self.move2SliceY)
        self.PCCtrl.Bind(wx.EVT_SPINCTRL, self.PC_Select)
        self.prev.Bind(wx.EVT_BUTTON, self.prevClick)
        self.next.Bind(wx.EVT_BUTTON, self.nextClick)
        self.play.Bind(wx.EVT_BUTTON, self.playClick)
        self.pause.Bind(wx.EVT_BUTTON, self.pauseClick)
        self.volume.Bind(wx.EVT_BUTTON, self.volumeClick)

    def init_data(self, path):

        self.Data = []
        self.PCA_data = []
        min_value = 350
        # Generate some data to plot:
        print "Loading brain data from " + path
        print "..."
        if os.path.exists(path):
            nii_files = sorted (glob.glob( os.path.join(path, '*.img')), key = str.lower)
            #nim = NiftiImage(nii_files[0])
            print nii_files[0]
            img = nib.load(nii_files[0])
            print img.shape
            self.num_figs = len(nii_files) #time axis
            (self.len_z,self.len_x,self.len_y) = img.shape # 3D axis
            self.Data  = num.empty((self.num_figs,self.len_z,self.len_x,self.len_y)) # Data allocation of memory
            
            flatImg = num.ravel(img.get_data())
            print flatImg.shape
            mskInd = num.all(flatImg > min_value, axis = 0)
            print mskInd
            msk = flatImg[mskInd]
            print msk.shape
            # IMPORTANT y[self.tasks[i]]= self.Voxel[self.tasks[i]].copy()
            self.PCA_data = num.empty((self.len_z*self.len_x*self.len_y,self.num_figs)) # Data allocation of memory
            for i in range(self.num_figs):
                #nim = NiftiImage(nii_files[i])
                img = nib.load(nii_files[i])
                self.Data [i,:,:,:] = img.get_data() #filling the data with every frame
                #print img.get_data().ravel().shape()
                #print num.ravel(img.get_data())
                self.PCA_data [:,i] = num.ravel(img.get_data())
                print "Loading: " + nii_files[i]

            print "Brain data loaded..."

        else:
            print '\nNo Brain data my friend...\n'

        
        print self.PCA_data.shape
        self.max_data =  self.Data.max()
        print "Max Data value: ", self.max_data

        
        #msk = num.all(self.PCA_data > min_value, axis=0)

        print "Calculating PCA ..."
        #self.res = pca(self.PCA_data, axis = 0, mask=msk, ncomp=9)
        self.pca =  PCA(n_components=self.numPC, copy= False)
        self.pca.fit(self.PCA_data)
        print(self.pca.components_.shape) 
        print(self.pca.explained_variance_ratio_) 
        print self.principalComponent
        print "PCA done!"
        """print self.Data.shape
        print self.res['basis_vectors'].shape
        print self.res['basis_projections'].shape
        print self.res['pcnt_var'].shape"""

        self.pos_t = 0
        self.pos_x = int(self.len_x/2)
        self.pos_y = int(self.len_y/2)
        self.pos_z = int(self.len_z/2)
        self.pos_t = 0
        #ind  = self.voxels_ind[0] #takes the nth best voxel
        
        self.slice_x = int(self.len_x/2)
        self.slice_y = int(self.len_y/2)
        self.slice_z = int(self.len_z/2)
        self.vals = self.Data[self.pos_t,:,:,:]
        self.principalComponent = self.pca.components_[self.pcInd]


    def PC_Select(self,event):
        self.pcInd = self.PCCtrl.GetValue() - 1
        self.principalComponent = self.pca.components_[self.pcInd]
        print self.principalComponent
        self.updateSlices()

    def update_voxel_data(self):
        self.vals = self.Data[self.pos_t,:,:,:]
        self.Voxel = self.Data[:,self.slice_z,self.slice_x,self.slice_y]
        self.VoxelZeroPad = num.zeros(32048)
        self.VoxelZeroPad[0:self.num_figs] = self.Voxel
        [self.FFTVoxel,self.frqs] = utils.calcFFT(self.Voxel,self.Fs) 
        [self.maxtab, self.mintab ]= utils.peakdet(self.FFTVoxel,0.01)
        self.fftPeaks = self.maxtab[:,1]
        self.frqsPeaks = self.frqs[list(self.maxtab[:,0])]
        print "FTT Peaks: " 
        print self.fftPeaks 
        print "f(Hz): " 
        print self.frqsPeaks

    def update_panel(self):
        self.slider1.SetRange(0,self.num_figs) #set the new range of slider
        self.slider1.SetValue(0)
        self.trackCounter.SetLabel(" 0 / " + str(self.num_figs)) 
        self.CtrlSliceX.SetRange(0,self.len_x) 
        self.CtrlSliceX.SetValue(self.slice_x) 
        self.CtrlSliceY.SetRange(0,self.len_y) 
        self.CtrlSliceY.SetValue(self.slice_y) 
        self.CtrlSliceZ.SetRange(0,self.len_z) 
        self.CtrlSliceZ.SetValue(self.slice_z) 
        
    def enter_axes(self,event):        
        i = 0
        for ax in self.fig.axes:
            if ax==event.inaxes:
                self.subplot_num = i
                print self.subplot_num
            i = i +1
        
    def onclick(self,event):
        print 'button=%d, x=%d, y=%d, xdata=%f, ydata=%f'%(
            event.button, event.x, event.y, event.xdata, event.ydata)
        if self.subplot_num ==0: #x-y plane
            self.pos_x = int(event.xdata)
            self.pos_y = int(event.ydata)
            self.draw_plot()
        elif self.subplot_num ==2: #x-z plane
            self.pos_x = int(event.xdata) #not sure about that
            self.pos_z = int(event.ydata) #not sure about that
            self.draw_plot()
        elif self.subplot_num ==4: #y-z plane
            self.pos_y = int(event.xdata) #not sure about that
            self.pos_z = int(event.ydata) #not sure about that
            self.draw_plot()

    def move2SliceX(self,event):
        self.slice_x = self.CtrlSliceX.GetValue()
        self.updateSlices()
    
    def move2SliceZ(self,event):
        self.slice_z = self.CtrlSliceZ.GetValue()
        self.updateSlices()
    
    def move2SliceY(self,event):
        self.slice_y = self.CtrlSliceY.GetValue()
        self.updateSlices()
    
    def updateSlices(self):
        self.update_voxel_data()
        self.center.invalidate_and_redraw()
        self.right.invalidate_and_redraw()
        self.bottom.invalidate_and_redraw()
        self._update_images()
        self.updateOSC()

    def updateOSC(self):
        self.osc.send_frame(self.pos_t)
        self.osc.send_fftPeaks(self.fftPeaks,self.frqsPeaks)
        self.osc.send_voxel_coordinates([self.slice_x,self.slice_y,self.slice_z])
    
    def slider2Update(self, event):
        self.volumeLevel = float(self.slider2.GetValue())/100.0 #to set the volume in range [0 1]
        self.osc.send_volume(self.volumeLevel)
    
    def slider3Update(self, event):
        pos_slider3 = self.slider3.GetValue()
        self.clkFreq = (self.MaxSlider3 + self.MinSlider3) - pos_slider3
        #self.osc.send_IVT(self.clkFreq)
        fSpeed = 1000.0/self.clkFreq
        strSpeed = "%.2f Frames/s" % fSpeed
        self.TextSpeed.SetLabel(strSpeed)
        self.timer.Start(self.clkFreq)
           
    def slider1Update(self, event):
        # get the slider position
        self.pos_t = self.slider1.GetValue() 
        self.trackCounter.SetLabel(" " + str(self.pos_t) + " / " + str(self.num_figs))      
        self.vals = self.Data[self.pos_t,:,:,:]
        string= "Voxel Energy: %.2f" % self.Data[self.pos_t,self.slice_z,self.slice_x,self.slice_y]
        self.TextVoxelEnergy.SetLabel(string)
        self._update_model()
        self._update_images()
        
        
    def prevClick(self, event):
        # Set the slider position
        if(self.slider1.GetValue()>0):
            self.slider1.SetValue(self.slider1.GetValue()-1)
            self.slider1Update(event)
            #print "prev_click: ", self.pos1

    def nextClick(self, event):
        # Set the slider position
        if(self.slider1.GetValue()<self.num_figs):
            self.slider1.SetValue(self.slider1.GetValue()+1)
            self.slider1Update(event)
            #print "next_click: ", self.pos1

    def VoxelSelect(self,event):
        n = self.bestVoxelsCtrl.GetValue()
        #ind  = self.voxels_ind[n-1] #takes the nth best voxel
        self.slice_y = ind%self.len_y #y axis
        rest = ind/self.len_y 
        self.slice_x = rest%self.len_x #x axis
        self.slice_z = rest/self.len_x #z axis
        self.CtrlSliceY.SetValue(self.slice_y)
        self.CtrlSliceX.SetValue(self.slice_x)
        self.CtrlSliceZ.SetValue(self.slice_z)
        self.cursorXY.current_position = self.slice_y , self.slice_x
        self.cursorYZ.current_position = self.slice_y , self.slice_z
        self.cursorXZ.current_position = self.slice_x , self.slice_z
        self.updateSlices()
        
    def SetVoxelSelect(self,n):
        self.bestVoxelsCtrl.SetValue(n)
        #ind  = self.voxels_ind[n-1] #takes the nth best voxel
        self.slice_y = ind%self.len_y #y axis
        rest = ind/self.len_y 
        self.slice_x = rest%self.len_x #x axis
        self.slice_z = rest/self.len_x #z axis
        self.CtrlSliceY.SetValue(self.slice_y)
        self.CtrlSliceX.SetValue(self.slice_x)
        self.CtrlSliceZ.SetValue(self.slice_z)
        self.cursorXY.current_position = self.slice_y , self.slice_x
        self.cursorYZ.current_position = self.slice_y , self.slice_z
        self.cursorXZ.current_position = self.slice_x , self.slice_z
        self.updateSlices()


    def OnTimer(self, event):
        # Set the slider position
        if(self.slider1.GetValue()<self.num_figs):
            self.slider1.SetValue(self.slider1.GetValue()+1)
            self.slider1Update(event)
            
    def volumeClick(self, event):
        if self.volume_on:
            self.previous_vol = self.slider2.GetValue()
            self.slider2.SetValue(0)
            self.slider2Update(event)
            self.volume_on = False
        else:
            self.slider2.SetValue(self.previous_vol)
            self.previous_vol = 0
            self.slider2Update(event)
            self.volume_on = True

    def volumeClick(self, event):
        if self.volume_on:
            self.previous_vol = self.slider2.GetValue()
            self.slider2.SetValue(0)
            self.slider2Update(event)
            self.volume_on = False
        else:
            self.slider2.SetValue(self.previous_vol)
            self.previous_vol = 0
            self.slider2Update(event)
            self.volume_on = True

    def playClick(self, event):
        # update clock every 0.5 seconds (500ms)
        self.timer.Start(self.clkFreq)
        #self.audioServer.gui(locals())
        if(self.slider1.GetValue()<self.num_figs):  
            self.slider1Update(event)
        else:
            self.timer.Stop()
            elf.osc.send_PC(num.zeros(self.numPC))
        
    def pauseClick(self, event):
        self.timer.Stop()
        self.osc.send_best_voxels(num.zeros(self.numPC))
            
    def OnExit(self, event):
        self.timer.Stop()
        self.Close()
        return 0

    def OnOpen(self, event):
        self.panel = wx.Panel(self, -1)
        filters = 'NIFTI images (*.img)|*.img' 
        dialog = wx.FileDialog ( self.panel, message = 'Choose a NIFTI image', wildcard = filters, style = wx.OPEN | wx.MULTIPLE )
        
        if dialog.ShowModal() == wx.ID_OK:
           selected = dialog.GetPaths()
           for selection in selected:
              print 'Selected:', selection
        else:
           print 'Nothing was selected.'
        
        ind = selected[0].rfind('/')
        data_path =  str(selected[0][0:ind+1])
        dialog.Destroy()
        self.init_data(data_path)
        self.update_panel()
        self.update_voxel_data()
        self.updateOSC()

    def draw_plot(self):
        self._create_plot_window()
        self.SetSize(wx.Size(1280, 800))
        self.Show(True)
        
    def _scatter_plot_default(self):
        self._create_plot_window()
    
    def _line_plot_default(self):
        self._create_plot_window()
        
        #demo_main(self.window, size=(800,700), title="fMRI analyzer")
        # Create the model 
    def _index_callback(self, tool, x_index, y_index):
        plane = tool.token
        if plane == "TimeVoxel":
            self.slider1.SetValue( x_index)
            self.slider1Update(event)
            self.update_voxel_data()
            self._update_images()
            self.timePlotBig.invalidate_and_redraw()
            self.freqPlotBig.invalidate_and_redraw()
            self.timePlot.invalidate_and_redraw()
        else:
            if plane == "xy":
                self.slice_y = x_index
                self.slice_x = y_index   
            elif plane == "yz":
                self.slice_y = x_index
                self.slice_z = y_index
            elif plane == "xz":
                self.slice_x = x_index
                self.slice_z = y_index
            elif plane == "TimeVoxel":
                self.pos_t = x_index
            else:
                warnings.warn("Unrecognized plane for _index_callback: %s" % plane)
            
            self.cursorXY.current_position = self.slice_y , self.slice_x
            self.cursorYZ.current_position = self.slice_y , self.slice_z
            self.cursorXZ.current_position = self.slice_x , self.slice_z
            string= "Voxel Energy: %.2f" % self.Data[self.pos_t,self.slice_z,self.slice_x,self.slice_y]
            self.TextVoxelEnergy.SetLabel(string)
            self.update_voxel_data()
            self.updateOSC()
            self.CtrlSliceX.SetValue(self.slice_x) 
            self.CtrlSliceY.SetValue(self.slice_y) 
            self.CtrlSliceZ.SetValue(self.slice_z) 
            self._update_images()
            self.center.invalidate_and_redraw()
            self.right.invalidate_and_redraw()
            self.bottom.invalidate_and_redraw()
        return

    def _wheel_callback(self, tool, wheelamt):
        plane_slice_dict = {"xy": ("slice_z", 0), 
                            "yz": ("slice_x", 2),
                            "xz": ("slice_y", 1)}
        attr, shape_ndx = plane_slice_dict[tool.token]
        val = getattr(self, attr)
        max = self.vals.shape[shape_ndx]
        if val + wheelamt > max:
            setattr(self, attr, max-1)
        elif val + wheelamt < 0:
            setattr(self, attr, 0)
        else:
            setattr(self, attr, val + wheelamt)

        self.cursorXY.current_position = self.slice_y , self.slice_x
        self.cursorYZ.current_position = self.slice_y , self.slice_z
        self.cursorXZ.current_position = self.slice_x , self.slice_z
        self.CtrlSliceX.SetValue(self.slice_x) 
        self.CtrlSliceZ.SetValue(self.slice_z)
        self.CtrlSliceY.SetValue(self.slice_y)
        string= "Voxel Energy: %.2f" % self.Data[self.pos_t,self.slice_z,self.slice_x,self.slice_y]
        self.TextVoxelEnergy.SetLabel(string)
        self.update_voxel_data()
        self.updateOSC()
        self._update_images()
        self.center.invalidate_and_redraw()
        self.right.invalidate_and_redraw()
        self.bottom.invalidate_and_redraw()
        return
    
    def _create_plot_window(self):
        # Create the model
        min_value = 350 
        max_value = self.max_data
        image_value_range = DataRange1D(low=min_value,high=max_value)
        self.cmap = jet(range = image_value_range )
        self._update_model()
        datacube = self.colorcube 
    
        # Create the plot
        self.plotdata = ArrayPlotData()
        self.plotdataVoxel = ArrayPlotData()
        self.plotdataSlices = ArrayPlotData()
        self.plotdataVoxelFFT = ArrayPlotData()
        self.plotdataPC = ArrayPlotData()
        self._update_images()
        
         # Top Left plot
        centerplot = Plot(self.plotdata, resizable= 'hv', padding=20, title = "Slice_X")
        imgplot=centerplot.img_plot("yz", 
                                 xbounds= None,
                                 ybounds= None,
                                colormap=self.cmap)[0]
                                
        centerplot.x_axis.title = "Y"
        centerplot.y_axis.title = "Z"            
        self._add_plot_tools(imgplot, "yz")
        self.cursorYZ = CursorTool(imgplot, drag_button='left', 
                                 color='white')
        self.cursorYZ.current_position = self.slice_y , self.slice_z
        imgplot.overlays.append(self.cursorYZ)
        self.center = imgplot

        # Top Right Plot
        rightplot = Plot(self.plotdata, resizable= 'hv', padding=20,title = "Slice_Y")
        rightplot.x_axis.title = "X"
        rightplot.y_axis.title = "Z" 
        imgplot = rightplot.img_plot("xz", 
                                 xbounds= None,
                                 ybounds= None,
                                colormap=self.cmap)[0]
                   
        self._add_plot_tools(imgplot, "xz")
        self.cursorXZ = CursorTool(imgplot, drag_button='left', 
                                 color='white')
        self.cursorXZ.current_position = self.slice_x , self.slice_z
        imgplot.overlays.append(self.cursorXZ)
        self.right = imgplot

        # Bottom  LeftPlot
        bottomplot = Plot(self.plotdata, resizable= 'hv',padding=20, title = "Slice_Z")
        bottomplot.x_axis.title = "Y"
        bottomplot.y_axis.title = "X"
        imgplot = bottomplot.img_plot("xy", 
                                xbounds= None,
                                ybounds= None, 
                                colormap=self.cmap)[0]
                                
        """bottomplot.contour_plot("xy", 
                          type="poly",
                          xbounds=None,
                          ybounds=None)[0]"""   
                   
        self._add_plot_tools(imgplot, "xy")
        self.cursorXY = CursorTool(imgplot, drag_button='left', 
                                 color='white')
        self.cursorXY.current_position = self.slice_y , self.slice_x
        imgplot.overlays.append(self.cursorXY)
        self.bottom = imgplot
        
        """ # Create a colorbar
        cbar_index_mapper = LinearMapper(range=image_value_range)
        self.colorbar = ColorBar(index_mapper=cbar_index_mapper,
                                 plot=centerplot,
                                 padding_top=centerplot.padding_top,
                                 padding_bottom=centerplot.padding_bottom,
                                 padding_right=40,
                                 resizable='v',
                                 width=30, height = 100)"""
                                 
        lTasksName = ['DB','DN','VB','VN']
        # Create data series to plot
        timeplot = Plot(self.plotdataVoxel, resizable= 'hv', padding=20)
        timeplot.x_axis.title = "Frames"
        timeplot.plot("TimeVoxel", color = 'lightblue', line_width=1.0, bgcolor="white", name = "Time")[0]
        """for i in range(len(self.tasks)):
                timeplot.plot("task" + str(i),color=tuple(COLOR_PALETTE[i]), 
                line_width=1.0, bgcolor = "white", border_visible=True, name = lTasksName[i])[0]"""
        
        timeplot.legend.visible = True
        timeplot.plot("time", type = "scatter",color=tuple(COLOR_PALETTE[2]), line_width=1, bgcolor = "white", border_visible=True, 
                        name = "time")[0]
        self.timePlot = timeplot       
        # Create data series to plot
        timeplotBig = Plot(self.plotdataVoxel, resizable= 'hv', padding=20)
        timeplotBig.x_axis.title = "Frames"
        timeplotBig.plot("TimeVoxel", color = 'lightblue', line_width=1.5, bgcolor="white", name = "Time")[0]        
        timeplotBig.legend.visible = True
        timeplotBig.plot("time", type = "scatter",color=tuple(COLOR_PALETTE[2]), 
                line_width=1, bgcolor = "white", border_visible=True, name = "time")[0]
        self.timePlotBig = timeplotBig 

        # Create data series to plot
        freqplotBig = Plot(self.plotdataVoxelFFT, resizable= 'hv', padding=20)
        freqplotBig.x_axis.title = "Frequency (Hz)"
        freqplotBig.plot("FreqVoxel", color = 'lightblue', line_width=1.5, bgcolor="white", name = "Abs(Y)")[0]        
        freqplotBig.legend.visible = True
        freqplotBig.plot("peaks", type = "scatter",color=tuple(COLOR_PALETTE[2]), 
                line_width=1, bgcolor = "white", border_visible=True, name = "peaks")[0]
        self.freqPlotBig = freqplotBig 

         # Create data series to plot
        PCplotBig = Plot(self.plotdataPC, resizable= 'hv', padding=20)
        PCplotBig.x_axis.title = "Frames"
        PCplotBig.plot("Principal Component", color = 'lightblue', line_width=1.5, bgcolor="white", name = "Principal Component")[0]        
        PCplotBig.legend.visible = True
        PCplotBig.plot("time", type = "scatter",color=tuple(COLOR_PALETTE[2]), 
                line_width=1, bgcolor = "white", border_visible=True, name = "time")[0]
        self.PCplotBig = PCplotBig 

        #self.time = time
        # Create a GridContainer to hold all of our plots
        container = GridContainer(padding=10, fill_padding=True,
                              bgcolor="white", use_backbuffer=True,
                              shape=(2,2), spacing=(10,10))
        containerTime = GridContainer(padding=10, fill_padding=True,
                              bgcolor="white", use_backbuffer=True,
                              shape=(1,1), spacing=(5,5))

        containerFreq = GridContainer(padding=10, fill_padding=True,
                              bgcolor="white", use_backbuffer=True,
                              shape=(1,1), spacing=(5,5))
        containerPC = GridContainer(padding=10, fill_padding=True,
                              bgcolor="white", use_backbuffer=True,
                              shape=(1,1), spacing=(5,5))

        
        container.add(centerplot)
        container.add(rightplot)
        container.add(bottomplot)
        container.add(timeplot)
        containerTime.add(timeplotBig)
        containerFreq.add(freqplotBig)
        containerPC.add(PCplotBig)
        
        """container = GridContainer(padding=10, fill_padding=True,
                              bgcolor="white", use_backbuffer=True,
                              shape=(3,3), spacing=(10,10))
       
        for i in range(14,23):
             slicePlot = Plot(self.plotdataSlices, resizable= 'hv', padding=20,title = "slice " + str(i),bgcolor = "white")
             slicePlot.img_plot("slice " + str(i),xbounds= None, ybounds= None, colormap=self.cmap,bgcolor = "white")[0]
             container.add(slicePlot)"""

        self.container = container
        self.nb.DeleteAllPages()
        self.window =  Window(self.nb, -1, component=container)
        self.windowTime =  Window(self.nb, -1, component=containerTime)
        self.windowFreq =  Window(self.nb, -1, component=containerFreq)
        self.windowPC =  Window(self.nb, -1, component=containerPC)
        self.sizer.Detach(self.topsizer)
        self.sizer.Detach(self.pnl2)
        self.topsizer.Clear()
        self.topsizer.Add(self.pnl3, 0, wx.ALL, 10)
        self.nb.AddPage(self.window.control, "fMRI Slices")
        self.nb.AddPage(self.windowTime.control, "Time Voxel")
        self.nb.AddPage(self.windowFreq.control, "Frequency Voxel")
        self.nb.AddPage(self.windowPC.control, "Principal Component")
        self.topsizer.Add(self.nb, 1, wx.EXPAND) 
        self.sizer.Add(self.topsizer, 1, wx.EXPAND)
        self.sizer.Add(self.pnl2, flag=wx.EXPAND | wx.BOTTOM | wx.TOP, border=10)
   
        self.SetSizer(self.sizer)
        self.Centre()
        self.Show(True)
        #return self.window
        
    def _add_plot_tools(self, imgplot, token):
        """ Add LineInspectors, ImageIndexTool, and ZoomTool to the image plots. """
        
        imgplot.overlays.append(ZoomTool(component=imgplot, tool_mode="box",
                                           enable_wheel=False, always_on=False))
        imgplot.overlays.append(LineInspector(imgplot, axis="index_y", color="white",
            inspect_mode="indexed", write_metadata=True, is_listener=True))
        imgplot.overlays.append(LineInspector(imgplot, axis="index_x", color="white",
            inspect_mode="indexed", write_metadata=True, is_listener=True))
        imgplot.tools.append(ImageIndexTool(imgplot, token=token, 
            callback=self._index_callback, wheel_cb=self._wheel_callback))
        imgplot.tools.append(PanTool(imgplot))
        #imgplot.legend.visible = True
        
    def _add_timePlot_tools(self, imgplot, token):
        """ Add LineInspectors, ImageIndexTool, and ZoomTool to the image plots. """
        
        imgplot.overlays.append(ZoomTool(component=imgplot, tool_mode="box",
                                           enable_wheel=False, always_on=False))
        imgplot.overlays.append(LineInspector(imgplot, axis="index_y", color="white",
            inspect_mode="indexed", write_metadata=True, is_listener=True))
        imgplot.overlays.append(LineInspector(imgplot, axis="index_x", color="white",
            inspect_mode="indexed", write_metadata=True, is_listener=True))
        imgplot.tools.append(ImageIndexTool(imgplot, token=token, 
            callback=self._indexTime_callback, wheel_cb=self._wheel_callback))
        imgplot.tools.append(PanTool(imgplot))
        #imgplot.legend.visible = True

    def _update_model(self):
        self.colormap = self.cmap
        self.colorcube = (self.colormap.map_screen(self.vals) * 255).astype(num.uint8)
        
    def _update_images(self):
        """ Updates the image data in self.plotdata to correspond to the 
        slices given.
        """
        cube = self.colorcube
        pd = self.plotdata
        pdVoxel = self.plotdataVoxel
        pdVoxelFFT = self.plotdataVoxelFFT
        pdPC = self.plotdataPC
        # These are transposed because img_plot() expects its data to be in 
        # row-major order
        pd.set_data("yz", cube[:, self.slice_x, :])
        pd.set_data("xz", cube[:, :, self.slice_y])
        pd.set_data("xy", cube[self.slice_z,:,:])
        
        pdVoxel.set_data("TimeVoxel", self.Voxel)
        aTime = num.zeros(self.num_figs)
        aTime[:] = num.nan
        aTime[self.pos_t]= self.Voxel[self.pos_t]
        pdVoxel.set_data("time", aTime)

        pcTime = num.zeros(self.num_figs)
        pcTime[:] = num.nan
        pcTime[self.pos_t]= self.principalComponent[self.pos_t]
        pdPC.set_data("Principal Component",self.principalComponent)
        pdPC.set_data("time", pcTime)

        pdVoxelFFT.set_data("FreqVoxel",self.FFTVoxel)
        aFreq = num.zeros(self.frqs.shape)
        aFreq[:] = num.nan
        aFreq[list(self.maxtab[:,0])]= self.fftPeaks
        pdVoxelFFT.set_data("peaks", aFreq)

class run(wx.App):
    def __init__(self,  redirect=False,clargs=None):
        # call parent class initializer
        wx.App.__init__(self, redirect,clargs)
        
    def OnInit(self):
        self.frame = BrainFrame(parent=None,id=-1)
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        return True



