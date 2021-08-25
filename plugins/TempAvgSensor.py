import logging
import aiofiles
import asyncio
import re
from interfaces import Sensor
from event import notify, Event

from common import components

logger = logging.getLogger(__name__)

def factory(name, settings):
    sensors = settings['sensors']
    offset = settings.get('offset', 0.0)
    return TempAvgSensor(name, sensors, offset)

class TempAvgSensor(Sensor):
    def __init__(self, name, sensors, offset=0):
        self.name = name
        self.sensors = sensors
        self.offset = offset
        self.lastTemp = 0
        asyncio.get_event_loop().create_task (self.run())

    async def run(self):
        while True:
            self.lastTemp = await self.readTemp() 
            await asyncio.sleep(10)

    async def readTemp(self):
        tempsum = 0.0
        for sensor in self.sensors:
            tempsum += components[sensor].temp ()
        temp = tempsum / len (self.sensors) + self.offset
        notify(Event(source=self.name, endpoint='temperature', data=temp))
        return temp

    def temp(self):
        return self.lastTemp
