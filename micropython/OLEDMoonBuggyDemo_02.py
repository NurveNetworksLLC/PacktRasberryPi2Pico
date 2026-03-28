"""
================================================================================
HAL 9000: BARE-METAL SSD1306 DRIVER (128x32) & VECTOR MOON PATROL v2.0
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

    def circle(self, x0, y0, r, color=1):
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
# MAIN DEMO: VECTOR MOON PATROL v2.0 (SCORING ENGINE)
# ==============================================================================

# Custom 3x5 Wireframe Vector Font for High-Speed Rendering
VECTOR_FONT = {
    '0': [((0,0),(2,0)), ((2,0),(2,4)), ((2,4),(0,4)), ((0,4),(0,0))],
    '1': [((1,0),(1,4)), ((0,1),(1,0)), ((0,4),(2,4))],
    '2': [((0,0),(2,0)), ((2,0),(2,2)), ((2,2),(0,2)), ((0,2),(0,4)), ((0,4),(2,4))],
    '3': [((0,0),(2,0)), ((2,0),(2,4)), ((2,4),(0,4)), ((0,2),(2,2))],
    '4': [((0,0),(0,2)), ((0,2),(2,2)), ((2,0),(2,4))],
    '5': [((2,0),(0,0)), ((0,0),(0,2)), ((0,2),(2,2)), ((2,2),(2,4)), ((2,4),(0,4))],
    '6': [((2,0),(0,0)), ((0,0),(0,4)), ((0,4),(2,4)), ((2,4),(2,2)), ((2,2),(0,2))],
    '7': [((0,0),(2,0)), ((2,0),(2,4))],
    '8': [((0,0),(2,0)), ((2,0),(2,4)), ((2,4),(0,4)), ((0,4),(0,0)), ((0,2),(2,2))],
    '9': [((2,4),(2,0)), ((2,0),(0,0)), ((0,0),(0,2)), ((0,2),(2,2))]
}

def draw_vector_text(oled, text, start_x, start_y):
    """Draws wireframe text. Each character is 3px wide + 1px spacing."""
    for i, char in enumerate(str(text)):
        if char in VECTOR_FONT:
            for line in VECTOR_FONT[char]:
                oled.line(start_x + (i * 4) + line[0][0], start_y + line[0][1], 
                          start_x + (i * 4) + line[1][0], start_y + line[1][1])

def get_terrain_y(wx):
    y = 24 + math.sin(wx * 0.02) * 4 + math.sin(wx * 0.031) * 3
    p = math.sin(wx * 0.01)
    if p > 0.5:
        val = (p - 0.5) * 4
        if val > 1.0: val = 1.0
        y -= val * 10 
        
    s = math.sin(wx * 0.06)
    if s > 0.85:
        y -= (s - 0.85) * 40 
        
    if wx > 250:
        threshold = 0.94 + math.sin(wx * 0.011) * 0.035
        c = math.sin(wx * 0.025)
        if c > threshold: 
            y += 40 
            
    return y

def rotate_pt(px, py, angle):
    rx = px * math.cos(angle) - py * math.sin(angle)
    ry = px * math.sin(angle) + py * math.cos(angle)
    return rx, ry

def run_moon_rover_demo():
    print("HAL 9000: Initializing Moon Patrol V2 with Vector Telemetry...")
    i2c = machine.I2C(1, sda=machine.Pin(14), scl=machine.Pin(15), freq=1000000)
    oled = FastOLED_128x32(i2c, rotation=0)
    
    world_x = 0.0
    rover_x = 30.0 
    rover_y = 0.0
    vy = 0.0
    gravity = 0.22 
    jump_power = -3.4
    
    current_speed = 1.0
    current_angle = 0.0
    target_angle = 0.0
    
    # Scoring State
    score = 0
    in_chasm = False
    chasm_start_x = 0
    
    particles = []
    stars = [[random.randint(0, 127), random.randint(0, 31)] for _ in range(25)]
    
    try:
        while True:
            pad = read_gamepad()
            
            # --- 1. ACCELERATION ---
            target_speed = 1.2
            if pad[2]: target_speed = 0.5 
            if pad[3]: target_speed = 2.6 
            
            current_speed += (target_speed - current_speed) * 0.1
            world_x += current_speed
            
            # --- 2. PHYSICS & COLLISION ---
            vy += gravity
            rover_y += vy
            
            ty = get_terrain_y(world_x + rover_x)
            grounded = False
            
            if rover_y >= ty - 3:
                if ty < 34: 
                    rover_y = ty - 3
                    vy = 0
                    grounded = True
                    
                    if current_speed > 1.0 and random.random() < 0.4:
                        particles.append([rover_x - 6, rover_y + 2, -current_speed * 0.5 + random.uniform(-0.5, 0), random.uniform(-1, 0), random.randint(5, 12)])

            # --- 3. JUMPING & RAMPING ---
            if pad[4] and grounded: 
                vy = jump_power
                grounded = False
                
            if grounded and target_angle < -0.6 and current_speed > 1.5:
                vy = jump_power * 0.8
                grounded = False
                
            if rover_y > 40: # Death
                world_x = 0.0
                rover_y = -5.0 
                vy = 0.0
                current_speed = 1.0
                score = 0 # Reset score on crash
                in_chasm = False

            # --- 4. CHASM SCORING SENSOR ---
            # If the terrain beneath the chassis drops drastically, you are over a gap
            currently_over_chasm = (ty > 45)
            
            if currently_over_chasm and not in_chasm:
                in_chasm = True
                chasm_start_x = world_x
                
            elif not currently_over_chasm and in_chasm:
                in_chasm = False
                # If we made it across and haven't crashed...
                if rover_y < 36:
                    chasm_width = world_x - chasm_start_x
                    # Scale ~10px to 38px width into a 100 to 500 point reward
                    reward = int(100 + ((chasm_width - 10) / 28) * 400)
                    reward = max(100, min(500, reward))
                    
                    score += reward
                    if score > 99999: 
                        score = 99999
                        
                    # Trigger a burst of particles to celebrate the jump
                    for _ in range(8):
                        particles.append([rover_x, rover_y + 4, random.uniform(-1, 1), random.uniform(-2, 0), random.randint(10, 20)])

            # --- 5. KINEMATICS ---
            if grounded:
                ty_front = get_terrain_y(world_x + rover_x + 4)
                ty_rear = get_terrain_y(world_x + rover_x - 4)
                target_angle = math.atan2(ty_front - ty_rear, 8)
            else:
                target_angle += vy * 0.02
                
            current_angle += (target_angle - current_angle) * 0.2

            # --- 6. PARTICLES ---
            for p in particles[:]:
                p[0] += p[2] 
                p[1] += p[3] 
                p[4] -= 1    
                if p[4] <= 0: particles.remove(p)

            # --- 7. RENDER ENGINE ---
            oled.clear()
            
            for s in stars:
                s[0] -= current_speed * 0.1
                if s[0] < 0: 
                    s[0] = 127
                    s[1] = random.randint(0, 31)
                    
                terrain_height = get_terrain_y(world_x + s[0])
                if s[1] < terrain_height:
                    oled.pixel(int(s[0]), s[1])

            for sx in range(0, 128, 4):
                my = 16 + math.sin((world_x * 0.3 + sx) * 0.02) * 5
                terrain_height = get_terrain_y(world_x + sx)
                if my < terrain_height:
                    oled.pixel(sx, int(my))

            last_y = get_terrain_y(world_x)
            for sx in range(2, 128, 2):
                y = get_terrain_y(world_x + sx)
                oled.line(sx - 2, int(last_y), sx, int(y))
                last_y = y

            chassis_lines = [
                ((-6, -2), (6, -2)), 
                ((-6, -2), (-2, -6)), 
                ((-2, -6), (2, -6)), 
                ((2, -6), (6, -2))   
            ]
            
            for line_pts in chassis_lines:
                p1 = rotate_pt(line_pts[0][0], line_pts[0][1], current_angle)
                p2 = rotate_pt(line_pts[1][0], line_pts[1][1], current_angle)
                oled.line(int(rover_x + p1[0]), int(rover_y + p1[1]), 
                          int(rover_x + p2[0]), int(rover_y + p2[1]))
                
            rw = rotate_pt(-4, 0, current_angle)
            fw = rotate_pt(4, 0, current_angle)
            oled.circle(int(rover_x + rw[0]), int(rover_y + rw[1]), 2)
            oled.circle(int(rover_x + fw[0]), int(rover_y + fw[1]), 2)
            
            spin_angle = world_x * 0.4
            sxr = int(rover_x + rw[0] + math.cos(spin_angle)*2)
            syr = int(rover_y + rw[1] + math.sin(spin_angle)*2)
            sxf = int(rover_x + fw[0] + math.cos(spin_angle)*2)
            syf = int(rover_y + fw[1] + math.sin(spin_angle)*2)
            oled.line(int(rover_x + rw[0]), int(rover_y + rw[1]), sxr, syr)
            oled.line(int(rover_x + fw[0]), int(rover_y + fw[1]), sxf, syf)

            for p in particles: oled.pixel(p[0], p[1])
            
            # --- 8. TELEMETRY DISPLAY ---
            # Format score to exactly 5 digits with leading zeros (e.g., "00450")
            score_str = f"{score:05d}"
            # Draw at top right corner: 128px wide - (5 characters * 4px width) = X: 108
            draw_vector_text(oled, score_str, 108, 1)

            oled.show()
            time.sleep(0.005)

    except KeyboardInterrupt:
        oled.clear()
        oled.show()
        print("HAL 9000: Simulation Halted.")

run_moon_rover_demo()