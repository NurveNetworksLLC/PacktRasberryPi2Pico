import machine
import neopixel
import math
import time

# Configuration
PIN = 25
WIDTH = 4
HEIGHT = 4
PIXELS = WIDTH * HEIGHT
LED_ORDER = 3
GLOBAL_BRIGHTNESS = 0.05  # Set between 0.0 (off) and 1.0 (blindingly bright)

# Initialize Matrix
np = neopixel.NeoPixel(machine.Pin(PIN), PIXELS, bpp=LED_ORDER)

def hsv_to_rgb(h, s, v):
    """Convert HSV (0.0-1.0) to RGB (0-255)."""
    if s == 0.0:
        return (int(v * 255), int(v * 255), int(v * 255))
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

def plasma():
    t = 0.0
    try:
        while True:
            for y in range(HEIGHT):
                for x in range(WIDTH):
                    # Classic plasma math: intersecting sine waves based on time and layout
                    v1 = math.sin(x * 0.8 + t)
                    v2 = math.sin(y * 0.8 + t)
                    v3 = math.sin((x + y + math.sin(t)) * 0.5)
                    v4 = math.sin(math.sqrt(x*x + y*y) * 0.4 + t)
                    
                    # Sum the waves and map to a 0.0 - 1.0 hue value
                    v = (v1 + v2 + v3 + v4) / 4.0
                    hue = (v + 1.0) / 2.0 
                    
                    # Convert to RGB utilizing the global brightness safeguard
                    rgb = hsv_to_rgb(hue, 1.0, GLOBAL_BRIGHTNESS)
                    
                    # Map the 2D (X,Y) coordinate to the 1D NeoPixel array index
                    idx = (y * WIDTH) + x
                    np[idx] = rgb
            
            np.write()
            t += 0.2
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        # Clear the matrix when you press Stop in Thonny
        for i in range(PIXELS):
            np[i] = (0, 0, 0)
        np.write()

# Ignite the matrix
plasma()