import sys
import time
import logging
import argparse
import concurrent.futures

from collections import deque
from readerwriterlock import rwlock

sys.path.append(r'/home/bhagatsj/RobotSystems/lib')
from picarx import Picarx
from utils import reset_mcu
from picamera import PiCamera
from picamera.array import PiRGBArray
from w3_sensors import *

reset_mcu()

logging_format = "%(asctime)s: %(message)s"
logging.basicConfig(format=logging_format, level=logging.ERROR , datefmt="%H:%M:%S ")

class Bus():
    def __init__(self):
        self.lock = rwlock.RWLockWriteD()
        self.message = None

    def read(self):
        return self.message

    def write(self, message):
        with self.lock.gen_wlock():
            self.message = message

def sensor_func(sensor_bus, sensor, delay_time):
    #Producer
    adc_list = sensor.get_adc_value()
    sensor_bus.write(adc_list)
    time.sleep(delay_time)

def interpretor_func(sensor_bus, interpretor_bus, interpretor, delay_time):
    #Consumer-Producer
    adc_list = sensor_bus.read()
    maneuver_val = interpretor.get_manuever_val(adc_list)
    interpretor_bus.write(maneuver_val)
    time.sleep(delay_time)

def controller_func(interpretor_bus, controller, delay_time):
    #Consumer
    maneuver_val = interpretor_bus.read()
    maneuver_val = controller.set_angle(maneuver_val)
    time.sleep(delay_time)


def main(config):
    #Line following simultaneity
    if config.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    car = Picarx()
    interpretor = Grayscale_Interpreter(75, 1.0)
    controller = Controller(car, scale=0.9)
    sensor_bus = Bus()
    interpretor_bus = Bus()

    duration = 30 #run the program for 30 seconds
    controller.start_car()

    #Spin up futures to write to the busses
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor :
        eSensor = executor.submit(sensor_func, sensor_bus , car, 1)
        eInterpreter = executor.submit(interpretor_func, sensor_bus, interpretor_bus, interpretor, 1)
        eController = executor.submit(controller_func, interpretor_bus, controller, 1)

    #Use main thread for the controller to follow line
    start_time = time.time()
    rel_time = 0
    while rel_time < duration:
        time.sleep(1)
        rel_time = time.time() - start_time
                    
    controller.stop_car()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--time', default=10,
                        help='Duration of running the program')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Debug flag')
    main(parser.parse_args())
