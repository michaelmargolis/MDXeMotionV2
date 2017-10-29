"""
pc_monitor

receives UDP hearbeat messages from the server
containing CPU and GPU temperatires in degrees CPU

"""

import sys
import socket
import threading
import time
from Queue import Queue

import traceback


deg = u"\N{DEGREE SIGN}"

class pc_monitor_client():
    def __init__(self, cpu_thresholds, gpu_thresholds): 
        self.cpu_threshold = cpu_thresholds
        self.gpu_threshold = gpu_thresholds
        self.HOST = ""
        self.PORT = 10010
        self.inQ = Queue()
        
    def begin(self):
        self.thread = threading.Thread(target=self.listener_thread, args=(self.inQ, self.HOST, self.PORT))
        if self.thread:
           self.thread.daemon = True
           self.thread.start()
           return True
        else:
            return False


    def read(self):
        msg = ""
        # throw away all but most recent message
        while not self.inQ.empty():
            msg = self.inQ.get()
        try:
            if msg is not None:
                data = msg[0].rstrip()
                addr = msg[1].rstrip()
                print msg
                warning_level = 0
                vals = data.split(',',1)
                d = dict(v.split('=') for v in vals)
                if 'cpu' in d and d['cpu'].isdigit():
                    cpu = int(d['cpu'])
                    cpu_string = format("CPU temperature %d%sC, " % (cpu, deg))
                    if cpu > self.cpu_threshold[1]:
                         warning_level = 2
                    elif cpu > self.cpu_threshold[0]:
                         warning_level = max(warning_level,1)
                else:
                    cpu_string = "CPU Temperature ??   "
                    warning_level = 1
                if 'gpu' in d and  d['gpu'].isdigit():
                    gpu = int(d['gpu'])
                    gpu_string = format(" GPU: %d%sC" % (gpu, deg))
                    if gpu > self.gpu_threshold[1]:
                        warning_level = 2
                    elif gpu > self.gpu_threshold[0]:
                        warning_level = max(warning_level,1)
                else:
                    gpu_string = "GPU ??"
            
            return addr, cpu_string + gpu_string, warning_level
        except:
            #  print error if input not a string or cannot be converted into valid request
            e = sys.exc_info()[0]
            s = traceback.format_exc()
            print e, s

    def fin(self):
       pass

          
    def listener_thread(self, inQ, HOST, PORT):
        try:
            MAX_MSG_LEN = 128
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((HOST, PORT))
            print "opening socket on", PORT
            self.inQ = inQ
        except:
            e = sys.exc_info()[0]
            s = traceback.format_exc()
            print "thread init err", e, s
        while True:
            try:
                msg, addr = sock.recvfrom(MAX_MSG_LEN)
                print msg, addr
                self.inQ.put((msg,addr))
            except:
                e = sys.exc_info()[0]
                s = traceback.format_exc()
                print "listener err", e, s
