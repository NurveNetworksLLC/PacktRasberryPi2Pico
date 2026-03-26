import machine
import time

# --- Gamepad Hardware Configuration ---
# Sequentially mapped to GP0 - GP6. 
# You can easily swap these integers if your physical jumper wires are in a different order.
PIN_UP = 0
PIN_DOWN = 1
PIN_LEFT = 2
PIN_RIGHT = 3
PIN_MID = 4
PIN_SET = 5
PIN_RST = 6

# Initialize all pins as inputs with internal pull-up resistors engaged
# A value of 1 means unpressed (floating high at 3.3v)
# A value of 0 means pressed (shorted to ground)
btn_up = machine.Pin(PIN_UP, machine.Pin.IN, machine.Pin.PULL_UP)
btn_down = machine.Pin(PIN_DOWN, machine.Pin.IN, machine.Pin.PULL_UP)
btn_left = machine.Pin(PIN_LEFT, machine.Pin.IN, machine.Pin.PULL_UP)
btn_right = machine.Pin(PIN_RIGHT, machine.Pin.IN, machine.Pin.PULL_UP)
btn_mid = machine.Pin(PIN_MID, machine.Pin.IN, machine.Pin.PULL_UP)
btn_set = machine.Pin(PIN_SET, machine.Pin.IN, machine.Pin.PULL_UP)
btn_rst = machine.Pin(PIN_RST, machine.Pin.IN, machine.Pin.PULL_UP)

def test_gamepad():
    print("HAL 9000 Gamepad Diagnostic Initialized...")
    print("Monitoring GPIO 0-6. Press 'Stop' in Thonny to terminate.")
    
    try:
        while True:
            # We create an empty list to hold any buttons pressed during this exact millisecond
            pressed_this_frame = []
            
            # Check the logic level of each pin (0 = Pressed)
            if btn_up.value() == 0:    pressed_this_frame.append("UP")
            if btn_down.value() == 0:  pressed_this_frame.append("DOWN")
            if btn_left.value() == 0:  pressed_this_frame.append("LEFT")
            if btn_right.value() == 0: pressed_this_frame.append("RIGHT")
            if btn_mid.value() == 0:   pressed_this_frame.append("MID")
            if btn_set.value() == 0:   pressed_this_frame.append("SET")
            if btn_rst.value() == 0:   pressed_this_frame.append("RESET")
            
            # If the list is not empty, print the results to the console
            if pressed_this_frame:
                # Joins multiple presses with a plus sign (e.g., "UP + RIGHT")
                print(" + ".join(pressed_this_frame))
                
            # A 100ms delay acts as a software debounce so the console doesn't flood 
            # with 10,000 lines for a single half-second button press.
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("Diagnostic Terminated. Standing by.")

# Ignite the polling sequence
test_gamepad()