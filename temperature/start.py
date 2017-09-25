#!/usr/bin/python
import time
import os
import win32gui
from subprocess import Popen, CREATE_NEW_CONSOLE

#import os
import sys
import win32com.shell.shell as shell
ASADMIN = 'asadmin'

if sys.argv[-1] != ASADMIN:
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([script] + sys.argv[1:] + [ASADMIN])
    shell.ShellExecuteEx(lpVerb='runas', lpFile=sys.executable, lpParameters=params)    
    print "I am root now."

handles = []

handles.append(Popen("python test.py", creationflags=CREATE_NEW_CONSOLE))

"""
nl2 = os.path.normpath('"D:/Program Files/NoLimits 2/64bit/nolimits2app.exe" --telemetry')
nl2VR = os.path.normpath('"D:/Program Files/NoLimits 2/64bit/nolimits2app.exe" --telemetry --vr')

def set_focus():
    guiHwnd = win32gui.FindWindow("ConsoleWindowClass","C:\Windows\System32\cmd.exe - start.py")
    print guiHwnd
    win32gui.ShowWindow(guiHwnd,5)
    win32gui.SetForegroundWindow(guiHwnd)
        
input = raw_input("Press Enter key to start NoLimits coaster (n disables vr mode,l uses legacy code)")
input = input.lower()
if len(input) > 0 and ('n' in input):
    print "starting NL2 without VR", nl2
    nl2P = Popen(nl2)
else:
    print "starting NL2 with VR", nl2VR
    nl2P = Popen(nl2VR)


print("If coaster is not loaded, click 'Play' then click 'MDXVrCoaster'")
raw_input("Press Enter key to continue when ready")

if len(input) > 0 and ('l' in input):
    controller = 'python platform_controller_std.py'
    print "starting Legacy platform controller:",
else:
    controller = 'python platform_controller.py'
    print "starting Attraction licenced platform controller:",

print  controller
handles.append(Popen(controller, creationflags=CREATE_NEW_CONSOLE))
time.sleep(2)

print("\n")
"""

