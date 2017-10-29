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
        # returns tuple of: IP address of server, temperature strings, warning level(0-2) 
        # IP address will be "" if no heartbeat available
        payload = None
        status = ""
        addr = ("", 0)
        warning_level = 0
        # throw away all but most recent message
        #  print "in read()"
        while not self.inQ.empty():
            payload = self.inQ.get()
            #  print "in Q, payload", payload, "..."
        try:
            if payload != None:
                # print "payload", payload, payload[0], payload[0].rstrip()
                data = payload[0].rstrip()
                addr = payload[1]
                #print format("data {%s}, addr [%s] [%s]" % (data, addr[0], addr[1]))
                vals = data.split(',',1)
                d = dict(v.split('=') for v in vals)
                if 'CPU' in d and d['CPU'].isdigit():
                    cpu = int(d['CPU'])
                    cpu_string = format("CPU temperature %d%sC, " % (cpu, deg))
                    status = cpu_string                  
                    if cpu > self.cpu_threshold[1]:
                         warning_level = 2
                    elif cpu > self.cpu_threshold[0]:
                         warning_level = max(warning_level,1)
                else:
                    cpu_string = "CPU Temperature ??   "
                    warning_level = 1
                if 'GPU' in d and  d['GPU'].isdigit():
                    gpu = int(d['GPU'])
                    gpu_string = format(" GPU: %d%sC" % (gpu, deg))
                    if gpu > self.gpu_threshold[1]:
                        warning_level = 2
                    elif gpu > self.gpu_threshold[0]:
                        warning_level = max(warning_level,1)
                else:
                    gpu_string = "GPU ??"
                status += gpu_string

                #  print format("In pc monitor, heartbeat {%s:%s} {%s} {%d}" % (addr[0], addr[1], data, warning_level))
            return addr, status, warning_level
        except:
            #  print error if input not a string or cannot be converted into valid request
            e = sys.exc_info()[0]
            s = traceback.format_exc()
            print e, s
            return ("", 0), "Error", 2

    def fin(self):
       pass

          
    def listener_thread(self, inQ, HOST, PORT):
        try:
            MAX_MSG_LEN = 128
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((HOST, PORT))
            #print "opening socket on", PORT
            self.inQ = inQ
        except:
            e = sys.exc_info()[0]
            s = traceback.format_exc()
            print "thread init err", e, s
        while True:
            try:
                msg, addr = sock.recvfrom(MAX_MSG_LEN)
                #  print "in thread:", msg, addr
                self.inQ.put((msg,addr))
            except:
                e = sys.exc_info()[0]
                s = traceback.format_exc()
                print "listener err", e, s
