"""
coaster_interface module

This version requires NoLimits attraction license and NL ver 2.5.3.5 or later
"""

import socket
from time import time,sleep
from struct import *
import collections
from quaternion import Quaternion
from math import pi, degrees, sqrt
import sys
import threading
import ctypes #  for bit fields
import os
#import pc_address  # address of pc running NL2
from coaster_state import ConnectStatus # bit mask defs

import  binascii  # only for debug
import traceback

# bit fields for station message
bit_e_stop = 0x1
bit_manual = 0x2
bit_can_dispatch = 0x4
bit_gates_can_close = 0x8
bit_gates_can_open = 0x10
bit_harness_can_close = 0x20
bit_harness_can_open = 0x40
bit_platform_can_raise = 0x80
bit_platform_can_lower = 0x100
bit_flyercar_can_lock =  0x200
bit_flyercar_can_unlock = 0x400
bit_train_in_station = 0x800
bit_current_train_in_station = 0x1000

class CoasterInterface():

    N_MSG_OK = 1
    N_MSG_ERROR = 2
    N_MSG_GET_VERSION = 3 # datasize 0
    N_MSG_VERSION = 4
    N_MSG_GET_TELEMETRY = 5  # datasize 0
    N_MSG_TELEMETRY = 6
    N_MSG_GET_STATION_STATE = 14 #size=8 (int32=coaster index, int32=station index)
    N_MSG_STATION_STATE = 15 #DataSize = 4 
    N_MSG_SET_MANUAL_MODE = 16 # datasize 9
    N_MSG_DISPATCH = 17  # datasize 8
    N_MSG_SET_PLATFORM = 20  # datasize 9
    N_MSG_LOAD_PARK = 24   # datasize 1 + string 
    N_MSG_CLOSE_PARK = 25  # datasize 0
    N_MSG_SET_PAUSE = 27   # datasize 1
    N_MSG_RESET_PARK = 28  # datasize 1
    N_MSG_SELECT_SEAT = 29 # datasize = 16 
    N_MSG_SET_ATTRACTION_MODE = 30   # datasize 1
    N_MSG_RECENTER_VR = 31 # datasize 0
    
    c_nExtraSizeOffset = 9  # Start of extra size data within message

    telemetryMsg = collections.namedtuple('telemetryMsg', 'state, frame, viewMode, coasterIndex,\
                                           coasterStyle, train, car, seat, speed, posX, posY,\
                                           posZ, quatX, quatY, quatZ, quatW, gForceX, gForceY, gForceZ')

    def __init__(self):
        self.coaster_buffer_size = 1024
        #self.coaster_ip_addr = pc_address._ip_address  #'localhost'
        self.coaster_port = 15151
        self.interval = .05  # time in seconds between telemetry requests
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.settimeout(3)
        self.telemetry_err_str = "Waiting to connect to NoLimits Coaster"
        self.telemetry_status_ok = False
        self.formattedData = None
        self._telemetry_state_flags = 0
        self.prev_yaw = None
        self.prev_time = time()
        self.lift_height = 32  # max height in meters
        self.pause_mode = False  # for toggle todo replace with explicit pause state
        # self.is_play_mode = False # set to true if NL2 telemetry is in play mode
        self.station_status = 0
        self.coaster_status = 0
        self.nl2_version = None
        #self.can_dispatch = None  # set true when it station ready for dispatch
        #self.train_in_station = None # true when the riders train is in the station
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.client.settimeout(3)

    def begin(self):
        return
        """
        print "todo fix itf begin"
        return True
        print "3 in coaster interface begin"
        if self.connect_to_coaster(ip_addr):
            # print "connect_to_coaster returned True"
            self.get_telemetry()
            #  print "telemetry flags = ", self._telemetry_state_flags
            if self._telemetry_state_flags & 1:
                return True
        else:
            #  print "coaster status mask:", self.coaster_status
            return False
        """
 
    def connect_to_coaster(self, coaster_ip_addr):
        # returns true iff connected to NL2 derver socket and in play mode        
        if self.check_coaster_status(ConnectStatus.is_pc_connected) == False:
            print "Not connected to VR PC"
            return False
        if self.check_coaster_status(ConnectStatus.is_nl2_connected) == False:
            try:
                print "attempting connect to NoLimits"
                self.client.connect((coaster_ip_addr, self.coaster_port))
                # here if client connected to NL2
                self.set_coaster_status(ConnectStatus.is_nl2_connected, True)
            except Exception, e:
                self.set_coaster_status(ConnectStatus.is_nl2_connected, False)
                print "error connecting to NoLimits", e
                return False

        self.get_telemetry()
        #  print "telemetry flags = ", self._telemetry_state_flags 
        return self.check_coaster_status(ConnectStatus.is_in_play_mode)

    def set_coaster_status(self, flag_bit, state):
        if state:
            self.coaster_status |= flag_bit
        else:
            self.coaster_status &= ~flag_bit

    def check_coaster_status(self, flag_bit ):
        return  (self.coaster_status & flag_bit) != 0

    def get_coaster_status(self):
        if not self.check_coaster_status(ConnectStatus.is_pc_connected):
            return (False, "Not connected to VR server", "red")
        if not self.check_coaster_status(ConnectStatus.is_nl2_connected):
            return (False, "Not connected to NoLimits server", "red")
        if not self.check_coaster_status(ConnectStatus.is_in_play_mode):
            return (False, "NoLimits is not in play mode", "red")
        return (True, "Receiving NoLimits Telemetry", "green3")

    def send(self, r):
        try:
            self.client.sendall(r)
        except:
            e = sys.exc_info()[0]  # report error           
            # print e

    def dispatch(self):
        msg = pack('>ii', 0, 0)  # coaster, station
        r = self._create_NL2_message(self.N_MSG_DISPATCH, self.N_MSG_DISPATCH, msg)
        #  print "dispatch msg",  binascii.hexlify(msg),len(msg), "full", binascii.hexlify(r)
        self.send(r)

        #  self.send_windows_key(0x17, ord('I'))

    def _get_station_status(self, status_mask):
        if not self.is_in_play_mode():
            return False
        msg = pack('>ii', 0, 0)  # coaster, station
        r = self._create_NL2_message(self.N_MSG_GET_STATION_STATE, self.N_MSG_GET_STATION_STATE, msg)
        #  print "get station state msg", self.N_MSG_GET_STATION_STATE,  binascii.hexlify(msg),len(msg), "full", binascii.hexlify(r)
        self.send(r)       
        #  self._process_station_state_msgs()
        self._process_telemtry_msgs()
        #  print "station status", self.station_status
        if self.coaster_status != 7: # connected and in play mode
            return False
        #  print format("in get station status %x" % (self.station_status))
        if self.station_status & bit_manual != bit_manual:
            self.set_manual_mode()
            sleep(0.1)
        #  print format("station status %x" % (self.station_status))
        return self.station_status & status_mask == status_mask # return true if all bits are set

    def is_train_in_station(self):
        # print "is train in station", self._get_station_status(bit_train_in_station), self._get_station_status( bit_current_train_in_station)
        ret = self._get_station_status(bit_train_in_station | bit_current_train_in_station)
        return ret
    
    def prepare_for_dispatch(self):
        if self._get_station_status(bit_platform_can_lower):
            self.disengageFloor()
            return False
        elif self._get_station_status(bit_harness_can_close):
            self.close_harness()
            return False
        else:
            can_dispatch = self._get_station_status(bit_can_dispatch)
            print "can dispatch", can_dispatch
            return can_dispatch

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
        r = self._create_NL2_message(self.N_MSG_SET_PLATFORM, self.N_MSG_SET_PLATFORM, msg)
        #  print "set platform msg", binascii.hexlify(r)
        self.send(r)

    def set_manual_mode(self):
        msg = pack('>ii?', 0, 0, True)  # coaster, car, True sets manual mode, false sets auto
        r = self._create_NL2_message(self.N_MSG_SET_MANUAL_MODE, self.N_MSG_SET_MANUAL_MODE, msg)
        #  print "set mode msg", binascii.hexlify(r)
        self.send(r)

    def reset_rift(self):
        self.send(self._create_simple_message(self.N_MSG_RECENTER_VR, self.N_MSG_RECENTER_VR))
        print "reset rift"


    def _process_station_state_msgs(self):
        try:
            data = self.client.recv(self.coaster_buffer_size)
            if data: #and len(data) >= 10:
                # print "data len",len(data)
                msg, requestId, size = (unpack('>HIH', data[1:9]))
                # print " in process station state", msg, requestId, size
                if msg == self.N_MSG_STATION_STATE:
                    s = unpack('>I', data[self.c_nExtraSizeOffset:self.c_nExtraSizeOffset+4])
                    # print "got station state msg", s[0]
                    self.station_status = s[0]
        except socket.error:
            print "Connection to NoLimits broken while processing station state msgs"

            
    def _process_telemtry_msgs(self):
        try:
            data = self.client.recv(self.coaster_buffer_size)
            if data: #and len(data) >= 10:
                #print "data len",len(data)
                msg, requestId, size = (unpack('>HIH', data[1:9]))
                # print msg, requestId, size
                if msg == self.N_MSG_VERSION:
                    v0, v1, v2, v3 = unpack('cccc', data[self.c_nExtraSizeOffset:self.c_nExtraSizeOffset+4])
                    self.nl2_verson = format("%c.%c.%c.%c" % (chr(ord(v0)+48),chr(ord(v1)+48),chr(ord(v2)+48), chr(ord(v3)+48)))
                    print 'NL2 version', self.nl2_verison
                    self.set_coaster_status(ConnectStatus.is_nl2_connected, True)
                    #self.send(self._create_simple_message(self.N_MSG_GET_TELEMETRY, self.N_MSG_GET_TELEMETRY))
                elif msg == self.N_MSG_STATION_STATE:
                    s = unpack('>I', data[self.c_nExtraSizeOffset:self.c_nExtraSizeOffset+4])
                    #  print format( "in telemetry, got station state msg %x" % (s[0]))
                    self.station_status = s[0]
                elif msg == self.N_MSG_TELEMETRY:
                    if size == 76:
                        t = (unpack('>IIIIIIIIfffffffffff', data[self.c_nExtraSizeOffset:self.c_nExtraSizeOffset+76]))
                        tm = self.telemetryMsg._make(t)
                        #print "tm", tm
                        self.formattedData = self._process_telemetry_msg(tm)
                        self.telemetry_status_ok = True
                        #self.is_play_mode = True
                        #self.set_coaster_status(ConnectStatus.is_nl2_connected, True)
                        self.set_coaster_status(ConnectStatus.is_in_play_mode, True)
                        #  print "telemetry ", self.telemetry_status_ok 
                    else:
                        print 'invalid msg len expected 76, got ', size
                    #sleep(self.interval)
                    #self.send(self._create_simple_message(self.N_MSG_GET_TELEMETRY, self.N_MSG_GET_TELEMETRY))
                elif msg == self.N_MSG_OK:
                    self.telemetry_status_ok = True
                    self.set_coaster_status(ConnectStatus.is_nl2_connected, True)
                    pass
                elif msg == self.N_MSG_ERROR:
                    self.telemetry_status_ok = False     
                    self.telemetry_err_str = data[self.c_nExtraSizeOffset: self.c_nExtraSizeOffset+size]
                    print "telemetry err:", self.telemetry_err_str
                    #if "Not in play mode" in self.telemetry_err_str:
                    #self.is_play_mode = False
                    #self.set_coaster_status(ConnectStatus.is_nl2_connected, True)
                    #self.set_coaster_status(ConnectStatus.is_in_play_mode, False)
                else:
                    print 'unhandled message', msg
        except socket.error:
            #  print "Connection to NoLimits broken"
            self.set_coaster_status(ConnectStatus.is_nl2_connected, False)
        

    def get_telemetry(self):
        self.send(self._create_simple_message(self.N_MSG_GET_TELEMETRY,self.N_MSG_GET_TELEMETRY))
        self._process_telemtry_msgs()
        return self.formattedData

    def get_nl2_version(self):
        self.nl2_version = None
        self.send(self._create_simple_message(self.N_MSG_GET_VERSION,self.N_MSG_GET_VERSION))
        sleep(0.1)
        self._process_telemtry_msgs()
        return self.nl2_version

            
    def load_park(self, isPaused, park):
        #  print "in load park", park
        path = park
        #  print path
        start = time()
        msg = pack('>?', isPaused) + path  # start in pause, park string
        #  print msg
        r = self._create_extended_NL2_message(self.N_MSG_LOAD_PARK, 43981, msg, len(path)+1)
        #  print "load park r", binascii.hexlify(r),"msg=", binascii.hexlify(msg)
        self.send(r)

        while True:
            self.get_telemetry()
            #  print self._telemetry_state_flags & 1
            print ".",
            sleep(1)
            if self.check_coaster_status(ConnectStatus.is_in_play_mode):
            # was if self._telemetry_state_flags & 1: # test if in play mode
                self.set_manual_mode()
                if self._get_station_status(bit_manual):
                   self.reset_park(True)
                   print "\nset manual mode and reset park"
                   break

    def close_park(self):
        self.send(self._create_simple_message(self.N_MSG_CLOSE_PARK, self.N_MSG_CLOSE_PARK))

    def set_pause(self, isPaused):
        msg = pack('>?', isPaused) # pause if arg is True
        r = self._create_NL2_message(self.N_MSG_SET_PAUSE, self.N_MSG_SET_PAUSE, msg)
        #  print "set pause msg", binascii.hexlify(r)
        self.send(r)
        self.pause_mode = isPaused

    def reset_park(self, start_paused):
        msg = pack('>?', start_paused) # start paused if arg is True
        r = self._create_NL2_message(self.N_MSG_RESET_PARK, self.N_MSG_RESET_PARK, msg)
        #  print "reset park msg", binascii.hexlify(r)
        self.send(r)

    def select_seat(self, seat):
        msg = pack('>iiii', 0, 0, 0, seat)  # coaster, train, car, seat 
        r = self._create_NL2_message(self.N_MSG_SELECT_SEAT, self.N_MSG_SELECT_SEAT, msg)
        #  print "select seat msg",  binascii.hexlify(msg),len(msg), "full", binascii.hexlify(r)
        self.send(r)

    def set_attraction_mode(self, state):
        msg = pack('>?', state)   # enable mode if state True
        r = self._create_NL2_message(self.N_MSG_SET_ATTRACTION_MODE, self.N_MSG_SET_ATTRACTION_MODE, msg)
        print "set attraction mode msg", binascii.hexlify(r)
        self.send(r)

    def get_telemetry_err_str(self):
        return self.telemetry_err_str

    def get_telemetry_status(self):
        return self.telemetry_err_str


    def is_in_play_mode(self):
        return self.check_coaster_status(ConnectStatus.is_in_play_mode)
        """
        print "todo remove telemetry_state_flags and change is_in_play to use bitmap, returning ", (self._telemetry_state_flags & 1) != 0
        #print repr(traceback.extract_tb(exc_traceback))
        #sys.exit()
        return (self._telemetry_state_flags & 1) != 0
        
        """
        

    def _process_telemetry_msg(self, msg):
        """
        returns four fields:
            boolean indicating if NL2 is in play mode
            boolean indicating if coaster is running (not paused)
            float  coaster speed in meters per seconds
            list of the six xyzrpy values
        """
        self._telemetry_state_flags = msg.state
        is_play_mode = (msg.state & 1) != 0
        if is_play_mode:  # only process if coaster is in play
            self.set_coaster_status(ConnectStatus.is_in_play_mode, True)
            if(False): # set this to True to use real world values (not supported in this version)
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
                ##if msg.speed < 001:
                ##  self.get_station_state()
                   
                status = [isRunning, msg.speed]
                #print "formatteddata", formattedData
                #  self.coaster_msg_q.put(formattedData)
                return [is_play_mode, isRunning, msg.speed, formattedData]

            ##if( msg.posX != 0 and msg.posY !=0):
            ##print msg.posX, msg.posY, msg.posZ, pitch, yaw, roll
            #print "pitch=", degrees( quat.toPitchFromYUp()),quat.toPitchFromYUp(), "roll=" ,degrees(quat.toRollFromYUp()),quat.toRollFromYUp()
        #  print "in telemetry, Coaster not in play mode"
        self.set_coaster_status(ConnectStatus.is_in_play_mode, False)
        return [False, False, 0, None]

    #  see NL2TelemetryClient.java in NL2 distribution for message format
    def _create_simple_message(self, msgId, requestId):  # message with no data
        result = pack('>cHIHc', 'N', msgId, requestId, 0, 'L')
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
