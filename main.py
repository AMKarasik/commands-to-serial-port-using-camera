"""
Program for sending commands to the control unit using the camera
"""

import time
from datetime import datetime
import sys
import cv2
import numpy as np
import serial

CFG_NAME = "bmsd.cfg"  # file with serial-port name

# start commands
G_CMD = [
    [0xE6, 0x00, 0xA5, 0x18, 0x4E],
    [0xE6, 0x00, 0xA6, 0x18, 0x1B],
    [0xE6, 0x00, 0xA7, 0x00, 0x80],
    [0xE6, 0x00, 0xA3, 0x00, 0xBB],
    [0xE6, 0x00, 0x51, 0x00, 0xB3]
    #       ...
]


def bmsd_open_rs485(port):
    """open serial port"""
    print("opening " + port + "...")

    try:
        # open serial port and serial port parameters
        rs485 = serial.Serial(port=port, baudrate=9600, bytesize=serial.EIGHTBITS,
                              stopbits=serial.STOPBITS_ONE, parity=serial.PARITY_NONE, timeout=1)
    except ValueError as err:
        print("ERROR: parameters are out of range")
        print(err)
        sys.exit(-1)
    except serial.SerialException as err:
        print("ERROR: serial port not found")
        print(err)
        sys.exit(-1)
    print("done\n")

    return rs485


def crc8(in_data, seed):
    """CRC algorithm"""
    for j in range(8, 0, -1):
        j += 1
        temp = ((seed ^ in_data) & 0x01)

        if temp != 0:
            seed ^= 0x18
            seed >>= 1
            seed |= 0x80
        else:
            seed >>= 1
        in_data >>= 1

    return seed


def get_seed(line):
    """helper function to determine the crc"""
    seed = 0

    for k in line:
        seed = crc8(k, seed)

    return seed


def bmsd_gen_data():
    """generation commands function"""
    for k in range(0, 250, 2):
        line = [0xE6, 0x00, 0xA3, k]
        line.append(get_seed(line[1:]))

        G_CMD.insert(5, line)


def bmsd_poll_data(rs_485, data):
    """polling commands to the control unit"""
    print("polling...")

    # send command
    try:
        rs_485.write(bytes(data))
    except serial.SerialTimeoutException:
        print("ERROR sending data")

    # wait timeout
    time.sleep(0.5)

    # print reply from the port (if any)
    string = hRS232.readline()
    print(string)

    # wait timeout
    time.sleep(0.1)

    print("\n")


if __name__ == '__main__':
    # greeting message
    print("bmsd: motor control app")

    # read configuration
    with open(CFG_NAME, "r") as file:

        if file.closed:
            print("\nERROR opening configuration from " + CFG_NAME)
            sys.exit(-1)

        using_port = file.read()
        file.close()

    # open serial port and check if succeeded
    hRS232 = bmsd_open_rs485(using_port)

    # generate commands
    bmsd_gen_data()

    # iterator over a list with commands
    i = 0

    # poll data
    for i in range(0, 6):
        bmsd_poll_data(hRS232, G_CMD[i])

    TIMEENTER = None  # First entry time of black pixel
    TIMECHANGE = None  # Time to change from black to white
    TIMER_UP = None  # Timer checker

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    # camera = cv2.VideoCapture(0)

    while camera.isOpened():
        WORKING = True
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
            avg_up = 0  # black
            if TIMER_UP is not None and TIMEENTER is None:
                TIMER_UP = True
                timeenter = datetime.now()

                print(f'First entry time of black pixel: {TIMEENTER}')

        else:
            # white
            avg_up = 255

            # We already have the first occurrence of black
            if TIMER_UP and TIMEENTER is not None:
                time_st = datetime.now() - TIMEENTER

                milliseconds = (time_st.seconds * 10 ^ 6 + time_st.microseconds) / 1000

                time_current = round(milliseconds)
                print(f'Time to change from black to white pixel: {time_current} milliseconds')

                v_angular = angle_rad / (time_current / 1000)
                print(f'Omega = {round(v_angular, 4)} rad/sec')

                timechange = time_current
                TIMER_UP = False

                file = open('text.txt', 'a')

                # Prints first occurrence and angular speed
                file.write(f'{TIMEENTER}\t{round(v_angular, 4)}\n')
                file.close()

                if i < len(G_CMD):
                    # poll data
                    bmsd_poll_data(hRS232, G_CMD[i])
                    i += 1
                else:
                    camera.release()

                TIMEENTER = None

            elif TIMER_UP is None:
                TIMER_UP = True

        B_down, G_down, R_down = img[y_down][x_down]
        avg_down = sum([R_down, G_down, B_down]) // 3

        if avg_down < 60:
            avg_down = 0
        else:
            avg_down = 255

        B_right, G_right, R_right = img[y_right][x_right]
        avg_right = sum([R_right, G_right, B_right]) // 3

        if avg_right < 60:
            avg_right = 0
        else:
            avg_right = 255

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
