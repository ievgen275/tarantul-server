from pymavlink import mavutil
import time

connection = mavutil.mavlink_connection('/dev/ttyS0', baud=115200)

def check_connection():
    try:
        connection.wait_heartbeat()
        print("MAVLink is connect")
        return True
    except:
        print("MAVLink connection is lost")
        return False

def set_servo(servo_number, pwm_value):
    connection.mav.command_long_send(
        connection.target_system,
        connection.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
        0,
        servo_number,
        pwm_value,
        0, 0, 0, 0, 0
    )
    print("MAVLink comand is send")