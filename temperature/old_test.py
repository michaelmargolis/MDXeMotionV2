from pynvml import *
import wmi


local_encoding = 'cp850'    # adapt for other encodings
deg = u'\xb0'.encode(local_encoding)
w = wmi.WMI(namespace="root\wmi")

import time

for i in range(20):
    try:
      #print "CPU temperatures are:",
      temp = []
      for zone in range(4):
         temperature_info = w.MSAcpi_ThermalZoneTemperature()[zone]
         temp.append((temperature_info.CurrentTemperature-2730)/10)    
    except IndexError:
        pass

    #print temp

    cpu_string = ""
    for t in temp:
       cpu_string += format("%d%sC, " % (t, deg))
    cpu_string = "CPU temperatures: " + cpu_string

    #print format("CPU zone temperatures: %s" % (cpu_string))

    try:
        nvmlInit()
        #print "Driver Version:", nvmlSystemGetDriverVersion()
        numOfGPUs = int(nvmlDeviceGetCount())
        if numOfGPUs ==0:
           print "no Nvidia GPUs found"
        elif numOfGPUs > 1:
            print numOfGPUs, "found, only displaying 1"
          
        handle = nvmlDeviceGetHandleByIndex(0)
        temperature = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
        gpu_string = format(" GPU: %d%sC" % (temperature, deg))

    except NVMLError, err:
        print "Failed to initialize NVML: ", err


    print cpu_string + gpu_string

    #raw_input("press enter to quit")
    
    time.sleep(1)
   
nvmlShutdown()