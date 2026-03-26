"""
================================================================================
DEMO #3: 2D PARALLAX STARFIELD (The Starboard Window)
================================================================================
THE PARALLAX ALGORITHM:
This engine creates an array of "star" objects using floating-point coordinates 
to allow for smooth "sub-pixel" speed.

By moving the stars from Right to Left (decreasing the X coordinate), we 
trigger the human brain's natural association with looking out the side window 
of a moving vehicle. 

The core trick remains the brightness calculation. We multiply the star's 
color by its speed. This means a star moving at 0.1 speed is very dim 
(deep background), and a star moving at 0.9 speed is blindingly bright 
(foreground). When they overlap, the optical illusion of 3D depth is created.
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

# --- Starfield Engine State ---
NUM_STARS = 6 
stars = []

def create_star():
    """Generates a new star off the RIGHT side of the screen."""
    # We spawn them at an X value greater than the width so they stagger 
    # their entry onto the screen, rather than appearing all at once.
    x = random.uniform(WIDTH, WIDTH + 3.0) 
    
    # Random physical row (0 to 3)
    y = random.randint(0, HEIGHT - 1)
    
    # Speed ranges from 0.15 (very slow/dim) to 0.8 (very fast/bright)
    speed = random.uniform(0.15, 0.8) 
    
    # 80% chance of pure white, 10% hot blue, 10% cool orange
    color_roll = random.randint(1, 10)
    if color_roll <= 8:
        base_color = (255, 255, 255) # Standard White Star
    elif color_roll == 9:
        base_color = (150, 150, 255) # Hot Blue Star
    else:
        base_color = (255, 180, 150) # Cool Orange/Red Dwarf
        
    return [x, y, speed, base_color]

# Populate the initial universe array
for _ in range(NUM_STARS):
    stars.append(create_star())

def update_and_draw_stars():
    """Calculates orbital physics and renders the frame."""
    
    # 1. Clear the canvas (Deep Space is black)
    for i in range(PIXELS):
        np[i] = (0, 0, 0)
        
    # 2. Update and draw each star
    for i in range(NUM_STARS):
        star = stars[i]
        
        # Apply velocity to the X axis (moving LEFT means subtracting)
        star[0] -= star[2] 
        
        # If the star falls completely off the LEFT edge (drops below 0), recycle it!
        # We overwrite its data with a brand new star starting on the right.
        if star[0] < 0:
            stars[i] = create_star()
            star = stars[i]
        
        # 3. Rendering Logic
        # We only draw the star if it has actually entered the visible screen (X < WIDTH)
        if star[0] < WIDTH:
            # Truncate the float to an integer to find the physical LED
            x_pos = int(star[0])
            y_pos = int(star[1])
            
            # Check boundaries to prevent memory index errors
            if 0 <= x_pos < WIDTH and 0 <= y_pos < HEIGHT:
                
                # Multiply the color by the global safeguard, AND by the star's speed
                brightness_mod = star[2] 
                
                r = int(star[3][0] * GLOBAL_BRIGHTNESS * brightness_mod)
                g = int(star[3][1] * GLOBAL_BRIGHTNESS * brightness_mod)
                b = int(star[3][2] * GLOBAL_BRIGHTNESS * brightness_mod)
                
                idx = y_pos * WIDTH + x_pos
                
                # Push the color to the physical hardware array
                np[idx] = (r, g, b)
                
    np.write()

def run_starfield_demo():
    """The main warp drive loop."""
    try:
        while True:
            update_and_draw_stars()
            time.sleep(0.04) 
            
    except KeyboardInterrupt:
        # Clean shutdown via Thonny
        for i in range(PIXELS):
            np[i] = (0, 0, 0)
        np.write()

# Ignite the warp drive
run_starfield_demo()