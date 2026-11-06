from pioneer_sdk import Pioneer, VideoStream # импортируем класс Pioneer, VideoStream из библиотеки pioneer_sdk
import time                                  # библиотека time содержит функции для работы со временем
import keyboard                              # библиотека keyboard предназначена для работы с клавиатурой

min = 1200                    # условно минимальное  значение канала, минимум  1000, влияет на скорость
max = 1800                    # условно максимальное значение канала, максимум 2000, влияет на скорость

drone_1 = Pioneer()           # создаем экземпляр класса Pioneer
time.sleep(3)                 # пауза, ожидаем подключения к квадрокоптеру
video_drone_1 = VideoStream() # создаем экземпляр класса VideoStream
video_drone_1.start()         # запускаем видеопоток

print("""
Управление:   ___________________________
1 - arm      |  ↶q  w↑  e↷  |  space ↑ | 
2 - disarm   |  ←a      d→   |  ctrl  ↓ |
3 - takeoff  |      s↓       |          |
4 - land     |_______________|__________|
""")

while True:  # запускаем бесконечный цикл 
    ch1=1500 # автопилот требует постоянное наличие "радиосигнала", имитируем центральное положение стиков:
    ch2=1500
    ch3=1500
    ch4=1500
    ch5=2000 # имитация тумблера через который происходит управление магнитом, 2000 = 2 для Lua

    if keyboard.is_pressed("esc"):     # если нажата Esc - завершаем программу
        drone_1.led_control()          # выключаем светодиоды
        drone_1.land()                 # производим посадку
        video_drone_1.stop()           # останавливаем видеопоток
        drone_1.close_connection()     # закрываем соединение
        break                          # выходим из цикла

    elif keyboard.is_pressed("1"):     # если нажата 1 - запускаем двигатели
        drone_1.arm()
    elif keyboard.is_pressed("2"):     # если нажата 2 - выключаем двигатели
        drone_1.disarm()
    elif keyboard.is_pressed("3"):     # если нажата 3 - взлет
        drone_1.takeoff()
    elif keyboard.is_pressed("4"):     # если нажата 4 - посадка
        drone_1.land()

    elif keyboard.is_pressed("w"):     # если зажата W - летим вперед
        ch3=min
    elif keyboard.is_pressed("s"):     # если зажата S - летим назад
        ch3=max
    elif keyboard.is_pressed("a"):     # если зажата A - летим влево
        ch4=min
    elif keyboard.is_pressed("d"):     # если зажата D - летим вправо
        ch4=max

    elif keyboard.is_pressed("q"):     # если зажата Q - поворачиваем налево
        ch2=max
    elif keyboard.is_pressed("e"):     # если зажата E - поворачиваем направо
        ch2=min
    elif keyboard.is_pressed("space"): # если зажат Пробел - набираем высоту
        ch1=max
    elif keyboard.is_pressed("ctrl"):  # если зажат Ctrl - сбрасываем высоту
        ch1=min

    print(
        f"CH1={ch1} CH2={ch2} "
        f"CH3={ch3} CH4={ch4}",
        end="\r",
        flush=True
    )
    drone_1.send_rc_channels(          # имитируем значения каналов пульта
        channel_1=ch1, channel_2=ch2, channel_3=ch3, channel_4=ch4, channel_5=ch5)
    time.sleep(0.05)                   # небольшая задержка, улучшает отзывчивость 