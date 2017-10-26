"""
coaster_state contains definitions for the coaster state machine

RideState is the high level similated coaster state that is displayed on the GUI

ConnectStatus is the status of connection between the contoller and NoLimits

"""
class RideState:
    DISABLED, READY_FOR_DISPATCH, RUNNING, PAUSED, EMERGENCY_STOPPED, RESETTING = range(6)


class ConnectStatus():
   is_pc_connected = 0x1
   is_nl2_connected = 0x2
   is_in_play_mode = 0x4
   is_ready_to_dispatch = 0x8
   