"""
================================================================================
DEMO #6: THE BEATING HEART (Version 6.1 - Hardware Anti-Aliasing)
================================================================================
THE UPGRADE:
To make the 4x4 heart look organic and not blocky (or like a Galaga space 
invader), we implemented Hardware Anti-Aliasing.

The 'blueprints' now store a third value: Per-Pixel Intensity (0.0 to 1.0).

In the FULL_HEART blueprint, we added coordinate (1, 0). That is the gap 
between the two humps. We assigned it an intensity of 0.15 (15%). By making 
that single pixel much dimmer, we visually "smooth" the edge of the humps, 
selling the illusion of a curved heart much better on a tiny resolution.
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
GLOBAL_BRIGHTNESS = 0.05 

np = neopixel.NeoPixel(machine.Pin(PIN), PIXELS, bpp=LED_ORDER)

def hsv_to_rgb(h, s, v):
    """Converts a Hue (0.0 to 1.0) into standard RGB."""
    # The 'v' parameter (Value/Brightness) MUST remain between 0.0 and 1.0
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

# --- The NEW Heart Blueprints with Anti-Aliasing Map ---
# Format: (X_Offset, Y_Offset, Per-Pixel_Intensity [0.0 - 1.0])

# Just the core dot
DOT = [(1, 1, 1.0)] 

# The growing cross shape
SMALL_HEART = [(1, 1, 1.0), (0, 1, 1.0), (2, 1, 1.0), (1, 2, 1.0)]

# The final, anti-aliased shape
FULL_HEART = [
    # --- Main Core Body (Max Brightness) ---
    (1, 1, 1.0), (0, 1, 1.0), (2, 1, 1.0), (1, 2, 1.0),
    (0, 0, 1.0), (2, 0, 1.0), # Top-Left Hump & Top-Right Hump

    # --- THE ANTI-ALIASING PIXELS ---
    # User requested gap between top humps, set at 15% intensity.
    # This visually "rounds" the sharp corner.
    (1, 0, 0.15) 
]

def clear_screen():
    """Wipes the matrix clean."""
    for i in range(PIXELS):
        np[i] = (0, 0, 0)
    np.write()

def draw_shape(offset_x, offset_y, shape, hue, animation_intensity):
    """Draws a blueprint, combining global brightness, pulse, and pixel mapping."""
    # animation_intensity comes from the fading loops (0.0 to 1.0)
    
    # We don't wipe the screen here. The loops handle clearing to prevent 
    # accidental sub-frame flicker.

    # Format of 'shape' is now (dx, dy, pixel_intensity_mod)
    for dx, dy, pixel_intensity_mod in shape:
        x = offset_x + dx
        y = offset_y + dy
        
        # Verify physical hardware bounds
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            idx = y * WIDTH + x
            
            # THE BRIGHTNESS COMPOSITOR:
            # We multiply 3 separate factors to find the final luminosity:
            # 1. Hardware Safeguard (0.05)
            # 2. Animation Cycle (the Pulse/Fade value)
            # 3. Per-Pixel Blueprint Map (the Anti-Aliasing mod)
            
            final_intensity = GLOBAL_BRIGHTNESS * animation_intensity * pixel_intensity_mod
            
            # Map the combined intensity value (0.0 - 1.0) to RGB
            rgb = hsv_to_rgb(hue, 1.0, final_intensity)
            
            # Physical hardware write
            np[idx] = rgb
            
    np.write()

def run_heart_animation():
    print("HAL 9000: Heart Sequence 2.1 (Anti-Aliasing) Initialized for Alexia.")
    try:
        while True:
            # 1. Pick a random corner (0 or 1) and a random rainbow color
            ox = random.randint(0, 1) 
            oy = random.randint(0, 1) 
            hue = random.random()     

            # 2. THE SPARK: Flicker the center dot
            for _ in range(4):
                draw_shape(ox, oy, DOT, hue, random.uniform(0.2, 1.0))
                time.sleep(0.08)
                clear_screen()
                time.sleep(0.05)

            # 3. THE BLOOM: Grow the shape smoothly
            draw_shape(ox, oy, DOT, hue, 1.0)
            time.sleep(0.2)
            clear_screen() # Clear before adding the new layer
            draw_shape(ox, oy, SMALL_HEART, hue, 1.0)
            time.sleep(0.2)
            clear_screen()
            draw_shape(ox, oy, FULL_HEART, hue, 1.0) # Now draws the AA pixels
            time.sleep(0.4)

            # 4. THE PULSE: Beat 3 times
            for _ in range(3):
                # Exhale (Fade down to 20%)
                for i in range(10, 1, -1):
                    # We must clear the screen inside the pulse loop to ensure
                    # the dim anti-alias pixels don't get "stuck" bright.
                    clear_screen()
                    draw_shape(ox, oy, FULL_HEART, hue, i / 10.0)
                    time.sleep(0.015)
                # Inhale (Fade up to 100%)
                for i in range(2, 11):
                    clear_screen()
                    draw_shape(ox, oy, FULL_HEART, hue, i / 10.0)
                    time.sleep(0.015)
                
                time.sleep(0.18) # Brief rest between beats

            # 5. THE GHOST: Fade away smoothly into the void
            for i in range(10, -1, -1):
                clear_screen()
                draw_shape(ox, oy, FULL_HEART, hue, i / 10.0)
                time.sleep(0.04)

            # Rest in the dark before starting over
            time.sleep(1.2)

    except KeyboardInterrupt:
        clear_screen()
        print("HAL 9000: Animation Terminated.")

# Ignite the Heart
run_heart_animation()