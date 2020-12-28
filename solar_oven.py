import time
import sys
import threading
import json
import datetime

import pysolar
import pytz

import pan_tilt


class SolarOven(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

        with open('location_data.json') as location_data:
            location = json.load(location_data)

        self.latitude = location["location_data"]["latitude"]
        self.longitude = location["location_data"]["longitude"]
        # print(self.latitude, self.longitude)

    def get_solar_info_by_time(self, calc_time):

        alt = pysolar.solar.get_altitude(self.latitude, self.longitude, calc_time)
        ret_data = {'altitude_deg': alt,
                    'azimuth_deg': pysolar.solar.get_azimuth(self.latitude, self.longitude, calc_time),
                    'power': pysolar.radiation.get_radiation_direct(calc_time, alt),
                    'calc_time': calc_time.strftime("%H:%M:%S %Z %a %d/%m/%y")}
        # print(ret_data)

        return ret_data


if __name__ == "__main__":

    solar_oven = SolarOven()

    time_data = datetime.datetime.now(tz=pytz.timezone("Europe/London"))

    # Create some servo objects

    pan_servo_def = {'pwm_pin': 6, 'low_duty': 500, 'high_duty': 2500}
    tilt_servo_def = {'pwm_pin': 5, 'low_duty': 500, 'high_duty': 2500}

    # Set up the pan tilt controller and start the thread.
    pan_tilt_controller = pan_tilt.PanTiltController(pan_servo_def, tilt_servo_def, 2, pan_offset=2, tilt_offset=15)
    pan_tilt_controller.daemon = True
    pan_tilt_controller.start()

    try:
        print("Going to 0,0")

        cmd = {'pan_angle': 0, 'tilt_angle': 0}
        pan_tilt_controller.cmd_queue.put_nowait(cmd)
        time.sleep(30)

        while True:

            time_data = datetime.datetime.now(tz=pytz.timezone("Europe/London"))
            sun_data = solar_oven.get_solar_info_by_time(time_data)
            # print(time_data, sun_data)
            cmd = {'pan_angle': 270 - sun_data['azimuth_deg'], 'tilt_angle': 180 - sun_data['altitude_deg']}
            pan_tilt_controller.cmd_queue.put_nowait(cmd)
            time.sleep(60)

    except KeyboardInterrupt:

        print("Quitting the program due to Ctrl-C")

    except:
        print("Unexpected error:", sys.exc_info())
        raise

    finally:
        print("\nTidying up")
