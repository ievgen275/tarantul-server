import socket
import subprocess
import threading
from network_signal_settings import ETHERNET_SETTINGS, RADIO_SETTINGS
from sbus_communication import read_sbus_data, get_channel, stop_read_sbus, is_payload_ready, start_read_sbus
from gps_handler import start_read_gps
# from mavlink_connection import set_servo, check_connection
import time
import RPi.GPIO as GPIO
import asyncio
import websockets
import json

# Define the GPIO pins based on your setup
# pin_front_left_motor_control = 13  # PWM Output
pin_rear_left_motor_control = 19  # PWM Output
pin_front_right_motor_control = 18  # PWM Output
# pin_rear_right_motor_control = 12  # PWM Output
pin_bomba_a = 25  # Bomba A pin
pin_bomba_b = 27  # Bomba B pin
pin_front_mine_dropping = 20  # Mine Front
pin_rear_mine_dropping = 21  # Mine Rear

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.cleanup()

# Constants for signal processing
MIN_SIGNAL_VALUE = ETHERNET_SETTINGS.min
MAX_SIGNAL_VALUE = ETHERNET_SETTINGS.max
IDLE_SIGNAL_VALUE = ETHERNET_SETTINGS.idle
MAX_IDLE_VALUE = ETHERNET_SETTINGS.idle + ETHERNET_SETTINGS.offset
MIN_IDLE_VALUE = ETHERNET_SETTINGS.idle - ETHERNET_SETTINGS.offset

STANDARD = 5
DUO = 6

is_bombaA_released = False
lest_ws_msg = 0
pwm_front_left_motor = None
pwm_rear_left_motor = None
pwm_front_right_motor = None
pwm_rear_right_motor = None

# checking connection variables
connection_type = RADIO_SETTINGS.type
control_option = STANDARD


def main():
    threading.Thread(target=start_ws).start()
    threading.Thread(target=read_radio_signal).start()


def setup():
    print('Setup start')
    subprocess.run(['sudo', 'motion'], check=True)
    threading.Thread(target=read_sbus_data, daemon=True).start()

    global pwm_rear_left_motor, pwm_front_right_motor

    GPIO.setup(pin_bomba_b, GPIO.OUT)
    GPIO.setup(pin_bomba_a, GPIO.OUT)
    GPIO.setup(pin_front_mine_dropping, GPIO.OUT)
    GPIO.setup(pin_rear_mine_dropping, GPIO.OUT)

    # GPIO.setup(pin_front_left_motor_control, GPIO.OUT)
    GPIO.setup(pin_rear_left_motor_control, GPIO.OUT)
    GPIO.setup(pin_front_right_motor_control, GPIO.OUT)
    # GPIO.setup(pin_rear_right_motor_control, GPIO.OUT)

    # pwm_front_left_motor = GPIO.PWM(pin_front_left_motor_control, 50)
    pwm_rear_left_motor = GPIO.PWM(pin_rear_left_motor_control, 50)
    pwm_front_right_motor = GPIO.PWM(pin_front_right_motor_control, 50)
    # pwm_rear_right_motor = GPIO.PWM(pin_rear_right_motor_control, 50)

    main()


async def handler(websocket):
    print('Websocket is open')
    global is_bombaA_released, lest_ws_msg
    change_network(ETHERNET_SETTINGS)
    threading.Thread(target=start_read_gps, args=(websocket,), daemon=True).start()

    print('Start websocket')
    while True:
        try:
            try:
                data_json = await websocket.recv()
                message = json.loads(data_json)
                block_mine_dropping(pin_rear_mine_dropping)
                block_mine_dropping(pin_front_mine_dropping)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                continue
            except websockets.ConnectionClosed as e:
                print(f"WebSocket connection closed: {e}")
                motor_stop()
                change_network(RADIO_SETTINGS)
                break

            if message.get("type") == "joystick":
                if connection_type == ETHERNET_SETTINGS.type:
                    drone_control(message.get("x"), message.get("y"))
                    lest_ws_msg = time.time()
            elif message.get("type") == "mine":
                if message.get("frontMine"):
                    print('Drop front mine')
                    drop_mine(pin_front_mine_dropping)
                if message.get("rearMine"):
                    print('Drop rear mine')
                    drop_mine(pin_rear_mine_dropping)

            elif message.get("type") == "bomba":
                if message.get("bombA"):
                    print('Bomba in A position')
                    is_bombaA_released = True
                    drop_bomba(pin_bomba_a)
                else:
                    is_bombaA_released = False
                    block_bomba(pin_bomba_a)
                if message.get("bombB"):
                    if is_bombaA_released:
                        print('Bomba in B position')
                        drop_bomba(pin_bomba_b)
                        is_bombaA_released = False
                else:
                    block_bomba(pin_bomba_b)
                    is_bombaA_released = False

            elif message.get("type") == "controlOption":
                global control_option
                if message.get("value") == "duo":
                    control_option = DUO
                else:
                    control_option = STANDARD

        except Exception as e:
            print(f"Exception occurred: {e}")
            change_network(RADIO_SETTINGS)
            break


async def start_websocket():
    async with websockets.serve(handler, "0.0.0.0", 8001):
        await asyncio.Future()


def start_ws():
    asyncio.run(start_websocket())


def drone_control(left_motor, right_motor):
    print("LEFT_MOTOR_SPEED: ", left_motor)
    print("RIGHT_MOTOR_SPEED: ", right_motor)
    speed_left_motor = map_value(left_motor, ETHERNET_SETTINGS.min, ETHERNET_SETTINGS.max, 4.1, 9.1)
    speed_right_motor = map_value(right_motor, ETHERNET_SETTINGS.min, ETHERNET_SETTINGS.max, 4.1, 9.1)
    print("LEFT_MOTOR_SPEED------MAP: ", speed_left_motor)
    print("RIGHT_MOTOR_SPEED------MAP: ", speed_right_motor)

    # pwm_front_left_motor.ChangeDutyCycle(speed_left_motor)
    pwm_rear_left_motor.ChangeDutyCycle(speed_left_motor)
    pwm_front_right_motor.ChangeDutyCycle(speed_right_motor)
    # pwm_rear_right_motor.ChangeDutyCycle(speed_right_motor)
    # speed_left_motor = map_value(left_motor, ETHERNET_SETTINGS.min, ETHERNET_SETTINGS.max, 1000, 2000)
    # speed_right_motor = map_value(right_motor, ETHERNET_SETTINGS.min, ETHERNET_SETTINGS.max, 1000, 2000)
    # if check_connection():
    #     set_servo(1, speed_left_motor)
    #     set_servo(2, speed_right_motor)

def map_value(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min


def motor_stop():
    # pwm_front_left_motor.ChangeDutyCycle(7.2)
    pwm_rear_left_motor.ChangeDutyCycle(7.2)
    pwm_front_right_motor.ChangeDutyCycle(7.2)
    # pwm_rear_right_motor.ChangeDutyCycle(7.2)


def read_radio_signal():
    print('Radio is connect')
    while True:
        # it's validation for security drone
        if time.time() - lest_ws_msg > 1:
            motor_stop()
        if is_payload_ready():
            rotation_signal = get_channel(0)
            # speed_channel = 1 if control_option == STANDARD else 3
            speed_signal = get_channel(1)
            rotation_signal = map_value(rotation_signal, RADIO_SETTINGS.min, RADIO_SETTINGS.max, ETHERNET_SETTINGS.min, ETHERNET_SETTINGS.max)
            speed_signal = map_value(speed_signal, RADIO_SETTINGS.min, RADIO_SETTINGS.max, ETHERNET_SETTINGS.min, ETHERNET_SETTINGS.max)
        else:
            rotation_signal = IDLE_SIGNAL_VALUE
            speed_signal = IDLE_SIGNAL_VALUE
        if connection_type == RADIO_SETTINGS.type:
            drone_control(rotation_signal, speed_signal)
            read_mine()
            read_bomb()
        time.sleep(0.24)


def read_mine():
    drop_mine(pin_front_mine_dropping) if get_channel(2) > RADIO_SETTINGS.idle else block_mine_dropping(pin_front_mine_dropping)
    drop_mine(pin_rear_mine_dropping) if get_channel(3) > RADIO_SETTINGS.idle else block_mine_dropping(pin_rear_mine_dropping)


def read_bomb():
    bomb_position = get_channel(5)

    if bomb_position == 997:
        drop_bomba(pin_bomba_a)
        block_bomba(pin_bomba_b)
    elif bomb_position > 997:
        drop_bomba(pin_bomba_a)
        drop_bomba(pin_bomba_b)
    else:
        block_bomba(pin_bomba_a)
        block_bomba(pin_bomba_b)


def drop_mine(pin_mine):
    GPIO.output(pin_mine, GPIO.OUT)


def block_mine_dropping(pin_mine):
    GPIO.output(pin_mine, GPIO.OUT)


def drop_bomba(pin_bomb):
    GPIO.output(pin_bomb, GPIO.HIGH)


def block_bomba(pin_bomb):
    GPIO.output(pin_bomb, GPIO.LOW)


def change_network(network_settings):
    print(network_settings.type)
    global connection_type, MIN_SIGNAL_VALUE, MAX_SIGNAL_VALUE, IDLE_SIGNAL_VALUE, MAX_IDLE_VALUE, MIN_IDLE_VALUE
    connection_type = network_settings.type
    MIN_SIGNAL_VALUE = network_settings.min
    MAX_SIGNAL_VALUE = network_settings.max
    IDLE_SIGNAL_VALUE = network_settings.idle
    MAX_IDLE_VALUE = network_settings.idle + network_settings.offset
    MIN_IDLE_VALUE = network_settings.idle - network_settings.offset

    if connection_type == RADIO_SETTINGS.type:
        MIN_SIGNAL_VALUE = map_value(MIN_SIGNAL_VALUE, network_settings.min, network_settings.max,
                                                     ETHERNET_SETTINGS.min, ETHERNET_SETTINGS.max)
        MAX_SIGNAL_VALUE = map_value(MAX_SIGNAL_VALUE, network_settings.min, network_settings.max,
                                                     ETHERNET_SETTINGS.min, ETHERNET_SETTINGS.max)
        IDLE_SIGNAL_VALUE = ETHERNET_SETTINGS.idle
        MAX_IDLE_VALUE = map_value(MAX_IDLE_VALUE, network_settings.idle - network_settings.offset,
                                                   network_settings.idle + network_settings.offset,
                                                   ETHERNET_SETTINGS.idle - ETHERNET_SETTINGS.offset,
                                                   ETHERNET_SETTINGS.idle + ETHERNET_SETTINGS.offset)
        MIN_IDLE_VALUE = map_value(MIN_IDLE_VALUE, network_settings.idle - network_settings.offset,
                                                   network_settings.idle + network_settings.offset,
                                                   ETHERNET_SETTINGS.idle - ETHERNET_SETTINGS.offset,
                                                   ETHERNET_SETTINGS.idle + ETHERNET_SETTINGS.offset)


setup()