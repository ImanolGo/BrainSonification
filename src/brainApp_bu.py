
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

class BrainFrame(wx.Frame):
    def __init__(self, parent, id):
        wx.Frame.__init__(self,parent, id, 'fMRI Player',size=(600, 600))
        self.pnl1 = wx.Panel(self, -1)
        self.pnl1.SetBackgroundColour(wx.BLACK)
        self.pnl2 = wx.Panel(self, -1 )
        self.pos1 = 0;
        self.brainX = 0
        self.brainY = 0
        self.brainZ = 0

        self.fig = plt.figure()
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        #self.canvas.SetScrollbar(wx.HORIZONTAL, 0, 5,self.scroll_range)
        self.init_data()
        self.init_panel()
        self.init_plot()

    def init_panel(self):
        # initialize menubar
        self.menubar = wx.MenuBar()
        file = wx.Menu()
        play = wx.Menu()
        view = wx.Menu()
        tools = wx.Menu()
        favorites = wx.Menu()
        help = wx.Menu()

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

        hbox1.Add(self.slider1, 1)
        hbox2.Add(self.pause)
        hbox2.Add(self.play, flag=wx.RIGHT, border=5)
        hbox2.Add(self.prev, flag=wx.LEFT, border=5)
        hbox2.Add(self.next)
        hbox2.Add((150, -1), 1, flag=wx.EXPAND | wx.ALIGN_RIGHT)
        hbox2.Add(self.volume, flag=wx.ALIGN_RIGHT)
        hbox2.Add(self.slider2, flag=wx.ALIGN_RIGHT | wx.TOP | wx.LEFT, border=5)

        vbox.Add(hbox1, 1, wx.EXPAND | wx.BOTTOM, 10)
        vbox.Add(hbox2, 1, wx.EXPAND)
        self.pnl2.SetSizer(vbox)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, flag=wx.EXPAND)
        sizer.Add(self.pnl2, flag=wx.EXPAND | wx.BOTTOM | wx.TOP, border=10)
   
        self.SetSizer(sizer)
        self.Centre()
        self.slider1.Bind(wx.EVT_SLIDER, self.slider1Update)
        #self.slider2.Bind(wx.EVT_SLIDER, self.slider2Update)
        # respond to the click of the button
        self.prev.Bind(wx.EVT_BUTTON, self.prevClick)
        self.next.Bind(wx.EVT_BUTTON, self.nextClick)
    
    def init_data(self):
        # Generate some data to plot:
        path = '../data/s03_epi_snr01_xxx/'
        print "Loading brain data from " + path
        print "..."
        if os.path.exists(path):
            nii_files = sorted (glob.glob( os.path.join(path, '*.img')), key = str.lower)
            nim = NiftiImage(nii_files[0])
            self.num_figs = len(nii_files) #time axis
            (self.brainZ,self.brainX,self.brainY) = num.shape(nim.data) # 3D axis
            self.Data  = num.zeros((self.num_figs,self.brainZ,self.brainX,self.brainY)) # Data allocation of memory
            print self.brainZ
            print self.brainX
            print self.brainY
            print self.num_figs

            for i in range(self.num_figs):
                nim = NiftiImage(nii_files[i])
                self.Data [i,:,:,:] = nim.data #filling the data with every frame
                print "Loading: " + nii_files[i]

            print "Brain data loaded..."

        else:
            print '\nNo Brain data my friend...\n'

        

    
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
        vmax = self.Data[self.pos1].max()
        vmin = self.Data[self.pos1].min()                
        grid = AxesGrid(self.fig, 111, # similar to subplot(111) 
        nrows_ncols = (4, 7),axes_pad = 0.2,share_all=True,
        cbar_location = "top",cbar_mode="single")
        for n in range(self.brainZ):
            im = grid[n].imshow(self.Data[self.pos1][n,:,:], vmin=vmin, vmax=vmax,interpolation="nearest")
        
        grid.cbar_axes[0].colorbar(im)
        for cax in grid.cbar_axes:
            cax.toggle_label(False)
        # This affects all axes as share_all = True.
        grid.axes_llc.set_xticks([0, 30, 60])
        grid.axes_llc.set_yticks([0, 30, 60])
       
        self.canvas.draw()

    def slider1Update(self, event):
        # get the slider position
        self.pos1 = self.slider1.GetValue()
        #print self.pos1
        # set the gauge position
        self.draw_plot()

    def prevClick(self, event):
        # Set the slider position
        if(self.slider1.GetValue()>0):
            self.slider1.SetValue(self.slider1.GetValue()-1)
            self.pos1 = self.slider1.GetValue()
            #print "prev_click: ", self.pos1
            self.draw_plot()

    def nextClick(self, event):
        # Set the slider position
        if(self.slider1.GetValue()<self.num_figs):
            self.slider1.SetValue(self.slider1.GetValue()+1)
            self.pos1 = self.slider1.GetValue()
            #print "next_click: ", self.pos1
            self.draw_plot()

class App(wx.App):
    def __init__(self,  redirect=False,clargs=None):
        self.filename = clargs or [] # store reference to args
        # call parent class initializer
        wx.App.__init__(self, redirect,clargs)
        
    def OnInit(self):
        self.frame = BrainFrame(parent=None,id=-1)
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        return True



