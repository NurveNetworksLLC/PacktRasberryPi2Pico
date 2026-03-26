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
GLOBAL_BRIGHTNESS = 0.05  # Kept at 5% to protect the Pico's voltage regulator

# Initialize the NeoPixel matrix
np = neopixel.NeoPixel(machine.Pin(PIN), PIXELS, bpp=LED_ORDER)

# --- The Physics Engine State ---
# We create a 2D list (an array of arrays) to represent the 4x4 grid.
# 0 means empty space. Any number > 0 represents a grain of sand.
grid = [[0 for _ in range(WIDTH)] for _ in range(HEIGHT)]

def apply_color(idx, color_code):
    """Maps the virtual grid data to physical LED colors."""
    if color_code == 0:
        np[idx] = (0, 0, 0) # Turn LED off if empty
    else:
        # We use the color_code to slightly randomize the sand's tint 
        # so it looks textured, not just a solid block of color.
        r = int(255 * GLOBAL_BRIGHTNESS)
        g = int((200 - color_code * 15) * GLOBAL_BRIGHTNESS) # Varies the green to make yellow/orange
        b = int(50 * GLOBAL_BRIGHTNESS)
        np[idx] = (r, g, b)

def draw_grid():
    """Iterates through our 2D memory array and pushes it to the 1D hardware array."""
    for y in range(HEIGHT):
        for x in range(WIDTH):
            # Calculate the 1D index from 2D coordinates
            idx = y * WIDTH + x
            apply_color(idx, grid[y][x])
    np.write()

def update_sand():
    """
    The Core Physics Step.
    We must scan from the BOTTOM row to the TOP row. If we scanned top-down, 
    a falling grain of sand would be moved down, then evaluated again on the 
    next row, causing it to teleport instantly to the bottom of the screen!
    """
    # Start at the second-to-last row (HEIGHT - 2) and step backwards to 0
    for y in range(HEIGHT - 2, -1, -1): 
        for x in range(WIDTH):
            if grid[y][x] > 0: # If there is a grain of sand here
                
                # Rule 1: Try to fall straight down
                if grid[y+1][x] == 0:
                    grid[y+1][x] = grid[y][x] # Move sand down
                    grid[y][x] = 0            # Clear original spot
                
                # Rule 2: If blocked below, try to slide diagonally DOWN-LEFT
                # (We check x > 0 to ensure we don't fall off the left edge)
                elif x > 0 and grid[y+1][x-1] == 0:
                    grid[y+1][x-1] = grid[y][x]
                    grid[y][x] = 0
                
                # Rule 3: If blocked below and left, try to slide DOWN-RIGHT
                # (We check x < WIDTH - 1 to ensure we don't fall off the right edge)
                elif x < WIDTH - 1 and grid[y+1][x+1] == 0:
                    grid[y+1][x+1] = grid[y][x]
                    grid[y][x] = 0

def count_sand():
    """Counts how many pixels are currently filled with sand."""
    count = 0
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] > 0:
                count += 1
    return count

def run_sand_demo():
    """The main game loop."""
    try:
        while True:
            # 1. Calculate gravity/collisions for this frame
            update_sand()
            
            # 2. Spawn a new grain of sand at the top
            spawn_x = random.randint(0, WIDTH - 1)
            # Only spawn if the top row slot is empty
            if grid[0][spawn_x] == 0:
                # Assign a random value (1 to 5) to generate slight color variations
                grid[0][spawn_x] = random.randint(1, 5)
            
            # 3. Render the frame to the hardware
            draw_grid()
            
            # 4. Check for the reset condition
            # If 15 out of 16 pixels are full, the hourglass is packed.
            if count_sand() >= PIXELS - 1: 
                time.sleep(2) # Pause for 2 seconds to admire the full screen
                
                # Wipe the virtual grid clean
                for y in range(HEIGHT):
                    for x in range(WIDTH):
                        grid[y][x] = 0
            
            # 5. Frame rate delay (adjust this to make the sand fall faster or slower)
            time.sleep(0.15)
            
    except KeyboardInterrupt:
        # Clean shutdown if you press Stop in Thonny
        for i in range(PIXELS):
            np[i] = (0, 0, 0)
        np.write()

# Ignite the simulation
run_sand_demo()