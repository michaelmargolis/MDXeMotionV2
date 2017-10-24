""" Actuator Test

"""

import Tkinter as tk
import ttk


from platform_output import OutputInterface

isActive = True  # set False to terminate
frameRate = 0.05

chair = OutputInterface()

class Controller:

    def __init__(self):
        self.prevT = 0
        self.is_output_enabled = False
        self.actuator_length_range = chair.get_actuator_lengths()
        self.actuator_lengths = [self.actuator_length_range[1] for i in range(6)]
        print self.actuator_lengths

    def init_gui(self, root):
        self.root = root
        self.root.geometry("580x320+2200+200")
        self.root.iconbitmap('images\ChairIcon3.ico')
        title = "Actuator test for " + chair.get_platform_name()
        self.root.title(title)
        print title
        nb = ttk.Notebook(root)
        page1 = ttk.Frame(nb)  # client
        nb.add(page1, text='  Input  ')
        page2 = ttk.Frame(nb)  # output
        nb.add(page2, text='  Output ')
        nb.pack(expand=1, fill="both")
        chair.init_gui(page2)
        
        # input page 
        frame = tk.Frame(page1)
        frame.pack()
        self.label0 = tk.Label(frame, text="Adjust Actuator length (value is muscle length plus fixed length)")
        self.label0.pack(fill=tk.X, pady=10)
        sLabels = ("1", "2", "3", "4", "5", "6")
        min_len = self.actuator_length_range[0]
        max_len = self.actuator_length_range[1]
        for i in range(6):
            s = tk.Scale(frame, from_=min_len, to=max_len, resolution=5, length=180,
                         command=lambda g, i=i: self._set_value(i, g), label=sLabels[i])
            s.set(max_len)
            s.pack(side=tk.LEFT, padx=(6, 4))

        frame2 = tk.Frame(page1)
        frame2.pack(fill=tk.X, side=tk.BOTTOM, pady=10)

        self.chair_status_Label = tk.Label(frame2, text="Using Festo Controllers", fg="orange")
        self.chair_status_Label.pack()

        self.enableState = tk.StringVar()
        self.enableState.set('disable')
        self.enable_cb = tk.Checkbutton(frame2, text="Enable", command=self._enable,
                                        variable=self.enableState, onvalue='enable', offvalue='disable')
        self.enable_cb.pack(side=tk.LEFT, padx=220)

        self.close_button = tk.Button(frame2, text="Quit", command=self.quit)
        self.close_button.pack(side=tk.LEFT)

    def _enable(self):
        if self.enableState.get() == 'enable':
            self.enable_platform()
        elif self.enableState.get() == 'disable':
            self.disable_platform()

    def _set_value(self, idx, value):
        self.actuator_lengths[idx] = float(value)

        chair.show_muscles([0,0,0,0,0,0], self.actuator_lengths)
        controller.update_gui()
        chair.move_platform(self.actuator_lengths)

    def update_gui(self):
        self.root.update_idletasks()
        self.root.update()

    def quit(self):       
        global isActive
        isActive = False

    def enable_platform(self):
        chair.set_enable(True, self.actuator_lengths)
        self.is_output_enabled = True
        #  print "enable", self.actuator_lengths

    def disable_platform(self):        
        chair.set_enable(False, self.actuator_lengths)
        self.is_output_enabled = False

    def chair_status_changed(self, status):
        self.chair_status_Label.config(text=status[0], fg=status[1])

    def temperature_status_changed(self, status):
        self.temperature_status_Label.config(text=status[0], fg=status[1])
        
controller = Controller()


def main():

    root = tk.Tk()
    controller.init_gui(root)
    chair_status = None

    while isActive:
        controller.update_gui()
        if chair_status != chair.get_output_status():
            chair_status = chair.get_output_status()
            controller.chair_status_changed(chair_status)


if __name__ == "__main__":
    main()
    chair.fin()
