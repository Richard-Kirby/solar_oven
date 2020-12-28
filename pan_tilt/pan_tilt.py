# !/usr/bin/env python3

import pigpio
import threading
import time
import sys
import subprocess
import queue
import os
import json

"""
This bit just gets the pigpiod daemon up and running if it isn't already.
The pigpio daemon accesses the Raspberry Pi GPIO.  
"""
p = subprocess.Popen(['pgrep', '-f', 'pigpiod'], stdout=subprocess.PIPE)
out, err = p.communicate()

if len(out.strip()) == 0:
    os.system("sudo pigpiod")
    time.sleep(3)

pi = pigpio.pi()


# Sets up a Servo and drives it as requested.
class Servo:

    # Details of how to drive the servo.
    def __init__(self, servo_dict):
        self.servo_dict = servo_dict

    # Drives the servo to a certain angle.
    def set_angle(self, angle):

        servo_pulse = int((float(angle / 210) * (self.servo_dict['high_duty'] - self.servo_dict['low_duty']))
                          + self.servo_dict['low_duty'])

        if servo_pulse > self.servo_dict['high_duty']:
            print("Setting PWM pulse to max {} from {} request" .format(self.servo_dict['high_duty'], servo_pulse))
            servo_pulse = self.servo_dict['high_duty']

        if 0 < servo_pulse < self.servo_dict['low_duty']:
            print("Setting PWM pulse to min {} from {} request" .format(self.servo_dict['low_duty'], servo_pulse))
            servo_pulse = self.servo_dict['low_duty']

        if servo_pulse < 0:
            print("Setting PWM pulse to 0 from {} request" .format(servo_pulse))
            servo_pulse = 0

        pi.set_servo_pulsewidth(self.servo_dict['pwm_pin'], int(servo_pulse))


# The pan tilt controller, which owns the servos (or whatever motor) and sets the angles as required.
class PanTiltController(threading.Thread):

    def __init__(self, pan_servo_dict, tilt_servo_dict, pause_time, pan_offset=0, tilt_offset=0):
        threading.Thread.__init__(self)

        self.pan_servo = Servo(pan_servo_dict)
        self.tilt_servo = Servo(tilt_servo_dict)
        self.pan_offset = pan_offset
        self.tilt_offset = tilt_offset
        self.pause_time = pause_time
        self.cmd_queue = queue.Queue()

    # Send the servos to zero position.
    def send_servos_home(self):
        self.pan_servo.set_angle(0 + self.pan_offset)
        self.tilt_servo.set_angle(0 + self.tilt_offset)

    # This is the over-ridden function for the running of the thread.  It just looks for things to pop up
    # in its queue and gets the angles set accordingly.
    def run(self):

        try:

            while True:

                # If Queue isn't empty, deal with the string by processing each letter.
                if not self.cmd_queue.empty():

                    # Get the string
                    cmd = self.cmd_queue.get_nowait()

                    #print(cmd)
                    self.pan_servo.set_angle(float(cmd['pan_angle'] + self.pan_offset))
                    self.tilt_servo.set_angle(float(cmd['tilt_angle'] + self.tilt_offset))

                    time.sleep(self.pause_time)

        except KeyboardInterrupt:
            pi.set_servo_pulsewidth(self.pwm_pin, self.low_duty)

        except:
            print("Unexpected error:", sys.exc_info())
            raise


if __name__ == "__main__":

    # Create some servo objects

    pan_servo_def = {'pwm_pin': 6, 'low_duty': 500, 'high_duty': 2500}
    tilt_servo_def = {'pwm_pin': 5, 'low_duty': 500, 'high_duty': 2500}

    # Set up the Semaphore flagger and start the thread.
    pan_tilt_controller = PanTiltController(pan_servo_def, tilt_servo_def, 2, pan_offset=0, tilt_offset=0)
    pan_tilt_controller.daemon = True
    pan_tilt_controller.start()

    try:
        while True:

            #pan_tilt_controller.send_servos_home()

            time.sleep(1)

            print("Panning 0 to 210")
            for i in range(0, 180):
                cmd = {'pan_angle': i, 'tilt_angle': i}

                #print(cmd['pan_angle'])
                pan_tilt_controller.cmd_queue.put_nowait(cmd)

            #time.sleep(1)

    except KeyboardInterrupt:

        print("Quitting the program due to Ctrl-C")

    except:
        print("Unexpected error:", sys.exc_info())
        raise

    finally:
        print("\nTidying up")
        pi.stop()
