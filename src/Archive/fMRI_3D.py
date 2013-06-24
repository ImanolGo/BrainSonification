
import osc_send as sn
import os
# Standard library imports
import numpy as num
import wx
import cPickle as pickle


class MyFrame(wx.Frame):
    def __init__(self, parent, id):
        self.Window = wx.Frame.__init__(self,parent, id, 'fMRI 3D Player',size=(1280, 775))
        self.pnl1 = wx.Panel(self, -1)
        self.pnl1.SetBackgroundColour(wx.BLACK)
        self.pnl2 = wx.Panel(self, -1 )
        self.pnl3 = wx.Panel(self, -1 )
        self.pnl4 = wx.Panel(self, -1)
        self.pnl4.SetBackgroundColour(wx.BLACK)
        self.nb = wx.Notebook(self,-1)
        self.timer = wx.Timer(self, -1)
        self.n= 50 #best voxels
        self.volume_on = False
        self.previous_vol = 0
        self.portNum = 9001
        self.osc = sn.osc_send(self.portNum)
        self.volumeLevel = 0.0
        self.num_figs = 10 
        
        self.voxels = []
        self.CoordinatesSemisphere = []
        self.stimuli = []
    
        #########################################
        
        self.init_panel()
    
    def init_panel(self):


        self.TextTask = wx.StaticText(self.pnl3, -1, 'Idle')
        self.bestVoxelsText = wx.StaticText(self.pnl3, -1, '# Voxels:')
        self.bestVoxelsCtrl  = wx.SpinCtrl(self.pnl3, -1, '50', min=1, max=1000)
        self.n = self.bestVoxelsCtrl.GetValue()
        self.subjectText = wx.StaticText(self.pnl3, -1, 'Subject:')
        self.subjects = []
        
        for name in os.listdir("../data/"): 
            ind = name.find('_')
            subject_name = name[0:ind]
            #print subject_name
            self.subjects.append(subject_name)
        
        self.subjectBox = wx.ComboBox(self.pnl3,-1 , choices=self.subjects,style=wx.CB_READONLY)
        
        # create track counter
        self.trackCounter = wx.StaticText(self.pnl2, label=" 0 / 0")
        self.Bind(wx.EVT_TIMER, self.OnTimer)

        # initialize slider
        # default id = -1 is used, initial value = 0, min value = 0, max value = number of figures
        self.MaxSlider3 = 2000
        self.MinSlider3 = 125
        self.slider1 = wx.Slider(self.pnl2, -1, 0, 0, self.num_figs)
        self.pos_t = self.slider1.GetValue() 
        self.slider2 = wx.Slider(self.pnl2, -1, 0, 0, 100, size=(120, -1))
        self.slider3 = wx.Slider(self.pnl2, -1, (self.MaxSlider3 - self.MinSlider3), self.MinSlider3, self.MaxSlider3, size=(120, -1))
        self.pos_slider1 = self.slider1.GetValue()
        self.pos_slider2 = self.slider2.GetValue()
        self.pos_slider3 = self.slider3.GetValue()
        self.clkFreq = (self.MaxSlider3 + self.MinSlider3) - self.pos_slider3
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
        ctrlsizer.AddSpacer(10)
        ctrlsizer.Add(self.bestVoxelsText, 0, wx.ALIGN_CENTER, 5)
        ctrlsizer.AddSpacer(5)
        ctrlsizer.Add(self.bestVoxelsCtrl,0,wx.ALIGN_CENTER)
        ctrlsizer.AddSpacer(10)
        ctrlsizer.Add(self.subjectText,0,wx.ALIGN_CENTER)
        ctrlsizer.AddSpacer(5)
        ctrlsizer.Add(self.subjectBox,0,wx.ALIGN_CENTER)
        ctrlsizer.AddSpacer(15)
        ctrlsizer.Add(self.TextTask, 0, wx.ALIGN_CENTER, 5)
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
        self.bestVoxelsCtrl.Bind(wx.EVT_SPINCTRL, self.VoxelSelect) 
        self.subjectBox.Bind(wx.EVT_COMBOBOX, self.subjectBoxChoose)
        self.prev.Bind(wx.EVT_BUTTON, self.prevClick)
        self.next.Bind(wx.EVT_BUTTON, self.nextClick)
        self.play.Bind(wx.EVT_BUTTON, self.playClick)
        self.pause.Bind(wx.EVT_BUTTON, self.pauseClick)
        self.volume.Bind(wx.EVT_BUTTON, self.volumeClick)
        
    def writeTaskText(self):
        
        if(len(self.stimuli)>0):
            stim = self.stimuli[self.pos_t]
            if(stim>0):
                strStim = "Stimulus %d" % (stim)
                self.TextTask.SetLabel(strStim)
            else:
                self.TextTask.SetLabel("Idle")
    
    def subjectBoxChoose(self,event):
        item = event.GetSelection()
        self.sSubjectBoxChoose = self.subjects[item]
        self.init_data(self.subjects[item])
        self.slider1Update(event)
    
    def VoxelSelect(self,event):
        self.n = self.bestVoxelsCtrl.GetValue()  
    
    def OnTimer(self, event):
        # Set the slider position
        if(self.slider1.GetValue()<self.num_figs-1):  
            self.slider1.SetValue(self.slider1.GetValue()+1)
            self.slider1Update(event)
        else:
            self.timer.Stop() 
            self.osc.send_best_voxels(num.zeros(self.n))
            
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
            self.osc.send_best_voxels(num.zeros(self.n))
        
    def pauseClick(self, event):
        self.timer.Stop()
        self.osc.send_best_voxels(num.zeros(self.n))
             
    def OnExit(self, event):
        self.timer.Stop()
        self.Close()

    def init_data(self, subject):
        # Generate some data to plot:
        
        try:
            fi = open("../data/" +subject + "_hemisphere.dat", 'r')
        except IOError:
            #No such file
            print "File " + subject + "_hemisphere.dat not found" 
            self.voxels = []
            self.CoordinatesSemisphere = []
            self.stimuli = []
        else:
            self.voxels = pickle.load(fi)
            self.CoordinatesSemisphere = pickle.load(fi)
            self.stimuli = pickle.load(fi)
            fi.close()
            [numVoxels,self.num_figs] = num.shape(self.voxels)
            
            self.slider1.SetRange(0,self.num_figs) #set the new range of slider
            self.osc.send_coordinates(self.CoordinatesSemisphere[0:self.n,:])
            
        
    def slider2Update(self, event):
        self.volumeLevel = float(self.slider2.GetValue())/100.0 #to set the volume in range [0 1]
        self.osc.send_volume(self.volumeLevel)
        
    def slider3Update(self, event):
        pos_slider3 = self.slider3.GetValue()
        self.clkFreq = (self.MaxSlider3 + self.MinSlider3) - pos_slider3
        fSpeed = 1000.0/self.clkFreq
        strSpeed = "%.2f Frames/s" % fSpeed
        self.TextSpeed.SetLabel(strSpeed)
        self.timer.Start(self.clkFreq)
           
    def slider1Update(self, event):
        # get the slider position
        self.pos_t = self.slider1.GetValue() 
        self.trackCounter.SetLabel(" " + str(self.pos_t) + " / " + str(self.num_figs))      
        self.writeTaskText()
        self.osc.send_best_voxels(self.voxels[0:self.n, self.pos_t])
        self.osc.send_stimulus(self.stimuli[self.pos_t])
          
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
    
class run(wx.App):
    def __init__(self,  redirect=False,clargs=None):
        # call parent class initializer
        wx.App.__init__(self, redirect,clargs)
        
    def OnInit(self):
        self.frame = MyFrame(parent=None,id=-1)
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        return True
    