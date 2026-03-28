"""
================================================================================
HAL 9000: BARE-METAL SSD1306 DRIVER (128x32) & ASTEROIDS DELUXE DEMO
Hardware: RP2350 (Pico 2) | I2C1: SDA=GP14, SCL=GP15 | Gamepad: GP0-GP6
================================================================================
"""
import machine
import time
import math
import random

# --- GAMEPAD DRIVER ---
pad_pins = [machine.Pin(i, machine.Pin.IN, machine.Pin.PULL_UP) for i in range(7)]

def read_gamepad():
    """Returns: [UP, DOWN, LEFT, RIGHT, MID, SET, RST] -> 1=Pressed, 0=Open"""
    return [1 if p.value() == 0 else 0 for p in pad_pins]

# --- THE OLED DRIVER ---
class FastOLED_128x32:
    def __init__(self, i2c, address=0x3c, rotation=0):
        self.i2c = i2c
        self.addr = address
        self.rot = rotation
        
        # Logical dimensions for bounds checking
        if self.rot == 90 or self.rot == 270:
            self.width, self.height = 32, 128
        else:
            self.width, self.height = 128, 32

        # 513-byte Double Buffer. Index 0 is the control byte (0x40).
        self.payload = bytearray(513)
        self.payload[0] = 0x40 
        self.buffer = memoryview(self.payload)[1:] 

        self._init_display()

    def _init_display(self):
        seg_remap = 0xA1 if self.rot != 180 else 0xA0
        com_scan = 0xC8 if self.rot != 180 else 0xC0

        init_cmds = [
            0xAE, 0xD5, 0x80, 0xA8, 0x1F, 0xD3, 0x00, 0x40, 
            0x8D, 0x14, 0x20, 0x00, seg_remap, com_scan, 
            0xDA, 0x02, 0x81, 0x8F, 0xD9, 0xF1, 0xDB, 0x40, 
            0xA4, 0xA6, 0xAF
        ]
        for cmd in init_cmds:
            self.i2c.writeto(self.addr, bytes([0x00, cmd]))

    def show(self):
        self.i2c.writeto(self.addr, self.payload)

    def clear(self):
        for i in range(512):
            self.buffer[i] = 0

    def pixel(self, x, y, color=1):
        """Translates logical Portrait/Landscape coordinates to physical memory."""
        # Convert floats to ints automatically
        x, y = int(x), int(y)
        
        # Hardware memory mapping based on rotation
        if self.rot == 90:
            px, py = y, 31 - x
        elif self.rot == 270:
            px, py = 127 - y, x
        elif self.rot == 180:
            px, py = 127 - x, 31 - y
        else:
            px, py = x, y

        if 0 <= px < 128 and 0 <= py < 32:
            idx = px + (py // 8) * 128
            if color:
                self.buffer[idx] |= (1 << (py % 8))
            else:
                self.buffer[idx] &= ~(1 << (py % 8))

    # --- GEOMETRY PRIMITIVES ---
    def hline(self, x, y, w, color=1):
        for i in range(x, x + w): self.pixel(i, y, color)

    def vline(self, x, y, h, color=1):
        for i in range(y, y + h): self.pixel(x, i, color)

    def line(self, x0, y0, x1, y1, color=1):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.pixel(x0, y0, color)
            if x0 == x1 and y0 == y1: break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def rect(self, x, y, w, h, color=1, filled=False):
        if filled:
            for i in range(x, x + w): self.vline(i, y, h, color)
        else:
            self.hline(x, y, w, color); self.hline(x, y + h - 1, w, color)
            self.vline(x, y, h, color); self.vline(x + w - 1, y, h, color)

    def circle(self, x0, y0, r, color=1, filled=False):
        # Implementation hidden for brevity, same as previous.
        f = 1 - r
        ddF_x, ddF_y = 1, -2 * r
        x, y = 0, r
        self.pixel(x0, y0 + r, color); self.pixel(x0, y0 - r, color)
        self.pixel(x0 + r, y0, color); self.pixel(x0 - r, y0, color)
        while x < y:
            if f >= 0:
                y -= 1; ddF_y += 2; f += ddF_y
            x += 1; ddF_x += 2; f += ddF_x
            self.pixel(x0 + x, y0 + y, color); self.pixel(x0 - x, y0 + y, color)
            self.pixel(x0 + x, y0 - y, color); self.pixel(x0 - x, y0 - y, color)
            self.pixel(x0 + y, y0 + x, color); self.pixel(x0 - y, y0 + x, color)
            self.pixel(x0 + y, y0 - x, color); self.pixel(x0 - y, y0 - x, color)


# ==============================================================================
# MAIN DEMO: ASTEROIDS DELUXE (VERTICAL)
# ==============================================================================

class Asteroid:
    def __init__(self, x, y, size):
        self.x = float(x)
        self.y = float(y)
        self.size = size # 2 = Big, 1 = Small
        
        # The 32-pixel screen is incredibly narrow. We must scale down radii.
        self.radius = 5.0 if size == 2 else 2.5
        
        # Generate random craggy shape
        num_points = 6 if size == 2 else 4
        self.pts = []
        for i in range(num_points):
            angle = (i / num_points) * math.pi * 2
            r = self.radius * random.uniform(0.7, 1.3)
            self.pts.append((r * math.cos(angle), r * math.sin(angle)))
            
        self.angle = 0.0
        self.rot_speed = random.uniform(-0.15, 0.15)
        # Smaller asteroids fall faster
        self.vy = random.uniform(0.6, 1.2) if size == 2 else random.uniform(1.0, 2.0)

    def update(self):
        self.y += self.vy
        self.angle += self.rot_speed

    def draw(self, oled):
        """Applies a math rotation matrix to draw the wireframe on the fly."""
        last_px, last_py = None, None
        first_px, first_py = None, None
        
        for px, py in self.pts:
            # Mathematical 2D Rotation
            rx = px * math.cos(self.angle) - py * math.sin(self.angle)
            ry = px * math.sin(self.angle) + py * math.cos(self.angle)
            
            screen_x = self.x + rx
            screen_y = self.y + ry
            
            if last_px is not None:
                oled.line(last_px, last_py, screen_x, screen_y)
            else:
                first_px, first_py = screen_x, screen_y
            last_px, last_py = screen_x, screen_y
            
        # Close the polygon
        oled.line(last_px, last_py, first_px, first_py)

def run_asteroids_demo():
    print("HAL 9000: Initializing Vector Engine in Portrait Mode...")
    i2c = machine.I2C(1, sda=machine.Pin(14), scl=machine.Pin(15), freq=1000000)
    
    # Init display rotated 90 degrees (Logical 32 width x 128 height)
    oled = FastOLED_128x32(i2c, rotation=270)
    
    # --- Game State ---
    ship_x = 16.0
    ship_y = 115.0
    ship_speed = 1.8
    fire_cooldown = 0
    
    missiles = []
    asteroids = []
    particles = []
    
    # Generate Parallax Starfield [x, y, speed]
    stars = [[random.randint(0, 31), random.randint(0, 127), random.uniform(0.1, 0.8)] for _ in range(15)]
    
    try:
        while True:
            pad = read_gamepad()
            
            # --- 1. SHIP MOVEMENT ---
            thrusting = False
            if pad[0] and ship_y > 100: ship_y -= ship_speed # UP (Limited to bottom 20%)
            if pad[1] and ship_y < 122: ship_y += ship_speed # DOWN
            if pad[2]: 
                ship_x -= ship_speed # LEFT
                thrusting = True
            if pad[3]: 
                ship_x += ship_speed # RIGHT
                thrusting = True
            
            # Wrap lateral edges
            ship_x %= oled.width
            
            # --- 2. WEAPONS ---
            if fire_cooldown > 0:
                fire_cooldown -= 1
            if pad[4] and fire_cooldown == 0: # MID button to fire
                missiles.append([ship_x, ship_y - 5])
                fire_cooldown = 8 # Prevent constant laser beams

            # Update Missiles
            for m in missiles[:]:
                m[1] -= 3.0 # Travel UP
                if m[1] < 0:
                    missiles.remove(m)

            # --- 3. ASTEROID SPAWNER ---
            if len(asteroids) < 4 and random.random() < 0.05:
                asteroids.append(Asteroid(random.randint(4, 28), -10, size=2))

            # Update Asteroids
            for a in asteroids[:]:
                a.update()
                if a.y > 140: # Missed, went off bottom
                    asteroids.remove(a)

            # --- 4. PARTICLES ---
            for p in particles[:]:
                p[0] += p[2] # vx
                p[1] += p[3] # vy
                p[4] -= 1    # life
                if p[4] <= 0:
                    particles.remove(p)

            # --- 5. COLLISION DETECTION ---
            for m in missiles[:]:
                hit = False
                for a in asteroids[:]:
                    # Simple radius distance check
                    dist = math.sqrt((m[0] - a.x)**2 + (m[1] - a.y)**2)
                    if dist <= a.radius:
                        hit = True
                        asteroids.remove(a)
                        
                        # Spawn explosion particles
                        for _ in range(5):
                            particles.append([a.x, a.y, random.uniform(-1, 1), random.uniform(-1, 1), random.randint(10, 20)])
                        
                        # Shatter into smaller asteroids
                        if a.size == 2:
                            asteroids.append(Asteroid(a.x - 3, a.y, size=1))
                            asteroids.append(Asteroid(a.x + 3, a.y, size=1))
                        break
                if hit and m in missiles:
                    missiles.remove(m)

            # --- 6. RENDER PHASE ---
            oled.clear()
            
            # Draw Parallax Stars
            for s in stars:
                s[1] += s[2] # Fall down
                if s[1] > 128: 
                    s[1] = 0
                    s[0] = random.randint(0, 31)
                oled.pixel(s[0], s[1])

            # Draw Asteroids
            for a in asteroids:
                a.draw(oled)

            # Draw Missiles
            for m in missiles:
                oled.line(m[0], m[1], m[0], m[1]+2)

            # Draw Particles
            for p in particles:
                oled.pixel(p[0], p[1])

            # Draw Ship (Vector Triangle)
            oled.line(ship_x, ship_y-5, ship_x+4, ship_y+4) # Right wing
            oled.line(ship_x+4, ship_y+4, ship_x-4, ship_y+4) # Bottom
            oled.line(ship_x-4, ship_y+4, ship_x, ship_y-5) # Left wing
            
            # Draw Engine Thrust
            if thrusting or pad[0]:
                if random.random() < 0.5:
                    oled.line(ship_x-2, ship_y+4, ship_x, ship_y+8)
                    oled.line(ship_x+2, ship_y+4, ship_x, ship_y+8)

            oled.show()
            time.sleep(0.015)

    except KeyboardInterrupt:
        oled.clear()
        oled.show()
        print("HAL 9000: Game Terminated.")

run_asteroids_demo()