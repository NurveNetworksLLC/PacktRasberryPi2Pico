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
GLOBAL_BRIGHTNESS = 0.05  # Safe power limit for the Pico regulator

# Initialize the NeoPixel matrix
np = neopixel.NeoPixel(machine.Pin(PIN), PIXELS, bpp=LED_ORDER)

# --- The Physics Engine State ---
# We use -1 to represent EMPTY space. 
# Any value from 0 to 255 represents a grain of sand and its specific Hue (Color).
grid = [[-1 for _ in range(WIDTH)] for _ in range(HEIGHT)]

def hsv_to_rgb(h, s, v):
    """
    Converts a Hue (0.0 to 1.0) into standard RGB.
    This is critical for easily shifting colors through the rainbow
    without having to manually calculate Red, Green, and Blue sine waves.
    """
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

def apply_color(idx, hue_val):
    """Maps the virtual grid data to physical LED colors."""
    if hue_val == -1:
        np[idx] = (0, 0, 0) # Turn LED off if empty
    else:
        # Convert our 0-255 Hue integer into a 0.0-1.0 float for the math function
        h_float = hue_val / 255.0
        # Get the RGB tuple, utilizing our global brightness safeguard
        rgb = hsv_to_rgb(h_float, 1.0, GLOBAL_BRIGHTNESS)
        np[idx] = rgb

def draw_grid():
    """Iterates through our 2D memory array and pushes it to the hardware."""
    for y in range(HEIGHT):
        for x in range(WIDTH):
            idx = y * WIDTH + x
            apply_color(idx, grid[y][x])
    np.write()

def update_sand():
    """The Core Physics Step (Scanning bottom-to-top to prevent teleportation)."""
    for y in range(HEIGHT - 2, -1, -1): 
        for x in range(WIDTH):
            if grid[y][x] != -1: # If there is a grain of sand here
                # Rule 1: Fall straight down
                if grid[y+1][x] == -1:
                    grid[y+1][x] = grid[y][x]
                    grid[y][x] = -1
                # Rule 2: Slide diagonally DOWN-LEFT
                elif x > 0 and grid[y+1][x-1] == -1:
                    grid[y+1][x-1] = grid[y][x]
                    grid[y][x] = -1
                # Rule 3: Slide diagonally DOWN-RIGHT
                elif x < WIDTH - 1 and grid[y+1][x+1] == -1:
                    grid[y+1][x+1] = grid[y][x]
                    grid[y][x] = -1

def count_sand():
    """Counts how many pixels are currently filled."""
    count = 0
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] != -1:
                count += 1
    return count

def drop_floor():
    """
    The Infinite Scroll Mechanic.
    Shifts every row down by 1. The bottom row is overwritten and lost.
    The top row is cleared to make room for new sand.
    """
    for y in range(HEIGHT - 1, 0, -1):
        for x in range(WIDTH):
            grid[y][x] = grid[y-1][x]
    
    # Clear the very top row
    for x in range(WIDTH):
        grid[0][x] = -1

def run_infinite_sand():
    """The main game loop."""
    base_hue = 0        # Start at Red
    grains_spawned = 0  # Track how much sand has fallen to know when to change color
    frame_tick = 0      # Used to slow down the spawn rate slightly
    
    try:
        while True:
            # 1. Calculate gravity/collisions
            update_sand()
            
            # 2. Spawn new sand (every other frame so it doesn't instantly clog)
            if frame_tick % 2 == 0:
                spawn_x = random.randint(0, WIDTH - 1)
                if grid[0][spawn_x] == -1:
                    # Add a slight random variance (-15 to +15) to the hue 
                    # so the sand looks textured, not just a solid block of color.
                    hue_variance = random.randint(-15, 15)
                    grain_color = (base_hue + hue_variance) % 256
                    
                    grid[0][spawn_x] = grain_color
                    grains_spawned += 1
                    
                    # 3. Change the overall color palette every 16 grains (approx 1 screen)
                    if grains_spawned % 16 == 0:
                        # Shift the hue by 45 degrees (e.g., Red -> Yellow -> Green)
                        base_hue = (base_hue + 45) % 256
            
            # 4. Render the frame
            draw_grid()
            
            # 5. Check the "Weight" of the screen
            # If 12 or more pixels are full (75% capacity), drop the floor.
            # This ensures the screen never fills, and old sand falls off the bottom.
            if count_sand() >= 12:
                drop_floor()
            
            frame_tick += 1
            time.sleep(0.15) # Adjust for overall speed
            
    except KeyboardInterrupt:
        # Clean shutdown for Thonny
        for i in range(PIXELS):
            np[i] = (0, 0, 0)
        np.write()

# Ignite the simulation
run_infinite_sand()