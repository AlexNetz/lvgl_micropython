# init_driver.py
# MicroPython 78ff170de9-dirty on 2025-12-19; Generic ESP32S3 module with Octal-SPIRAM with ESP32S3
# Waveshare ESP32-S3-Touch-LCD-4.3

import lvgl as lv
from micropython import const
import lcd_bus
import rgb_display
import task_handler
import i2c
import gt911
import time
import ch422g
import machine
import vfs
import os


_WIDTH = const(800)
_HEIGHT = const(480)

_DATA15 = const(10)  # B7
_DATA14 = const(17)  # B6
_DATA13 = const(18)  # B5
_DATA12 = const(38)  # B4
_DATA11 = const(14)  # B3
_DATA10 = const(21)  # G7
_DATA9 = const(47)  # G6
_DATA8 = const(48)  # G5
_DATA7 = const(45)  # G4
_DATA6 = const(0)  # G3
_DATA5 = const(39)  # G2
_DATA4 = const(40)  # R7
_DATA3 = const(41)  # R6
_DATA2 = const(42)  # R5
_DATA1 = const(2)  # R4
_DATA0 = const(1)  # R3

_BUFFER_SIZE = const(76800)

_CTP_SCL = const(9)
_CTP_SDA = const(8)
_CTP_IRQ = const(4)

_SD_BAUD = const(400000)
_SD_MOSI = const(11)
_SD_SCK = const(12)
_SD_MISO = const(13)

_LCD_FREQ = const(13000000)
_PCLK_ACTIVE_NEG = const(0)

_HSYNC_PULSE_WIDTH = const(10)
_HSYNC_BACK_PORCH = const(10)
_HSYNC_FRONT_PORCH = const(10)

_VSYNC_PULSE_WIDTH = const(10)
_VSYNC_BACK_PORCH = const(10)
_VSYNC_FRONT_PORCH = const(20)

_PCLK = const(7)
_HSYNC = const(46)
_VSYNC = const(3)
_DE = const(5)
_DISP = None
_BCKL = None
_DRST = None

spi_bus = machine.SPI.Bus(host=2, sck=_SD_SCK, mosi=_SD_MOSI, miso=_SD_MISO)
i2c_bus = i2c.I2C.Bus(host = 0, scl = _CTP_SCL, sda = _CTP_SDA)

io_expander_device = i2c.I2C.Device(     # Initializing the io expander
    i2c_bus,
    ch422g.I2C_ADDR,
    ch422g.BITS
)

touch_i2c = i2c.I2C.Device(     # touch controller
    bus = i2c_bus,
    dev_id = gt911.I2C_ADDR,
    reg_bits = gt911.BITS
)

ch422g.Pin.set_device(device = io_expander_device)

bckl_pin = ch422g.Pin(     # set backlight pin for display
    ch422g.EXIO2,
    ch422g.Pin.OUT,
    value = 1
)

rst_pin = ch422g.Pin(     # set reset pin for touch device
    ch422g.EXIO1,
    ch422g.Pin.OUT,
    value = 0
)

sd_cs_pin = ch422g.Pin(     # chip select for TF card
    ch422g.EXIO4,
    ch422g.Pin.OUT,
    value = 0,                      # Pin needs to be low to enable TF Card
)

int_pin = machine.Pin(
    _CTP_IRQ,
    machine.Pin.OUT,
    value=0
)

rgb_bus = lcd_bus.RGBBus(     
    hsync = _HSYNC,
    vsync = _VSYNC,
    de = _DE,
    pclk = _PCLK,
    data0 = _DATA0,
    data1 = _DATA1,
    data2 = _DATA2,
    data3 = _DATA3,
    data4 = _DATA4,
    data5 = _DATA5,
    data6 = _DATA6,
    data7 = _DATA7,
    data8 = _DATA8,
    data9 = _DATA9,
    data10 =  _DATA10,
    data11 =  _DATA11,
    data12 = _DATA12,
    data13 = _DATA13,
    data14 = _DATA14,
    data15 = _DATA15,
    freq = _LCD_FREQ,
    hsync_front_porch = _HSYNC_FRONT_PORCH,
    hsync_back_porch = _HSYNC_BACK_PORCH,
    hsync_pulse_width = _HSYNC_PULSE_WIDTH,
    hsync_idle_low = False,
    vsync_front_porch = _VSYNC_FRONT_PORCH,
    vsync_back_porch = _VSYNC_BACK_PORCH,
    vsync_pulse_width = _VSYNC_PULSE_WIDTH,
    vsync_idle_low = False,
    de_idle_high = False,
    pclk_idle_high = False,
    pclk_active_low = _PCLK_ACTIVE_NEG,
)

_BUF1 = rgb_bus.allocate_framebuffer(_BUFFER_SIZE, lcd_bus.MEMORY_SPIRAM)
_BUF2 = rgb_bus.allocate_framebuffer(_BUFFER_SIZE, lcd_bus.MEMORY_SPIRAM)

display = rgb_display.RGBDisplay(
    data_bus = rgb_bus,
    display_width = _WIDTH,
    display_height = _HEIGHT,
    frame_buffer1 = _BUF1,
    frame_buffer2 = _BUF2,
    backlight_pin = bckl_pin,
    color_space = lv.COLOR_FORMAT.RGB565,
    rgb565_byte_swap = False,
)

class MainScreen(lv.obj):
    def __init__(self, parent):
        super().__init__(parent)
        self.set_size(800,480)
        self.set_style_bg_color(lv.color_make(100,100,100),0)
        
         
main_scr = MainScreen(parent = 0) 
lv.screen_load(main_scr)
slider = lv.slider(main_scr)
slider.center()
label = lv.label(main_scr)
lv.label.set_text(label, 'Hello LVGL')
label.align(lv.ALIGN.TOP_MID,0,50)

indev = gt911.GT911(
    device = touch_i2c,
    reset_pin = rst_pin,
    interrupt_pin = int_pin
)

if indev.hw_size != (_WIDTH, _HEIGHT):
    fw_config = indev.firmware_config
    fw_config.width = _WIDTH
    fw_config.height = _HEIGHT 
    fw_config.save()

try:
    sd = machine.SDCard(
        spi_bus=spi_bus,
        slot=3,
        width=1,
        freq=20000000,
    )
    
    vfs.mount(sd, "/sd")
    print("Mounted /sd")
    print(os.listdir('/sd')) 
    os.chdir('/sd')
    sd_dir=str(os.listdir("/sd"))    
    sd_lbl=lv.label(main_scr)
    lv.label.set_text(sd_lbl, sd_dir)
    sd_lbl.align(lv.ALIGN.TOP_MID,0,90)
    os.chdir('/')
except Exception as e:
    print("SDCard error:",e)
    

print('Driver initialization done')
task_handler = task_handler.TaskHandler()
