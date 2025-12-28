from micropython import const
import lvgl as lv

import task_handler
import gt911
import rgb_display
import lcd_bus
import ch422g
import i2c
import machine

_SPI_BUS_ID = const(2)
_SPI_BUS_SCK = const(12)
_SPI_BUS_MOSI = const(11)
_SPI_BUS_MISO = const(13)
_I2C_BUS_HOST = const(0)
_I2C_BUS_SCL = const(9)
_I2C_BUS_SDA = const(8)
_I2C_BUS_FREQ = const(400000)
_CTP_IRQ_PIN = const(4)
_DISPLAY_BUS_DATA0 = const(14)
_DISPLAY_BUS_DATA1 = const(38)
_DISPLAY_BUS_DATA2 = const(18)
_DISPLAY_BUS_DATA3 = const(17)
_DISPLAY_BUS_DATA4 = const(10)
_DISPLAY_BUS_DATA5 = const(39)
_DISPLAY_BUS_DATA6 = const(0)
_DISPLAY_BUS_DATA7 = const(45)
_DISPLAY_BUS_DATA8 = const(48)
_DISPLAY_BUS_DATA9 = const(47)
_DISPLAY_BUS_DATA10 = const(21)
_DISPLAY_BUS_DATA11 = const(1)
_DISPLAY_BUS_DATA12 = const(2)
_DISPLAY_BUS_DATA13 = const(42)
_DISPLAY_BUS_DATA14 = const(41)
_DISPLAY_BUS_DATA15 = const(40)
_DISPLAY_BUS_HSYNC = const(46)
_DISPLAY_BUS_VSYNC = const(3)
_DISPLAY_BUS_DE = const(5)
_DISPLAY_BUS_PCLK = const(7)
_DISPLAY_BUS_FREQ = const(12000000)
_DISPLAY_BUS_HSYNC_FRONT_PORCH = const(8)
_DISPLAY_BUS_HSYNC_BACK_PORCH = const(8)
_DISPLAY_BUS_HSYNC_PULSE_WIDTH = const(4)
_DISPLAY_BUS_HSYNC_IDLE_LOW = const(True)
_DISPLAY_BUS_VSYNC_FRONT_PORCH = const(8)
_DISPLAY_BUS_VSYNC_BACK_PORCH = const(8)
_DISPLAY_BUS_VSYNC_PULSE_WIDTH = const(4)
_DISPLAY_BUS_VSYNC_IDLE_LOW = const(False)
_DISPLAY_BUS_DE_IDLE_HIGH = const(False)
_DISPLAY_BUS_PCLK_IDLE_HIGH = const(False)
_DISPLAY_BUS_PCLK_ACTIVE_LOW = const(True)
__BUF1_SIZE = const(76800)
__BUF2_SIZE = const(76800)
_DISPLAY_WIDTH = const(800)
_DISPLAY_HEIGHT = const(480)

spi_bus = machine.SPI.Bus(
    id=_SPI_BUS_ID,
    sck=_SPI_BUS_SCK,
    mosi=_SPI_BUS_MOSI,
    miso=_SPI_BUS_MISO
)

i2c_bus = i2c.I2C.Bus(
    host=_I2C_BUS_HOST,
    scl=_I2C_BUS_SCL,
    sda=_I2C_BUS_SDA,
    freq=_I2C_BUS_FREQ
)

expander = i2c.I2C.Device(
    bus=i2c_bus,
    dev_id=ch422g.I2C_ADDR,
    reg_bits=ch422g.BITS
)

indev_device = i2c.I2C.Device(
    bus=i2c_bus,
    dev_id=gt911.I2C_ADDR,
    reg_bits=gt911.BITS
)

ch422g.Pin.set_device(expander)
bckl_pin = ch422g.Pin(
    id=ch422g.EXIO2,
    mode=ch422g.Pin.OUT,
    value=1
)

rst_pin = ch422g.Pin(
    id=ch422g.EXIO1,
    mode=ch422g.Pin.OUT,
    value=0
)

sd_cs_pin = ch422g.Pin(
    id=ch422g.EXIO4,
    mode=ch422g.Pin.OUT,
    value=0
)

ctp_irq = machine.Pin(
    Pin=_CTP_IRQ_PIN,
    mode=machine.Pin.OUT,
    value=0
)

display_bus = lcd_bus.RGBBus(
    data0=_DISPLAY_BUS_DATA0,
    data1=_DISPLAY_BUS_DATA1,
    data2=_DISPLAY_BUS_DATA2,
    data3=_DISPLAY_BUS_DATA3,
    data4=_DISPLAY_BUS_DATA4,
    data5=_DISPLAY_BUS_DATA5,
    data6=_DISPLAY_BUS_DATA6,
    data7=_DISPLAY_BUS_DATA7,
    data8=_DISPLAY_BUS_DATA8,
    data9=_DISPLAY_BUS_DATA9,
    data10=_DISPLAY_BUS_DATA10,
    data11=_DISPLAY_BUS_DATA11,
    data12=_DISPLAY_BUS_DATA12,
    data13=_DISPLAY_BUS_DATA13,
    data14=_DISPLAY_BUS_DATA14,
    data15=_DISPLAY_BUS_DATA15,
    hsync=_DISPLAY_BUS_HSYNC,
    vsync=_DISPLAY_BUS_VSYNC,
    de=_DISPLAY_BUS_DE,
    pclk=_DISPLAY_BUS_PCLK,
    disp=bckl_pin,
    freq=_DISPLAY_BUS_FREQ,
    hsync_front_porch=_DISPLAY_BUS_HSYNC_FRONT_PORCH,
    hsync_back_porch=_DISPLAY_BUS_HSYNC_BACK_PORCH,
    hsync_pulse_width=_DISPLAY_BUS_HSYNC_PULSE_WIDTH,
    hsync_idle_low=_DISPLAY_BUS_HSYNC_IDLE_LOW,
    vsync_front_porch=_DISPLAY_BUS_VSYNC_FRONT_PORCH,
    vsync_back_porch=_DISPLAY_BUS_VSYNC_BACK_PORCH,
    vsync_pulse_width=_DISPLAY_BUS_VSYNC_PULSE_WIDTH,
    vsync_idle_low=_DISPLAY_BUS_VSYNC_IDLE_LOW,
    de_idle_high=_DISPLAY_BUS_DE_IDLE_HIGH,
    pclk_idle_high=_DISPLAY_BUS_PCLK_IDLE_HIGH,
    pclk_active_low=_DISPLAY_BUS_PCLK_ACTIVE_LOW
)

_BUF1 = display_bus.allocate_framebuffer(
    size=__BUF1_SIZE,
    caps=lcd_bus.MEMORY_SPIRAM
)

_BUF2 = display_bus.allocate_framebuffer(
    size=__BUF2_SIZE,
    caps=lcd_bus.MEMORY_SPIRAM
)

display = rgb_display.RGBDisplay(
    data_bus=display_bus,
    display_width=_DISPLAY_WIDTH,
    display_height=_DISPLAY_HEIGHT,
    frame_buffer1=_BUF1,
    frame_buffer2=_BUF2,
    backlight_pin=bckl_pin,
    color_space=lv.COLOR_FORMAT.RGB565
)

display.set_power(True)
display.init()
display.set_backlight(100)
touch = gt911.GT911(device=indev_device)
fw_config = touch.firmware_config
fw_config.width = _DISPLAY_WIDTH
fw_config.height = _DISPLAY_HEIGHT
fw_config.save()
task_handler.TaskHandler()