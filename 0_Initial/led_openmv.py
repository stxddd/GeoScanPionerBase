import time
import utime

import sensor
from pyb import LED, UART


UART_ID = 3
UART_BAUDRATE = 9600
UART_TIMEOUT_MS = 1000
LED_TOGGLE_PERIOD = 10
FRAME_PERIOD_MS = 100
RECTANGLE_THRESHOLD = 10000


def configure_uart():
    uart = UART(UART_ID)
    uart.init(
        UART_BAUDRATE,
        bits=8,
        parity=None,
        stop=1,
        timeout_char=UART_TIMEOUT_MS,
    )
    return uart


def configure_camera():
    sensor.reset()
    sensor.set_pixformat(sensor.RGB565)
    sensor.set_framesize(sensor.LCD)
    sensor.skip_frames(100)


def draw_rectangles(frame):
    for rectangle in frame.find_rects(threshold=RECTANGLE_THRESHOLD):
        frame.draw_rectangle(
            rectangle.x(),
            rectangle.y(),
            rectangle.w(),
            rectangle.h(),
            (255, 0, 0),
        )

        for corner_x, corner_y in rectangle.corners():
            frame.draw_circle(corner_x, corner_y, 5, color=(0, 255, 0))

        print(rectangle)


def update_status_led(led, counter, mode):
    counter -= 1
    if counter == 0:
        if mode == 0:
            led.on()
        else:
            led.off()

        return LED_TOGGLE_PERIOD, 1 - mode

    return counter, mode


blue_led = LED(2)
green_led = LED(3)
uart = configure_uart()

blue_led.on()
configure_camera()
clock = time.clock()
blue_led.off()

led_counter = LED_TOGGLE_PERIOD
led_mode = 0

while True:
    clock.tick()
    frame_started_at = utime.ticks_ms()
    frame = sensor.snapshot()
    draw_rectangles(frame)

    brightness = frame.get_histogram().get_statistics().l_mean()
    print(brightness)
    uart.writechar(brightness)

    led_counter, led_mode = update_status_led(
        green_led,
        led_counter,
        led_mode,
    )

    while frame_started_at + FRAME_PERIOD_MS > utime.ticks_ms():
        pass
