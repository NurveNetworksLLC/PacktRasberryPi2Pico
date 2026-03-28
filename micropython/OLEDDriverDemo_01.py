"""
================================================================================
HAL 9000: BARE-METAL SSD1306 DRIVER (128x32) & DEMO
Hardware: RP2350 (Pico 2) | I2C1: SDA=GP14, SCL=GP15 | Gamepad: GP0-GP6
================================================================================
"""
import machine
import time

# --- GAMEPAD DRIVER ---
# GP0=UP, GP1=DOWN, GP2=LEFT, GP3=RIGHT, GP4=MID, GP5=SET, GP6=RST
pad_pins = [machine.Pin(i, machine.Pin.IN, machine.Pin.PULL_UP) for i in range(7)]

def read_gamepad():
    """Returns a list of 7 integers: 1 = Pressed, 0 = Open."""
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

        # THE DOUBLE BUFFER: 
        # 513 bytes total. Index 0 is the I2C control byte (0x40). 
        # Indexes 1-512 are the raw video RAM.
        self.payload = bytearray(513)
        self.payload[0] = 0x40 
        self.buffer = memoryview(self.payload)[1:] 

        self._init_display()

    def _init_display(self):
        # Determine hardware mirroring for 0 vs 180 degrees
        seg_remap = 0xA1 if self.rot != 180 else 0xA0
        com_scan = 0xC8 if self.rot != 180 else 0xC0

        # Standard 128x32 Boot Sequence
        init_cmds = [
            0xAE,          # Display OFF
            0xD5, 0x80,    # Set clock divide ratio
            0xA8, 0x1F,    # Multiplex ratio for 32 lines (0x1F = 31)
            0xD3, 0x00,    # Display offset
            0x40,          # Set start line 0
            0x8D, 0x14,    # Enable charge pump
            0x20, 0x00,    # Memory addressing mode: Horizontal
            seg_remap,     # Hardware Segment Remap
            com_scan,      # Hardware COM Output Scan Direction
            0xDA, 0x02,    # COM pins hardware config for 128x32
            0x81, 0x8F,    # Contrast
            0xD9, 0xF1,    # Pre-charge period
            0xDB, 0x40,    # VCOMH deselect level
            0xA4,          # Entire display ON resume
            0xA6,          # Normal display (not inverted)
            0xAF           # Display ON
        ]
        for cmd in init_cmds:
            self.i2c.writeto(self.addr, bytes([0x00, cmd]))

    def show(self):
        """BLASTS the entire 513-byte payload to the screen instantly."""
        self.i2c.writeto(self.addr, self.payload)

    def clear(self):
        """Zeroes out the 512-byte video RAM."""
        for i in range(512):
            self.buffer[i] = 0

    def pixel(self, x, y, color=1):
        """Translates logical coordinates, handles rotation, and sets the bit."""
        # Software coordinate swapping for portrait modes
        if self.rot == 90:
            x, y = y, 127 - x
        elif self.rot == 270:
            x, y = 31 - y, x
            
        if 0 <= x < 128 and 0 <= y < 32:
            idx = x + (y // 8) * 128
            if color:
                self.buffer[idx] |= (1 << (y % 8))
            else:
                self.buffer[idx] &= ~(1 << (y % 8))

    # --- GEOMETRY PRIMITIVES ---
    def hline(self, x, y, w, color=1):
        for i in range(x, x + w): self.pixel(i, y, color)

    def vline(self, x, y, h, color=1):
        for i in range(y, y + h): self.pixel(x, i, color)

    def line(self, x0, y0, x1, y1, color=1):
        """Bresenham's Line Algorithm"""
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
            for i in range(x, x + w):
                self.vline(i, y, h, color)
        else:
            self.hline(x, y, w, color)
            self.hline(x, y + h - 1, w, color)
            self.vline(x, y, h, color)
            self.vline(x + w - 1, y, h, color)

    def circle(self, x0, y0, r, color=1, filled=False):
        """Midpoint Circle Algorithm"""
        f = 1 - r
        ddF_x, ddF_y = 1, -2 * r
        x, y = 0, r
        
        self.pixel(x0, y0 + r, color)
        self.pixel(x0, y0 - r, color)
        self.pixel(x0 + r, y0, color)
        self.pixel(x0 - r, y0, color)
        if filled: self.vline(x0, y0 - r, 2*r + 1, color)
        
        while x < y:
            if f >= 0:
                y -= 1
                ddF_y += 2
                f += ddF_y
            x += 1
            ddF_x += 2
            f += ddF_x
            
            if filled:
                self.vline(x0 + x, y0 - y, 2*y + 1, color)
                self.vline(x0 - x, y0 - y, 2*y + 1, color)
                self.vline(x0 + y, y0 - x, 2*x + 1, color)
                self.vline(x0 - y, y0 - x, 2*x + 1, color)
            else:
                self.pixel(x0 + x, y0 + y, color)
                self.pixel(x0 - x, y0 + y, color)
                self.pixel(x0 + x, y0 - y, color)
                self.pixel(x0 - x, y0 - y, color)
                self.pixel(x0 + y, y0 + x, color)
                self.pixel(x0 - y, y0 + x, color)
                self.pixel(x0 + y, y0 - x, color)
                self.pixel(x0 - y, y0 - x, color)

    def blit_8x8(self, x, y, bmp_bytes, color=1):
        """Draws an 8x8 bitmap from a tuple of 8 bytes."""
        for row in range(8):
            b = bmp_bytes[row]
            for col in range(8):
                # Check each bit from left to right
                if b & (1 << (7 - col)):
                    self.pixel(x + col, y + row, color)


# ==============================================================================
# MAIN DEMO: THE GEOMETRY ENGINE & SHIP
# ==============================================================================
def run_oled_demo():
    print("HAL 9000: Initializing I2C1 and OLED Driver...")
    i2c = machine.I2C(1, sda=machine.Pin(14), scl=machine.Pin(15), freq=1000000) # Pushed to 1MHz!
    
    # Initialize display at 0 degrees rotation
    oled = FastOLED_128x32(i2c, rotation=0)
    
    # A tiny 8x8 alien spacecraft bitmap (1 in binary means draw pixel)
    # 0x18 = 00011000
    # 0x3C = 00111100
    ship_bmp = (
        0x18, 
        0x3C, 
        0x7E, 
        0xFF, 
        0xDB, 
        0xFF, 
        0x24, 
        0x5A  
    )
    
    ship_x, ship_y = 60, 12
    
    print("HAL 9000: Display active. Use D-pad to fly.")
    
    try:
        while True:
            # 1. Read Inputs
            pad = read_gamepad()
            if pad[0]: ship_y -= 2  # UP
            if pad[1]: ship_y += 2  # DOWN
            if pad[2]: ship_x -= 2  # LEFT
            if pad[3]: ship_x += 2  # RIGHT
            
            # Wrap around screen edges
            ship_x %= oled.width
            ship_y %= oled.height
            
            # 2. Clear Double Buffer
            oled.clear()
            
            # 3. Draw Static Geometry Test Elements
            oled.rect(0, 0, oled.width, oled.height)         # Outer Frame
            oled.circle(10, 16, 8, filled=False)             # Left Target
            oled.circle(118, 16, 8, filled=True)             # Right Moon
            oled.line(20, 0, 40, 31)                         # Cross line 1
            oled.line(40, 0, 20, 31)                         # Cross line 2
            
            # 4. Draw Player Ship
            oled.blit_8x8(ship_x, ship_y, ship_bmp)
            
            # 5. Blast to Hardware (Zero flicker)
            oled.show()
            
            # Tiny delay to keep it playable
            time.sleep(0.01)

    except KeyboardInterrupt:
        oled.clear()
        oled.show()
        print("HAL 9000: Demo Terminated. Goodnight.")

run_oled_demo()