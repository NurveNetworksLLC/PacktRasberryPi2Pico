"""
================================================================================
DEMO #5: THE LIGHT CYCLE (Version 5.1 - Seamless Transition & Brightness Fix)
================================================================================
THE UPGRADES:
1. MATH FIX: GLOBAL_BRIGHTNESS is now correctly passed as a 0.0 to 1.0 float, 
   preventing the integer overflow that blinded you.
2. CONTINUOUS MOTION: The artificial pause has been removed. When a cycle dies, 
   the new one spawns 3 coordinates OUTSIDE the physical matrix. As it drives 
   inward, the previous tail has exactly 3 frames to smoothly fade to black 
   before the new cycle enters the frame.
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
GLOBAL_BRIGHTNESS = 0.05 # Now functioning correctly as a 5% cap

np = neopixel.NeoPixel(machine.Pin(PIN), PIXELS, bpp=LED_ORDER)

# --- Phosphor Decay Buffer ---
led_state = [[0.0, 0.0, 0.0] for _ in range(PIXELS)]

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

class LightCycle:
    def __init__(self):
        self.reset()

    def reset(self):
        """Spawns a new cycle in the 'Void' outside the physical matrix."""
        # Fixed the brightness bug here: Passed GLOBAL_BRIGHTNESS cleanly
        self.color = hsv_to_rgb(random.random(), 1.0, GLOBAL_BRIGHTNESS)
        
        edge = random.randint(0, 3)
        spawn_dist = 3 # Start 3 frames away from the screen to allow the old tail to fade
        
        if edge == 0:
            self.x, self.y = random.randint(0, WIDTH-1), -spawn_dist
            self.dx, self.dy = 0, 1
        elif edge == 1:
            self.x, self.y = WIDTH + spawn_dist - 1, random.randint(0, HEIGHT-1)
            self.dx, self.dy = -1, 0
        elif edge == 2:
            self.x, self.y = random.randint(0, WIDTH-1), HEIGHT + spawn_dist - 1
            self.dx, self.dy = 0, -1
        else:
            self.x, self.y = -spawn_dist, random.randint(0, HEIGHT-1)
            self.dx, self.dy = 1, 0

        self.lifespan = random.randint(6, 15)
        self.state = "ENTERING"

    def update(self):
        """Calculates movement and AI. Returns True if completely off-screen."""
        self.x += self.dx
        self.y += self.dy

        if self.state == "ENTERING":
            if 0 <= self.x < WIDTH and 0 <= self.y < HEIGHT:
                self.state = "ROAMING"
        
        elif self.state == "ROAMING":
            self.lifespan -= 1
            if self.lifespan <= 0:
                self.state = "EXITING"
            else:
                next_x = self.x + self.dx
                next_y = self.y + self.dy
                
                hit_wall = not (0 <= next_x < WIDTH and 0 <= next_y < HEIGHT)
                random_turn = random.random() < 0.2  
                
                if hit_wall or random_turn:
                    # 90-degree turn
                    if random.choice([True, False]):
                        self.dx, self.dy = self.dy, -self.dx 
                    else:
                        self.dx, self.dy = -self.dy, self.dx 
                        
                    # Corner trap check
                    next_x = self.x + self.dx
                    next_y = self.y + self.dy
                    if not (0 <= next_x < WIDTH and 0 <= next_y < HEIGHT):
                        self.dx, self.dy = -self.dx, -self.dy

        elif self.state == "EXITING":
            if not (0 <= self.x < WIDTH and 0 <= self.y < HEIGHT):
                return True 
        
        return False

def run_tron_demo():
    cycle = LightCycle()
    
    try:
        while True:
            # 1. Decay the phosphor buffer by 40% every frame
            for i in range(PIXELS):
                led_state[i][0] *= 0.6
                led_state[i][1] *= 0.6
                led_state[i][2] *= 0.6

            # 2. Update AI
            needs_reset = cycle.update()
            
            # 3. Draw the Head (if it is currently within physical bounds)
            if 0 <= cycle.x < WIDTH and 0 <= cycle.y < HEIGHT:
                idx = cycle.y * WIDTH + cycle.x
                led_state[idx][0] = cycle.color[0]
                led_state[idx][1] = cycle.color[1]
                led_state[idx][2] = cycle.color[2]

            # 4. Render to hardware
            for i in range(PIXELS):
                np[i] = (int(led_state[i][0]), int(led_state[i][1]), int(led_state[i][2]))
            np.write()

            # 5. Continuous Loop Logic
            if needs_reset:
                cycle.reset() # Spawns in the void, no artificial sleep required
            
            time.sleep(0.12) # Standard driving speed

    except KeyboardInterrupt:
        for i in range(PIXELS):
            np[i] = (0, 0, 0)
        np.write()

run_tron_demo()