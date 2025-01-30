# sbus_communication
import serial
import time
from pysbus.sbus import SBUS
from pysbus.constants import SBUSConsts
from pysbus.serial_parser import SerialParser

port = '/dev/ttyS0'
baudrate = SBUSConsts.BAUD_RATE

stop_reading = False
is_ready = False

sbus = SBUS(
    SerialParser(port, baudrate)
)
sbus.begin()

channels = [0] * SBUSConsts.NUM_CHANNELS


def read_sbus_data():
    print("Start reading SBUS")
    global is_ready
    try:
        while not stop_reading:
            print("Start reading")
            payload_ready, failsafe, lost_frame = sbus.read(channels)
            is_ready = payload_ready
            #if payload_ready:
            #    print("Channels: ", channels)
            #    print("Fail-Safe Status:", failsafe)
            #    print("Lost Frame Status:", lost_frame)
 
    except KeyboardInterrupt:
        print("Stopped by User")

    finally:
        sbus.close()


def get_channel(num):
    return channels[num]


def is_payload_ready():
    return is_ready


def start_read_sbus():
    global stop_reading
    stop_reading = False


def stop_read_sbus():
    global stop_reading
    stop_reading = True
