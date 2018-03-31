"""
 coaster_client control module for NoLimits2.
 
 module coordinates chair activity with logical coaster state 
This version requires NoLimits attraction license and NL ver 2.5.3.5 or later
"""

import sys
import socket
import time
import ctypes
import tkMessageBox

#from coaster_interface import CoasterInterface
from nl2_interface import CoasterInterface

from coaster_gui import CoasterGui
from coaster_state import ConnectStatus, RideState
from serial_remote import SerialRemote

#import pc_address

from pc_monitor import pc_monitor_client
heartbeat = pc_monitor_client((40,60),(75,90))

class CoasterEvent:
    ACTIVATED, DISABLED, PAUSED, UNPAUSED, DISPATCHED, ESTOPPED, STOPPED, RESETEVENT = range(8)

CoasterEventStr = ("ACTIVATED", "DISABLED", "PAUSED", "UNPAUSED", "DISPATCHED", "ESTOPPED", "STOPPED", "RESETEVENT")


#  this state machine determines current coaster state from button and telemetry events
class State(object):
    def __init__(self, position_requestCB):
        self._state = None
        self._state = RideState.DISABLED
        self.position_requestCB = position_requestCB
        self.is_chair_active = False
        self.prev_event = None  # only used for debug

    @property
    def state(self):
        """the 'state' property."""
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

    def set_is_chair_active(self, isActive):
        self.is_chair_active = isActive

    def __str__(self):
        return self.string(self._state)

    @staticmethod
    def string(state):
        return ("Disabled", "ReadyForDispatch", "Running", "Paused",
                "EmergencyStopped", "Resetting")[state]

    def coaster_event(self, event):
        if event != self.prev_event:
            self.prev_event = event
            #  print "coaster event is",CoasterEventStr[event], "active state is", self.is_chair_active
        if self.is_chair_active:
            if event == CoasterEvent.STOPPED and self._state != RideState.READY_FOR_DISPATCH:
                #  here if stopped at station
                self._state = RideState.READY_FOR_DISPATCH
                self._state_change()
            elif event == CoasterEvent.DISPATCHED and self._state != RideState.RUNNING:
                self._state = RideState.RUNNING
                self._state_change()
            elif event == CoasterEvent.PAUSED and self._state != RideState.PAUSED:
                self._state = RideState.PAUSED
                self._state_change()
            elif event == CoasterEvent.UNPAUSED and self._state == RideState.PAUSED:
                self._state = RideState.RUNNING
                self._state_change()
            elif event == CoasterEvent.DISABLED and self._state != EMERGENCY_STOPPED:
                self._state = RideState.EMERGENCY_STOPPED
                self._state_change()

        else:
            #  things to do if chair has been disabled:
            if event == CoasterEvent.RESETEVENT and self._state != RideState.RESETTING:
                #  print "resetevent, state  = ", self._state
                if self._state == RideState.DISABLED:
                    print "here if coaster moving at startup"
                self._state = RideState.RESETTING
                #  print "got reset event"
                self._state_change()
            elif event == CoasterEvent.ESTOPPED and self._state != RideState.EMERGENCY_STOPPED:
                self._state = RideState.EMERGENCY_STOPPED
                self._state_change()
            if event == CoasterEvent.STOPPED and self._state != RideState.READY_FOR_DISPATCH:
                #  here if stopped at station
                # print "stopped at station while deactivated, state = ", self._state
                self._state = RideState.READY_FOR_DISPATCH
                self._state_change()
                #  print "state=", self.state

    def _state_change(self):
        if self.position_requestCB is not None:
            self.position_requestCB(self._state)  # tell user interface that state has changed

colors = ["green3","orange","red"] # for warning level text

class InputInterface(object):
    USE_GUI = True

    def __init__(self):
        self.cmd_func = None
        self.is_normalized = True
        self.current_pos = []
        self.is_chair_activated = False
        self.coaster = CoasterInterface()
        self.gui = CoasterGui(self.dispatch, self.pause, self.reset, self.set_activate_state, self.quit)
        actions = {'detected remote': self.detected_remote, 'activate': self.activate,
                   'deactivate': self.deactivate, 'pause': self.pause, 'dispatch': self.dispatch,
                   'reset': self.reset, 'emergency_stop': self.emergency_stop, 'intensity' : self.set_intensity}
        self.RemoteControl = SerialRemote(actions)
        self.prev_movement_time = 0  # holds the time of last reported movement from NoLimits
        self.isNl2Paused = False
        self.speed = 0
        self.isLeavingStation = False  # set true on dispatch, false when no longer in station
        self.coasterState = State(self.process_state_change)
        self.rootTitle = "NL2 Coaster Ride Controller"  # the display name in tkinter
        self.prev_heartbeat = 0
        self.server_address = None # set on receipt of hearbeat from server

    def init_gui(self, master):
        self.gui.init_gui(master)
        self.master = master

    def connection_msgbox(self, msg):
        result = tkMessageBox.askquestion(msg, icon='warning')
        return result != 'no'

    def _sleep_func(self, duration):
        start = time.time()
        while time.time() - start < duration:
            self.master.update_idletasks()
            self.master.update()

    def command(self, cmd):
        if self.cmd_func is not None:
            print "Requesting command:", cmd
            self.cmd_func(cmd)

    def dispatch(self):
        if self.is_chair_activated and self.coasterState.state == RideState.READY_FOR_DISPATCH:
            print 'dispatch'
            self.coasterState.coaster_event(CoasterEvent.DISPATCHED)
            print "preparing to dispatch"
            while not self.coaster.prepare_for_dispatch():
                 self._sleep_func(1)
            self.command("ready")  # slow rise of platform
            self.command("unparkPlatform")
            print "todo check delay is needed to free platform"
            #  self._sleep_func(1)
            self.coaster.dispatch()
            print "dispatched"
            self.prev_movement_time = time.time()  # set time that train started to move
            self.isLeavingStation = True
            while self.coaster.is_train_in_station():
                print "Leaving station"
                pass
            """
            while self.coaster.train_in_station:
                self.coaster.get_station_state()
                print "sent get station state"
                print "todo - exit and handle if not ready to dispatch"
                self.service()
            """
            self.isLeavingStation = False
            print "left station"

    def pause(self):
        if self.coasterState.state  == RideState.RUNNING:
            self.coaster.set_pause(True)
        elif self.coasterState.state == RideState.PAUSED:
            self.coaster.set_pause(False)
        elif self.coasterState.state == RideState.READY_FOR_DISPATCH:
            self.command("swellForStairs")

    def reset(self):
        self.coaster.reset_rift()

    def set_intensity(self, intensity_msg):
        self.command(intensity_msg)

    def emergency_stop(self):
        print "legacy emergency stop callback"
        self.deactivate()

    def set_activate_state(self, state):
        #  print "in setActivatedState", state
        if state:
            self.activate()
        else:
            self.deactivate()

    def activate(self):
        #  only activate if coaster is ready for dispatch
        #  print "in activate state= ", self.coasterState.state
        print "resetting park in manual mode"
        #self.coaster.set_manual_mode()
        self.coaster.reset_park(False)
        self.coasterState.coaster_event(CoasterEvent.RESETEVENT)
        ####if self.coasterState.state == RideState.READY_FOR_DISPATCH:
        #  print "in activate "
        self.is_chair_activated = True
        self.coasterState.set_is_chair_active(True)
        self.command("enable")
        self.gui.set_activation_buttons(True)
        self.gui.process_state_change(self.coasterState.state, True)
        #  print "in activate", str(RideState.READY_FOR_DISPATCH), RideState.READY_FOR_DISPATCH
        self.RemoteControl.send(str(RideState.READY_FOR_DISPATCH))

    def deactivate(self):
        #  print "in deactivate "
        if self.coasterState.state == RideState.READY_FOR_DISPATCH:
            self.RemoteControl.send(str(RideState.DISABLED))
        self.command("disable")
        self.gui.set_activation_buttons(False)
        self.is_chair_activated = False
        self.coasterState.set_is_chair_active(False)
        if self.coasterState.state == RideState.RUNNING or self.coasterState.state == RideState.PAUSED:
            if self.coasterState.state != RideState.PAUSED:
                self.pause()
            print 'emergency stop '
            self.coasterState.coaster_event(CoasterEvent.ESTOPPED)
        else:
            self.coasterState.coaster_event(CoasterEvent.DISABLED)
        self.gui.process_state_change(self.coasterState.state, False)

    def quit(self):
        self.command("quit")

    def detected_remote(self, info):
        if "Detected Remote" in info:
            self.set_remote_status_label((info, "green3"))
        elif "Looking for Remote" in info:
            self.set_remote_status_label((info, "orange"))
        else:
            self.set_remote_status_label((info, "red"))

    def set_coaster_connection_label(self, label):
        self.gui.set_coaster_connection_label(label)

    def chair_status_changed(self, status):
        self.gui.chair_status_changed(status)

    def temperature_status_changed(self, status):
        self.gui.temperature_status_changed(status)

    def intensity_status_changed(self, status):
        self.gui.intensity_status_changed(status)

    def set_remote_status_label(self, label):
        self.gui.set_remote_status_label(label)

    def process_state_change(self, new_state):
        #  print "in process state change", new_state, self.is_chair_activated
        if new_state == RideState.READY_FOR_DISPATCH:
            if self.is_chair_activated:
                #  here at the end of a ride
                self.command("idle")  # slow drop of platform
                self.RemoteControl.send(str(RideState.READY_FOR_DISPATCH))
            else:
                self.RemoteControl.send(str(RideState.DISABLED)) # at station but deactivated
        else: 
            self.RemoteControl.send(str(new_state))

        self.gui.process_state_change(new_state, self.is_chair_activated)

    def load_park(self, isPaused, park, seat):

        print "load park", park, "seat",seat
        self.coasterState.coaster_event(CoasterEvent.RESETEVENT) 
        self.gui.set_coaster_connection_label(("loading: " + park, "orange"))
        self._sleep_func(2)
        self.coaster.load_park(isPaused, park)
        while self.coaster.check_coaster_status(ConnectStatus.is_in_play_mode) == False:
            self.service()
        print "selecting seat", seat
        self.coaster.select_seat(int(seat))
        self.coasterState.coaster_event(CoasterEvent.STOPPED)

    def fin(self):
        # client exit code goes here
        heartbeat.fin()

    def get_current_pos(self):
        return self.current_pos

    def begin(self, cmd_func, move_func, limits):      
        self.cmd_func = cmd_func
        self.move_func = move_func
        #self.limits = limits
        heartbeat.begin()
        self.coaster.begin()
        self.gui.set_park_callback(self.load_park)
        while not self.connect():
             self._sleep_func(0.1)
        self.coaster.reset_park(False)
        return True  # now always returns true, connections are completed in service if necessary
    
    def check_heartbeat(self):
        addr, heartbeat_status, warning = heartbeat.read()
        #  print "in connect, addr = ", addr,  addr[1] == 10011
        if len(addr[0]) > 6 and addr[1]  == 10011: #  server sends on port 10011
            self.prev_heartbeat = time.time()
            if self.server_address != addr[0]:
                self.server_address = addr[0]
                print "first time connection to server @", self.server_address
            #  print format("heartbeat {%s:%s} {%s} {%s}" % (addr[0], addr[1], heartbeat_status, warning))
            self.gui.set_coaster_connection_label((heartbeat_status,colors[warning]))
            self.temperature_status_changed((heartbeat_status, colors[warning]))
            self.coaster.set_coaster_status(ConnectStatus.is_pc_connected, True)

        # print "t=", time.time() - self.prev_heartbeat
        duration = time.time() - self.prev_heartbeat
        if duration > 3.2: # if no heartbeat after three seconds
            self.coaster.set_coaster_status(ConnectStatus.is_pc_connected, False)
            self.temperature_status_changed(("Lost heartbeat with server", "red"))
            return False
        elif duration > 2.2: # if no heartbeat after two seconds
            self.temperature_status_changed(("Missed Heartbeat from Server", "orange"))
            self.gui.set_coaster_connection_label(("Attempting to connect to No Limits", "red"))
        return True

    def connect(self):
        if not self.check_heartbeat():
            return False
        elif not self.coaster.check_coaster_status(ConnectStatus.is_nl2_connected):
            if not self.coaster.connect_to_coaster(self.server_address):
                print "coaster connect returned false!!!!!!" 
                self.gui.set_coaster_connection_label(("No connection to NoLimits, is it running?", "red"))
                self._sleep_func(1)
            return False
            """    
            elif not self.coaster.check_coaster_status(ConnectStatus.is_in_play_mode):
                print "!!!NL2 not in play mode"
                return False
            """
        else:
            #  print "All connections ok"
            # self.coasterState.coaster_event(CoasterEvent.STOPPED)
            return True


    def check_is_stationary(self, speed):
        if speed < 0.1:
            #if self.coaster.get_station_status(bit_train_in_station | bit_current_train_in_station):
            if self.coaster.is_train_in_station():
                #  print "in station check, leaving flag is", self.isLeavingStation, speed
                if self.isLeavingStation == False:
                   #  print "in station check, state is ",  self.coasterState
                   if self.coasterState.state == RideState.RUNNING:
                       print "train arrived in station"
                       self.command("parkPlatform")
                       print "Todo check if swell or delay is needed here"
                       return True
                ##print "CAN DISPATCH"
            else:
                #  print "in station check, setting leaving flag to false"  
                self.isLeavingStation = False

            if time.time() - self.prev_movement_time > 3:
                #  print "speed", speed
                return True
        else:
            self.prev_movement_time = time.time()
            self.gui.set_coaster_status_label(speed)
        return False

    def service(self):
        self.RemoteControl.service()
        if self.connect():
            self.coaster.service()
            status  = self.coaster.get_coaster_status()
            self.gui.set_coaster_connection_label((status[1], status[2]))
            input_field = self.coaster.get_telemetry()
            # print len(input_field), "data fieldsfrom coaster", input_field 
            #if self.coaster.get_telemetry_status() and input_field and len(input_field) == 3:
            if input_field and len(input_field) == 4:
                is_in_play_mode = input_field[0]
                # print "is_in_play_mode",  is_in_play_mode
                if is_in_play_mode:
                    self.gui.set_coaster_connection_label(("Receiving Coaster Telemetry", "green3"))
                    isRunning = input_field[1]
                    self.speed = float(input_field[2])
                    self.isNl2Paused = not isRunning
                    if isRunning:
                        # print "is running"
                        if self.check_is_stationary(self.speed):
                            #  print "is stopped??"
                            self.coasterState.coaster_event(CoasterEvent.STOPPED)
                            #  here if coaster not moving and not paused
                            #  print "Auto Reset"
                        else:
                            if self.coasterState.state == RideState.DISABLED:
                                # coaster is moving at startup
                                self.coasterState.coaster_event(CoasterEvent.RESETEVENT)
                            else:                                
                                self.coasterState.coaster_event(CoasterEvent.UNPAUSED)
                    else:
                        self.coasterState.coaster_event(CoasterEvent.PAUSED)
                    #  print isRunning, speed
                    """  
                        if self.coasterState.state == RideState.PAUSED:
                             self.coasterState.coaster_event(CoasterEvent.UNPAUSED)
                        if self.speed < 0.1:
                            print "speed", self.speed
                            if not self.isLeavingStation:
                                print "not leaving station"
                                if self.coaster.is_train_in_station():
                                    print "coaster is in station"
                                    if self.coaster.is_in_play_mode():
                                        print "setting stop state because in station"
                                        self.coasterState.coaster_event(CoasterEvent.STOPPED)
                                    else:
                                        self.gui.set_coaster_connection_label(("Coaster not in play mode", "red"))
                                        return
                                else:
                                    print "train is not in station ??, status=",  self.coaster.is_train_in_station()
                        self.coasterState.coaster_event(CoasterEvent.PAUSED)
                    """
                    #  print isRunning, speed
                else:
                    self.gui.set_coaster_connection_label(("Coaster not in play mode", "red"))

                if  input_field[3] and len(input_field[3]) == 6:  # check if we have data for all 6 DOF
                        self.current_pos = [float(f) for f in input_field[3]]
                if self.is_chair_activated and self.coasterState.state != RideState.READY_FOR_DISPATCH:
                        # only send if activated and not waiting in station
                        if self.move_func is not None:
                            self.move_func(self.current_pos)

            else:
                errMsg = format("Telemetry error: %s" % self.coaster.get_telemetry_err_str())
                #  print errMsg
                self.gui.set_coaster_connection_label((errMsg, "red"))

