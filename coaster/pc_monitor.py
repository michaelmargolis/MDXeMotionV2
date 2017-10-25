"""
pc_monitor  - this version is for the pi

returns CPU and GPU temperatires in degrees CPU

"""

"""
from pynvml import *
import wmi
"""

import collections
import socket
#import SocketServer

deg = u"\N{DEGREE SIGN}"

class pc_monitor_client():
    def __init__(self, cpu_thresholds, gpu_thresholds): 
        self.cpu_threshold = cpu_thresholds
        self.gpu_threshold = gpu_thresholds      
        
    def begin(self, coaster_ip_addr, monitor_port):
        self.coaster_ip_addr = coaster_ip_addr
        self.monitor_port = monitor_port
        return self._connect()

    def _connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.coaster_ip_addr, self.monitor_port))
            print "connected to VR pc"
            return True
        except socket.error as serr:
            print self.coaster_ip_addr, serr
            return False

    def read(self):
        try:
            self.sock.send('heat?')
            # todo add exception handling
            warning_level = 0
            data = self.sock.recv(512)
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
            
            return cpu_string + gpu_string, warning_level
        except socket.error as serr:
            print serr
            self._connect()
            return  "error accessing VR PC"  

    def fin(self):
        self.sock.close()

"""
this class runs on the pc running VR

class PC_monitor():
    # thresholds are levels for warnings and error indicators
    def __init__(self): 
        self.wmi = wmi.WMI(namespace="root\wmi")
        
        try:
            nvmlInit()
            #print "Driver Version:", nvmlSystemGetDriverVersion()
            numOfGPUs = int(nvmlDeviceGetCount())
            if numOfGPUs ==0:
               print "Error, no Nvidia GPUs found"
            elif numOfGPUs > 1:
                print numOfGPUs, "GPUs found, only displaying first"
            self.nvml_handle = nvmlDeviceGetHandleByIndex(0)
        except NVMLError, err:
            print "Failed to initialize NVML: ", err

    #  returns cpu and gpu temperature 
    def read(self):
        warning_level = 0
        try:
          temp = []
          for zone in range(4):
             temperature_info = self.wmi.MSAcpi_ThermalZoneTemperature()[zone]
             t = (temperature_info.CurrentTemperature-2730)/10
             temp.append(t)
        except IndexError:
            pass
        except Exception, e:
            if "Unexpected COM Error" in str(e):
               temp = None
            else:
                print e

        #print temp

        if temp == None:
            cpu_string = "CPU=??,"
        else:   
            cpu_string = format("cpu=%d," % (max(temp)))

        try:
            gpu_string = "GPU ???"
            if self.nvml_handle:
                 t = nvmlDeviceGetTemperature(self.nvml_handle, NVML_TEMPERATURE_GPU)
                 gpu_string = format("gpu=%d" % (t))
        except:
             print "error reading GPU temperature" 
             warning_level = max(warning_level,1)

        #print cpu_string + gpu_string
        return cpu_string + gpu_string

    def fin(self):
        nvmlShutdown()

if __name__ == '__main__':
    pc_monitor = PC_monitor()
    HOST, PORT = '', 10010
    # Create the server, binding to localhost on port effector port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(2)
    print "PC Monitor server ready to receive on port ",PORT

    try:
        while True:
            newSocket, address = sock.accept( )
            print "Connected from", address
            while True:
                receivedData = newSocket.recv(512)
                if not receivedData: break
                if "heat?" in receivedData:
                    t = pc_monitor.read()
                    t = t.encode('ascii', 'ignore').decode('ascii')
                    print "sending", t
                    newSocket.send(t)
        newSocket.close(  )
        print "Disconnected from", address
    finally:
        sock.close(  )
"""

