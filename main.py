import customtkinter
import tkintermapview
from tkintermapview import TkinterMapView
import tkinter as tk
import gc
import math
import datetime
import os
from PIL import Image, ImageTk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
import time
from threading import *

#customtkinter.set_default_color_theme("blue")

class CRunInfos(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.laps=[]

        r=0
        self.label_runstart=customtkinter.CTkLabel(self,text="Date : ",anchor="w", justify=tk.LEFT)
        self.label_runstart.grid(row=r, column=0, padx=4,sticky=tk.W)
        self.val_runstart=customtkinter.CTkLabel(self,text="",anchor="w", justify=tk.LEFT)
        self.val_runstart.grid(row=r, column=1, padx=4,sticky=tk.W)
        r+=1

        self.label_rundur=customtkinter.CTkLabel(self,text="Duration : ",anchor="w", justify=tk.LEFT)
        self.label_rundur.grid(row=r, column=0, padx=4,sticky=tk.W)
        self.val_rundur=customtkinter.CTkLabel(self,text="",anchor="w", justify=tk.LEFT)
        self.val_rundur.grid(row=r, column=1, padx=4,sticky=tk.W)
        r+=1

        self.textmax_label=customtkinter.CTkLabel(self, text="Text max:", justify=tk.LEFT)
        self.textmax_label.grid(pady=(0, 0), padx=4, row=r,column=0,sticky="W")
        self.textmax_val=customtkinter.CTkLabel(self, text="°C", justify=tk.LEFT)
        self.textmax_val.grid(pady=(0, 0), padx=4, row=r, column=1,sticky="W")
        r+=1
        
        self.label_nblaps=customtkinter.CTkLabel(self,text="Nb laps : ",anchor="w", justify=tk.LEFT)
        self.label_nblaps.grid(row=r, column=0, padx=4,sticky=tk.W)
        self.val_nblaps=customtkinter.CTkLabel(self,text="",anchor="w", justify=tk.LEFT)
        self.val_nblaps.grid(row=r, column=1, padx=4,sticky=tk.W)
        r+=1
        

    
class CLapsFrame(customtkinter.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.laps=[]
        
    def ms2HMS(self,ms):
        ms = ms * 10
        h = math.floor((ms / 1000.0) / 3600.0)
        m = math.floor(((ms / 1000.0) / 60.0) % 60.0)
        s = math.floor((ms / 1000.0) % 60.0)
        r = ms%1000
        return "%.2d"%h + ":" + "%.2d"%m + ":" + "%.2d"%s+"."+"%.3d"%r
    
    def addlaps(self,laptimes,lapdistances):
        i=0
        eval_link = lambda x: (lambda p: self.extractlap(x))
        for laptime in laptimes:
            label = customtkinter.CTkLabel(self,text=str(i+1)+": "+self.ms2HMS(laptime)+" ("+str(round(lapdistances[i],1))+" Kms)")
            label.grid(row=i, column=0, padx=4)
            label.bind("<Button-1>", eval_link(i))
            self.laps.append(label)
            i+=1

    def clearlaps(self):
        for lap in self.laps:
            lap.destroy()
        self.laps=[]

    def extractlap(self,i):
        l=0
        startindex=-1
        app.carpath=[]
        maxlapspeed=0
        for line in app.out:
            chan=app.get_chan(10,line)
            if chan["lap"]==i:
                if startindex==-1:startindex=l
                app.carpath.append((chan["decoded"][1],chan["decoded"][0]))
                curspeed=app.get_chan(64,line)["decoded"]
                if maxlapspeed < curspeed:
                    maxlapspeed=curspeed
            l+=1
        if(len(app.carpath)>0):
            app.map_widget.delete_all_path()
            app.colorize_path(maxlapspeed,startindex)
            
        for label in self.laps:
            label.configure(text_color=("#000000","#FFFFFF"))
        if i < len(self.laps):
            self.laps[i].configure(text_color=("#FF0000"))
                
            
            

class App(customtkinter.CTk):

    APP_NAME = "PyRS-REPLAY"
    WIDTH = 1280
    HEIGHT = 720
    #liste des canaux (Octet du canal : nombre d'octets des datas)
    CL = {
		0x01 : 7,
		0x02 : 9,
		0x06 : 4,
		0x08 : 4,
		0x09 : 3,
		0x0a : 12,
		0x0e : 3,
		0x0f : 3,
		0x10 : 3,
		0x11 : 3,
		0x12 : 3,
		0x37 : 8,
		0x39 : 8,
		0x3f : 1,
		0x40 : 3,
		0x48 : 3,
		0x4a : 3,
		0x4e : 4,
		0x4f : 2,
		0x5d : 3,
		0x5e : 4,
		0x1b : 2,
		0x19 : 2,
		0x1a : 2,
		0x18 : 2,
		0x17 : 2
	}

    out=[]
    
    def init_vars(self):
        self.curindex=0
        self.max_speed=0
        self.max_glat=0
        self.max_glon=0
        self.max_rpm=0
        self.max_Text=0
        self.max_Tin=0
        self.max_power=0
        self.carpath=[]
        self.out=[]
        self.run_datas=[]
        self.RUN_START_LATITUDE=None
        self.RUN_START_LONGITUDE=None
        self.START_DISTANCE=0.10
        self.m_bInStartProximity=False
        self.ANGLE_MARGIN=45.0
        self.FLT_MIN=0.0
        self.m_fDirectionAngle=self.FLT_MIN
        self.lapstarttime=0
        self.lapstartindex=0
        self.nblaps=0
        self.EARTH_RADIUS=6371.0
        self.besttime=float('inf')
        self.map_widget.delete_all_path()
        self.map_widget.delete_all_marker()
        self.lapsframe.clearlaps()
        self.vmax_val.configure(text=" Kmh")
        self.glatmax_val.configure(" G")
        self.glonmax_val.configure(" G")
        self.rpmmax_val.configure(" Tr/Mn")
        self.tinmax_val.configure(" °C")
        self.powermax_val.configure(text="")
        self.minlat=self.minlng=float('inf')
        self.maxlat=self.maxlng=-float('inf')
        self.RUN_START_TIME=0
        self.RUN_END_TIME=0
        self.runinfosframe.textmax_val.configure(" °C")
        self.isplaying=False
        self.marker_list = []
        self.stopevent = Event()
        self.pauseevent = Event()
        self.lastlap=-1

        
    def set_custom_start(self,coords):
            self.RUN_START_LATITUDE=coords[0]
            self.RUN_START_LONGITUDE=coords[1]
            self.lapsframe.clearlaps()
            self.nblaps=0
            self.getlaptime()
            self.lapsframe.addlaps(self.laptimes,self.lapdistances)
            self.chronomarker.set_position(coords[0], coords[1])
            self.runinfosframe.val_nblaps.configure(text=self.nblaps)
            
    def update_carpos(self,i):
        l=self.out[int(i)]
        chan=self.get_chan(10,l)
        v=chan["decoded"]
        speed=int(self.get_chan(64,l)["decoded"])
        gf=self.get_chan(8,l)["decoded"]
        
        self.carmarker.set_position(v[1],v[0])
        self.carmarker.set_text(str(speed)+" Kmh"+
                                "\n"+str(self.get_chan(23,l)["decoded"])+" Hp"+
                                "\nGear : "+str(self.get_chan(27,l)["decoded"])+
                                "\nThrottle :"+str(int(round(self.get_chan(74,l)["decoded"],1)))+"%"+
                                "\nBreak : "+str(int(round(self.get_chan(94,l)["decoded"],1)))+"%"
                                )
        
        #self.map_widget.update()
        self.slider.set(i)
        self.curtimelabel.configure(text=self.lapsframe.ms2HMS(self.curindex*10))
        curlap=chan["lap"]
        if curlap != self.lastlap:
            self.pauseevent.set()
            self.lapsframe.extractlap(curlap)
            self.lastlap=curlap
            self.pauseevent.clear()

        
        #graphs
        datas=[speed]
        datag=pd.DataFrame({'Glat': [gf[0]], 'Glon': [gf[1]] })

        self.axvrt.clear()
        self.axvrt.plot(i,datas,linestyle='', marker='p', markersize=8, color="red")
        self.figvmax.canvas.draw_idle()
        
        self.axgfrt.clear()
        self.axgfrt.plot('Glat', 'Glon', data=datag ,linestyle='', marker='o', markersize=8, color="red")
        self.figgf.canvas.draw_idle()
        
    def slider_event(self,val):
        if val >= len(self.out) or val<0 or self.isplaying==True :return
        self.curindex=int(val)
        self.update_carpos(self.curindex)

    def step_forward(self):
        if(self.isplaying==True):return
        self.update_carpos(self.curindex+1)
        self.curindex=self.curindex+1
    
    def step_backward(self):
        if(self.isplaying==True):return
        self.update_carpos(self.curindex-1)
        self.curindex=self.curindex-1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title(App.APP_NAME)
        self.geometry(str(App.WIDTH) + "x" + str(App.HEIGHT))
        self.minsize(App.WIDTH, App.HEIGHT)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind("<Command-q>", self.on_closing)
        self.bind("<Command-w>", self.on_closing)
        self.createcommand('tk::mac::Quit', self.on_closing)
        
        # ============ create two CTkFrames ============

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=2)
        self.grid_columnconfigure(2, weight=0)
        self.grid_rowconfigure(0, weight=1)

        self.frame_left = customtkinter.CTkFrame(master=self, width=150, corner_radius=0, fg_color=None)
        self.frame_left.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

        self.frame_right = customtkinter.CTkFrame(master=self, corner_radius=0,width=500)
        self.frame_right.grid(row=0, column=1, rowspan=1, pady=0, padx=0, sticky="nsew")

        self.frame_runinfo = customtkinter.CTkFrame(master=self,corner_radius=0)
        self.frame_runinfo.grid(row=0, column=2, pady=0, padx=0, sticky="nsew")

        # ============ frame_left ============

        self.frame_left.grid_rowconfigure(8, weight=1)

        self.map_label = customtkinter.CTkLabel(self.frame_left, text="Tile Server:", anchor="w")
        self.map_label.grid(row=0, column=0, padx=(20, 20), pady=(12, 0))
        self.map_option_menu = customtkinter.CTkOptionMenu(self.frame_left, values=["OpenStreetMap", "Google normal", "Google satellite"],command=self.change_map)
        self.map_option_menu.grid(row=1, column=0, padx=(20, 20), pady=(12, 0))

        self.appearance_mode_label = customtkinter.CTkLabel(self.frame_left, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=2, column=0, padx=(20, 20), pady=(20, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.frame_left, values=["Light", "Dark", "System"],command=self.change_appearance_mode)
        self.appearance_mode_optionemenu.grid(row=3, column=0, padx=(20, 20), pady=(10, 20))

        # ============ frame_right ============

        self.frame_right.grid_rowconfigure(1, weight=1)
        self.frame_right.grid_rowconfigure(0, weight=0)
        self.frame_right.grid_columnconfigure(0, weight=0)
        self.frame_right.grid_columnconfigure(1, weight=1)
        self.frame_right.grid_columnconfigure(2, weight=0)

        self.tracklocation = customtkinter.CTkLabel(master=self.frame_right,text="Paris")
        self.tracklocation.grid(row=0, column=0, sticky="we", padx=(12, 0), pady=12,columnspan=3)

        #self.button_5 = customtkinter.CTkButton(master=self.frame_right,text="Search",width=90,command=self.search_event)
        #self.button_5.grid(row=0, column=2, sticky="ew", padx=(12, 0), pady=12)

        self.map_widget = TkinterMapView(self.frame_right, corner_radius=0)
        self.map_widget.grid(row=1, column=0, columnspan=3, sticky="nswe", padx=(0, 0), pady=(0, 0))

        self.psframe=customtkinter.CTkFrame(master=self.frame_right,corner_radius=0, fg_color=None)
        self.psframe.grid(row=2, column=0, sticky="nsew",columnspan=3)
        self.psframe.grid_columnconfigure(0, weight=1)
        self.psframe.grid_columnconfigure(2, weight=1)
        
        self.btplay=customtkinter.CTkButton(master=self.psframe,text="play",command=self.start_render)
        self.btplay.grid(row=0, column=0, sticky="ew", padx=(0, 12), pady=0)
        self.curtimelabel = customtkinter.CTkLabel(self.psframe, text="curindex")
        self.curtimelabel.grid(row=0, column=1, padx=(20, 20), pady=(20, 0))
        self.btstop=customtkinter.CTkButton(master=self.psframe,text="stop",command=self.stop_render)
        self.btstop.grid(row=0, column=2, sticky="ew", padx=(0, 12), pady=0)

        
        self.btmoins=customtkinter.CTkButton(master=self.frame_right,text="-",command=self.step_backward)
        self.btmoins.grid(row=3, column=0, sticky="we", padx=(0, 12), pady=0)
        self.slider = customtkinter.CTkSlider(master=self.frame_right, from_=0, to=100, command=self.slider_event)
        self.slider.grid(row=3, column=1, sticky="we", padx=0, pady=12)
        self.slider.set(0)
        self.btplus=customtkinter.CTkButton(master=self.frame_right,text="+",command=self.step_forward)
        self.btplus.grid(row=3, column=2, sticky="we", padx=(12,0), pady=12)

        
        #frame runinfos
        self.frame_runinfo.grid_columnconfigure(0, weight=0)
        self.frame_runinfo.grid_columnconfigure(1, weight=1)
        
        self.frame_runinfo.grid_rowconfigure(2, weight=1)
        
        self.button_6 = customtkinter.CTkButton(master=self.frame_runinfo,text="Open RUN",width=90,anchor="center",command=self.open_run)
        self.button_6.grid(row=0, column=0, sticky="we", pady=(12, 0), padx=(20, 20),columnspan=2)

        col=1
        
        self.runinfosframe=CRunInfos(master=self.frame_runinfo)
        self.runinfosframe.grid(row=col, column=0, padx=10, pady=10,columnspan =2,sticky='nsew')
        col+=1
        
        self.lapsframe = CLapsFrame(master=self.frame_runinfo, width=300,height=100)
        self.lapsframe.grid(row=col, column=0, padx=10, pady=10,columnspan=2,sticky='nsew')  
        col+=1
        
        self.vmax_label=customtkinter.CTkLabel(self.frame_runinfo, text="V max:")
        self.vmax_label.grid(pady=(0, 0), padx=(10, 10), row=col,column=0,sticky="W")
        self.vmax_val=customtkinter.CTkLabel(self.frame_runinfo, text="Kmh")
        self.vmax_val.grid(pady=(0, 0), padx=(10, 10), row=col, column=1,sticky="W")
        col+=1

        self.figvmax = Figure(figsize=(2,2),dpi=50)
        self.axvmax = self.figvmax.add_subplot(111,label = "V")
        self.axvrt = self.figvmax.add_subplot(111,label = "Vrt",sharex=self.axvmax, sharey=self.axvmax)
        self.axvrt.set_facecolor("#ffffff00")
        self.canvasvmax = FigureCanvasTkAgg(self.figvmax, self.frame_runinfo)
        self.canvasvmax.get_tk_widget().grid(pady=(0, 0), padx=(10, 10), row=col, column=0,sticky="NSEW",columnspan=2)
        col+=1

        
        self.glatmax_label=customtkinter.CTkLabel(self.frame_runinfo, text="GLat max:")
        self.glatmax_label.grid(pady=(0, 0), padx=(10, 10), row=col,column=0,sticky="W")
        self.glatmax_val=customtkinter.CTkLabel(self.frame_runinfo, text="G")
        self.glatmax_val.grid(pady=(0, 0), padx=(10, 10), row=col, column=1,sticky="W")
        col+=1
        
        
        self.glonmax_label=customtkinter.CTkLabel(self.frame_runinfo, text="GLng max:")
        self.glonmax_label.grid(pady=(0, 0), padx=(10, 10), row=col,column=0,sticky="W")
        self.glonmax_val=customtkinter.CTkLabel(self.frame_runinfo, text="G")
        self.glonmax_val.grid(pady=(0, 0), padx=(10, 10), row=col, column=1,sticky="W")
        col+=1

        self.figgf = Figure(figsize=(3.5,3.5),dpi=50)
        self.axgf = self.figgf.add_subplot(111,label="1")
        self.axgfrt = self.figgf.add_subplot(111,label="2",sharex=self.axgf, sharey=self.axgf)
        self.axgfrt.set_facecolor("#ffffff00")
        self.canvasgf = FigureCanvasTkAgg(self.figgf, self.frame_runinfo)
        self.canvasgf.get_tk_widget().grid(pady=(0, 0), padx=(10, 10), row=col, column=0,sticky="NS",columnspan=2)
        col+=1

        self.rpmmax_label=customtkinter.CTkLabel(self.frame_runinfo, text="RPM max:")
        self.rpmmax_label.grid(pady=(0, 0), padx=(10, 10), row=col,column=0,sticky="W")
        self.rpmmax_val=customtkinter.CTkLabel(self.frame_runinfo, text="Tr/Mn")
        self.rpmmax_val.grid(pady=(0, 0), padx=(10, 10), row=col, column=1,sticky="W")
        col+=1

        self.tinmax_label=customtkinter.CTkLabel(self.frame_runinfo, text="Tin max:")
        self.tinmax_label.grid(pady=(0, 0), padx=(10, 10), row=col,column=0,sticky="W")
        self.tinmax_val=customtkinter.CTkLabel(self.frame_runinfo, text="°C")
        self.tinmax_val.grid(pady=(0, 0), padx=(10, 10), row=col, column=1,sticky="W")
        col+=1

        self.powermax_label=customtkinter.CTkLabel(self.frame_runinfo, text="Power max:")
        self.powermax_label.grid(pady=(0, 0), padx=(10, 10), row=col,column=0,sticky="W")
        self.powermax_val=customtkinter.CTkLabel(self.frame_runinfo, text="")
        self.powermax_val.grid(pady=(0, 0), padx=(10, 10), row=col, column=1,sticky="W")
        col+=1

              

        # Set default values
        self.map_widget.set_address("Paris")
        self.change_map("Google satellite")
        self.change_appearance_mode("Dark")
        self.map_option_menu.set("Google satellite")
        self.appearance_mode_optionemenu.set("Dark")

        self.map_widget.add_right_click_menu_command(label="Set Chrono Line",command=self.set_custom_start,pass_coords=True)

        self.current_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        self.starticon = ImageTk.PhotoImage(Image.open(os.path.join(self.current_path, "imgs", "finish-icon-24.png")).resize((40, 40)))
        self.caricon = ImageTk.PhotoImage(Image.open(os.path.join(self.current_path, "imgs", "car_pin.png")).resize((40, 40)))

        self.init_vars()
        
    def compute_value(self,c,d):
        if c == 9 or c == 14 or c == 15 or c == 16 or c == 17 or c == 18 or c == 64: #timestamp+rpm+vitesse
            v = 0
            v += d[0] << 16
            v += d[1] << 8
            v += d[2]
            if (c == 64):
                return v * 0.001379060159 #vitesse
            elif c != 9:
                if v!=0:
                    return (1.0 / v) / 0.000000166666666666667 # rpms
                else:
                    return 0
            else:
                return v
        elif c==10: #LAT/LNG
            Long = (((d[0] << 24) & 0x7F000000) + ((d[1] << 16) & 0x00FF0000) + ((d[2] << 8) & 0x0000FF00) + (0x000000FF & d[3])) * 0.0000001;
            if Long > 180.0:
                    Long = (128 - (((0x80 - d[0]) << 24) & 0x7F000000) + ((d[1] << 16) & 0x00FF0000) + ((d[2] << 8) & 0x0000FF00) + (0x000000FF & d[3])) * 0.0000001;
            Lat = (((d[4] << 24) & 0x7F000000) + ((d[5] << 16) & 0x00FF0000) + ((d[6] << 8) & 0x0000FF00) + (0x000000FF & d[7])) * 0.0000001;
            if Lat >= 90:
                    Lat = (128 - (((0x80 - d[4]) << 24) & 0x7F000000) + ((d[5] << 16) & 0x00FF0000) + ((d[6] << 8) & 0x0000FF00) + (0x000000FF & d[7])) * 0.0000001;
            return([Long,Lat])
        elif c==8: #GFORCE
            LatI = abs(d[0])
            LatF = abs(d[1]) / 0x100
            LonI = abs(d[2])
            LonF = abs(d[3]) / 0x100
            #LatG = LatI > 0 ? parseFloat(LatF) : -parseFloat(LatF)
            #LonG = LonI > 0 ? parseFloat(LonF) : -parseFloat(LonF)
            if LatI>0:
                LatG=LatF
            else:
                LatG=-LatF
            if LonI>0:
                LonG=LonF
            else:
                LonG=-LonF
            return([LatG,LonG])
        elif c==23: #POWER
            return (((d[0] << 8) & 0xFF00) + (d[1] & 0x00FF))
        elif c==26: #torque
            return (((d[0] << 8) & 0xFF00) + (d[1] & 0x00FF))
        elif c==78: #distance
            return (((d[0] << 24) & 0xFF000000) + ((d[1] << 16) & 0x00FF0000) + ((d[2] << 8) & 0x0000FF00) + (0x000000FF & d[3])) * 0.000001
        elif c==74: #throttle
            return (((d[2] << 8) & 0xFF00) + (d[1] & 0x00FF)) * 0.1
        elif c==57: #altitude
            alt=(((d[0] << 24) & 0x7F000000) + ((d[1] << 16) & 0x00FF0000) + ((d[2] << 8) & 0x0000FF00) + (0x000000FF & d[3]))
            acc=(((d[4] << 24) & 0xFF000000) + ((d[5] << 16) & 0x00FF0000) + ((d[6] << 8) & 0x0000FF00) + (0x000000FF & d[7])) * 0.001
            return([alt,acc])
        elif c==27: #vitesse engagee
            return (((d[0] << 8) & 0xFF00) + (d[1] & 0x00FF))
        elif c==93: #angle volant
            fAngle = (((d[2] & 0x7F) << 8) | d[1])
            if fAngle > 0 and (d[2] & 0x80) != 0x00:
                fAngle -= (0x01 << 15)
            fAngle *= 0.1
            return fAngle
        elif c==94: #breakp/boostp
            if d[0]==2:
                return ((((d[3] << 8) & 0xFF00) + (d[2] & 0x00FF)) * 0.01) #breakp
            else:
                return (((d[3] << 8) & 0xFF00) + (d[2] & 0x00FF)) #boostp
        elif c==55: #date du run
            gmtoff = d[7]
            return datetime.datetime(((d[5] << 8) & 0xFF00) + (d[6] & 0x00FF), d[4], d[3], d[2], d[1], d[0])
        elif c==79: #yawrate
            return -(((((d[0] << 8) & 0xFF00) + (d[1] & 0x00FF)) - 32768) * 0.01)
        elif c==25: # break flag
            return ((d[0] << 8) & 0xFF00) + (d[1] & 0x00FF)
        elif c==72: #temperatures
            if ((d[2] << 8) & 0x7F00) >= 128:
                Temp = round((((d[2] << 8) & 0x7F00) + (d[1] & 0x00FF)) * 0.1,2)
            else:
                Temp = round((((d[2] << 8) & 0x7F00) + 0X80 + (d[1] & 0x00FF)) * 0.1,2)
            ret=[]
            ret.append([d[0],Temp])
            return ret
        
    def colorize_path(self,max_speed,startindex):
        colors=[]
        pts=[]
        lcp=len(self.carpath)
        for i in range(0, lcp, 10):
            if i+10 < lcp:
                points=[self.carpath[i],self.carpath[i+10]]
            else:
                points=[self.carpath[i],self.carpath[lcp-1]]
            speed=self.get_chan(64,self.out[i+startindex])["decoded"]
            if max_speed!=0:
                f=int(round(255*(speed/max_speed),0))
            else:
                f=0
            txt = "#{:02x}{:02x}{:02x}"
            rgb=txt.format(f,255-f,64)
            self.map_widget.set_path(points,color=rgb)
            #colors.append(rgb)
            #pts.append(points[0])
            #pts.append(points[1])
        #self.map_widget.set_colored_path(points,colors)

    def check_crc(self,cur):
        sum=cur['channel']
        for d in cur['datas']:
            sum+=d
        sum=sum&0xFF
        return sum == cur['crc']

    def get_chan(self,ch,curline):
        ret=0
        for channel in curline:
            if channel['channel']==ch:
                ret=channel
        return ret
            
    def format_tab(self,inp):
        out=[]
        curline=-1
        for cur in inp:
            if cur['channel']==9:
                curline+=1
                out.append([])
            if self.check_crc(cur):
                out[curline].append(cur)
            else:
                print("CRC ERROR")
        del inp
        gc.collect()
        return out

    def computedistance(self,f,t):
        return self.get_chan(78, self.out[t])['decoded'] - self.get_chan(78, self.out[f])['decoded']
        
    def getlaptime(self):
        self.laptimes = []
        self.lapdistances = []
        i=0
        for line in self.out:
            c = self.get_chan(10, line)
            ct = self.get_chan(9, line)
            if self.lapDetection(c['decoded'][1], c['decoded'][0])==True:
                laptime = ct['decoded'] - self.lapstarttime
                lapdistance = self.computedistance(self.lapstartindex, i)
                self.lapstarttime = ct['decoded']
                self.lapstartindex = i
                if laptime>10:
                    self.nblaps+=1
                    if (laptime < self.besttime):
                        self.besttime = laptime
                    self.laptimes.append(laptime)
                    self.lapdistances.append(lapdistance)
            c['lap']=self.nblaps
            i+=1
                
    def lapDetection(self,fLatitude, fLongitude):
        bResult=False
        fDeltaLatitude = (fLatitude - self.RUN_START_LATITUDE) * math.pi / 180.0
        fDeltaLongitude = (fLongitude - self.RUN_START_LONGITUDE) * math.pi / 180.0
        fSinus2 = (math.sin(fDeltaLatitude * 0.5) * math.sin(fDeltaLatitude * 0.5)) + (math.sin(fDeltaLongitude * 0.5) * math.sin(fDeltaLongitude * 0.5) * math.cos(fLatitude * (math.pi / 180.0)) * math.cos(self.RUN_START_LATITUDE * (math.pi / 180.0)))
        fDistance = self.EARTH_RADIUS * 2.0 * math.atan2(math.sqrt(fSinus2), math.sqrt(1.0 - fSinus2))
        if ((self.m_bInStartProximity is False) and (fDistance <= self.START_DISTANCE)):
            fAngle = math.atan2((fLatitude - self.RUN_START_LATITUDE), (fLongitude - self.RUN_START_LONGITUDE) * math.cos(self.RUN_START_LATITUDE * (math.pi / 180.0))) * 180.0 / math.pi;
            if (self.m_fDirectionAngle == self.FLT_MIN):
                self.m_fDirectionAngle = fAngle
            elif ((self.m_fDirectionAngle != self.FLT_MIN) and (fAngle >= (self.m_fDirectionAngle - self.ANGLE_MARGIN)) and (fAngle <= (self.m_fDirectionAngle + self.ANGLE_MARGIN))):
                self.m_bInStartProximity = True
                bResult = True
        if (self.m_bInStartProximity and fDistance > self.START_DISTANCE):
            self.m_bInStartProximity = False
        return bResult

    def getNextPos(self,inlat, inlng, inp, instart):
        for i in range(instart+1,len(inp)):
            curline = inp[i]
            for channel in curline:
                if channel["channel"]==10:
                    if (channel["decoded"][1] == inlat and channel["decoded"][0] == inlng):
                        a=1
                    else:
                        return i
        return len(inp)
                    
    def interpolatePositions(self,inp):
        oldLat=None
        oldLng=None
        curlat=0
        curlng=0
        i=0
        #for curline in inp:
        while i<len(inp):
            curline=inp[i]
            for channel in curline:
                if channel["channel"]==10:
                    curlat=channel["decoded"][1]
                    curlng=channel["decoded"][0]
                    if (curlat != oldLat and curlng != oldLng):
                        stepstart=i
                        stepend=self.getNextPos(curlat, curlng, inp, stepstart)
                        inp = self.smoothPosition(curlat, curlng, stepend, stepend - stepstart, inp, stepstart)
                        oldlng = curlng
                        oldlat = curlat
                        i = stepend
                    else:
                        i+=1
            
        return inp
    
    def smoothPosition(self,fromlat, fromlng, stepend, steps, inp, stepstart):
        if(stepend>=len(inp)):return inp
        curline = inp[stepend]
        tolat=None
        tolng=None
        for channel in curline:
            if channel["channel"]==10:
                tolat=channel["decoded"][1]
                tolng=channel["decoded"][0]
                steplat = (tolat - fromlat) / steps
                steplng = (tolng - fromlng) / steps
                for s in range(stepstart,stepend):
                    mline = inp[s]
                    c = self.get_chan(10, mline)
                    if (c != 0):
                        c["decoded"][1]=fromlat + steplat * (s - stepstart)
                        c["decoded"][0]=fromlng + steplng * (s - stepstart)
                        #self.get_chan(10,mline)["decoded"]=c["decoded"]
                        #inp[s] = mline
        return inp

    def open_run(self):
        self.init_vars()
        self.filetypes = (
            ('RUN files', '*.run'),
        )
        self.filename = tk.filedialog.askopenfilename(
            title='Open a file',
            initialdir='/',
            filetypes=self.filetypes)

        popup = tk.Toplevel()
        tk.Label(popup, text="Processing Run, please wait...").grid(row=0,column=0,padx=20,pady=20)
        popup.update()
        with open(self.filename, "rb") as self.run_file:
            self.run_file.seek(8)
            self.run_datas = self.run_file.read()
        Ccount=len(self.run_datas)
        index=0
        q=0
        self.carpath=[]
        self.out=[]
        for q in range(Ccount):
            if(index>=Ccount):
                break
            cur={}
            aByte=self.run_datas[index]
            cl=App.CL[aByte]
            cur['offset'] = index
            cur['channel'] = aByte
            cur['datas']=[]
            for nbb in range(cl):
                index+=1
                cur['datas'].append(self.run_datas[index])
            ret=self.compute_value(cur['channel'],cur['datas'])
            cur["decoded"]=ret
            if(cur['channel']==10):
                lon = ret[0]
                lat = ret[1]
                if lat>self.maxlat:
                    self.maxlat=lat
                if lon>self.maxlng:
                    self.maxlng=lon
                if lat<self.minlat:
                    self.minlat=lat
                if lon<self.minlng:
                    self.minlng=lon
                self.carpath.append((lat,lon))
                if self.RUN_START_LATITUDE is None:
                    self.RUN_START_LATITUDE=lat
                    self.RUN_START_LONGITUDE=lon
            if(cur['channel']==64):
                if self.max_speed<ret:
                    self.max_speed=ret
            if(cur['channel']==8):
                if self.max_glat < ret[0]:
                    self.max_glat=ret[0]
                if self.max_glon < ret[1]:
                    self.max_glon=ret[1]
            if(cur['channel']==18):
                if self.max_rpm < ret:
                    self.max_rpm=ret
            if(cur['channel']==23):
                if self.max_power < ret:
                    self.max_power=ret
            if(cur['channel']==72):
                if(cur['decoded'][0][0]==1):
                   if self.max_Text < cur['decoded'][0][1]:
                        self.max_Text=cur['decoded'][0][1]
                if(cur['decoded'][0][0]==6):
                   if self.max_Tin < cur['decoded'][0][1]:
                        self.max_Tin=cur['decoded'][0][1]
            if(cur['channel']==55):
                if self.RUN_START_TIME==0:
                    self.RUN_START_TIME=cur['decoded']
                self.RUN_END_TIME=cur['decoded'];
            index+=1
            cur['crc']=self.run_datas[index] 
            index+=1 #crc
            self.out.append(cur)

      
        duration=self.RUN_END_TIME-self.RUN_START_TIME
        
        self.out=self.format_tab(self.out)
        self.out=self.interpolatePositions(self.out)
        
        self.map_widget.fit_bounding_box((self.maxlat, self.minlng), (self.minlat,self.maxlng))

        #self.colorize_path()

        self.getlaptime()
        self.lapsframe.addlaps(self.laptimes,self.lapdistances)

        self.lapsframe.extractlap(0)

        self.vmax_val.configure(text=str(round(self.max_speed,2))+" Kmh")
        self.glatmax_val.configure(text=str(round(self.max_glat,3))+" G")
        self.glonmax_val.configure(text=str(round(self.max_glon,3))+" G")
        self.rpmmax_val.configure(text=str(round(self.max_rpm,2))+" Tr/Mn")
        self.tinmax_val.configure(text=str(round(self.max_Tin,2))+" °C")
        self.powermax_val.configure(text=str(round(self.max_power,2)))

        self.runinfosframe.textmax_val.configure(text=str(round(self.max_Text,2))+" °C")
        self.runinfosframe.val_runstart.configure(text=self.RUN_START_TIME)
        self.runinfosframe.val_nblaps.configure(text=self.nblaps)
        self.runinfosframe.val_rundur.configure(text=self.lapsframe.ms2HMS(duration.total_seconds()*100))
       
        self.chronomarker=self.map_widget.set_marker(self.RUN_START_LATITUDE, self.RUN_START_LONGITUDE, icon_anchor="s",icon=self.starticon)
        self.carmarker=self.map_widget.set_marker(self.RUN_START_LATITUDE, self.RUN_START_LONGITUDE, icon_anchor="s" ,text="",icon=self.caricon,text_color="#FFFFFF")
        

        self.slider.configure(from_=0, to=len(self.out))
        self.update_carpos(0)

        adr = tkintermapview.convert_coordinates_to_address(self.RUN_START_LATITUDE, self.RUN_START_LONGITUDE)
        if len(adr)>0:
            self.tracklocation.configure(text=str(adr[0]))
        else:
            self.tracklocation.configure(text="Unknown location")

        #graphs
        datasv=[]
        datasg=[[],[]]
        for line in self.out:
            datasv.append(self.get_chan(64,line)["decoded"])
            datasg[0].append(self.get_chan(8,line)["decoded"][0])
            datasg[1].append(self.get_chan(8,line)["decoded"][1])
            
        self.axvmax.clear()
        self.axvmax.plot(datasv)
        self.figvmax.canvas.draw_idle()

        df=pd.DataFrame({'Glat': datasg[0], 'Glon': datasg[1] })
        self.axgf.clear()
        self.axgf.plot('Glat', 'Glon', data=df,linestyle='', marker='o', markersize=3, alpha=0.05)
        self.figgf.canvas.draw_idle()

        popup.destroy()

    def render(self):
        self.isplaying=True
        lastindex=-1
        self.starttime = time.perf_counter()
        while self.curindex < len(self.out)-1:
            if self.stopevent.is_set():
                break
##            if self.pauseevent.is_set():
##                continue
            now=time.perf_counter()
            elapsed = now - self.starttime
            self.curindex+=elapsed*1000*100
            inti=int(self.curindex)
            if(inti==lastindex):
                self.starttime = time.perf_counter()
                continue
            else: lastindex=inti
            self.update_carpos(inti)
            time.sleep(0.05)
            self.starttime = time.perf_counter()
        self.stopevent.clear()
        self.isplaying=False

    def start_render(self):
        #create render thread
        self.t_render=Thread(target=self.render)
        self.t_render.start()

    def stop_render(self):
        #stop render thread
        self.stopevent.set()
        #self.t_render.join()
            
    def search_event(self, event=None):
        self.map_widget.set_address(self.entry.get())

    def set_marker_event(self):
        current_position = self.map_widget.get_position()
        self.marker_list.append(self.map_widget.set_marker(current_position[0], current_position[1]))

    def clear_marker_event(self):
        for marker in self.marker_list:
            marker.delete()

    def change_appearance_mode(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def change_map(self, new_map: str):
        if new_map == "OpenStreetMap":
            self.map_widget.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png")
        elif new_map == "Google normal":
            self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)
        elif new_map == "Google satellite":
            self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)

    def on_closing(self, event=0):
        self.destroy()

    def start(self):
        self.mainloop()


if __name__ == "__main__":
    app = App()
    app.start()
