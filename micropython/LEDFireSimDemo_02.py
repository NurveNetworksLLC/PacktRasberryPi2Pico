"""
================================================================================
DEMO #2: PROCEDURAL THERMODYNAMIC FIRE (Version 2.1)
================================================================================
THE DEMOSCENE ALGORITHM:
This code utilizes a legendary computer graphics technique pioneered by 
demoscene hackers in the early 1990s (and famously utilized for the fire 
effects in games like DOOM). 

Instead of trying to animate colors directly, this algorithm simulates real-world 
thermodynamics using a cellular automaton. It operates on a virtual "Heat Map" 
rather than a screen of pixels. 

The physics work in three distinct steps every single frame:
1. IGNITION: The very bottom row of the matrix acts as the "fuel source," randomly 
   spiking with maximum heat values (simulating sparking embers).
2. CONVECTION: That heat travels upwards to the next row, but slightly drifts 
   left or right to simulate wind and natural flame flicker.
3. COOLING: As the heat rises away from the fuel source, it rapidly decays. 

Finally, the raw "temperature" data (0 to 255) is passed through a color palette 
function that maps cold values to Black, warm values to Red, hot to Orange, and 
intense heat to Yellow. By simulating the physics of heat rather than the look of 
fire, the resulting animation is organically chaotic and highly realistic.
================================================================================
"""

import machine
import neopixel
import time
import random

# --- Hardware Configuration ---
PIN = 25
WIDTH = 4
HEIGHT = 4
PIXELS = WIDTH * HEIGHT
LED_ORDER = 3
GLOBAL_BRIGHTNESS = 0.05  # Essential safeguard for the Pico's regulator

# Initialize the NeoPixel matrix
np = neopixel.NeoPixel(machine.Pin(PIN), PIXELS, bpp=LED_ORDER)

# --- The Thermodynamics Engine State ---
# 0 is cold (black), 255 is intensely hot (yellow).
heat = [[0 for _ in range(WIDTH)] for _ in range(HEIGHT)]

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

def heat_to_color(temperature):
    """Translates a raw temperature (0-255) into a realistic fire color."""
    temperature = max(0, min(255, temperature))

    # If it drops below 30, the ember has died and emits no light
    if temperature < 30:
        return (0, 0, 0)

    # Calculate Hue: 0.0 is Red, 0.15 is Yellow.
    hue = (temperature / 255.0) * 0.15

    # Calculate Brightness scaled by our hardware safeguard
    val = (temperature / 255.0) * GLOBAL_BRIGHTNESS

    return hsv_to_rgb(hue, 1.0, val)

def update_fire():
    """The Core Thermodynamics Step."""
    
    # 1. AGGRESSIVE ALTITUDE COOLING
    for y in range(HEIGHT):
        for x in range(WIDTH):
            # To see the tips of the fire, it must cool faster as it gets higher.
            # y=0 is the top row, so (HEIGHT - y) is higher at the top.
            base_cooling = random.randint(15, 35)
            altitude_penalty = (HEIGHT - y) * 12 
            cooling_amount = base_cooling + altitude_penalty
            
            heat[y][x] = max(0, heat[y][x] - cooling_amount)

    # 2. CONVECTION (Move the heat UPWARDS)
    # Iterate from the top row (0) down to the second-to-last row (2).
    for y in range(HEIGHT - 1): 
        for x in range(WIDTH):
            # Random drift left or right
            drift = random.randint(-1, 1)
            source_x = x + drift
            
            # Keep the drift within the physical matrix bounds
            if source_x < 0: source_x = 0
            if source_x >= WIDTH: source_x = WIDTH - 1

            # Pull the heat from the cell below it
            heat[y][x] = heat[y+1][source_x]

    # 3. IGNITION (Fuel the bottom row)
    for x in range(WIDTH):
        # 55% chance to spark. We lowered the minimum spark heat to 160 
        # so some flames naturally start smaller than others.
        if random.randint(0, 100) < 55: 
            heat[HEIGHT-1][x] = random.randint(160, 255)
        else:
            # If it doesn't spark, rapidly cool the bottom row gap
            heat[HEIGHT-1][x] = max(0, heat[HEIGHT-1][x] - random.randint(30, 60))

def run_fire_demo():
    """The main simulation loop."""
    try:
        while True:
            update_fire()
            
            # Render the heat map to the physical LEDs
            for y in range(HEIGHT):
                for x in range(WIDTH):
                    idx = y * WIDTH + x
                    np[idx] = heat_to_color(heat[y][x])
            
            np.write()
            time.sleep(0.06) 
            
    except KeyboardInterrupt:
        # Clean shutdown via Thonny
        for i in range(PIXELS):
            np[i] = (0, 0, 0)
        np.write()

# Ignite the simulation
run_fire_demo()