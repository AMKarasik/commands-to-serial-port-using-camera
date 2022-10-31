"""
smth text
"""

import time
from datetime import datetime
import sys
import cv2
import numpy as np
import serial

CFG_NAME = "bmsd.cfg"

G_CMD = [
    [0xE6, 0x00, 0xA5, 0x18, 0x4E],
    [0xE6, 0x00, 0xA6, 0x18, 0x1B],
    [0xE6, 0x00, 0xA7, 0x00, 0x80],
    [0xE6, 0x00, 0xA3, 0x00, 0xBB],
    [0xE6, 0x00, 0x51, 0x00, 0xB3]
    #       ...
]


def bmsd_open_rs232(port):
    """open serial port"""
    print("opening " + port + "...")

    hRS232 = None

    try:
        # open serial port and serial port parameters
        hRS232 = serial.Serial(port=port, baudrate=9600, bytesize=serial.EIGHTBITS, stopbits=serial.STOPBITS_ONE,
                               parity=serial.PARITY_NONE, timeout=1)
    except ValueError as err:
        print("ERROR: parameters are out of range")
        print(err)
        sys.exit(-1)
    except serial.SerialException as err:
        print("ERROR: serial port not found")
        print(err)
        sys.exit(-1)
    print("done\n")

    return hRS232


def ComputeCRC8(inData, seed):
    """CRC algorithm"""
    for i in range(8, 0, -1):
        temp = ((seed ^ inData) & 0x01)

        if temp != 0:
            seed ^= 0x18
            seed >>= 1
            seed |= 0x80
        else:
            seed >>= 1
        inData >>= 1

    return seed


def getSeed(line):
    seed = 0

    for i in line:
        seed = ComputeCRC8(i, seed)

    return seed


def bmsd_gen_data():
    for i in range(0, 250, 2):
        line = [0xE6, 0x00, 0xA3, i]

        line.append(getSeed(line[1:]))

        G_CMD.insert(5, line)


def bmsd_poll_data(hRS232, data):
    print("polling...")

    # send command
    try:
        hRS232.write(bytes(data))
    except serial.SerialTimeoutException as err:
        print("ERROR sending data")

    # wait timeout
    time.sleep(0.5)

    # print reply from the port (if any)
    string = hRS232.readline()
    print(string)

    # wait timeout
    time.sleep(0.1)

    print("\n")


# greeting message
print("bmsd: motor control app")

# read configuration
file = open(CFG_NAME, "r")

if file.closed:
    print("\nERROR opening configuration from " + CFG_NAME)

    sys.exit(-1)

port = file.read()

file.close()

# open serial port and check if succeeded
hRS232 = bmsd_open_rs232(port)

# generate commands
bmsd_gen_data()

print(len(G_CMD))

# итератор для итерации по списку с командами
i = 0

# poll data
for i in range(0, 6):
    bmsd_poll_data(hRS232, G_CMD[i])

# Первое время вхождения черного пикселя
timeenter = None

# Время смены черного пикселя на белый
timechange = None

# Проверка на работу таймера
timer_up = None

camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
# camera = cv2.VideoCapture(0)

while camera.isOpened():
    working = True
    success, img = camera.read()

    img = cv2.resize(img, (img.shape[1] * 2, img.shape[0] * 2))
    h = len(img)
    w = len(img[0])
    angle_rad = np.pi / 2
    angle_deg = angle_rad * (180 / np.pi)

    x_up, y_up = w // 2, h // 4
    x_down, y_down = w // 2, h - h // 4
    x_right, y_right = w - w // 4, h // 2
    x_left, y_left = w // 4, h // 2

    B_up, G_up, R_up = img[y_up][x_up]
    avg_up = sum([R_up, G_up, B_up]) // 3

    # while working:
    if avg_up < 70:
        avg_up = 0  # черный
        if timer_up is not None and timeenter is None:
            timer_up = True
            timeenter = datetime.now()

            print(f'Первое время вхождения черного пикселя: {timeenter}')

    else:
        # белый
        avg_up = 255

        # у нас уже есть первое вхождение черного
        if timer_up and timeenter is not None:
            time_st = datetime.now() - timeenter

            milliseconds = (time_st.seconds * 10 ^ 6 + time_st.microseconds) / 1000

            time_current = round(milliseconds)
            print(f'Время смены черного на белый пиксель: {time_current} миллисекунд')

            v_angular = angle_rad / (time_current / 1000)
            print(f'Omega = {round(v_angular, 4)} рад/с')

            timechange = time_current
            timer_up = False

            file = open('text.txt', 'a')

            # печатает первое вхождение и скорость
            file.write(f'{timeenter}\t{round(v_angular, 4)}\n')
            file.close()

            if i < len(G_CMD):
                # poll data
                bmsd_poll_data(hRS232, G_CMD[i])
                i += 1
            else:
                camera.release()

            timeenter = None

        elif timer_up is None:
            timer_up = True

    B_down, G_down, R_down = img[y_down][x_down]
    avg_down = sum([R_down, G_down, B_down]) // 3

    if avg_down < 60:
        avg_down = 0
    else:
        avg_down = 255

    # print('средняя яркость низ', avg_down)

    B_right, G_right, R_right = img[y_right][x_right]
    avg_right = sum([R_right, G_right, B_right]) // 3

    if avg_right < 60:
        avg_right = 0
    else:
        avg_right = 255

    # print('средняя яркость прав', avg_right)

    B_left, G_left, R_left = img[y_left][x_left]
    avg_left = sum([R_left, G_left, B_left]) // 3

    if avg_left < 60:
        avg_left = 0
    else:
        avg_left = 255

    cv2.line(img, (0, h // 2), (w, h // 2), (0, 0, 255), thickness=2)  # center
    cv2.line(img, (w // 2, 0), (w // 2, h), (0, 0, 255), thickness=2)
    cv2.line(img, (0, h // 4), (w, h // 4), (255, 0, 0), thickness=1)  # up
    cv2.line(img, (w // 4, 0), (w // 4, h), (255, 0, 0), thickness=1)  # left
    cv2.line(img, (w - w // 4, 0), (w - w // 4, h), (255, 0, 0), thickness=1)  # right
    cv2.line(img, (0, h - h // 4), (w, h - h // 4), (255, 0, 0), thickness=1)  # down

    cv2.imshow('circle_test', np.hstack([img]))

    if cv2.waitKey(1) & 0xFF == ord('q'):
        # working = False
        break

cv2.destroyAllWindows()

hRS232.close()
print("application terminated.")
sys.exit(0)
