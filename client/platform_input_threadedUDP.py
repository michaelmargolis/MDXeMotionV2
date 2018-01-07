"""
  platform_input_threadedUDP.py

  Receives UDP messages on port 10009
  Move messages are: "xyzrpy,x,y,z,r,p,y,\n"
  xyz are translations in mm, rpy are rotations in radians
  however if self.is_normalized is set True, range for all fields is -1 to +1
  
  Command messages are:
  "command,enable,\n"   : activate the chair for movement
  "command,disable,\n"  : disable movement and park the chair
  "command,exit,\n"     : shut down the application
"""

import sys
import socket
from math import radians, degrees
import threading
from Queue import Queue
import Tkinter as tk
import traceback


class InputInterface(object):
    USE_GUI = True  # set True if using tkInter
    print "USE_GUI", USE_GUI

    def __init__(self):
        #  set True if input range is -1 to +1
        self.is_normalized = False
        self.expect_degrees = True # convert to radians if True
        self.HOST = "localhost"
        self.PORT = 10009
        if self.is_normalized:
            print 'Platform Input is UDP with normalized parameters'            
        else:
            print 'Platform Input is UDP with realworld parameters'
        self.levels = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.rootTitle = "UDP Platform Interface"
        self.inQ = Queue()
        t = threading.Thread(target=self.listener_thread, args=(self.inQ, self.HOST, self.PORT))
        t.daemon = True
        t.start()

    def init_gui(self, master):       
        self.master = master
        frame = tk.Frame(master)
        frame.pack()
        self.label0 = tk.Label(frame, text="Accepting UDP messages on port " + str(self.PORT))
        self.label0.pack(fill=tk.X, pady=10)

        """ 
        self.units_label = tk.Label(frame, text=t)
        self.units_label.pack(side="top", pady=10)
        """
        
        self.msg_label = tk.Label(frame, text="")
        self.msg_label.pack(side="top", pady=10)
        
        self.cmd_label = tk.Label(frame, text="")
        self.cmd_label.pack(side="top", pady=10)

    def chair_status_changed(self, chair_status):
        print(chair_status[0])

    def begin(self, cmd_func, move_func, limits):
        self.cmd_func = cmd_func
        self.move_func = move_func       

    def fin(self):
        # client exit code goes here
        pass
        
    def get_current_pos(self):
        return self.levels

    def intensity_status_changed(self, status):
        pass

    def service(self):
        # move request returns translations as mm and angles as radians
        msg = None
        # throw away all but most recent message
        while not self.inQ.empty():
            msg = self.inQ.get()
        try:
            if msg is not None:
                msg = msg.rstrip()
                #print msg
                fields = msg.split(",")
                field_list = list(fields)
                if field_list[0] == "xyzrpy":
                    self.msg_label.config(text="got: " + msg)
                    try:
                        r = [float(f) for f in field_list[1:7]]
                        # remove next 3 lines if angles passed as radians 
                        r[3] = radians(r[3])
                        r[4] = radians(r[4])
                        r[5] = radians(r[5])
                        #print r
                        if self.move_func:
                            #print r
                            self.move_func(r)
                            self.levels = r
                    except:  # if not a list of floats, process as command
                        e = sys.exc_info()[0]
                        print "UDP svc err", e
                elif field_list[0] == "command":
                    print "command is {%s}:" % (field_list[1])
                    self.cmd_label.config(text="Most recent command: " + field_list[1])
                    if self.cmd_func:
                        self.cmd_func(field_list[1])
        except:
            #  print error if input not a string or cannot be converted into valid request
            e = sys.exc_info()[0]
            s = traceback.format_exc()
            print e, s

    def listener_thread(self, inQ, HOST, PORT):
        try:
            self.MAX_MSG_LEN = 80
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client.bind((HOST, PORT))
            print "opening socket on", PORT
            self.inQ = inQ
        except:
            e = sys.exc_info()[0]
            s = traceback.format_exc()
            print "thread init err", e, s
        while True:
            try:
                msg = client.recv(self.MAX_MSG_LEN)
                self.inQ.put(msg)
            except:
                e = sys.exc_info()[0]
                s = traceback.format_exc()
                print "listener err", e, s
