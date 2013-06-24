
import matplotlib
matplotlib.interactive( False )
matplotlib.use( 'WXAgg' )

from nifti import *
import numpy as num
import wx
import os, glob
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.figure import Figure
from mpl_toolkits.axes_grid import AxesGrid
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid.inset_locator import inset_axes
from mpl_toolkits.axes_grid.colorbar import colorbar

class BrainFrame(wx.Frame):
    def __init__(self, parent, id):
        wx.Frame.__init__(self,parent, id, 'Brain Player',size=(1280, 800))

        self.pnl1 = wx.Panel(self, -1)
        self.pnl1.SetBackgroundColour(wx.BLACK)
        self.pnl2 = wx.Panel(self, -1 )
        self.pnl3 = wx.Panel(self, -1 )
        self.pnl4 = wx.Panel(self, -1)
        self.pnl4.SetBackgroundColour(wx.BLACK)
        self.nb = wx.Notebook(self,-1)
        self.timer = wx.Timer(self, -1)
        self.num_figs = 10
        self.Data = 0
        self.subplot_num = 0
        self.fig = plt.figure()
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.volume_on = False
        self.previous_vol = 0
        
        self.init_data()
        self.init_panel()
        self.draw_plot()


    def init_panel(self):
        # initialize menubar
        toolbar = self.CreateToolBar()
        toolbar.AddLabelTool(wx.ID_EXIT, '', wx.Bitmap('../icons/icon_close.png'))
        toolbar.Realize()
        
        self.VAText = wx.StaticText(self.pnl3, -1, 'Voxel Analysis')
        self.VoxelAnalysisTypes = ['Time','Frequency']
        self.VoxelAnalysisBox = wx.ComboBox(self.pnl3,-1 , choices=self.VoxelAnalysisTypes, 
                        style=wx.CB_READONLY)
        self.VoxelAnalysisBox.SetName('Time')

        self.TextSliceX = wx.StaticText(self.pnl3, -1, 'X: ')
        self.TextSliceY = wx.StaticText(self.pnl3, -1, 'Y: ')
        self.TextSliceZ = wx.StaticText(self.pnl3, -1, 'Z: ')
        self.CtrlSliceX  = wx.SpinCtrl(self.pnl3, -1, '0', min=0, max=64)
        self.CtrlSliceY  = wx.SpinCtrl(self.pnl3, -1, '0', min=0, max=64)
        self.CtrlSliceZ  = wx.SpinCtrl(self.pnl3, -1, '0', min=0, max=36)

        # create track counter
        self.trackCounter = wx.StaticText(self.pnl2, label=" 0 / 0")
        self.Bind(wx.EVT_TOOL, self.OnExit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_TIMER, self.OnTimer)

        # initialize slider
        # default id = -1 is used, initial value = 0, min value = 0, max value = number of figures
        self.slider1 = wx.Slider(self.pnl2, -1, 0, 0, self.num_figs)
        self.slider2 = wx.Slider(self.pnl2, -1, 0, 0, 100, size=(120, -1))
        self.pos_slider1 = self.slider1.GetValue()
        self.pos_slider2 = self.slider2.GetValue()

        # initialize buttons
        self.pause = wx.BitmapButton(self.pnl2, -1, wx.Bitmap('../icons/stock-media-pause.png'))
        self.play  = wx.BitmapButton(self.pnl2, -1, wx.Bitmap('../icons/stock-media-play.png'))
        self.prev  = wx.BitmapButton(self.pnl2, -1, wx.Bitmap('../icons/stock-media-prev.png'))
        self.next  = wx.BitmapButton(self.pnl2, -1, wx.Bitmap('../icons/stock-media-next.png'))
        self.volume = wx.BitmapButton(self.pnl2, -1, wx.Bitmap('../icons/stock-volume.png'))
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        self.topsizer= wx.BoxSizer(wx.HORIZONTAL) # left controls, right image output
        # slider controls controls
        ctrlsizer= wx.BoxSizer(wx.VERTICAL)
        
        ctrlsizer.Add(self.VAText, 0,wx.ALIGN_CENTER, 5)
        ctrlsizer.AddSpacer(5)
        ctrlsizer.Add(self.VoxelAnalysisBox,0,wx.ALIGN_CENTER)
        ctrlsizer.AddSpacer(20)
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
        
        self.topsizer.Add(self.pnl3, 0, wx.ALL, 10)
        self.topsizer.Add(self.nb, 2, wx.ALL)  

        hbox1.Add(self.slider1, 1, wx.ALL|wx.EXPAND, 20)
        hbox1.Add(self.trackCounter, 0, wx.ALL|wx.CENTER, 20)
        hbox2.Add(self.pause,flag=wx.LEFT,border=10)
        hbox2.Add(self.play, flag=wx.RIGHT, border=10)
        hbox2.Add(self.prev, flag=wx.LEFT, border=10)
        hbox2.Add(self.next)
        hbox2.Add((150, -1), 1, flag=wx.EXPAND | wx.ALIGN_RIGHT)
        hbox2.Add(self.volume, flag=wx.ALIGN_RIGHT)
        hbox2.Add(self.slider2, flag=wx.ALIGN_RIGHT | wx.TOP | wx.LEFT, border=10)

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

        # respond to the click of the button
        self.CtrlSliceX.Bind(wx.EVT_SPINCTRL, self.move2SliceX)
        self.CtrlSliceX.Bind(wx.EVT_SPINCTRL, self.move2SliceX)
        self.CtrlSliceZ.Bind(wx.EVT_SPINCTRL, self.move2SliceZ)
        self.CtrlSliceY.Bind(wx.EVT_SPINCTRL, self.move2SliceY)
        self.VoxelAnalysisBox.Bind(wx.EVT_COMBOBOX, self.VoxelAnalysisType)
        self.prev.Bind(wx.EVT_BUTTON, self.prevClick)
        self.next.Bind(wx.EVT_BUTTON, self.nextClick)
        self.play.Bind(wx.EVT_BUTTON, self.playClick)
        self.pause.Bind(wx.EVT_BUTTON, self.pauseClick)
        self.volume.Bind(wx.EVT_BUTTON, self.volumeClick)

        self.Show(True)
    
    def init_data(self):

        # Generate some data to plot:
        path = '../data/s03_epi_snr01_xxx/'
        print "Loading brain data from " + path
        print "..."
        if os.path.exists(path):
            nii_files = sorted (glob.glob( os.path.join(path, '*.img')), key = str.lower)
            nim = NiftiImage(nii_files[0])
            self.num_figs = len(nii_files) #time axis
            (self.len_z,self.len_x,self.len_y) = num.shape(nim.data) # 3D axis
            self.Data  = num.zeros((self.num_figs,self.len_z,self.len_x,self.len_y)) # Data allocation of memory

            for i in range(self.num_figs):
                nim = NiftiImage(nii_files[i])
                self.Data [i,:,:,:] = nim.data #filling the data with every frame
                print "Loading: " + nii_files[i]

            print "Brain data loaded..."

        else:
            print '\nNo Brain data my friend...\n'

        
        self.pos_t = 0
        self.pos_x = int(self.len_x/2)
        self.pos_y = int(self.len_y/2)
        self.pos_z = int(self.len_z/2)

    
    def init_plot(self):
        """Draw data."""
        plt.jet()
        """(frames,z,x,y) = num.shape(self.Data) # 4D axis
        for t in range(frames):
            filename = "Images/Im_" + str(t) + ".png"
            for self.n in range(36):
                self.subplot = self.fig.add_subplot( 6,6,self.n+1)
                self.subplot.imshow(self.Data[t,self.n,:,:], interpolation='nearest')
            self.fig.savefig(filename)"""
        vmax = self.Data[0].max()
        vmin = self.Data[0].min()                
        grid = AxesGrid(self.fig, 111, # similar to subplot(111) 
        nrows_ncols = (4, 7),axes_pad = 0.2,share_all=True,
        cbar_location = "top",cbar_mode="single")
        for n in range(self.brainZ):
            im = grid[n].imshow(self.Data[0][n,:,:], vmin=vmin, vmax=vmax,interpolation="nearest")
        
        grid.cbar_axes[0].colorbar(im)
        for cax in grid.cbar_axes:
            cax.toggle_label(False)
        # This affects all axes as share_all = True.
        grid.axes_llc.set_xticks([0, 30, 60])
        grid.axes_llc.set_yticks([0, 30, 60])
    
        self.canvas.draw()

    def draw_plot(self):
        """Draw data."""
        
        plt.jet()

        self.fig.canvas.mpl_connect('button_press_event', self.onclick)
        self.fig.canvas.mpl_connect('axes_enter_event', self.enter_axes)

        vmax = self.Data[self.pos_t].max()
        vmin = self.Data[self.pos_t].min()                
        grid = AxesGrid(self.fig, 111, # similar to subplot(111) 
        nrows_ncols = (2, 2),axes_pad = 0.2,share_all=True,
        cbar_location = "top",cbar_mode="single")
        for n in range(3):
            ax = self.fig.add_subplot(2,2,i+1)
            #im = grid[n].imshow(self.Data[self.pos_t][n,:,:], vmin=vmin, vmax=vmax,interpolation="nearest")
        
        grid.cbar_axes[0].colorbar(im)
        for cax in grid.cbar_axes:
            cax.toggle_label(False)
        # This affects all axes as share_all = True.
        grid.axes_llc.set_xticks([0, 30, 60])
        grid.axes_llc.set_yticks([0, 30, 60])
    
        self.canvas.draw()


        """plt.jet()
        self.fig.canvas.mpl_connect('button_press_event', self.onclick)
        self.fig.canvas.mpl_connect('axes_enter_event', self.enter_axes)
        #fig = plt.figure()
        #self.canvas = FigureCanvasWxAgg(self, -1,fig)
        vmax = self.Data[self.pos_t].max()
        vmin = self.Data[self.pos_t].min()
        
        m1 = self.Data[self.pos_t,self.pos_z,:,:]
        m2 = self.Data[self.pos_t,::-1,self.pos_y,:]
        m3 = self.Data[self.pos_t,::-1,:,self.pos_x]
        
        for i, m in enumerate([m1, m2, m3]):
           ax = self.fig.add_subplot(2,2,i+1)
           axins = inset_axes(ax,width="5%",  height="100%", loc=3,bbox_to_anchor=(1.05, 0., 1, 1),bbox_transform=ax.transAxes,
                              borderpad=0)
           im = ax.imshow(m, vmin=vmin, vmax=vmax,interpolation='nearest')
           #im = ax.imshow(m, vmin=vmin, vmax=vmax)
           colorbar(im, cax=axins) #ticks=["lo", "med", "hi"]
            
        ax = self.fig.add_subplot(224)
        ax.plot(self.Data[:,self.pos_z,self.pos_y,self.pos_x],color='black') #t axis"""
                     
       
        self.canvas.draw()


    def VoxelAnalysisType(self,event):
        item = event.GetSelection()
        if (self.FeatureSelectionTypes[item] == 'Time'): 
            print 'Time'
        elif (self.FeatureSelectionTypes[item] == 'Frequency'): 
            print 'Frequency'
        
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
        self.draw_plot()
    
    def move2SliceZ(self,event):
        self.slice_z = self.CtrlSliceZ.GetValue()
        self.draw_plot()
    
    def move2SliceY(self,event):
        self.slice_y = self.CtrlSliceY.GetValue()
        self.draw_plot()
    
    def slider2Update(self, event):
        volume = float(self.slider2.GetValue())/100.0 #to set the volume in range [0 1]
        self.osc.send_volume(volume)
        
    def slider1Update(self, event):
        # get the slider position
        self.pos_t = self.slider1.GetValue()        
        self.draw_plot()
        
        
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

    def playClick(self, event):
        # update clock every 2 seconds (2000ms)
        self.timer.Start(2000)  
        self.slider1Update(event)
        
    def pauseClick(self, event):
        self.timer.Stop() 
            
    def OnExit(self, event):
        self.timer.Stop()
        self.Close()
        return 0

class run(wx.App):
    def __init__(self,  redirect=False,clargs=None):
        # call parent class initializer
        wx.App.__init__(self, redirect,clargs)
        
    def OnInit(self):
        self.frame = BrainFrame(parent=None,id=-1)
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        return True



