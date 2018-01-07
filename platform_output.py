"""
platform_output module drives chair with Festo UDP messages

Old and New Festo controllers are supported
The module can also drive a serial platform for testing or demo

Muscle calculations use the following formula to convert % contraction to pressure:
  pressure = 35 * percent*percent + 15 * percent + .03  # assume 25 Newtons for now
percent is calculated as follows:
 percent =  1- (distance + MAX_MUSCLE_LEN - MAX_ACTUATOR_LEN)/ MAX_MUSCLE_LEN
"""

import sys
import socket
import traceback
import math
import time
import copy
import numpy as np
from output_gui import OutputGui
# import matplotlib.pyplot as plt    #  only for testing

TESTING = False
if not TESTING:
    sys.path.insert(0, './fstlib')
    from fstlib import easyip

"""
  Import platform configuration
"""
# from ConfigServo import *
#  from ConfigV1 import *
from ConfigV2 import *
#  from ConfigServoSim import *
#  from ConfigServoSimChair import *

PRINT_MUSCLES = False
PRINT_PRESSURE_DELTA = True
WAIT_FESTO_RESPONSE = False #True
OLD_FESTO_CONTROLLER = False

MONITOR_PORT = 10010 # echo actuator lengths to this port
MONITOR_ADDR = ('localhost', MONITOR_PORT)

if TESTING:
    print "THIS IS TESTING MODE, no output to Festo!!!"
    FST_ip = 'localhost'

print "starting", PLATFORM_NAME
if PLATFORM_NAME == "SERVO_SIM":
    IS_SERIAL = True
    import serial
else:
    IS_SERIAL = False
    print GEOMETRY_TYPE
    if not TESTING:
        if OLD_FESTO_CONTROLLER:
            FST_port = 991
            FST_ip = '192.168.10.10'
            print "using old Festo controller socket at",  FST_ip, FST_port
        else:
            # Set the socket parameters
            FST_ip = '192.168.0.10'
            FST_port = easyip.EASYIP_PORT
            bufSize = 1024
            print "using new Festo controller socket at",  FST_ip, FST_port


class OutputInterface(object):

    #  IS_SERIAL is set True if using serial platform simulator for testing
    global IS_SERIAL

    def __init__(self):
        np.set_printoptions(precision=2, suppress=True)
        self._calculate_geometry()
        self.LIMITS = platform_1dof_limits  # max movement in a single dof
        self.platform_disabled_pos = np.empty(6)   # position when platform is disabled
        self.platform_disabled_pos.fill(DISABLED_LEN)
        self.platform_winddown_pos = np.empty(6)  # position for attaching stairs
        self.platform_winddown_pos.fill(WINDDOWN_LEN)
        self.isEnabled = False  # platform disabled if False
        self.loaded_weight = PLATFORM_UNLOADED_WEIGHT + DEFAULT_PAYLOAD_WEIGHT
        self.prev_pos = [0, 0, 0, 0, 0, 0]  # requested distances stored here
        self.requested_pressures = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.actual_pressures = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.pressure_percent = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.prev_time = time.clock()
        self.netlink_ok = False # True if festo responds without error
        self.ser = None
        self.monitor_client = None
        if MONITOR_PORT:       
            self.monitor_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)              
            print "platform monitor output on port", MONITOR_PORT
        if IS_SERIAL:
            #  configure the serial connection
            try:
                self.ser = serial.Serial(port=OutSerialPort, baudrate=57600, timeout=1)
                print "Serial Output simulator opened on ", OutSerialPort
            except:
                print "unable to open Out simulator serial port", OutSerialPort
        elif not TESTING:
            self.FSTs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.FST_addr = (FST_ip, FST_port)         
            if not OLD_FESTO_CONTROLLER:
                self.FSTs.bind(('0.0.0.0', 0))
                self.FSTs.settimeout(1)  # timout after 1 second if no response
        print ""
        self.prevMsg = []
        self.use_gui = False # defualt is no gui
        self.activate_piston_flag = 0  # park piston is extended when flag set to 1, parked when 0
        
    def init_gui(self, master):
        self.gui = OutputGui()
        self.gui.init_gui(master, MIN_ACTUATOR_LEN, MAX_ACTUATOR_LEN)
        self.use_gui = True
         
    def fin(self):
        """
        free resources used by ths module
        """
        if IS_SERIAL:
            try:
                if self.ser and self.ser.isOpen():
                    self.ser.close()
            except:
                pass
        else:
            if not TESTING:
                self.FSTs.close()
                
    def get_platform_name(self):
         return PLATFORM_NAME

    def get_geometry(self):
        """
        get coordinates of fixed and moving attachment points and mid height
        """
        "platform mid height", self.platform_mid_height 
        return base_pos, platform_pos, self.platform_mid_height 

    def get_actuator_lengths(self):
        return MIN_ACTUATOR_LEN, MAX_ACTUATOR_LEN

    def get_platform_pos(self):
        """
        get coordinates of fixed platform attachment points
        """
        return platform_pos

    def get_output_status(self):
        """
        return string describing output status
        """
        if TESTING:
            return ("Test mode, no output to Festo", "red")
        if OLD_FESTO_CONTROLLER:
            return ("Old Festo Controller", "green3")
        else:
            if WAIT_FESTO_RESPONSE:
                ###self._get_pressure()
                if not self.netlink_ok:
                    return ("Festo network error (check ethernet cable and festo power)", "red")
                else:    
                    bad = []
                    if 0 in self.actual_pressures:
                        for idx, v in enumerate(self.actual_pressures):
                           if v == 0:
                              bad.append(idx)
                        if len(bad) == 6:
                           return ("Festo Pressure Zero on all muscles", "red")
                        else:
                           bad_str = ','.join(map(str, bad))                   
                           return ("Festo Pressure Zero on muscles: " + bad_str, "red")
                    elif any(p < 10 for p in self.pressure_percent):
                        return ("Festo Pressure is Low", "orange")
                    elif any(p < 10 for p in self.pressure_percent):
                        return ("Festo Pressure is High", "orange")
                    else:
                        return ("Festo Pressure is Good", "green3")  # todo, also check if pressure is low
            else:        
                return ("New Festo controller response not enabled", "orange")

    def get_platform_mid_height(self):
        """
        get actuater lengths in mid (ready for ride) position
        """
        return self.platform_mid_height  # height in mm from base at mid position

    def get_limits(self):
        """
        provide limit of movement in all 6 DOF from imported platform config file
        """
        return self.LIMITS

    def set_payload(self, payload_kg):
        """
        set passenger weight in killograms
        """
        self.loaded_weight = PLATFORM_UNLOADED_WEIGHT + payload_kg

    def set_enable(self, state, actuator_lengths):
        """
        enable platform if True, disable if False
        
        actuator_lengths are those needed to achieve current client orientation
        """
        if self.isEnabled != state:
            self.isEnabled = state
            print "Platform enabled state is", state
            if state:
                pass
                #  self._slow_move(self.platform_disabled_pos, actuator_lengths, 1000)
            else:
                self.activate_piston_flag = 0
                self._slow_move(actuator_lengths, self.platform_disabled_pos, 1000)
            
    def move_to_limits(self, pos):
        """
        + or - 1 in [x,y,z,ax,ay,az] moves to that limit, 0 to middle
        Args:
           pos is list of translations and rotations
        """
        self.moveTo([p*l for p, l in zip(pos, self.limits)])

    def move_to_idle(self, client_pos):
       self._slow_move(client_pos, self.platform_disabled_pos, 1000)
       #print "move to idle pos"

    def move_to_ready(self, client_pos):
        self._slow_move(self.platform_disabled_pos, client_pos, 1000)
        #print "move to ready pos"

    def swell_for_access(self, interval):
        """
        Briefly raises platform high enough to insert access stairs
        
        moves even if disabled
        Args:
          interval (int): time in ms before dropping back to start pos
        """       
        self._slow_move(self.platform_disabled_pos, self.platform_winddown_pos, 1000)
        time.sleep(interval)
        self._slow_move(self.platform_winddown_pos, self.platform_disabled_pos, 1000)

    def park_platform(self, state):
        if state:
            self.activate_piston_flag = 0
            print "setting flag to activate pistion to 0"
        else:
            self.activate_piston_flag = 1
            print "setting flag to activate pistion to 1"
            
    def move_platform(self, lengths):  # lengths is list of 6 actuator lengths as millimeters
        """
        Move all platform actuators to the given lengths
        
        Args:
          lengths (float): numpy array comprising 6 actuator lengths
        """
        clipped = []
        for idx, l in enumerate(lengths):
            if l < MIN_ACTUATOR_LEN:
                lengths[idx] = MIN_ACTUATOR_LEN
                clipped.append(idx)
            elif l > MAX_ACTUATOR_LEN:
                lengths[idx] = MAX_ACTUATOR_LEN
                clipped.append(idx)
        if len(clipped) > 0:
            pass
            #  print "Warning, actuators", clipped, "were clipped"
        if self.isEnabled:
            if IS_SERIAL:
                self._move_to_serial(lengths)
            else:
                self._move_to(lengths)  # only fulfill request if enabled
        """
        else:
            print "Platform Disabled"
        """

    def show_muscles(self, position_request, muscles):
        if self.use_gui:
           self.gui.show_muscles(position_request, muscles, self.pressure_percent)
        if self.monitor_client:
            # echo position requests to monitor port if enabled
             xyzrpy = ",".join('%0.3f' % item for item in position_request)             
             lengths = ",".join('%0.1f' % item for item in muscles)        
             msg = "monitor," + xyzrpy + ',' + lengths +'\n'
             # send pos as mm and radians, actuator lengths as mm
             self.monitor_client.sendto(msg, MONITOR_ADDR)
             print msg
        
    #  private methods
    def _slow_move(self, start, end, duration):
        if IS_SERIAL:
            move_func = self._move_to_serial
        else:
            move_func = self._move_to
       
        #  caution, this moves even if disabled
        interval = 50  # time between steps in ms
        steps = duration / interval
        if steps < 1:
            self.move(end)
        else:
            current = start
            print "moving from", start, "to", end, "steps", steps
            delta = [float(e - s)/steps for s, e in zip(start, end)]
            for step in xrange(steps):
                current = [x + y for x, y in zip(current, delta)]
                move_func(copy.copy(current))
                self.show_muscles([0,0,0,0,0,0], current)
                time.sleep(interval / 1000.0)

    def _calculate_geometry(self):
        #  reflect around X axis to generate right side coordinates
        global base_pos, platform_pos
        otherSide = copy.deepcopy(base_pos[::-1])  # order reversed
        for inner in otherSide:
            inner[1] = -inner[1]   # negate Y values
        base_pos.extend(otherSide)

        otherSide = copy.deepcopy(platform_pos[::-1])  # order reversed
        for inner in otherSide:
            inner[1] = -inner[1]   # negate Y values
        platform_pos.extend(otherSide)

        base_pos = np.array(base_pos)
        platform_pos = np.array(platform_pos)

        #  print "\nPlatformOutput using %s configuration" %(PLATFORM_NAME)
        #  print "Actuator lengths: Min %d, Max %d, mid %d" %( MIN_ACTUATOR_LEN, MAX_ACTUATOR_LEN, MID_ACTUATOR_LEN)

        self.platform_mid_height = platform_mid_height

        #  uncomment this section to plot the array coordinates
        """
        bx= base_pos[:,0]
        by = base_pos[:,1]
        plt.scatter(bx,by)
        px= platform_pos[:,0]
        py = platform_pos[:,1]
        plt.axis('equal')
        plt.scatter(px,py)
        plt.show()
        """

        #  print "base_pos:\n",base_pos
        #  print "platform_pos:\n",platform_pos

    def _move_to_serial(self, lengths):
        # msg = "xyzrpy," + ",".join([str(round(item)) for item in lengths])
        payload =   ",".join('%0.1f' % item for item in lengths)
        if payload != self.prevMsg:
            print "lengths: ", payload
            self.prevMsg = payload
        if self.ser and self.ser.isOpen():
            self.ser.write("xyzrpy," + payload + '\n')          
            #  print self.ser.readline()
        else:
            print "serial not open"

    def _move_to(self, lengths):
        print "lengths:\t ", ",".join('  %d' % item for item in lengths)
        now = time.clock()
        timeDelta = now - self.prev_time
        self.prev_time = now
        load_per_muscle = self.loaded_weight / 6  # if needed we could calculate individual muscle loads
        pressure = []
        #  print "LENGTHS = ",lengths
        for idx, len in enumerate(lengths):           
            pressure.append(int(1000*self._convert_MM_to_pressure(idx, len-FIXED_LEN, timeDelta, load_per_muscle)))
        self._send(pressure)

    def _convert_MM_to_pressure(self, idx, muscle_len, timeDelta, load):
        #  returns pressure in bar
        #  calculate the percent of muscle contraction to give the desired distance
        percent = (MAX_MUSCLE_LEN - muscle_len) / float(MAX_MUSCLE_LEN)
        #  check for range between 0 and .25
        #  print "muscle Len =", muscle_len, "percent =", percent
        if percent < 0 or percent > 0.25:
            print "%.2f percent contraction out of bounds for muscle length %.1f" % (percent, muscle_len)
        distDelta = muscle_len-self.prev_pos[idx]  # the change in length from the previous position
        accel = (distDelta/1000) / timeDelta  # accleration units are meters per sec

        if distDelta < 0:
            force = load * (1-accel)  # TODO  here we assume force is same magnitude as expanding muscle ???
            #  TODO modify formula for force
            #  pressure = 30 * percent*percent + 12 * percent + .01  # assume 25 Newtons for now
            pressure = 35 * percent*percent + 15 * percent + .03  # assume 25 Newtons for now
            if PRINT_MUSCLES:
                print("muscle %d contracting %.1f mm to %.1f, accel is %.2f, force is %.1fN, pressure is %.2f"
                      % (idx, distDelta, muscle_len, accel, force, pressure))
        else:
            force = load * (1+accel)  # force in newtons not yet used
            #  TODO modify formula for expansion
            pressure = 35 * percent*percent + 15 * percent + .03  # assume 25 Newtons for now
            if PRINT_MUSCLES:
                print("muscle %d expanding %.1f mm to %.1f, accel is %.2f, force is %.1fN, pressure is %.2f"
                      % (idx, distDelta, muscle_len, accel, force, pressure))

        self.prev_pos[idx] = muscle_len  # store the muscle len
        MAX_PRESSURE = 6.0 
        MIN_PRESSURE = .05  # 50 millibar is minimin pressure
        pressure = max(min(MAX_PRESSURE, pressure), MIN_PRESSURE)  # limit range 
        return pressure

    def _send(self, muscle_pressures):
        self.requested_pressures = muscle_pressures  # store this for display if reqiured
        if not TESTING:
            try:
                if not OLD_FESTO_CONTROLLER:
                    muscle_pressures.append(self.activate_piston_flag)
                    print "muscle pressures:",  muscle_pressures
                    packet = easyip.Factory.send_flagword(0, muscle_pressures)
                    try:
                        self._send_packet(packet)
                        if WAIT_FESTO_RESPONSE:
                            self.actual_pressures = self._get_pressure()
                            delta = [act - req for req, act in zip(muscle_pressures, self.actual_pressures)]
                            # todo - next line needs changing because park flag now appended to list
                            self.pressure_percent = [int(d * 100 / req) for d, req in zip(delta, muscle_pressures)]
                            if PRINT_PRESSURE_DELTA:
                                print muscle_pressures, delta, self.pressure_percent

                    except socket.timeout:
                        print "timeout waiting for replay from", self.FST_addr

                else:
                    for idx, muscle in enumerate(muscle_pressures):
                        maw = int(muscle*1000)
                        maw = max(min(6000, muscle), 0)  # limit range to 0 to 6000
                        command = "maw"+str(64+idx)+"="+str(maw)
                        #  print command,
                        command = command + "\r\n"
                        self.FSTs.sendto(command, self.FST_addr)
            except:
                e = sys.exc_info()[0]
                s = traceback.format_exc()
                print "error sending to Festo", e, s

    def _send_packet(self, packet):
        if not TESTING:
            data = packet.pack()
            #  print "sending to", self.FST_addr
            self.FSTs.sendto(data, self.FST_addr)
            if WAIT_FESTO_RESPONSE:
                #  print "in sendpacket,waiting for response..."
                data, srvaddr = self.FSTs.recvfrom(bufSize)
                resp = easyip.Packet(data)
                #  print "in senddpacket, response from Festo", resp
                if packet.response_errors(resp) is None:
                    self.netlink_ok = True
                    #  print "No send Errors"
                else:
                    self.netlink_ok = False
                    print "errors=%r" % packet.response_errors(resp)
            else:
                resp = None
            return resp

    def _get_pressure(self):
        # first arg is the number of requests your making. Leave it as 1 always
        # Second arg is number of words you are requesting (probably 6, or 16)
        # third arg is the offset.
        # words 0-5 are what you sent it.
        # words 6-9 are not used
        # words 10-15 are the current values of the presures
        # packet = easyip.Factory.req_flagword(1, 16, 0)
        if TESTING:
            return self.requested_pressures  # TEMP for testing
        #  print "attempting to get pressure"
        try:
            packet = easyip.Factory.req_flagword(1, 6, 10)
            resp = self._send_packet(packet)
            values = resp.decode_payload(easyip.Packet.DIRECTION_REQ)
            #  print list(values)
            return list(values)
        except socket.timeout:
            print "timeout waiting for Pressures from Festo"
        return [0,0,0,0,0,0]
