"""
 flight_sim_client control module 
 
 The system consists of the following elements:
   Platform controller - this receives and processes telemetry that is used to position the
   motion platform. The middlware can also send commands to control the flight simulation software.
 
 This client communicates with the motion platform controller using callbacks
   One callback is used to pass telemetry motion requests
   A second callback can be used to enable, disable or park the platform
   
 Todo service calls inform the client that the platform is ready for a telemetyr message
 
 The client communicates with the sim software through an MQTT gateway. In this implimentation,
 the sim software is an MQTT client that published telemetry events and subzcribes to commands that 
 may be send from the platform middleware. These commands compise requests to start, pause or reset a 
 simulation scenario. 
 
 Events:
  telemetry events (x,y,z translation and roll, pitch and yaw) are receved on the MQTT topic: "flightsim/telemetry"
  these six normalized values are provided as comma seperated float strings in the MQTT msg body.
  
  Commands:
     The platform control software published the following commands on the topic:   "flightsim/command"
         "Client Connected" - this informs the sim that that the platform middleware has connected
         "Client Disconnected" - this informs the sim that that the platform middleware has disconnected

  
"""

import sys
import socket
import errno
import time
import tkMessageBox
import copy
import math
from flight_sim_gui import FlightSimGui
from  mqtt_client import *

class InputInterface(object):
    USE_GUI = True

    def __init__(self):
        self.cmd_func = None
        self.is_normalized = True
        self.current_pos = []
        self.is_chair_activated = False
        self.gui = FlightSimGui(self.take_off, self.pause, self.reset, self.set_activate_state, self.quit)
        self.prev_movement_time = 0  # holds the time of last reported movement from NoLimits
        self.speed = 0
        self.rootTitle = "Flight Sim Controller"  # the display name in tkinter
        self.gui = FlightSimGui(self.take_off, self.pause, self.reset, self.set_activate_state, self.quit)
        self.mqtt = MQTTClient("FlightSimClient", self.telemetry_update)
        self.msg = None

    def init_gui(self, master):
        self.gui.init_gui(master)
        self.master = master
        while not self.is_SimConnect_accessable():
            self.master.update_idletasks()
            self.master.update()
            result = tkMessageBox.askquestion("Waiting for Flight Sim", "Flight Sim not found, Start Sim and interface and press Yes to retry, No to quit", icon='warning')
            if result == 'no':
                sys.exit(0)
         
        self.gui.set_coaster_connection_label(("Flight Sim Connected", "green3"))

    def is_SimConnect_accessable(self):
        try:
            self.mqtt.connect("127.0.0.1") # connect to local broker    
            self.mqtt.subscribe("flightsim/telemetry")
            self.mqtt.publish("flightsim/command", "Client Connected")            
            return True
        except: 
           print "error connecting to MQTT broker, is it running?"
        
    def _sleep_func(self, duration):
        start = time.time()
        while time.time() - start < duration:
            self.master.update_idletasks()
            self.master.update()
            win32gui.PumpWaitingMessages()


    def command(self, cmd):
        if self.cmd_func is not None:
            print "Requesting command with", cmd
            self.cmd_func(cmd)

    def take_off(self):
        if self.is_chair_activated: #and self.coasterState.state == MoveState.READY_FOR_DISPATCH:
            print 'taking off'            
            self.command("ready")  # slow rise of platform          
            print "take off here"
         

    def pause(self):
        print "pause here"
        
    def reset(self):
        print "reset rift here"

    def set_intensity(self, intensity_msg):
        self.command(intensity_msg)

    def emergency_stop(self):
        print "legacy emergency stop callback"
        self.deactivate()

    def set_activate_state(self, state):
        #  print "in setActivatedState", state
        if state:
            self.activate()
        else:
            self.deactivate()

    def activate(self):      
        #  print "in activate "
        self.is_chair_activated = True
        self.command("enable")
        self.gui.set_activation_buttons(True)
       
    def deactivate(self):
        #  print "in deactivate "       
        self.command("disable")
        self.gui.set_activation_buttons(False)
        self.is_chair_activated = False
        self.coasterState.set_is_chair_active(False)
     
    def quit(self):
        self.command("quit")

    def detected_remote(self, info):
        if "Detected Remote" in info:
            self.set_remote_status_label((info, "green3"))
        elif "Looking for Remote" in info:
            self.set_remote_status_label((info, "orange"))
        else:
            self.set_remote_status_label((info, "red"))

    def set_coaster_connection_label(self, label):
        self.gui.set_coaster_connection_label(label)

    def chair_status_changed(self, status):
        self.gui.chair_status_changed(status)

    def temperature_status_changed(self, status):
        self.gui.temperature_status_changed(status)

    def intensity_status_changed(self, status):
        self.gui.intensity_status_changed(status)

    def set_remote_status_label(self, label):
        self.gui.set_remote_status_label(label)

    def begin(self, cmd_func, move_func, limits):
        self.cmd_func = cmd_func
        self.move_func = move_func
        self.limits = limits

    def fin(self):
        # client exit code goes here
        self.mqtt.publish("flightsim/command", "Client Disconnected")
        time.sleep(0.1)
        
    def get_current_pos(self):
        return self.current_pos
    
    def process_xyzrpy(self, msg):
        if len(msg) == 6: # need header and six values
           vals = []
           for idx, val in enumerate(msg):
               vals.append(float(val)) 
           print vals
           self.current_pos = vals
           if self.is_chair_activated:
                # only send if platform is activated 
                if self.move_func is not None:
                    # msg is normalized values for x,y,z translations and roll, pitch and yaw
                    self.move_func(self.current_pos)   
        
    def service(self):      
        #  if using remote control, uncomment this: self.RemoteControl.service()
        try:
            if self.msg  == None:
                return
            if self.msg.find('disconnected') != -1:
                print "Gateway is disconnected from Sim"
                result = tkMessageBox.askquestion("Waiting for Flight Sim", "Flight Sim Gateway not connected, Connect to Sim and press Yes to retry, No to quit", icon='warning')
                if result == 'no':
                    sys.exit(0)
      
            elif self.msg.find('\n') != -1:
                #  print msg
                msg = self.msg.split(',',1)     
                self.process_xyzrpy(msg[1].split(',')[:6])
        except Exception, e:
           print "service eexception", e

    def telemetry_update(self, msg):
        self.msg = msg
        # print(msg)
