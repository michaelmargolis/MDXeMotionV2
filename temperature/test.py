from temperature import system_temperature
import time

temperature = system_temperature((40,60),(75,90))

while True:
   text,warn = temperature.read()
   print text,warn
   time.sleep(1)

