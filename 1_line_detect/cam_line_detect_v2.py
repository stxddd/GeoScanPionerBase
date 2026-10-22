#   1) Пятна, касающиеся левого/правого края кадра, отбрасываются (край стола, рука, тень).
#   2) Кусок линии должен пересекать полосу почти по всей высоте
#      (линия идёт сверху вниз; мелкий мусор и горизонтальные штрихи отпадают).
#   3) Из кусков в разных полосах собирается ЦЕПОЧКА: соседние куски должны
#      быть рядом по x (не дальше MAX_JUMP). Перебираются все варианты,
#      выбирается самая длинная и самая ровная цепочка.
#   4) Если линия была в прошлом кадре — предпочитается цепочка рядом с ней
#      (не перескакиваем на соседний предмет).
#   5) Через цепочку проводится прямая, dx считается по ней.
#   6) Резкий скачок dx (> MAX_DX_JUMP) принимается только после подтверждения
#      CONFIRM_FRAMES кадрами подряд.
import sensor
import utime
from pyb import UART

# ---------- настройки ----------
LINE_COLOR = "black"   # "black" — тёмная линия, "white" — белая
DARK_K = 0.75          # чёрное = темнее DARK_K * средней яркости (тонкий провод ~0.75-0.8)
BRIGHT_K = 0.5         # белое = ярче середины между средней яркостью и 255

STRIPS = 6             # полос по высоте (6 по 20 пикселей)
EDGE = 4               # пятна ближе EDGE пикселей к левому/правому краю — отбрасываем
MIN_PIX = 6            # минимум пикселей в куске
MAX_LINE_W = 40        # кусок шире — не линия
MIN_H_PART = 0.4       # кусок должен занимать >= 40% высоты полосы
MAX_JUMP = 20          # макс. сдвиг по x между соседними полосами, пикс
MIN_CHAIN = 3          # минимум полос в цепочке, чтобы считать линию найденной
TRACK_WEIGHT = 0.5     # насколько сильно держаться за линию из прошлого кадра
MAX_DX_JUMP = 30       # скачок dx больше этого требует подтверждения
CONFIRM_FRAMES = 3     # сколько кадров подряд подтверждать скачок
SHOW_BINARY = False    # True — показать маску порога
# --------------------------------

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.QQVGA)        # 160x120
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

uart = UART(3)
uart.init(9600, bits=8, parity=None, stop=1, timeout_char=1000)

W, H = sensor.width(), sensor.height()
SH = H // STRIPS

prev_line = None       # (a, b) прошлой линии: x = a*y + b
prev_dx = None         # последний принятый dx
pending_dx = None      # кандидат на скачок
pending_n = 0
last_send = 0


def threshold(img):
    m = img.get_statistics().mean()
    if LINE_COLOR == "black":
        return [(0, int(m * DARK_K))]
    return [(int(m + (255 - m) * BRIGHT_K), 255)]


def candidates(img, th):
    """Для каждой полосы — список x-центров подходящих кусков (снизу вверх)."""
    result = []
    for i in range(STRIPS - 1, -1, -1):           # от нижней полосы (ближе к дрону) к верхней
        y0 = i * SH
        found = []
        for b in img.find_blobs(th, roi=(0, y0, W, SH), pixels_threshold=MIN_PIX,
                                area_threshold=MIN_PIX, merge=True, margin=1):
            if b.x() <= EDGE or b.x() + b.w() >= W - EDGE:
                continue                           # касается края кадра
            if b.w() > MAX_LINE_W:
                continue                           # слишком широкий
            if b.h() < SH * MIN_H_PART:
                continue                           # не пересекает полосу
            found.append((b.cx(), y0 + SH // 2, b.rect()))
        result.append(found)
    return result


def best_chain(cands):
    """Перебор цепочек: старт с любого куска, дальше вверх к ближайшему по x."""
    best, best_score = None, None
    for start in range(len(cands)):
        for c in cands[start]:
            chain = [c]
            jumps = 0
            last_x = c[0]
            for j in range(start + 1, len(cands)):
                near = [d for d in cands[j] if abs(d[0] - last_x) <= MAX_JUMP]
                if not near:
                    continue                       # в этой полосе пропуск — допустимо
                d = min(near, key=lambda d: abs(d[0] - last_x))
                jumps += abs(d[0] - last_x)
                last_x = d[0]
                chain.append(d)
            # оценка: длина цепочки важнее всего, потом ровность, потом близость к прошлой линии
            score = len(chain) * 100 - jumps
            if prev_line:
                a, b = prev_line
                dist = sum(abs(p[0] - (a * p[1] + b)) for p in chain) / len(chain)
                score -= TRACK_WEIGHT * dist
            if best_score is None or score > best_score:
                best, best_score = chain, score
    return best


def fit(chain):
    n = len(chain)
    my = sum(p[1] for p in chain) / n
    mx = sum(p[0] for p in chain) / n
    syy = sum((p[1] - my) ** 2 for p in chain)
    a = 0 if syy == 0 else sum((p[1] - my) * (p[0] - mx) for p in chain) / syy
    return a, mx - a * my


while True:
    img = sensor.snapshot()
    th = threshold(img)
    cands = candidates(img, th)
    chain = best_chain(cands)

    if SHOW_BINARY:
        img.binary(th)

    # все кандидаты — тонкие серые рамки
    for strip in cands:
        for c in strip:
            img.draw_rectangle(c[2], color=100)

    dx = None
    if chain and len(chain) >= MIN_CHAIN:
        a, b = fit(chain)
        prev_line = (a, b)
        for c in chain:
            img.draw_rectangle(c[2], color=255, thickness=2)   # выбранные — жирные белые
        img.draw_line(int(b), 0, int(a * H + b), H, color=255, thickness=2)
        new_dx = max(-49, min(49, int(a * (H / 2) + b - W / 2)))

        # защита от скачков
        if prev_dx is None or abs(new_dx - prev_dx) <= MAX_DX_JUMP:
            dx = new_dx
            pending_n = 0
        else:
            if pending_dx is not None and abs(new_dx - pending_dx) <= MAX_DX_JUMP:
                pending_n += 1
            else:
                pending_dx, pending_n = new_dx, 1
            if pending_n >= CONFIRM_FRAMES:
                dx = new_dx
                pending_n = 0
            else:
                dx = prev_dx                      # пока не подтвердилось — держим старое
        prev_dx = dx
    else:
        prev_line = None
        prev_dx = None
        pending_n = 0

    img.draw_cross(W // 2, H // 2, color=128)
    if dx is None:
        img.draw_string(2, 2, "no line", color=255, scale=2)
    else:
        img.draw_string(2, 2, "dx: %d " % dx, color=255, scale=2)

    if utime.ticks_diff(utime.ticks_ms(), last_send) >= 100:
        last_send = utime.ticks_ms()
        uart.writechar(0 if dx is None else dx + 50)
        print("dx =", dx, " цепочка =", len(chain) if chain else 0)
