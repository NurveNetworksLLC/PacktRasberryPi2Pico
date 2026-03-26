import machine
import neopixel

# Configuration
PIN = 25          # GPIO pin connected to DI
PIXELS = 25       # Number of LEDs in ZSRGB-2017H-08-Z3 strip
LED_ORDER = 3     # RGB

# Initialize
np = neopixel.NeoPixel(machine.Pin(PIN), PIXELS, bpp=LED_ORDER)

# Set Colors
np[0] = (255, 0, 0)
np[1] = (0, 255, 0)
np[2] = (0, 0, 255)
np[3] = (255, 255, 0)
np[4] = (255, 0, 255)


np.write()