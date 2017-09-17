"""
  PlatformInput.py

  keyboard input version that accepts comma separated values as: x,y,z,r,p,y
    x is forward/back movement in millimeters (+ is forward)
    y is side to side movement in mm (+ is left)
    z is up/down movement in mm (+ is up)
    r is roll in degrees (+ is left up)
    p is pitch in degrees (+ is nose down)
    y is yaw in degrees (+ is CCW)

    This module sends system commands or movement requests through callback
    methods  named cmd_func amd move_func that are passed in the begin method.
    
    The controller will poll this module at regular intervals (currently 50ms)
    for movement requests or system commands.

    Movement requests have six parameters:
     x,y,z,r,p,y
    x is forward/back movement in millimeters (+ is forward)
    y is side to side movement in mm (+ is left)
    z is up/down movement in mm (+ is up)
    r is roll in degrees (+ is left up)
    p is pitch in degrees (+ is nose down)
    y is yaw in degrees (+ is CCW)

    The controller accepts move requests as either actual values (mm and angles)
    or normalized (ranging from -1 to +1). Normalized values are easier to use
    when interfacing to a simulator that has a range of movements greater than
    the platform can achieve. For example, a flight simulator can move forward
    many meters each frame, but the platform movement is limted to under 200mm.
    To use normalized values, send 1 for maximim positive movement and -1 for
    maximum movement in the opposite direction.
    If the application requires gain control or washout then normalized values
    must be used.
    For example,  norm,1,0,-0.5,0,0,0.10  moves the platform fully forward
    (positive x direction), halfway down (negative z direction), and
    10% positive (CCW) yaw

    To use real world values, send the values as mm and radians.
    The range of real world values for the platform is passed to the begin function.
    for example :  real,100,0,-50,0,0,0.09 moves 100mm forward, 50mm down,
    0.09 radians (5 degrees) of positive (CCW) yaw
    Note that gain and washout are not available when using real world values

    The minimum interval between calls to recieve requests is 50 milliseconds
    
    System commands are entered as text:
       enable  enables the platform to move
       disable prevents the platform from moving
       exit    terminates the python program
"""

from math import radians
import sys
import traceback

#  InputParmType = 'realworld'  # can be 'realworld' or 'normalized'
InputParmType = 'normalized'


class InputInterface(object):
    USE_GUI = False

    def __init__(self):
        self.rootTitle = "Chair Test Client"
        self.levels = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        if InputParmType == 'normalized':
            self.is_normalized = True
            print 'Expecting normalized input parameters'
        else:
            self.is_normalized = False
            print 'Expecting realworld input parameters'
        print
        #  additional client init code goes here

    def init_gui(self, root):
        pass

    def chair_status_changed(self, chair_status):
        pass

    def begin(self, cmd_func, move_func, limits):
        self.cmd_func = cmd_func
        self.move_func = move_func
        self.limits = limits  # note limits are in mm and radians

        print "enter 'enable' to enable platform"
        print "enter 'disable' to disable platform"
        print "enter 'exit' to exit"

    def fin(self):
        #  client exit code goes here
        pass

    def get_current_pos(self):
        return self.levels
        
    def service(self):
        #  get command or move request from the keyboard
        #  move request expects translations as mm and angles as radians
        #  here we convert the last three fields from degrees to radians
        input = raw_input("enter orientation as: surge, sway, heave, roll, pitch, yaw: ")
        try:
            print input
            input_field = list(input.split(","))
            if len(input_field) == 1:
                if self.cmd_func:
                    self.cmd_func(input)  #  process a single field as a command
            else:
                #  print input_field
                if len(input_field) == 6:
                    r=[float(f) for f in input_field]
                    if not self.is_normalized:
                        #  real world values expect radians
                        r[3] = radians(r[3])
                        r[4] = radians(r[4])
                        r[5] = radians(r[5])
                    if self.move_func:
                        self.move_func(r)
                else:
                    print 'expected either a single command or 6 numeric values'
        except:
            #  print error if input not a string or cannot be converted into valid request
            e = sys.exc_info()[0]
            s = traceback.format_exc()
            print e, s
