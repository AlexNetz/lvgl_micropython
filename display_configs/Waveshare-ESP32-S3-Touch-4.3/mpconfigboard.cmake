set(IDF_TARGET esp32s3)

set(SDKCONFIG_DEFAULTS
    boards/sdkconfig.base
    ${SDKCONFIG_IDF_VERSION_SPECIFIC}
    boards/sdkconfig.ble
    boards/sdkconfig.spiram_sx
    boards/sdkconfig.spiram_oct
    boards/sdkconfig.240mhz
    /mnt/c/Users/alex/code/lvgl_alex/lvgl_micropython/display_configs/Waveshare-ESP32-S3-Touch-4.3/sdkconfig.board
)

list(APPEND MICROPY_DEF_BOARD
    MICROPY_HW_BOARD_NAME="Waveshare-ESP32-S3-Touch-4.3"
)

