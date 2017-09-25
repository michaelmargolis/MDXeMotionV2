"""
temperature

returns CPU and GPU temperatires in degrees CPU
requires admin priviliges
""" 
from pynvml import *
import wmi

deg = u"\N{DEGREE SIGN}"

class system_temperature():
    # thresholds are levels for warnings and error indicators
    def __init__(self, cpu_thresholds, gpu_thresholds): 
        self.wmi = wmi.WMI(namespace="root\wmi")
        self.cpu_threshold = cpu_thresholds
        self.gpu_threshold = gpu_thresholds
        
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

    #  returns temperature string and warning level (0-2)
    def read(self):
        warning_level = 0
        try:
          temp = []
          for zone in range(4):
             temperature_info = self.wmi.MSAcpi_ThermalZoneTemperature()[zone]
             t = (temperature_info.CurrentTemperature-2730)/10
             temp.append(t)
             if t > self.cpu_threshold[1]:
                 warning_level = 2
             elif t > self.cpu_threshold[0]:
                 warning_level = max(warning_level,1)
        except IndexError:
            pass
        except Exception, e:
            if "Unexpected COM Error" in str(e):
               temp = 0
            else:
                print e

        #print temp

        if temp == 0:
            cpu_string = "CPU Temperatures ??   "
        else:
            cpu_string = ""
            for t in temp:
               cpu_string += format("%d%sC, " % (t, deg))
            cpu_string = "CPU temperatures: " + cpu_string

        #print format("CPU zone temperatures: %s" % (cpu_string))

        try:
            gpu_string = "GPU ???"
            if self.nvml_handle:
                 t = nvmlDeviceGetTemperature(self.nvml_handle, NVML_TEMPERATURE_GPU)
                 gpu_string = format(" GPU: %d%sC" % (t, deg))
                 if t > self.gpu_threshold[1]:
                     warning_level = 2
                 elif t > self.gpu_threshold[0]:
                     warning_level = max(warning_level,1)
        except:
             print "error reading GPU temperature" 
             warning_level = max(warning_level,1)

        #print cpu_string + gpu_string, warning_level
        return cpu_string + gpu_string, warning_level
        
    def fin(self):
        nvmlShutdown()