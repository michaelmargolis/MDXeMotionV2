"""
  oscillate.py

  Steps all muscles up and down through full range of movement 
"""


import sys
import time

from platform_output import OutputInterface

chair = OutputInterface()

def main():
    actuator_length_range = chair.get_actuator_lengths()  # min, max lengths in mm
    actuator_lengths = [actuator_length_range[1] for i in range(6)]
    print actuator_length_range
    print actuator_lengths
    input = raw_input("enter mm per step, total duration: ")
    step,dur = input.split(",",1)
    step = int(step)
    dur = int(dur)
    span = (actuator_length_range[1] - actuator_length_range[0])
    steps = span / step
    interval =  float(dur) / steps
    print format("moving platform in %d mm steps over %d seconds, (%.2f secs per step)" % (step, dur, interval))
    chair.set_enable(True,actuator_lengths)
    print "moving up"
    while True:
        print actuator_lengths
        chair.move_platform(actuator_lengths)
        actuator_lengths = [actuator_lengths[i] - step for i in range(6)]
        if actuator_lengths[0] < actuator_length_range[0]:
            actuator_lengths = [actuator_length_range[0] for i in range(6)]
            break
        time.sleep(interval)
        
    print "moving down"
    while True:
        print actuator_lengths
        chair.move_platform(actuator_lengths)
        actuator_lengths = [actuator_lengths[i] + step for i in range(6)]
        if actuator_lengths[0] > actuator_length_range[1]:
            actuator_lengths = [actuator_length_range[1] for i in range(6)]
            break
        time.sleep(interval)

    chair.set_enable(False, actuator_lengths)


if __name__ == "__main__":
    main()
    chair.fin()
    
"""
def calibrate():
    minMaxTable = [[0 for x in range(2)] for y in range(sensorCount)]
    upTable = [[0 for x in range(sensorCount)] for y in range(stepCount)]
    downTable = [[0 for x in range(sensorCount)] for y in range(stepCount)]
    
   
    for sensor in range(sensorCount):
        FST_sendRaw(minPressure, sensor) # chair at max distance
    time.sleep(3)
    
    data = getSensorData()  
    for i in range(sensorCount):
        minMaxTable[i][1] = data[i]  #store max distances  
    
    #step up through pressure ranges
    for step in range(stepCount):  
         pressure = indexToPressure(step)
         for i in range(sensorCount):
             FST_sendRaw(pressure, i) 
         time.sleep(2)
         upTable[step] = getSensorData()
         print step, upTable[step]		 
    print upTable
    
    # the actuators are now at minimum distance
    data = getSensorData()  
    for i in range(sensorCount):         
        minMaxTable[i][0] = data[i]
    
    #step down through pressure ranges
    for s in range(stepCount):  
         step = stepCount-s-1
         pressure =  indexToPressure(step)              
         for i in range(sensorCount):
             FST_sendRaw(pressure, i) 
         time.sleep(2)
         downTable[step] = getSensorData()                 
    print downTable
    print "minMaxTable", minMaxTable

    with open(csvFname, 'wb') as myfile:
        wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
        wr.writerow( ('Min and Max Heights',) )
        wr.writerows(minMaxTable)
        wr.writerow( ('Table of Upgoing Heights',stepCount) )
        wr.writerows(upTable)
        wr.writerow( ('Table of Downgoing Heights',stepCount) )
        wr.writerows(downTable)  

            
#returns the pressure at a given index            
def indexToPressure(index):
    return   index * stepSize + minPressure     
    
def getSensorData():
    SIMULATE_SENSORS = False #True
    if SIMULATE_SENSORS:
        msg = [700,701,702,703,704,705]
           
    else:
        while not sensorQ.empty(): 
            msg = sensorQ.get(False)
        msg = sensorQ.get(True) #wait for next message (todo timeout needed)
    #print "got q msg: ", msg 
    return msg[:]
     
            
    
def scale( val, src, dst) :   # the Arduino 'map' function written in python  
  return (val - src[0]) * (dst[1] - dst[0]) / (src[1] - src[0])  + dst[0]
   
def FST_sendRaw(pressure, index):
    try:
        command = "maw"+str(64+index)+"="+str(pressure)
        print command,
        command = command +"\r\n"
        try:
            FSTs.sendto(command,(FST_ip, FST_port))
        except:
            print "Error sending to Festo"
        if index == sensorCount-1:
            print "\n"
		
    except: 
        e = sys.exc_info()[0]
        print e        

#  sensor message socket
class MyTCPHandler(SocketServer.StreamRequestHandler):
        
    def handle(self): 
        global sensorQ
        self.queue = sensorQ        
        while True:
            if kbhit():
                c = getch()                
                if ord(c) == 27: # ESC
                    sys.exit([0])        
            try:         
                json_str = self.rfile.readline() #.strip()[1:]
                if json_str != None:                          
                    #print json_str                  
                    #print "{} wrote:".format(self.client_address[0])       
                    try:                 
                        j = json.loads(json_str)                
                        #print "got:", j                                                  
                        if j['method'] == 'sensorEvent':                                              #
                           #for n in j['distanceArgs']:                         
                              #print j['distanceArgs'], n     
                           self.queue.put(j['distanceArgs'])                                                                                                           
                    except ValueError:
                        print "nothing decoded", "got:", json_str
                        continue
                    except socket.timeout:
                        print "socket timeout" 
                        continue                          
            except : 
                  print "Connection broken"
                  break;                   
            
if __name__ == "__main__":    
    
    # setup the UDP Socket  
    TESTING = False #True
    if TESTING: 
        FST_ip = 'localhost'
        FST_port = 991 
    else:  
       FST_ip = '192.168.10.10'
       FST_port = 991 
    print "Calibrate script opening festo socket on ", FST_port
    FSTs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # start the sensor message receiver server 
    HOST, PORT = '', 10009  

    # Create the server, binding to localhost on port effector port
    server = SocketServer.TCPServer((HOST, PORT), MyTCPHandler)
    remote_server_thread = threading.Thread(target=server.serve_forever)
    remote_server_thread.daemon = True
    remote_server_thread.start()
    print "Calibrate ready to receive sensor data on port ",PORT   
    #server.serve_forever()
    calibrate()     
"""