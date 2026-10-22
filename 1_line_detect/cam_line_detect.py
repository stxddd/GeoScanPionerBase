#   1. Снимаем кадр в оттенках серого (каждый пиксель — яркость 0..255).
#   2. Решаем, какие пиксели считать "линией" (тёмные или светлые)
#   3. Режем кадр на 4 горизонтальные полосы и в каждой ищем кусок линии.
#   4. Усредняем горизонтальные положения кусков — это и есть положение линии.
#   5. dx = насколько линия левее (<0) или правее (>0) центра кадра, в пикселях.
#   6. 10 раз в секунду отправляем dx на Пионер одним байтом по UART.

import sensor
import utime
from pyb import UART

#   "black" — тёмная линия на светлом фоне (изолента на полу, маркер на бумаге);
#   "white" — светлая линия на тёмном фоне (белая разметка на траве).
LINE_COLOR = "black"

DARK_K = 0.6
BRIGHT_K = 0.5
STRIPS = 4
MAX_LINE_W = 40

# Перезапуск матрицы камеры в исходное состояние.
sensor.reset()

# Оттенки серого: 1 число яркости на пиксель вместо трёх цветов.
sensor.set_pixformat(sensor.GRAYSCALE)

# Размер кадра 160×120 пикселей.
sensor.set_framesize(sensor.QQVGA)

# Пропускаем кадры 2 секунды, пока матрица "привыкает" к освещению.
sensor.skip_frames(time=2000)

# Отключаем автоусиление и автобаланс белого: иначе камера сама
# постоянно меняет яркость картинки, и линия то находится, то нет.
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

uart = UART(3)
uart.init(9600, bits=8, parity=None, stop=1, timeout_char=1000)
W, H = sensor.width(), sensor.height()
last_send = 0

while True:
    img = sensor.snapshot()
    # Делаем снимок. img — картинка 160×120, её же видно в OpenMV IDE.

    # Какие пиксели считать линией
    mean = img.get_statistics().mean()
    if LINE_COLOR == "black":
        th = [(0, int(mean * DARK_K))]
    else:
        th = [(int(mean + (255 - mean) * BRIGHT_K), 255)]
    # Ищем куски линии в полосах
    # Сюда складываем центры найденных кусков линии: (x, y).
    points = []

    # Высота одной полосы: 120 // 4 = 30 пикселей.
    strip_h = H // STRIPS

    for i in range(STRIPS):
        roi = (0, i * strip_h, W, strip_h)
        blobs = [b for b in img.find_blobs(th, roi=roi, pixels_threshold=8, merge=True)
                 if b.w() <= MAX_LINE_W]
        if blobs:
            best = max(blobs, key=lambda b: b.pixels())

            img.draw_rectangle(best.rect(), color=255)
            points.append((best.cx(), best.cy()))
    img.draw_cross(W // 2, H // 2, color=128)

    # Считаем dx
    if len(points) >= 2:
        img.draw_line(points[0][0], points[0][1], points[-1][0], points[-1][1],
                      color=255, thickness=2)
        dx = int(sum(p[0] for p in points) / len(points) - W / 2)
        value = max(1, min(99, dx + 50))
        img.draw_string(2, 2, "dx: %d" % dx, color=255, scale=2)

    else:
        dx = None
        value = 0
        img.draw_string(2, 2, "no line", color=255, scale=2)

    # Отправка на Пионер
    if utime.ticks_diff(utime.ticks_ms(), last_send) >= 100:
        last_send = utime.ticks_ms()
        uart.writechar(value)
        print("dx =", dx)
