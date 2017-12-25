"""
Created 21 dec 2017
@author: mem
configuration for Servo model
"""

"""
This file defines the coordinates of the upper (base) and lower (platform) attachment points
Note: because the chair is an inverted stewart platform, the base is the plane defined by the upper attachment points

The coordinate frame used follow ROS conventions, positive X is forward, positive Y us left, positive Z is up,
positive yaw is CCW from the persepective of person on the chair.

The origin is the center of the circle intersecting the attachment points. The X axis is the line through the origin running
 from back to front (X values increase moving from back to front). The Y axis passes through the origin with values increasing
 to the left.

 The diagram below shows the angles of the V1 chair (lines point to first entry in array)

                    Top Base                        Bottom Platform
                       -X                                 -X
                        |                                  |

                    185  ***                            -    -
                ,             `                    ,             `
             ,                   `             230                  ***
           ,                       `         250                      ***

          '                         '        '                         '
  -Y --                 O                                  O                  --- +Y
          '            /            '        '                         '
                     /                                   /
           '       /               '          '        /              '
           295   /              ***                  /
             305              ***                310             ***
                        |                                  |
                       +X                                 +X
                  Front of Chair                     Front of Chair


                     Top Base                        Bottom Platform
                       -X                                 -X
                        |                                  |



The attachment coordinates can be specified explicitly or with vectors from the origin to
 each attachment point. Uncomment the desired method of entry.

You only need enter values for the left side, the other side is a mirror image and is calculated for you
"""
import math

PLATFORM_NAME = "SERVO_SIM" 

OutSerialPort = 'COM12'

PLATFORM_UNLOADED_WEIGHT = 20  # weight of moving platform without 'passenger' in killograms
DEFAULT_PAYLOAD_WEIGHT = 65    # weight of 'passenger'
MAX_MUSCLE_LEN = 80           # length of muscle at minimum pressure
MIN_MUSCLE_LEN = MAX_MUSCLE_LEN * .75 # length of muscle at maximum pressure
FIXED_LEN = 0                #  length of fixing hardware
MIN_ACTUATOR_LEN = MIN_MUSCLE_LEN + FIXED_LEN  # total min actuator distance including fixing hardware
MAX_ACTUATOR_LEN = MAX_MUSCLE_LEN ++ FIXED_LEN # total max actuator distance including fixing hardware
MAX_ACTUATOR_RANGE = MAX_ACTUATOR_LEN - MIN_ACTUATOR_LEN
MID_ACTUATOR_LEN = MIN_ACTUATOR_LEN + (MAX_ACTUATOR_RANGE/2)

DISABLED_LEN = MAX_MUSCLE_LEN *.99  # todo ??
WINDDOWN_LEN = MAX_ACTUATOR_LEN *.92  # length to enable fitting of stairs

#  uncomment this to define attachment locations using angles and distance from origin (vectors)

#only the left side is needed (as viewed facing the chair), the other side is calculated for you

_baseAngles    = [340, 260, 220]   # enter angles from origin to attach point
_baseMagnitude = [81, 81, 81]

#Platform attachment vectors
_platformAngles    = [305, 295, 185] # enter angles from origin to attach point
_platformMagnitude = [81, 81, 81] # enter distance from origin to attach point

#convert to radians and calculate x and y coordinates using sin and cos of angles
_baseAngles  = [math.radians(x) for x in _baseAngles]
base_pos     = [[m*math.cos(a),m*math.sin(a),0]  for a,m in zip(_baseAngles,_baseMagnitude)]

_platformAngles  = [math.radians(x) for x in _platformAngles]
platform_pos     = [[m*math.cos(a),m*math.sin(a),0]  for a,m in zip(_platformAngles,_platformMagnitude)]

"""

#  uncomment this to enter hard coded coordinates

#  input x and y coordinates with origin as center of the base plate
#  the z value should be zero for both base and platform
#  only -Y side is needed as other side is symmetrical (see figure)
base_pos = [
            [373.8, -517.7, 0.],  # first upper attachment point
            [258.9, -583.7, 0.],
            [-635.7, -68.0, 0.]
           ]

platform_pos = [
                 [689.3, -70.0, 0.],  # lower (movable) attachment point
                 [-287.6, -634.1, 0.],
                 [-408.8, -564.1, 0.]
               }
"""            
platform_mid_height = 45 # vertical distance in mm between fixed and moving platform in mid position

#  the range in mm or radians from origin to max extent in a single DOF 
platform_1dof_limits = [15, 15, 17 , math.radians(15), math.radians(20), math.radians(12)]

# limits at extremes of movement
platform_6dof_limits = [10, 10, 10, math.radians(12), math.radians(12), math.radians(10)]

