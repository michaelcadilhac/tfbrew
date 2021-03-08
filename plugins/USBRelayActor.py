from interfaces import Actor
from event import notify, Event
from subprocess import call

def factory(name, settings):
    return USBRelayActor(name, settings['id'], settings.get('inverted', False))


class USBRelayActor(Actor):
    def __init__(self, name, relayName, inverted):
        self.name = name
        self.power = 0.0
        self.relayName = relayName
        self.inverted = bool(inverted)
        self.off()

    def updatePower(self, power):
        self.power = power
        print("Sending power %d to %s"%(power, self.name))
        if (self.power and not self.inverted) or (not self.power and self.inverted):
            call (["usbrelay", self.relayName + '=1'])
        else:
            call (["usbrelay", self.relayName + '=0'])
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
                print("Warning: USBRelayActor:%s unsupported data value: %d"%(self.name, data))
