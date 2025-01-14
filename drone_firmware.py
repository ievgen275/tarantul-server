import subprocess
import threading
from network_signal_settings import ETHERNET_SETTINGS, RADIO_SETTINGS
from sbus_communication import read_sbus_data, get_channel, is_payload_ready
from gps_handler import start_read_gps
#import mavlink_connection
import time
import RPi.GPIO as GPIO
import asyncio
import websockets
import json
import spidev

# Define the GPIO pins based on your setup
pin_left_motor_control = 12  # PWM Output
pin_right_motor_control = 18  # PWM Output
pin_bomba_a = 25  # Bomba A pin
pin_bomba_b = 16  # Bomba B pin
pin_front_mine_dropping = 20  # Mine Front
pin_rear_mine_dropping = 24  # Mine Rear

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.cleanup()

# Constants for signal processing
MIN_SIGNAL_VALUE = ETHERNET_SETTINGS.min
MAX_SIGNAL_VALUE = ETHERNET_SETTINGS.max
IDLE_SIGNAL_VALUE = ETHERNET_SETTINGS.idle
MAX_IDLE_VALUE = ETHERNET_SETTINGS.idle + ETHERNET_SETTINGS.offset
MIN_IDLE_VALUE = ETHERNET_SETTINGS.idle - ETHERNET_SETTINGS.offset

is_bombaA_released = False
lest_ws_msg = 0
pwm_left_motor = None
pwm_right_motor = None
mavlink_is_connect = None
spi = None

# checking connection variables
connection_type = RADIO_SETTINGS.type

def main():
    threading.Thread(target=start_ws).start()
    threading.Thread(target=read_radio_signal).start()
    threading.Thread(target=start_leash).start()


def setup():
    print('Setup start')
    global pwm_left_motor, pwm_right_motor, mavlink_is_connect, spi
    #subprocess.run(['sudo', 'motion'], check=True)
    #mavlink_is_connect = mavlink_connection.check_connection()
    #threading.Thread(target=mavlink_connection.send_heartbeat, daemon=True).start()
    #mavlink_connection.arm_vehicle()
    threading.Thread(target=read_sbus_data, daemon=True).start()

    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 1350000

    GPIO.setup(pin_bomba_b, GPIO.OUT)
    GPIO.setup(pin_bomba_a, GPIO.OUT)
    GPIO.setup(pin_front_mine_dropping, GPIO.OUT)
    GPIO.setup(pin_rear_mine_dropping, GPIO.OUT)

    GPIO.setup(pin_left_motor_control, GPIO.OUT)
    GPIO.setup(pin_right_motor_control, GPIO.OUT)

    pwm_left_motor = GPIO.PWM(pin_left_motor_control, 50)
    pwm_right_motor = GPIO.PWM(pin_right_motor_control, 50)
    pwm_left_motor.start(1)
    pwm_right_motor.start(1)

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
    # if mavlink_is_connect:
    #     speed_left_motor = map_value(left_motor, ETHERNET_SETTINGS.min, ETHERNET_SETTINGS.max, 1000, 2000)
    #     speed_right_motor = map_value(right_motor, ETHERNET_SETTINGS.min, ETHERNET_SETTINGS.max, 1000, 2000)
    #
    #     mavlink_connection.override_rc_channel(1, speed_left_motor)
    #     mavlink_connection.override_rc_channel(2, speed_right_motor)
    # else:
    #     speed_left_motor = map_value(left_motor, ETHERNET_SETTINGS.min, ETHERNET_SETTINGS.max, 5, 75)
    #     speed_right_motor = map_value(right_motor, ETHERNET_SETTINGS.min, ETHERNET_SETTINGS.max, 5, 75)
    #
    #     pwm_left_motor.ChangeDutyCycle(speed_left_motor)
    #     pwm_right_motor.ChangeDutyCycle(speed_right_motor)

    speed_left_motor = map_value(left_motor, ETHERNET_SETTINGS.min, ETHERNET_SETTINGS.max, 5, 75)
    speed_right_motor = map_value(right_motor, ETHERNET_SETTINGS.min, ETHERNET_SETTINGS.max, 5, 75)

    pwm_left_motor.ChangeDutyCycle(speed_left_motor)
    pwm_right_motor.ChangeDutyCycle(speed_right_motor)

def map_value(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min


def motor_stop():
    # if mavlink_is_connect:
    #     mavlink_connection.override_rc_channel(1, 1500)
    #     mavlink_connection.override_rc_channel(2, 1500)
    # else:
    #     pwm_left_motor.ChangeDutyCycle(40)
    #     pwm_right_motor.ChangeDutyCycle(40)

    pwm_left_motor.ChangeDutyCycle(40)
    pwm_right_motor.ChangeDutyCycle(40)

def read_adc(channel):
    if channel < 0 or channel > 7:
        return -1
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    value = ((adc[1] & 3) << 8) + adc[2]
    return value

def start_leash():
    while True:
        gas_throttle_left = read_adc(0)
        gas_throttle_right = read_adc(1)

        drone_control(gas_throttle_left, gas_throttle_right)

def read_radio_signal():
    print('Radio is connect')
    while True:
        # it's validation for security drone
        if time.time() - lest_ws_msg > 1:
            motor_stop()
        if is_payload_ready():
            rotation_signal = get_channel(0)
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
    GPIO.output(pin_mine, GPIO.HIGH)


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
