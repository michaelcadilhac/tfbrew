import logging
from interfaces import Actor
from event import notify, Event

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)

def factory(name, settings):
    return GPIOActor(name, settings['gpio'], settings.get('pwmFrequency',2))


logger = logging.getLogger(__name__)

class GPIOActor(Actor):
    def __init__(self, name, pin, pwmFrequency):
        logger.info ("Setting up GPIO pin %s as %s"%(pin, name))
        self.name = name
        self.power = 0.0
        self.pin = pin
        self.frequency = pwmFrequency
        GPIO.setup(self.pin, GPIO.OUT)
        self.p = GPIO.PWM(self.pin, self.frequency)
        self.p.start(self.power)

    def updatePower(self, power):
        self.power = power
        self.p.ChangeDutyCycle(self.power)
        notify(Event(source=self.name, endpoint='power', data=power))

    def getPower(self):
        return self.power

    def on(self):
        self.updatePower(100.0)

    def off(self):
        self.updatePower(0.0)

    def callback(self, endpoint, data):
        if endpoint == 'state':
            if data == 0:
                print("Turning %s off"%self.name)
                self.off()
            elif data == 1:
                print("Turning %s on"%self.name)
                self.on()
            else:
                print("Warning: GPIOActor:%s unsupported data value: %d"%(self.name, data))
