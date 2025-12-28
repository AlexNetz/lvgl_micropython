## **Waveshare ESP32-S3-Touch-4.3**

build command:   
python3 make.py esp32 BOARD=ESP32_GENERIC_S3 BOARD_VARIANT=SPIRAM_OCT --flash-size=16 --partition-size=4194304 --ota --enable-uart-repl=y --enable-cdc-repl=n --enable-jtag-repl=n DISPLAY=rgb_display INDEV=gt911 EXPANDER=ch422g  

The init_driver.py initializes the display, touch and sd card.   
**-Micropython 1.27.0**  
**-LVGL 9.4**
