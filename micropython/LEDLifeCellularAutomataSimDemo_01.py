"""
================================================================================
DEMO #4: CONWAY'S GAME OF LIFE (Version 4.3 - Phosphor & Structural Density)
================================================================================
THE UPGRADES:
1. STRUCTURAL COLORING: The render engine now does a micro-scan of the 16 
   visible pixels. Supported cells (>=3 neighbors) paint Red. Exposed edges 
   (<3 neighbors) paint White.
2. PHOSPHOR DECAY (ANTI-FLICKER): Instead of instantly turning off, dead 
   pixels now smoothly fade to black. This motion blur eliminates the 
   strobe effect inherent to Game of Life oscillators and makes the 
   integer-based camera panning look perfectly smooth.
3. SPEED: Locked to 0.015 seconds per frame for comfortable visual tracking.
================================================================================
"""

import machine
import neopixel
import time
import random
import math

# --- Hardware Configuration ---
PIN = 25
WIDTH = 4
HEIGHT = 4
PIXELS = WIDTH * HEIGHT
LED_ORDER = 3
GLOBAL_BRIGHTNESS = 0.05 

np = neopixel.NeoPixel(machine.Pin(PIN), PIXELS, bpp=LED_ORDER)

# --- Phosphor Decay Buffer ---
# We store the exact floating-point color of the 16 LEDs here to calculate smooth fades
led_state = [[0.0, 0.0, 0.0] for _ in range(PIXELS)]

# --- Universe Configuration ---
GRID_SIZE = 32
grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
next_grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

# --- Camera State ---
cam_x = float(GRID_SIZE / 2)
cam_y = float(GRID_SIZE / 2)
time_step = 0.0

def seed_universe(density=0.25):
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            if random.random() < density:
                grid[y][x] = 1
            else:
                grid[y][x] = 0

def inject_chaos():
    cx = random.randint(0, GRID_SIZE - 1)
    cy = random.randint(0, GRID_SIZE - 1)
    for dy in range(-3, 3):
        for dx in range(-3, 3):
            if random.random() < 0.5:
                nx = (cx + dx) % GRID_SIZE
                ny = (cy + dy) % GRID_SIZE
                grid[ny][nx] = 1

def update_universe():
    changed_cells = 0
    activity_x_sum = 0
    activity_y_sum = 0
    
    for y in range(GRID_SIZE):
        y_up = (y - 1) % GRID_SIZE
        y_dn = (y + 1) % GRID_SIZE
        
        for x in range(GRID_SIZE):
            x_left = (x - 1) % GRID_SIZE
            x_right = (x + 1) % GRID_SIZE
            
            neighbors = (
                grid[y_up][x_left] + grid[y_up][x] + grid[y_up][x_right] +
                grid[y][x_left]                    + grid[y][x_right] +
                grid[y_dn][x_left] + grid[y_dn][x] + grid[y_dn][x_right]
            )
            
            is_alive = grid[y][x] == 1
            
            if is_alive and (neighbors < 2 or neighbors > 3):
                next_grid[y][x] = 0
            elif not is_alive and neighbors == 3:
                next_grid[y][x] = 1 
            else:
                next_grid[y][x] = grid[y][x]
                
            if next_grid[y][x] != grid[y][x]:
                changed_cells += 1
                activity_x_sum += x
                activity_y_sum += y

    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            grid[y][x] = next_grid[y][x]
            
    if changed_cells > 0:
        target_x = activity_x_sum / changed_cells
        target_y = activity_y_sum / changed_cells
    else:
        target_x = GRID_SIZE / 2
        target_y = GRID_SIZE / 2
        
    return (target_x, target_y, changed_cells)

def render_viewport(cam_x, cam_y):
    start_x = int(cam_x)
    start_y = int(cam_y)
    
    for y in range(HEIGHT):
        for x in range(WIDTH):
            uni_x = (start_x + x) % GRID_SIZE
            uni_y = (start_y + y) % GRID_SIZE
            idx = y * WIDTH + x
            
            target_r, target_g, target_b = 0, 0, 0
            
            if grid[uni_y][uni_x] == 1:
                # Structural Density Scan (Check immediate neighbors)
                y_up = (uni_y - 1) % GRID_SIZE
                y_dn = (uni_y + 1) % GRID_SIZE
                x_left = (uni_x - 1) % GRID_SIZE
                x_right = (uni_x + 1) % GRID_SIZE
                
                n = (grid[y_up][x_left] + grid[y_up][uni_x] + grid[y_up][x_right] +
                     grid[uni_y][x_left]                    + grid[uni_y][x_right] +
                     grid[y_dn][x_left] + grid[y_dn][uni_x] + grid[y_dn][x_right])
                     
                if n >= 3:
                    # RED CORE: Protected inner cell
                    target_r = 255 * GLOBAL_BRIGHTNESS
                    target_g = 0
                    target_b = 0
                else:
                    # WHITE EDGE: Exposed outer cell
                    target_r = 200 * GLOBAL_BRIGHTNESS
                    target_g = 200 * GLOBAL_BRIGHTNESS
                    target_b = 200 * GLOBAL_BRIGHTNESS

            # THE PHOSPHOR BLEND (Motion Blur)
            # Mix 60% of the old color with 40% of the new target color
            led_state[idx][0] = (led_state[idx][0] * 0.6) + (target_r * 0.4)
            led_state[idx][1] = (led_state[idx][1] * 0.6) + (target_g * 0.4)
            led_state[idx][2] = (led_state[idx][2] * 0.6) + (target_b * 0.4)
            
            # Push the smoothed float values to the integer hardware array
            np[idx] = (int(led_state[idx][0]), int(led_state[idx][1]), int(led_state[idx][2]))
            
    np.write()

def run_life_demo():
    global cam_x, cam_y, time_step
    
    seed_universe()
    stagnation_timer = 0
    frame_count = 0
    
    try:
        while True:
            target_x, target_y, changes = update_universe()
            
            ideal_cam_x = target_x - 1.5
            ideal_cam_y = target_y - 1.5
            
            cam_x += (ideal_cam_x - cam_x) * 0.08
            cam_y += (ideal_cam_y - cam_y) * 0.08
            
            cam_x += math.sin(time_step * 0.8) * 0.3
            cam_y += math.cos(time_step * 0.6) * 0.3
            
            cam_x %= GRID_SIZE
            cam_y %= GRID_SIZE
            
            render_viewport(cam_x, cam_y)
            
            if changes < 5:
                stagnation_timer += 1
            else:
                stagnation_timer = 0
                
            if stagnation_timer > 30:
                seed_universe()
                stagnation_timer = 0
                
            if frame_count % 100 == 0:
                inject_chaos()
                
            time_step += 0.15
            frame_count += 1
            
            # THE GOLDEN RATIO SPEED THROTTLE
            time.sleep(0.015) 
            
    except KeyboardInterrupt:
        for i in range(PIXELS):
            np[i] = (0, 0, 0)
        np.write()

# Ignite the Universe
run_life_demo()