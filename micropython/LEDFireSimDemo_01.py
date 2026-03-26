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
# We maintain a "heat" map instead of a color map. 
# 0 is cold (black), 255 is intensely hot (yellow/white).
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
    """
    Translates a raw temperature (0-255) into a realistic fire color.
    0 = Black
    Low Temp = Dim Red
    Medium Temp = Bright Orange
    High Temp = Blinding Yellow
    """
    # Safety clamp to ensure temperature stays within 0-255 bounds
    temperature = max(0, min(255, temperature))

    # If it's too cold, it doesn't emit any light
    if temperature < 30:
        return (0, 0, 0)

    # 1. Calculate Hue: 0.0 is Red, 0.15 is Yellow.
    # The hotter it gets, the closer the hue shifts toward yellow.
    hue = (temperature / 255.0) * 0.15

    # 2. Calculate Brightness: The hotter it is, the brighter it glows.
    # We multiply by GLOBAL_BRIGHTNESS to prevent blowing out the board.
    val = (temperature / 255.0) * GLOBAL_BRIGHTNESS

    # Return fully saturated (1.0) fire colors
    return hsv_to_rgb(hue, 1.0, val)

def update_fire():
    """The Core Thermodynamics Step."""
    
    # 1. Cool down the entire grid slightly so the fire doesn't run out of control.
    for y in range(HEIGHT):
        for x in range(WIDTH):
            cooling_amount = random.randint(0, 30)
            heat[y][x] = max(0, heat[y][x] - cooling_amount)

    # 2. Move the heat UPWARDS.
    # We iterate from the top row (0) down to the second-to-last row (2).
    # We don't touch the bottom row (3) here, because that is our fuel source.
    for y in range(HEIGHT - 1): 
        for x in range(WIDTH):
            
            # To make the flames flicker naturally, the heat doesn't just go straight up.
            # It occasionally drifts slightly to the left or right.
            drift = random.randint(-1, 1)
            source_x = x + drift
            
            # Keep the drift within the 4x4 physical bounds
            if source_x < 0: source_x = 0
            if source_x >= WIDTH: source_x = WIDTH - 1

            # Pull the heat from the cell below it and move it to the current cell
            heat[y][x] = heat[y+1][source_x]

    # 3. Ignite the fuel source (The bottom row).
    for x in range(WIDTH):
        # We give the bottom row a 60% chance to spark with intense heat every frame.
        if random.randint(0, 100) < 60: 
            heat[HEIGHT-1][x] = random.randint(160, 255)
        else:
            # If it doesn't spark, it cools down rapidly.
            heat[HEIGHT-1][x] = max(0, heat[HEIGHT-1][x] - 40)

def run_fire_demo():
    """The main simulation loop."""
    try:
        while True:
            # 1. Calculate the physics for this frame
            update_fire()
            
            # 2. Render the heat map to the physical LEDs
            for y in range(HEIGHT):
                for x in range(WIDTH):
                    idx = y * WIDTH + x
                    np[idx] = heat_to_color(heat[y][x])
            
            np.write()
            
            # 3. Fire needs to move faster than falling sand to look kinetic and violent.
            time.sleep(0.06) 
            
    except KeyboardInterrupt:
        # Clean shutdown via Thonny
        for i in range(PIXELS):
            np[i] = (0, 0, 0)
        np.write()

# Ignite the simulation
run_fire_demo()