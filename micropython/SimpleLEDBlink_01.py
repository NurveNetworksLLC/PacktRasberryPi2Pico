# Raspi Pico 2+ Clone Blinking LED

from machine import Pin
import time

print("Blinking LED")

led = Pin(25, Pin.OUT)

while True:
    led.value(1)
    time.sleep(.5)
    
    led.value(0)
    time.sleep(.5)
    
    
    

