# OpenMV: полёт по квадрату из линий — поиск линии и поворотов 

import sensor
import utime
from pyb import UART

LINE_COLOR = "white"   # "white" — светлая лента на тёмном столе, "black" — тёмная линия
MIN_CONTRAST = 45      # насколько лента "белее" фона по обе стороны (0..255)
                       # ловится стол/блики -> увеличить; лента теряется -> уменьшить
REL_STRENGTH = 0.4     # кусок слабее 40% от самого контрастного в кадре — не лента
                       # ловится текстура/блики -> увеличить; лента теряется -> уменьшить
START_DIR = 0          # с какого направления начинаем: 0 вверх, 1 вправо, 2 вниз, 3 влево

STRIP = 20             # толщина полосы, пикс. (6 горизонтальных и 8 вертикальных)
STEP = 2               # шаг профиля, пикс.
MAX_LINE_W = 45        # лента шире этого — не линия (поперёк линии, пикс.)
                       # (широкая малярная лента с 30 см ~ 20-35 пикс; разметка поля ~10 см -> 60)
MIN_LINE_W = 4         # лента уже этого — шум
MAX_JUMP = 20          # макс. сдвиг между соседними кусками цепочки, пикс
MAX_GAP = 1            # сколько полос подряд может не хватать внутри цепочки (у угла — 1)
MIN_CHAIN = 3          # минимум кусков в основной цепочке
MIN_CHAIN_PERP = 3     # минимум кусков в поперечной цепочке (для поворота; пятно сбоку — 1-2 куска)
MIN_CHAIN_AFTER_TURN = 2  # сразу после поворота новая линия видна наполовину
TURN_PX = 12           # поворачиваем, когда поперечная линия ближе этого к центру
TURN_FAR = 30          # ...или ближе этого, если основная линия у самого угла уже пропала
SIDE_MIN = 40          # поперечная линия должна уходить в сторону минимум на столько
CONNECT_PX = 45        # и начинаться у основной линии (угол связан); это запасное значение,
                       # обычно предел считается по толщине ленты
TURN_COOLDOWN = 15     # кадров после поворота без новых поворотов
REACQUIRE = 8          # столько кадров подряд "линии нет", а через центр идёт лента поперёк
                       # курса — значит направление сбилось: перескакиваем на эту ленту
CROSS_UNIT = 3         # пикселей в одной единице cross
TRACK_K = 4            # насколько сильно держаться за "свою" линию (штраф за пиксель отхода).
                       # Если в кадре две параллельные стороны — не перескакивать на другую
DRAW_ALL = False       # True — рисовать все найденные куски (для отладки), False — только выбранные
FLIP_180 = True        # камера стоит "вверх ногами" (нос дрона был внизу кадра) — картинка разворачивается на 180°
AUTO_LIGHT = True      # камера сама подстраивает яркость и баланс белого (рекомендуется)
COLOR_VIEW = True      # цветная картинка в IDE (цветные рамки и стрелки); False — серая, чуть быстрее
if not COLOR_VIEW:
    MIN_CONTRAST = 30      # в серой картинке лента контрастирует со столом слабее


sensor.reset()
sensor.set_pixformat(sensor.RGB565 if COLOR_VIEW else sensor.GRAYSCALE)
sensor.set_framesize(sensor.QQVGA)        # 160x120
if FLIP_180:
    sensor.set_vflip(True)
    sensor.set_hmirror(True)
sensor.skip_frames(time=2000)
sensor.set_auto_gain(AUTO_LIGHT)
sensor.set_auto_exposure(AUTO_LIGHT)
sensor.set_auto_whitebal(AUTO_LIGHT)

uart = UART(3)
uart.init(9600, bits=8, parity=None, stop=1, timeout_char=1000)

W, H = sensor.width(), sensor.height()
CX, CY = W / 2, H / 2
NH, NV = H // STRIP, W // STRIP           # 6 горизонтальных, 8 вертикальных полос
REACH = MAX_LINE_W // STEP + 2            # насколько далеко искать тёмный фон по бокам

direction = START_DIR
cooldown = 0
last_cross = 0         # где была основная линия в последний раз (для поворота у самого угла)
last_thick = None      # и какой толщины
main_pos = None        # где в кадре была основная линия (x или y); None — ищем у центра
lost_frames = 0
last_turn = 1          # в какую сторону был последний поворот (+1 направо, -1 налево)
last_send = 0


def gray(v):
    """Во что превращаем цветной пиксель (R, G, B) перед поиском линии.
    Белая лента: берём МИНИМУМ из R, G, B — "насколько пиксель белый".
      Белая лента ~200+ по всем каналам, а коричневый стол почти без синего
      (~20-70), поэтому стол, его волокна и стыки досок становятся тёмными,
      и лента выделяется намного сильнее, чем по обычной яркости.
    Чёрная лента: берём МАКСИМУМ — у цветного стола хоть один канал яркий."""
    if isinstance(v, tuple):
        if LINE_COLOR == "white":
            return min(v)
        return max(v)
    return v


def profiles(img):
    """Профили яркости всех полос.
    hp[i] — средние по столбикам (шириной STEP) горизонтальной полосы i,
    vp[i] — средние по строкам (высотой STEP) вертикальной полосы i."""
    try:
        a = img.mean_pooled(STEP, STRIP)   # картинка W/STEP x NH: каждый пиксель — среднее блока
        b = img.mean_pooled(STRIP, STEP)   # картинка NV x H/STEP
        hp = [[gray(a.get_pixel(x, i)) for x in range(W // STEP)] for i in range(NH)]
        vp = [[gray(b.get_pixel(i, y)) for y in range(H // STEP)] for i in range(NV)]
    except AttributeError:
        def m(roi):
            st = img.get_statistics(roi=roi)
            return st.l_mean() * 255 // 100 if COLOR_VIEW else st.mean()
        hp = [[m((x * STEP, i * STRIP, STEP, STRIP)) for x in range(W // STEP)] for i in range(NH)]
        vp = [[m((i * STRIP, y * STEP, STRIP, STEP)) for y in range(H // STEP)] for i in range(NV)]
    return hp, vp


def ridges(p):
    """Участки профиля, которые ярче (для чёрной линии — темнее) фона с обеих сторон.
    Возвращает список (центр, ширина, начало, сила) в пикселях кадра; сила — контраст."""
    if LINE_COLOR != "white":
        p = [255 - v for v in p]
    n = len(p)
    line = [0] * n
    for x in range(n):
        left = p[max(0, x - REACH):x]
        right = p[x + 1:x + 1 + REACH]
        if not left or not right:
            continue                       # у края кадра — не проверить, пропускаем
        dl = p[x] - min(left)              # насколько ярче тёмного места слева
        dr = p[x] - min(right)             # ... и справа
        strong, weak = max(dl, dr), min(dl, dr)
        # обе стороны темнее; с одной стороны контраст может быть слабым
        # (край стола, затемнённый край кадра), но тогда с другой — заметно сильнее
        if (weak >= MIN_CONTRAST) or (strong >= MIN_CONTRAST * 1.5 and weak >= MIN_CONTRAST / 2):
            line[x] = weak + 1
    out = []
    x = 0
    while x < n:
        if line[x]:
            a = x
            s = sw = 0
            while x < n and line[x]:
                s += line[x]
                sw += line[x] * x
                x += 1
            width = (x - a) * STEP
            if MIN_LINE_W <= width <= MAX_LINE_W:
                strength = s // (x - a)        # средний контраст куска
                out.append((int(sw / s * STEP + STEP / 2), width, a * STEP, strength))
        else:
            x += 1
    return out


def pieces(hp, vp, vertical):
    """Куски линии по полосам.
    vertical=True  — линия идёт сверху вниз: горизонтальные полосы, координата куска — x.
    vertical=False — линия идёт слева направо: вертикальные полосы, координата — y.
    Возвращает список полос, в каждой — [(x, y, rect), ...]."""
    out = []
    if vertical:
        for i in range(NH):
            out.append([(c, i * STRIP + STRIP // 2, (a, i * STRIP, w, STRIP), f)
                        for (c, w, a, f) in ridges(hp[i])])
    else:
        for i in range(NV):
            out.append([(i * STRIP + STRIP // 2, c, (i * STRIP, a, STRIP, w), f)
                        for (c, w, a, f) in ridges(vp[i])])
    # куски намного слабее самого контрастного (лента) — это текстура стола, блики:
    # выбрасываем
    top = max([p[3] for st in out for p in st] or [0])
    return [[p for p in st if p[3] >= top * REL_STRENGTH] for st in out]


def best_chain(strips, vertical, penalty=None):
    """Лучшая цепочка кусков из соседних полос: длинная, ровная и (если задан penalty)
    близкая к тому месту, где линию ждём. penalty(chain) -> штраф в очках."""
    k = 0 if vertical else 1          # по какой координате меряем "ровность"
    tw = 2 if vertical else 3         # где в rect толщина куска поперёк линии
    best, best_score = [], None
    for s in range(len(strips)):
        for c in strips[s]:
            chain, jumps, last, last_w, gap = [c], 0, c[k], c[2][tw], 0
            for j in range(s + 1, len(strips)):
                # соседний кусок: рядом по положению и похожей толщины (лента не может
                # резко стать в 2 раза тоньше — это уже текстура стола, а не лента)
                near = [d for d in strips[j] if abs(d[k] - last) <= MAX_JUMP and
                        last_w * 0.5 <= d[2][tw] <= last_w * 2 + 4]
                if not near:
                    gap += 1
                    if gap > MAX_GAP:
                        break                  # дыра больше MAX_GAP полос — цепочка кончилась
                    continue
                d = min(near, key=lambda d: abs(d[k] - last))
                jumps += abs(d[k] - last)
                last, last_w, gap = d[k], d[2][tw], 0
                chain.append(d)
            score = len(chain) * 100 - jumps
            if penalty is not None:
                score -= penalty(chain)
            if best_score is None or score > best_score:
                best, best_score = chain, score
    return best


def mean_pos(chain, vertical):
    """Где цепочка в кадре: x для линии сверху вниз, y для линии слева направо."""
    k = 0 if vertical else 1
    return sum(p[k] for p in chain) / len(chain)


def to_canon(x, y, d):
    """Перевод точки кадра в систему, где движение — "вверх" (−Y), центр кадра — (0,0).
    +X в этой системе — справа от курса."""
    px, py = x - CX, y - CY
    if d == 0:
        return px, py
    if d == 1:
        return py, -px
    if d == 2:
        return -px, -py
    return -py, px


def cross_offset(chain, d):
    """Смещение основной линии вбок от курса в точке напротив центра кадра (пиксели)."""
    pts = [to_canon(p[0], p[1], d) for p in chain]
    n = len(pts)
    my = sum(p[1] for p in pts) / n
    mx = sum(p[0] for p in pts) / n
    syy = sum((p[1] - my) ** 2 for p in pts)
    a = 0 if syy == 0 else sum((p[1] - my) * (p[0] - mx) for p in pts) / syy
    return mx - a * my              # X при Y = 0


def thickness(piece, vertical):
    """Толщина куска поперёк линии: для линии сверху вниз — ширина, иначе — высота."""
    r = piece[2]
    return r[2] if vertical else r[3]


def check_turn(main_x, main_thick, perp, perp_vertical, d, far=None, main=None):
    """Вернуть +1 (направо), -1 (налево) или 0 (не поворачиваем).
    Поперечная линия засчитывается как поворот, только если:
      - она из MIN_CHAIN_PERP+ кусков;
      - она впереди и уже подошла к центру (ближе TURN_PX, или TURN_FAR у самого угла);
      - она уходит в одну сторону на SIDE_MIN+ пикселей (в другую — только короткий хвост);
      - она НАЧИНАЕТСЯ у основной линии (угол связан, а не отдельный предмет сбоку)."""
    if len(perp) < MIN_CHAIN_PERP:
        return 0
    if far is None:
        far = TURN_PX
    pts = [to_canon(p[0], p[1], d) for p in perp]
    y_line = sum(p[1] for p in pts) / len(pts)
    # чуть проскочили угол (поперечная линия немного позади центра) — тоже поворачиваем,
    # но только если основная линия НЕ продолжается дальше вперёд за поперечную
    # (если продолжается — это перекрёсток или линия, с которой уже свернули)
    upper = TURN_PX / 2
    if main is not None:
        th = (main_thick or 10) / 2 + STRIP / 2
        ahead = [q for q in main if to_canon(q[0], q[1], d)[1] < y_line - th]
        if not ahead:
            upper = TURN_PX * 2
    if not (-far < y_line < upper):
        return 0                     # ещё далеко впереди или уже позади
    xs = [p[0] for p in pts]
    right = max(xs) - main_x
    left = main_x - min(xs)
    # в "другую" сторону допускается небольшой хвост: у угла концы ленты
    # обычно заходят друг на друга и торчат за линию на полширины ленты
    tail = SIDE_MIN / 2
    connect = CONNECT_PX
    if main_thick is not None:
        tail = max(tail, main_thick / 2 + 15)
        # ближайший кусок поперечной линии должен быть вплотную к основной:
        # не дальше полуширины ленты + чуть больше половины полосы
        connect = max(20, main_thick / 2 + 15)
    if right > SIDE_MIN and left < tail and min(xs) - main_x <= connect:
        return 1
    if left > SIDE_MIN and right < tail and main_x - max(xs) <= connect:
        return -1
    return 0


# ---------- рисование (только для экрана OpenMV IDE) ----------
GREEN, YELLOW, RED, CYAN, WHITE, GREY = (0, 255, 0), (255, 230, 0), (255, 40, 40), (0, 220, 255), (255, 255, 255), (150, 150, 150)
NAMES = {0: "FORWARD", 1: "RIGHT", 2: "BACK", 3: "LEFT"}
ARROW = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}
SIDE = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}  


def col(c):
    return c if COLOR_VIEW else (255 if c != GREY else 120)


def draw_fit(img, chain, vertical, color):
    """Прямая через куски цепочки — так видно, какую линию камера считает лентой."""
    if len(chain) < 2:
        return
    if vertical:                      # x = a*y + b
        ys = [p[1] for p in chain]; xs = [p[0] for p in chain]
    else:                             # y = a*x + b
        ys = [p[0] for p in chain]; xs = [p[1] for p in chain]
    n = len(ys)
    my, mx = sum(ys) / n, sum(xs) / n
    syy = sum((y - my) ** 2 for y in ys)
    a = 0 if syy == 0 else sum((y - my) * (x - mx) for y, x in zip(ys, xs)) / syy
    b = mx - a * my
    if vertical:
        img.draw_line(int(b), 0, int(a * H + b), H, color=col(color), thickness=2)
    else:
        img.draw_line(0, int(b), W, int(a * W + b), color=col(color), thickness=2)


def draw_overlay(img, main, perp, along_vertical, cross):
    # перпендикулярная линия (кандидат на поворот) — жёлтая
    if len(perp) >= MIN_CHAIN_PERP:
        for c in perp:
            img.draw_rectangle(c[2], color=col(YELLOW))
    # основная линия — зелёная: рамки кусков + прямая через них
    if cross is not None:
        for c in main:
            img.draw_rectangle(c[2], color=col(GREEN), thickness=2)
        draw_fit(img, main, along_vertical, GREEN)
    # куда летим — красная стрелка
    ax, ay = ARROW[direction]
    img.draw_arrow(int(CX), int(CY), int(CX + ax * 30), int(CY + ay * 30), color=col(RED), thickness=3)
    # поправка вбок — голубая стрелка к линии
    if cross is not None and abs(cross) > 15:
        sx, sy = SIDE[direction]
        k = 20 if cross > 0 else -20
        img.draw_arrow(int(CX), int(CY), int(CX + sx * k), int(CY + sy * k), color=col(CYAN), thickness=2)
    img.draw_cross(int(CX), int(CY), color=col(WHITE), size=4)
    # текст
    img.draw_string(2, 2, "GO " + NAMES[direction], color=col(RED), scale=1)
    if cross is None:
        img.draw_string(2, H - 10, "NO LINE", color=col(RED), scale=1)
    elif abs(cross) <= 15:
        img.draw_string(2, H - 10, "ON LINE  %d" % int(cross), color=col(GREEN), scale=1)
    else:
        # куда сдвигаться — в направлениях дрона (нос = верх кадра)
        sx, sy = SIDE[direction]
        if cross < 0:
            sx, sy = -sx, -sy
        side = [k for k, v in ARROW.items() if v == (sx, sy)][0]
        img.draw_string(2, H - 10, "SHIFT %s %d" % (NAMES[side], abs(int(cross))), color=col(CYAN), scale=1)


clock = utime.ticks_ms()
fps = 0.0
while True:
    now = utime.ticks_ms()
    dt = utime.ticks_diff(now, clock)
    clock = now
    if dt > 0:
        fps = fps * 0.8 + 200.0 / dt     
    img = sensor.snapshot()
    hp, vp = profiles(img)

    along_vertical = direction in (0, 2)
    main_strips = pieces(hp, vp, along_vertical)
    perp_strips = pieces(hp, vp, not along_vertical)
    # основная: держимся за ту линию, по которой летели (или ближайшую к центру)
    target = main_pos
    if target is None:
        target = CX if along_vertical else CY
    main = best_chain(main_strips, along_vertical,
                      lambda ch: TRACK_K * abs(mean_pos(ch, along_vertical) - target))

    # поперечная: та, что впереди и ближе всего к месту поворота
    def perp_penalty(ch):
        y = sum(to_canon(p[0], p[1], direction)[1] for p in ch) / len(ch)
        pen = TRACK_K * abs(y)
        if y > TURN_PX:
            pen += 1000            # позади — это линия, с которой уже свернули
        return pen
    perp = best_chain(perp_strips, not along_vertical, perp_penalty)

    if DRAW_ALL:
        for s in main_strips + perp_strips:
            for c in s:
                img.draw_rectangle(c[2], color=col(GREY))

    # сразу после поворота новая линия видна только в половине кадра —
    # поэтому на время cooldown хватает и более короткой цепочки
    need = MIN_CHAIN_AFTER_TURN if cooldown > 0 else MIN_CHAIN

    cross = None
    if len(main) >= need:
        main_x = cross_offset(main, direction)
        cross = main_x
        th_list = sorted(thickness(c, along_vertical) for c in main)
        main_thick = th_list[len(th_list) // 2]    # медианная толщина линии
        if cooldown == 0:
            t = check_turn(main_x, main_thick, perp, not along_vertical, direction, main=main)
            if t != 0:
                direction = (direction + t) % 4
                cooldown = TURN_COOLDOWN
                last_turn = t
                print(">>> ПОВОРОТ", "направо" if t > 0 else "налево", "-> dir", direction)
    elif cooldown == 0:
        # основная пропала, но поперечная рядом и начинается у того места, где была
        # основная линия, — мы у самого угла
        t = check_turn(last_cross, last_thick, perp, not along_vertical, direction, far=TURN_FAR, main=main)
        if t != 0:
            direction = (direction + t) % 4
            cooldown = TURN_COOLDOWN
            last_turn = t
            print(">>> ПОВОРОТ (на углу)", "направо" if t > 0 else "налево", "-> dir", direction)
    elif cooldown > 0:
        cooldown -= 1
    if cooldown > 0 and cross is not None:
        cooldown -= 1
    if cross is not None:
        last_cross = cross
        last_thick = main_thick
        main_pos = mean_pos(main, along_vertical)
    if cross is None:
        lost_frames += 1
        if lost_frames > 10:
            main_pos = None        # линию давно не видно: снова ищем у центра
        # направление сбилось (ложный поворот, дрон повернули рукой): линии по курсу нет
        # давно, а через центр кадра уверенно идёт лента поперёк — переходим на неё
        if lost_frames >= REACQUIRE and cooldown == 0:
            centre = CY if along_vertical else CX
            other = best_chain(perp_strips, not along_vertical,
                               lambda ch: TRACK_K * abs(mean_pos(ch, not along_vertical) - centre))
            if len(other) >= MIN_CHAIN and abs(mean_pos(other, not along_vertical) - centre) < 40:
                direction = (direction + last_turn) % 4
                cooldown = TURN_COOLDOWN
                lost_frames = 0
                print(">>> ЛИНИЯ НАЙДЕНА ЗАНОВО -> dir", direction)
    else:
        lost_frames = 0
    if (direction in (0, 2)) != along_vertical:
        main_pos = None            # был поворот: новую линию ищем у центра

    draw_overlay(img, main, perp, along_vertical, cross)

    if cross is None:
        value = 0
    else:
        q = max(-15, min(15, int(round(cross / CROSS_UNIT))))
        value = 1 + direction * 31 + (q + 15)

    if utime.ticks_diff(utime.ticks_ms(), last_send) >= 100:
        last_send = utime.ticks_ms()
        uart.writechar(value)
        print("fps = %.1f" % fps, " dir =", direction, " cross =", None if cross is None else int(cross),
              " main =", len(main), " perp =", len(perp), " байт =", value)
