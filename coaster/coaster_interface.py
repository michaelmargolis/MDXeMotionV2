"""
coaster_interface module

This version requires NoLimits attraction license and NL ver 2.5.3.4 or later
"""

import socket
from time import time,sleep
from struct import *
import collections
from quaternion import Quaternion
from math import pi, degrees, sqrt
import sys
import threading

import  binascii  # only for debug


class CoasterInterface():

    N_MSG_OK = 1
    N_MSG_ERROR = 2
    N_MSG_GET_VERSION = 3 # datasize 0
    N_MSG_VERSION = 4
    N_MSG_GET_TELEMETRY = 5  # datasize 0
    N_MSG_TELEMETRY = 6
    N_MSG_SET_MANUAL_MODE = 16 # datasize 9
    N_MSG_DISPATCH = 17  # datasize 8
    N_MSG_SET_PLATFORM = 20  # datasize 9
    N_MSG_LOAD_PARK = 24   # datasize 1 + string 
    N_MSG_CLOSE_PARK = 25  # datasize 0
    N_MSG_SET_PAUSE = 27   # datasize 1
    N_MSG_RESET_PARK = 28  # datasize 1
    N_MSG_SET_ATTRACTION_MODE = 30   # datasize 1
    
    c_nExtraSizeOffset = 9  # Start of extra size data within message

    telemetryMsg = collections.namedtuple('telemetryMsg', 'state, frame, viewMode, coasterIndex,\
                                           coasterStyle, train, car, seat, speed, posX, posY,\
                                           posZ, quatX, quatY, quatZ, quatW, gForceX, gForceY, gForceZ')

    def __init__(self):
        self.coaster_buffer_size = 1024
        self.coaster_ip_addr = 'localhost'
        self.coaster_port = 15151
        self.interval = .05  # time in seconds between telemetry requests
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.id = 1
        self.telemetry_err_str = "Waiting to connect to NoLimits Coaster"
        self.telemetry_status_ok = False
        self._telemetry_state_flags = 0
        self.prev_yaw = None
        self.prev_time = time()
        self.lift_height = 32  # max height in meters
        self.pause_mode = False  # for toggle todo replace with explicit pause state

    def begin(self):
        self.connect_to_coaster()

    def is_NL2_accessable(self):
       self.get_telemetry()
       #  print "is accessable", self.telemetry_status_ok == True
       return self.telemetry_status_ok == True
       
    def connect_to_coaster(self):
       try:          
          self.client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
          self.client.connect((self.coaster_ip_addr, self.coaster_port))
          return self.is_NL2_accessable()
       except Exception, e:
          print "error connecting to NoLimits", e
          return False    


    def send(self, r):
        self.client.sendall(r)

    def toggle_pause(self):
        #  print "toggle Pause"
        if self.pause_mode:
            self.pause_mode = False
            self.set_pause(False)
        else:
          self.pause_mode = True
          self.set_pause(True)

    def dispatch(self):
        msg = pack('>ii', 0, 0)  # coaster, station
        r = self._create_NL2_message(self.N_MSG_DISPATCH, 9, msg)
        #  print "dispatch msg",  binascii.hexlify(msg),len(msg), "full", binascii.hexlify(r)
        self.send(r)

        #  self.send_windows_key(0x17, ord('I'))

    def open_harness(self):
        print 'Opening Harness'
        pass

    def close_harness(self):
        print 'Closing Harness'
        pass
     
    def disengageFloor(self):
        print 'Disengaging floor'
        #self.send_windows_key(0x4F, ord('1'))
        msg = pack('>ii?', 0, 0, True)  # coaster, car, True lowers, False raises
        r = self._create_NL2_message(self.N_MSG_SET_PLATFORM, 0, msg)
        #  print "set platform msg", binascii.hexlify(r)
        self.send(r)

    def set_manual_mode(self):
        msg = pack('>ii?', 0, 0, True)  # coaster, car, True sets manual mode, false sets auto
        r = self._create_NL2_message(self.N_MSG_SET_MANUAL_MODE, 0, msg)
        #  print "set mode msg", binascii.hexlify(r)
        self.send(r)

    def get_telemetry(self):
            #  returns err 
            #print "get telemetry"
            self.send(self._create_simple_message(self.id, self.N_MSG_GET_TELEMETRY))
            data = self.client.recv(self.coaster_buffer_size)
            if data and len(data) >= 10:
                #  print "data len",len(data)
                msg, requestId, size = (unpack('>HIH', data[1:9]))
                #  print msg, requestId, size
                if msg == self.N_MSG_VERSION:
                    v0, v1, v2, v3 = unpack('cccc', data[self.c_nExtraSizeOffset:self.c_nExtraSizeOffset+4])
                    print 'NL2 version', chr(ord(v0)+48), chr(ord(v1)+48), chr(ord(v2)+48), chr(ord(v3)+48)
                    self.send(self._create_simple_message(self.id, self.N_MSG_GET_TELEMETRY))
                elif msg == self.N_MSG_TELEMETRY:
                    if size == 76:
                        t = (unpack('>IIIIIIIIfffffffffff', data[self.c_nExtraSizeOffset:self.c_nExtraSizeOffset+76]))
                        tm = self.telemetryMsg._make(t)
                        #print "tm", tm
                        formattedData = self._process_telemetry_msg(tm)
                        self.telemetry_status_ok = True
                        #  print "telemetry ", self.telemetry_status_ok
                        return formattedData
                    else:
                        print 'invalid msg len expected 76, got ', size
                    sleep(self.interval)
                    self.send(self._create_simple_message(self.id, self.N_MSG_GET_TELEMETRY))
                elif msg == self.N_MSG_OK:
                    self.telemetry_status_ok = True
                    pass
                elif msg == self.N_MSG_ERROR:
                    self.telemetry_status_ok = False
                    self.telemetry_err_str = data[self.c_nExtraSizeOffset:-1]
                    #  print "err:", self.telemetry_err_str
                else:
                    print 'unhandled message', msg

    def load_park(self, isPaused, park):
        print "loading park", park
        start = time()
        msg = pack('>?', isPaused) + park # start in pause, park string
        r = self._create_extended_NL2_message(self.N_MSG_LOAD_PARK, 43981, msg, len(park)+1)
        #  print "load park r", binascii.hexlify(r),"msg=", binascii.hexlify(msg)
        self.send(r)

        while True:
            self.get_telemetry()
            print self._telemetry_state_flags & 1
            if self._telemetry_state_flags & 1: # test if in play mode
                self.set_manual_mode()
                self.reset_park(True)
                print "set manual mode and reset park"
                break
   

         
    def close_park(self):
        self.send(self._create_simple_message(self.id, self.N_MSG_CLOSE_PARK))

    def set_pause(self, isPaused):
        msg = pack('>?', isPaused) # pause if arg is True
        r = self._create_NL2_message(self.N_MSG_SET_PAUSE, 43981, msg)
        #  print "set pause msg", binascii.hexlify(r)
        self.send(r)

    def reset_park(self, start_paused):
        msg = pack('>?', start_paused) # start paused if arg is True
        r = self._create_NL2_message(self.N_MSG_RESET_PARK, 0, msg)
        #  print "reset park msg", binascii.hexlify(r)
        self.send(r)

    def set_attraction_mode(self, state):
        msg = pack('>?', state)   # enable mode if state True
        r = self._create_NL2_message(self.N_MSG_SET_ATTRACTION_MODE, 0, msg)
        print "set attraction mode msg", binascii.hexlify(r)
        self.send(r)

    def get_telemetry_err_str(self):
        return self.telemetry_err_str

    def get_telemetry_status(self):
        return self.telemetry_err_str

    def _process_telemetry_msg(self, msg):
        #  this version only creates a normalized message
        self._telemetry_state_flags = msg.state
        if(msg.state & 1):  # only process if coaster is in play
            if(False):
                #  code here is non-normalized (real) translation and rotation messages
                quat = Quaternion(msg.quatX, msg.quatY, msg.quatZ, msg.quatW)
                pitch = degrees(quat.toPitchFromYUp())
                yaw = degrees(quat.toYawFromYUp())
                roll = degrees(quat.toRollFromYUp())
                #print format("telemetry %.2f, %.2f, %.2f" % (roll, pitch, yaw))
            else:  # normalize
                quat = Quaternion(msg.quatX, msg.quatY, msg.quatZ, msg.quatW)
                roll = quat.toRollFromYUp() / pi
                pitch = -quat.toPitchFromYUp()  # / pi
                yaw = -quat.toYawFromYUp()                
                if self.prev_yaw != None:
                    time_delta = time() - self.prev_time
                    self.prev_time = time()
                    yaw_rate = self.prev_yaw - yaw
                    # handle crossings between 0 and 360 degrees
                    if yaw_rate  > pi:
                        yaw_rate -= 2*pi
                    if yaw_rate  < -pi:
                        yaw_rate += 2*pi
                    yaw_rate = yaw_rate / time_delta
                else:
                    yaw_rate = 0
                #print yaw,",", yaw_rate,",",
                self.prev_yaw = yaw
                # the following code limits dynamic range nonlinearly
                if yaw_rate > pi:
                   yaw_rate = pi
                elif yaw_rate < -pi:
                    yaw_rate = -pi
                #print yaw_rate,",",
                yaw_rate = yaw_rate / 2
                #print yaw_rate,",",
                if yaw_rate > 0:
                    yaw_rate = sqrt(yaw_rate)
                elif yaw_rate < 0:
                    yaw_rate = -sqrt(-yaw_rate)
                #print yaw_rate
                
                #data = [msg.gForceX, msg.posX, msg.gForceY-1, msg.posY, msg.gForceZ, msg.posZ]
                data = [msg.gForceX, msg.gForceY-1, msg.gForceZ]
                
                #  y from coaster is vertical
                #  z forward
                #  x side               
                if msg.posY > self.lift_height:
                   self.lift_height = msg.posY
                surge = max(min(1.0, msg.gForceZ), -1)
                sway = max(min(1.0, msg.gForceX), -1)
                heave = ((msg.posY * 2) / self.lift_height) -1
                #print "heave", heave

                data = [surge, sway, heave, roll, pitch, yaw_rate]
                intensity_factor = .5  # larger values are more intense
                yaw_rate = yaw_rate * 2 # increase intensity of yaw
                
                formattedData = ['%.3f' % (elem * intensity_factor)  for elem in data]
                isRunning = msg.state == 3        # 3 is running, 7 is paused
                status = [isRunning, msg.speed]
                #print "formatteddata", formattedData
                #  self.coaster_msg_q.put(formattedData)
                return [isRunning, msg.speed, formattedData]

            ##if( msg.posX != 0 and msg.posY !=0):
            ##print msg.posX, msg.posY, msg.posZ, pitch, yaw, roll
            #print "pitch=", degrees( quat.toPitchFromYUp()),quat.toPitchFromYUp(), "roll=" ,degrees(quat.toRollFromYUp()),quat.toRollFromYUp()

    #  see NL2TelemetryClient.java in NL2 distribution for message format
    def _create_simple_message(self, requestId, msg):  # message with no data
        result = pack('>cHIHc', 'N', msg, requestId, 0, 'L')
        return result

    def _create_NL2_message(self, msgId, requestId, msg):  # message is packed
        #  fields are: N Message Id, reqest Id, data size, L
        start = pack('>cHIH', 'N', msgId, requestId, len(msg))
        end = pack('>c', 'L')
        result = start + msg + end
        return result

    def _create_extended_NL2_message(self, msgId, requestId, msg, len):  # message is packed
        #  fields are: N Message Id, reqest Id, data size, L

        start = pack('>cHIH', 'N', msgId, requestId, len)
        end = pack('>c', 'L')
        result = start + msg + end
        return result

if __name__ == "__main__":
    #  identifyConsoleApp()
    coaster = CoasterInterface()
    coaster_thread = threading.Thread(target=coaster.get_telemetry)
    coaster_thread.daemon = True
    coaster_thread.start()

    while True:
        if raw_input('\nType quit to stop this script') == 'quit':
            break
