# Client V1 to V2 interface
# Input messages "xyzrpy","args":[array of 6 floats]
# example: {"jsonrpc":"2.0","method":"xyzrpy","args":[0.0, 0.0, 0.1, -0.2, 0.0, 0.0]}


import socket
import SocketServer
import threading
import sys 
from Queue import Queue
import json
import Tkinter as tk
import ttk


HOST, PORT = '', 10002 
msg_q = Queue()
thread_active = True
InputParmType = 'normalized'

class InputInterface(object):
    USE_GUI = True

    def __init__(self):
        self.USE_GUI = True  # set True if using tkInter
        self.rootTitle = "V1 Platform Interface"
        
        self.MAX_MSG_LEN = 255
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.timeout = 2
        #  self.client.settimeout(self.timeout)
        self.is_normalized = True
        print "Platform Input is V1 TCP on port", PORT
        self.connection = None

    def init_gui(self, master):
        self.master = master
        frame = tk.Frame(master)
        frame.pack()

        self.label0 = tk.Label(frame, text="V1 input values", font=("Calibri",20))
        self.label0.pack(fill=tk.X, pady=10)
        sLabels = ("Surge =", "Sway =", "Heave =", "Roll =", "Pitch =", "Yaw  =")
        self.in_args = ["0.0","0.0","0.0","0.0","0.0","0.0"]
        for i in range(6):
            f = tk.Frame(master)
            s = tk.Label(f, text=sLabels[i], anchor="w", width=6, font=("Calibri",16))
            s.pack(side=tk.LEFT, padx=(6, 4))
            self.in_args[i] = tk.Label(f, text="0,0", font=("Calibri",16))
            self.in_args[i].pack(side=tk.LEFT, padx=(6, 4))
            f.pack()


        frame2 = tk.Frame(master)
        frame2.pack(fill=tk.X, side=tk.BOTTOM, pady=10)

        self.chair_status_Label = tk.Label(frame2, text="Using Festo Controllers")
        self.chair_status_Label.pack()

        self.is_connected_label = tk.Label(frame2, text="Waiting Connection", fg="orange")
        self.is_connected_label.pack(side=tk.LEFT)
        
        self.enableState = tk.StringVar()
        self.enableState.set('disable')
        self.enable_cb = tk.Checkbutton(frame2, text="Enable", command=self._enable,
                                        variable=self.enableState, onvalue='enable', offvalue='disable')
        self.enable_cb.pack(side=tk.LEFT, padx=170)

        self.close_button = tk.Button(frame2, text="Quit", command=self.quit)
        self.close_button.pack(side=tk.LEFT)

    def chair_status_changed(self, chair_status):
        print(chair_status[0])

    def begin(self, cmd_func, move_func, limits):
        self.cmd_func = cmd_func
        self.move_func = move_func
        self.limits = limits    # note limits are in mm and radians
        server = ThreadedTCPServer((HOST, PORT), RemoteTCPHandler)
        remote_server_thread = threading.Thread(target=server.serve_forever)
        remote_server_thread.daemon = True
        remote_server_thread.start() 
        print "Waiting for V1 client connection on port", PORT

    def fin(self):
        # client exit code goes here
        pass
    
    def chair_status_changed(self, chair_status):
        pass
        #self.chair_status_Label.config(text=chair_status[0], fg=chair_status[1])

    def _enable(self):
        if(self.cmd_func):
            self.master.update_idletasks()
            self.master.update()
            self.cmd_func(self.enableState.get())
            
    def get_current_pos(self):
        return [0,0,0,0,0,0]

    def chair_status_changed(self, status):
        pass

    def temperature_status_changed(self, status):
        pass

    def intensity_status_changed(self, status):
        pass
        
    def quit(self):
        global thread_active
        thread_active = False
        if(self.cmd_func):
            self.cmd_func("quit")
        self.master.quit()

    def service(self):
        global msg_q
        if self.move_func:
            msg = None
            while not msg_q.empty(): 
                msg = msg_q.get(False)
            if msg:
                if "disconnected" in msg:
                    self.is_connected_label.config(text="Client Disconnected", fg="orange")
                elif len(msg) == 6:
                    self.is_connected_label.config(text="", fg="green3")
                    print "sending", msg
                    self.move_func(msg)
                    for i in range(6):
                       self.in_args[i].config(text=format("%.2f" % msg[i]))

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass 
    
class RemoteTCPHandler(SocketServer.StreamRequestHandler):

    def handle(self):
       global msg_q, thread_active
       self.queue = msg_q
       while thread_active: 
            #print "remote thread : ", threading.currentThread().getName()
            try:
                json_str = self.rfile.readline().strip()
                if json_str != None:
                    j = json.loads(json_str)
                    print "got:", j
                    if j['method'] == 'xyzrpy':
                        input_field = j['args']
                        self.queue.put(input_field)
            except ValueError:
                pass
            except socket.timeout:
                continue
            except socket.error:
                print "TCP connection error, try (re)starting the V1 client"
                self.queue.put("disconnected")
                while True:
                    try:
                       self.rfile.readline().strip() 
                       # todo - the first remote command after reconnect is ignored
                       break
                    #todo - exit if keyboard interrupt?
                    except socket.error:
                        pass
            except (KeyboardInterrupt, SystemExit):
                raise
