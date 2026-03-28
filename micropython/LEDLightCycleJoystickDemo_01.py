"""
================================================================================
DEMO #7: INTERACTIVE LIGHT CYCLE (Manual Override)
================================================================================
CONTROLS:
- UP/DOWN/LEFT/RIGHT (GPIO 0-3): Drive the cycle. Wrapping is enabled.
- MID (GPIO 4): Cycle to a new random primary color.

THE ENGINE:
The head of the cycle operates independently of the trail. As you drive, the 
cycle deposits its base color into a background "Phosphor Buffer". That buffer 
decays by 15% every single frame, naturally drawing the fading tail behind you 
without needing to track complex coordinate histories. 
================================================================================
"""

import machine
import neopixel
import time
import math
import random

# --- Hardware Configuration ---
PIN_MATRIX = 25
WIDTH = 4
HEIGHT = 4
PIXELS = WIDTH * HEIGHT
LED_ORDER = 3
GLOBAL_BRIGHTNESS = 0.05 

np = neopixel.NeoPixel(machine.Pin(PIN_MATRIX), PIXELS, bpp=LED_ORDER)

# --- Joystick Configuration ---
PIN_UP = 0
PIN_DOWN = 1
PIN_LEFT = 2
PIN_RIGHT = 3
PIN_MID = 4

# Initialize with internal pull-ups (0 = Pressed)
btn_up = machine.Pin(PIN_UP, machine.Pin.IN, machine.Pin.PULL_UP)
btn_dn = machine.Pin(PIN_DOWN, machine.Pin.IN, machine.Pin.PULL_UP)
btn_lf = machine.Pin(PIN_LEFT, machine.Pin.IN, machine.Pin.PULL_UP)
btn_rt = machine.Pin(PIN_RIGHT, machine.Pin.IN, machine.Pin.PULL_UP)
btn_mid = machine.Pin(PIN_MID, machine.Pin.IN, machine.Pin.PULL_UP)

# --- The Phosphor Decay Buffer ---
buffer = [[0.0, 0.0, 0.0] for _ in range(PIXELS)]

def hsv_to_rgb(h, s, v):
    """Converts a Hue (0.0 to 1.0) into standard RGB."""
    if s == 0.0: return (int(v * 255), int(v * 255), int(v * 255))
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i %= 6
    if i == 0: r, g, b = v, t, p
    elif i == 1: r, g, b = q, v, p
    elif i == 2: r, g, b = p, v, t
    elif i == 3: r, g, b = p, q, v
    elif i == 4: r, g, b = t, p, v
    else: r, g, b = v, p, q
    return (int(r * 255), int(g * 255), int(b * 255))

def get_random_primary_color():
    """Selects a highly visible primary/secondary hue."""
    # 0.0=Red, 0.16=Yellow, 0.33=Green, 0.5=Cyan, 0.66=Blue, 0.83=Magenta
    hue = random.choice([0.0, 0.16, 0.33, 0.5, 0.66, 0.83])
    return hsv_to_rgb(hue, 1.0, GLOBAL_BRIGHTNESS)

def run_interactive_cycle():
    print("HAL 9000: Manual Light Cycle Override Engaged.")
    
    # Starting State
    head_x = 1
    head_y = 1
    base_color = get_random_primary_color()
    
    # Input handling variables
    last_move_time = time.ticks_ms()
    move_delay = 200 # Milliseconds between steps (adjust to drive faster/slower)
    last_mid_state = 1
    
    try:
        while True:
            now = time.ticks_ms()
            
            # 1. DECAY THE TRAIL BUFFER
            # Multiplying by 0.85 every frame creates a perfect 3-4 pixel fading tail
            for i in range(PIXELS):
                buffer[i][0] *= 0.85
                buffer[i][1] *= 0.85
                buffer[i][2] *= 0.85

            # 2. POLL JOYSTICK & HANDLE MOVEMENT
            moved = False
            old_x, old_y = head_x, head_y

            # We use a timer to prevent the cycle from flying off the screen instantly
            if time.ticks_diff(now, last_move_time) > move_delay:
                if btn_up.value() == 0:
                    head_y = (head_y - 1) % HEIGHT
                    moved = True
                elif btn_dn.value() == 0:
                    head_y = (head_y + 1) % HEIGHT
                    moved = True
                elif btn_lf.value() == 0:
                    head_x = (head_x - 1) % WIDTH
                    moved = True
                elif btn_rt.value() == 0:
                    head_x = (head_x + 1) % WIDTH
                    moved = True

                if moved:
                    last_move_time = now
                    # Drop the base color into the buffer at the OLD position to start the trail
                    idx = old_y * WIDTH + old_x
                    buffer[idx][0] = base_color[0]
                    buffer[idx][1] = base_color[1]
                    buffer[idx][2] = base_color[2]

            # 3. HANDLE COLOR CHANGE (MID BUTTON)
            mid_state = btn_mid.value()
            if mid_state == 0 and last_mid_state == 1:
                base_color = get_random_primary_color()
            last_mid_state = mid_state

            # 4. RENDER TRAIL TO HARDWARE
            for i in range(PIXELS):
                np[i] = (int(buffer[i][0]), int(buffer[i][1]), int(buffer[i][2]))

            # 5. RENDER HEARTBEAT HEAD OVERLAY
            # Sine wave oscillates between 0.4 and 1.0 multiplier
            pulse_multiplier = 0.7 + 0.3 * math.sin(now / 150.0)
            
            head_r = int(base_color[0] * pulse_multiplier)
            head_g = int(base_color[1] * pulse_multiplier)
            head_b = int(base_color[2] * pulse_multiplier)
            
            head_idx = head_y * WIDTH + head_x
            np[head_idx] = (head_r, head_g, head_b)
            
            np.write()
            
            # Lock frame rate to ~33 FPS for smooth phosphor decay
            time.sleep(0.03) 

    except KeyboardInterrupt:
        for i in range(PIXELS):
            np[i] = (0, 0, 0)
        np.write()
        print("HAL 9000: Manual Override Terminated.")

# Ignite the Grid
run_interactive_cycle()