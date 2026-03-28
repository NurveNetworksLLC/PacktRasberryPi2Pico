"""
================================================================================
HAL 9000: BARE-METAL SSD1306 DRIVER (128x32) & ASTEROIDS DELUXE DEMO v8.4
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
        
        if self.rot == 90 or self.rot == 270:
            self.width, self.height = 32, 128
        else:
            self.width, self.height = 128, 32

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
        x, y = int(x), int(y)
        if self.rot == 90: px, py = y, 31 - x
        elif self.rot == 270: px, py = 127 - y, x
        elif self.rot == 180: px, py = 127 - x, 31 - y
        else: px, py = x, y

        if 0 <= px < 128 and 0 <= py < 32:
            idx = px + (py // 8) * 128
            if color: self.buffer[idx] |= (1 << (py % 8))
            else: self.buffer[idx] &= ~(1 << (py % 8))

    def hline(self, x, y, w, color=1):
        for i in range(x, x + w): self.pixel(i, y, color)

    def vline(self, x, y, h, color=1):
        for i in range(y, y + h): self.pixel(x, i, color)

    def line(self, x0, y0, x1, y1, color=1):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = 1 if x0 < x1 else -1, 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.pixel(x0, y0, color)
            if x0 == x1 and y0 == y1: break
            e2 = 2 * err
            if e2 >= dy: err += dy; x0 += sx
            if e2 <= dx: err += dx; y0 += sy

    def rect(self, x, y, w, h, color=1, filled=False):
        if filled:
            for i in range(x, x + w): self.vline(i, y, h, color)
        else:
            self.hline(x, y, w, color); self.hline(x, y + h - 1, w, color)
            self.vline(x, y, h, color); self.vline(x + w - 1, y, h, color)

    def circle(self, x0, y0, r, color=1, filled=False):
        f = 1 - r
        ddF_x, ddF_y = 1, -2 * r
        x, y = 0, r
        self.pixel(x0, y0 + r, color); self.pixel(x0, y0 - r, color)
        self.pixel(x0 + r, y0, color); self.pixel(x0 - r, y0, color)
        while x < y:
            if f >= 0: y -= 1; ddF_y += 2; f += ddF_y
            x += 1; ddF_x += 2; f += ddF_x
            self.pixel(x0 + x, y0 + y, color); self.pixel(x0 - x, y0 + y, color)
            self.pixel(x0 + x, y0 - y, color); self.pixel(x0 - x, y0 - y, color)
            self.pixel(x0 + y, y0 + x, color); self.pixel(x0 - y, y0 + x, color)
            self.pixel(x0 + y, y0 - x, color); self.pixel(x0 - y, y0 - x, color)

# ==============================================================================
# MAIN DEMO: ASTEROIDS DELUXE (HIGH FRAMERATE PATCH)
# ==============================================================================

class Asteroid:
    def __init__(self, x, y, size, vx=None, vy=None):
        self.x = float(x)
        self.y = float(y)
        self.size = size 
        self.radius = 6.5 if size == 2 else 3.5
        
        num_points = 6 if size == 2 else 4
        self.pts = []
        for i in range(num_points):
            angle = (i / num_points) * math.pi * 2
            r = self.radius * random.uniform(0.7, 1.3)
            self.pts.append((r * math.cos(angle), r * math.sin(angle)))
            
        self.angle = 0.0
        # Reduced rotation by half for 30+ FPS
        self.rot_speed = random.uniform(-0.075, 0.075) 
        
        if vx is None or vy is None:
            # Reduced drop speeds by half for 30+ FPS
            speed = random.uniform(0.3, 0.6) if size == 2 else random.uniform(0.5, 1.0)
            move_angle = (math.pi / 2) + random.uniform(-math.pi / 6, math.pi / 6)
            self.vx = speed * math.cos(move_angle)
            self.vy = speed * math.sin(move_angle)
        else:
            self.vx = vx
            self.vy = vy

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.angle += self.rot_speed

    def draw(self, oled):
        last_px, last_py = None, None
        first_px, first_py = None, None
        
        for px, py in self.pts:
            rx = px * math.cos(self.angle) - py * math.sin(self.angle)
            ry = px * math.sin(self.angle) + py * math.cos(self.angle)
            
            screen_x = self.x + rx
            screen_y = self.y + ry
            
            if last_px is not None:
                oled.line(last_px, last_py, screen_x, screen_y)
            else:
                first_px, first_py = screen_x, screen_y
            last_px, last_py = screen_x, screen_y
            
        oled.line(last_px, last_py, first_px, first_py)

def run_asteroids_demo():
    print("HAL 9000: Initializing Vector Engine in Portrait Mode (270)...")
    i2c = machine.I2C(1, sda=machine.Pin(14), scl=machine.Pin(15), freq=1000000)
    
    oled = FastOLED_128x32(i2c, rotation=270)
    
    ship_x = 16.0
    ship_y = 115.0
    # Reduced ship speed by half
    ship_speed = 0.9 
    fire_cooldown = 0
    
    missiles = []
    asteroids = []
    particles = []
    
    # Reduced star parallax speed by half
    stars = [[random.randint(0, 31), random.randint(0, 127), random.uniform(0.05, 0.4)] for _ in range(15)]
    
    try:
        while True:
            pad = read_gamepad()
            
            # --- 1. SHIP MOVEMENT ---
            thrusting = False
            if pad[0] and ship_y > 100: ship_y -= ship_speed 
            if pad[1] and ship_y < 122: ship_y += ship_speed 
            if pad[2]: 
                ship_x -= ship_speed 
                thrusting = True
            if pad[3]: 
                ship_x += ship_speed 
                thrusting = True
            
            # WIDENED HARDWARE CLAMP: Wings can now clip 2 pixels off the edge
            if ship_x < 2:
                ship_x = 2.0
            elif ship_x > oled.width - 3:
                ship_x = float(oled.width - 3)
            
            # --- 2. WEAPONS ---
            if fire_cooldown > 0: fire_cooldown -= 1
            if pad[4] and fire_cooldown == 0: 
                missiles.append([ship_x, ship_y - 5])
                # Doubled cooldown to compensate for faster framerate
                fire_cooldown = 16 

            for m in missiles[:]:
                # Reduced missile speed by half
                m[1] -= 1.5 
                if m[1] < 0: missiles.remove(m)

            # --- 3. ASTEROID SPAWNER ---
            # Reduced spawn chance to keep the asteroid density identical
            if len(asteroids) < 4 and random.random() < 0.025:
                asteroids.append(Asteroid(random.randint(8, 24), -10, size=2))

            for a in asteroids[:]:
                a.update()
                if a.y > 140 or a.x < -10 or a.x > oled.width + 10: 
                    asteroids.remove(a)

            # --- 4. PARTICLES ---
            for p in particles[:]:
                p[0] += p[2] 
                p[1] += p[3] 
                p[4] -= 1    
                if p[4] <= 0: particles.remove(p)

            # --- 5. COLLISION DETECTION ---
            for m in missiles[:]:
                hit = False
                for a in asteroids[:]:
                    dist = math.sqrt((m[0] - a.x)**2 + (m[1] - a.y)**2)
                    if dist <= a.radius:
                        hit = True
                        asteroids.remove(a)
                        
                        # Particles now move slower but live twice as long
                        for _ in range(6):
                            particles.append([a.x, a.y, random.uniform(-0.75, 0.75), random.uniform(-0.75, 0.75), random.randint(20, 40)])
                        
                        if a.size == 2:
                            base_angle = math.atan2(a.vy, a.vx)
                            speed = math.sqrt(a.vx**2 + a.vy**2) * random.uniform(0.7, 1.1) 
                            
                            angle1 = base_angle + random.uniform(math.pi/6, math.pi/4)
                            angle2 = base_angle - random.uniform(math.pi/6, math.pi/4)
                            
                            asteroids.append(Asteroid(a.x, a.y, size=1, vx=speed*math.cos(angle1), vy=speed*math.sin(angle1)))
                            asteroids.append(Asteroid(a.x, a.y, size=1, vx=speed*math.cos(angle2), vy=speed*math.sin(angle2)))
                        break
                if hit and m in missiles:
                    missiles.remove(m)

            # --- 6. RENDER PHASE ---
            oled.clear()
            
            for s in stars:
                s[1] += s[2] 
                if s[1] > 128: 
                    s[1] = 0
                    s[0] = random.randint(0, 31)
                oled.pixel(s[0], s[1])

            for a in asteroids: a.draw(oled)
            for m in missiles: oled.line(m[0], m[1], m[0], m[1]+2)
            for p in particles: oled.pixel(p[0], p[1])

            oled.line(ship_x, ship_y-5, ship_x+4, ship_y+4) 
            oled.line(ship_x+4, ship_y+4, ship_x-4, ship_y+4) 
            oled.line(ship_x-4, ship_y+4, ship_x, ship_y-5) 
            
            if thrusting or pad[0]:
                if random.random() < 0.5:
                    oled.line(ship_x-2, ship_y+4, ship_x, ship_y+8)
                    oled.line(ship_x+2, ship_y+4, ship_x, ship_y+8)

            oled.show()
            
            # Throttle opened up for maximum framerate
            time.sleep(0.005)

    except KeyboardInterrupt:
        oled.clear()
        oled.show()
        print("HAL 9000: Game Terminated.")

run_asteroids_demo()