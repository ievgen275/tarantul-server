from pymavlink import mavutil
import time

connection = mavutil.mavlink_connection('/dev/ttyACM0', baud=115200)

def check_connection():
    try:
        connection.wait_heartbeat()
        print("MAVLink is connect")
        return True
    except:
        print("MAVLink connection is lost")
        return False

def arm_vehicle():
    print("Sending arm command...")
    connection.mav.command_long_send(
        connection.target_system,
        connection.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        1,
        0, 0, 0, 0, 0, 0
    )
    print("Waiting for arming confirmation...")
    while True:
        msg = connection.recv_match(type='HEARTBEAT', blocking=True)
        if msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED:
            print("Vehicle is armed!")
            break
        time.sleep(1)

def override_rc_channel(channel_number, pwm_value):
    rc_channels = [65535]*18
    rc_channels[channel_number - 1] = pwm_value
    connection.mav.rc_channels_override_send(
        connection.target_system,
        connection.target_component,
        *rc_channels
    )
    print("MAVLink comand is send")

def send_heartbeat():
    while True:
        try:
            connection.mav.heatbeat_send(
                mavutil.mavlink.MAV_TYPE_GCS,
                mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                0, 0, 0
            )
            print("HEATBEAT send")
        except:
            print("HEATBEAT send is failed")
        time.sleep(1)
