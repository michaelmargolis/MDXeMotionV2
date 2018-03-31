"""
Python Coaster client GUI

This version requires NoLimits attraction license and NL ver 2.5.3.4 or later
"""

import os
import sys
import Tkinter as tk
import ttk
from coaster_state import RideState

ATTRACTION_LICENCE = True

class CoasterGui(object):

    def __init__(self, dispatch, pause, reset, activate_callback_request, quit_callback):
        self.dispatch = dispatch
        self.pause = pause
        self.reset = reset
        self.activate_callback_request = activate_callback_request
        self.quit = quit_callback
        self.park_path = []
        self.park_name = []
        self.seat = []
        self._park_callback = None

    def init_gui(self, master):
        self.master = master
        frame = tk.Frame(master)
        frame.grid()

        spacer_frame = tk.Frame(master, pady=4)
        spacer_frame.grid(row=0, column=0)
        self.label0 = tk.Label(spacer_frame, text="").grid(row=0)

        self.dispatch_button = tk.Button(master, height=2, width=16, text="Dispatch",
                                         command=self.dispatch, underline=0)
        self.dispatch_button.grid(row=1, column=0, padx=(24, 4))

        self.pause_button = tk.Button(master, height=2, width=16, text="Pause", command=self.pause, underline=0)
        self.pause_button.grid(row=1, column=2, padx=(30))

        self.reset_button = tk.Button(master, height=2, width=16, text="Reset Rift",
                                      command=self.reset, underline=0)
        self.reset_button.grid(row=1, column=3, padx=(24))

        label_frame = tk.Frame(master, pady=20)
        label_frame.grid(row=3, column=0, columnspan=4)

        if ATTRACTION_LICENCE:
            self.park_listbox = ttk.Combobox(label_frame)
            self.park_listbox.grid(row=0, column=0, columnspan=2, ipadx=16, sticky=tk.W)
            self.read_parks()

            self.park_listbox["values"] = self.park_name
            self.park_listbox.bind("<<ComboboxSelected>>", lambda _ : self._park_by_index(self.park_listbox.current()))
            self.park_listbox.current(0)

            # self.set_seat_button = tk.Button(label_frame, height=1, width=10, text="seat preset", command=self.preset_seat)
            # self.set_seat_button.grid(row=0, column=1)


        self.coaster_status_label = tk.Label(label_frame, text="Waiting for Coaster Status", font=(None, 24),)
        self.coaster_status_label.grid(row=1, columnspan=2, ipadx=16, sticky=tk.W)

        self.intensity_status_Label = tk.Label(label_frame, font=(None, 12),
                 text="Intensity", fg="orange")
        self.intensity_status_Label.grid(row=2, column=0, columnspan=2, ipadx=16, sticky=tk.W)
        
        self.coaster_connection_label = tk.Label(label_frame, fg="red", font=(None, 12),
               text="Coaster Software Not Found (start NL2 or maximize window if already started)")
        self.coaster_connection_label.grid(row=3, columnspan=2, ipadx=16, sticky=tk.W)

        self.remote_status_label = tk.Label(label_frame, font=(None, 12),
                 text="Looking for Remote Control", fg="orange")
        self.remote_status_label.grid(row=4, columnspan=2, ipadx=16, sticky=tk.W)

        self.chair_status_Label = tk.Label(label_frame, font=(None, 12),
                 text="Using Festo Controllers", fg="orange")
        self.chair_status_Label.grid(row=5, column=0, columnspan=2, ipadx=16, sticky=tk.W)

        self.temperature_status_Label = tk.Label(label_frame, font=(None, 12),
                 text="Attempting Connection to VR PC Server", fg="red")
        self.temperature_status_Label.grid(row=6, column=0, columnspan=2, ipadx=16, sticky=tk.W)

        bottom_frame = tk.Frame(master, pady=16)
        bottom_frame.grid(row=5, columnspan=3)

        self.is_chair_activated = tk.IntVar()
        self.is_chair_activated.set(0)  # disable by default

        self.activation_button = tk.Button(master, underline=0, command=self._enable_pressed)
        self.activation_button.grid(row=4, column=1)
        self.deactivation_button = tk.Button(master, command=self._disable_pressed)
        self.deactivation_button.grid(row=4, column=2)
        self.set_activation_buttons(False)

        self.close_button = tk.Button(master, text="Shut Down and Exit", command=self.quit)
        self.close_button.grid(row=4, column=3)

        self.label1 = tk.Label( bottom_frame, text="     ").grid(row=0, column=1)

        self.org_button_color = self.dispatch_button.cget("background")

        master.bind("<Key>", self.hotkeys)

    def set_seat(self, seat):
        if seat != '':
           print "seat", int(seat)
    """
    def preset_seat(self):
        print "preset seat"
    """
    """
    def set_focus(self):
        # not used in this version
        #needs: import win32gui # for set_focus
        guiHwnd = win32gui.FindWindow("TkTopLevel",None)
        print guiHwnd
        win32gui.SetForegroundWindow(guiHwnd)
    """

    def read_parks(self):
        try:
            path = os.path.abspath('CoasterParks/parks.cfg')
            print path
            with open(path) as f:
                parks = f.read().splitlines()
                for park in parks:
                    p = park.split(',')
                    self.park_path.append(p[0]) 
                    self.seat.append(p[1])
                    #  print park
                    p = p[0].split('/')
                    p = p[len(p)-1]
                    #  print p,
                    self.park_name.append(p.split('.')[0])
            self.park_listbox.configure(state="disabled")
            print "available parks are:", self.park_name
        except:
            e = sys.exc_info()[0]
            print "Unable to open parks.cfg file, select park in NoLimits", e

    def set_park_callback(self, cb):
        self._park_callback = cb
        
    def _park_by_index(self, idx):
        print idx, self.park_path[idx]
        if self._park_callback != None:
            print "loading park", self.park_name[idx]
            # load park in pause mode, this will unpuase when park is loaded
            self._park_callback(True, self.park_path[idx], self.seat[idx])

    def get_selected_park(self): 
        return None

    def _enable_pressed(self):
        #  self.set_activation_buttons(True)
        self.activate_callback_request(True)

    def _disable_pressed(self):
        #  self.set_activation_buttons(False)
        self.activate_callback_request(False)

    def set_activation_buttons(self, isEnabled):  # callback from Client
        if isEnabled:
            self.activation_button.config(text="Activated ", relief=tk.SUNKEN)
            self.deactivation_button.config(text="Deactivate", relief=tk.RAISED)
            self.park_listbox.configure(state="disabled")
        else:
            self.activation_button.config(text="Activate ", relief=tk.RAISED)
            self.deactivation_button.config(text="Deactivated", relief=tk.SUNKEN)
            self.park_listbox.configure(state="readonly")

    def set_coaster_status_label(self, speed):
        self.coaster_status_label.config(text=format("Coaster is Running %2.1fm/s" % (speed)), fg="green3")
        
    def set_coaster_connection_label(self, label):
        self.coaster_connection_label.config(text=label[0], fg=label[1])

    def chair_status_changed(self, status):
        self.chair_status_Label.config(text=status[0], fg=status[1])

    def temperature_status_changed(self, status):
        self.temperature_status_Label.config(text=status[0], fg=status[1])

    def intensity_status_changed(self, status):
        self.intensity_status_Label.config(text=status[0], fg=status[1])
        
    def set_remote_status_label(self, label):
        self.remote_status_label.config(text=label[0], fg=label[1])

    def hotkeys(self, event):
        print "pressed", repr(event.char)
        if event.char == 'd':  # ignore case
            self.dispatch()
        if event.char == 'p':
            self.pause()
        if event.char == 'r':
            self.reset()
        if event.char == 'e':
            self.emergency_stop()
        """ todo ?
        if event.char == 'a':
            if self.isActivated():
                #print "in hotkeys, cposition_requesting deactivate"
                self.deactivate()
            else:
                #print "in hotkeys, cposition_requesting activate"
                self.activate()
        """
    def process_state_change(self, new_state, isActivated):
        #  print "in coaster gui process state change, new state is", new_state
        if new_state == RideState.READY_FOR_DISPATCH:
            if isActivated:
                print "Coaster is Ready for Dispatch"
                self.dispatch_button.config(relief=tk.RAISED, state=tk.NORMAL)
                self.coaster_status_label.config(text="Coaster is Ready for Dispatch", fg="green3")
            else:
                print "Coaster at Station but deactivated"
                self.dispatch_button.config(relief=tk.RAISED, state=tk.DISABLED)
                self.coaster_status_label.config(text="Coaster at Station but deactivated", fg="orange")

            self.pause_button.config(relief=tk.RAISED, state=tk.NORMAL, text="Prop Platform")
            self.reset_button.config(relief=tk.RAISED, state=tk.NORMAL)

        elif new_state == RideState.RUNNING:
            self.dispatch_button.config(relief=tk.SUNKEN, state=tk.DISABLED)
            self.pause_button.config(relief=tk.RAISED, state=tk.NORMAL, text="Pause")
            self.reset_button.config(relief=tk.RAISED, state=tk.NORMAL)
            self.coaster_status_label.config(text="Coaster is Running", fg="green3")
        elif new_state == RideState.PAUSED:
            self.dispatch_button.config(relief=tk.SUNKEN, state=tk.DISABLED)
            self.pause_button.config(relief=tk.SUNKEN, state=tk.NORMAL)
            self.reset_button.config(relief=tk.RAISED, state=tk.NORMAL)
            self.coaster_status_label.config(text="Coaster is Paused", fg="orange")
        elif new_state == RideState.EMERGENCY_STOPPED:
            self.dispatch_button.config(relief=tk.SUNKEN, state=tk.DISABLED)
            self.pause_button.config(relief=tk.SUNKEN, state=tk.DISABLED)
            self.reset_button.config(relief=tk.RAISED, state=tk.NORMAL)
            self.coaster_status_label.config(text="Emergency Stop", fg="red")
        elif new_state == RideState.RESETTING:
            self.dispatch_button.config(relief=tk.SUNKEN, state=tk.DISABLED)
            self.pause_button.config(relief=tk.RAISED, state=tk.DISABLED)
            self.reset_button.config(relief=tk.SUNKEN, state=tk.NORMAL)
            self.coaster_status_label.config(text="Coaster is resetting", fg="blue")
