# This code is modified from code found in the WiPy project
# https://github.com/wipy/wipy/blob/master/lib/blynk/BlynkLib.py
# That code is licensed under the MIT License as shown below:
#
# Copyright (c) 2015 Daniel Campora
# Copyright (c) 2015 Volodymyr Shymanskyy
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# Modifications for TFBrew by Hrafnkell Eiríksson
# Copyright (c) 2017 Hrafnkell Eiríksson
#
import asyncio
import struct
import time
import sys
import logging

import interfaces
from event import notify, Event

logger = logging.getLogger(__name__)

def factory(name, settings):
    blynkServer = settings.get('server','blynk-cloud.com')
    blynkPort = settings.get('port', 8442)
    component = BlynkComponent(name, blynkServer, blynkPort, settings['token'])
    return component

epoch = time.time()

const = lambda x: x

HDR_LEN = const(5)
HDR_FMT = "!BHH"

MAX_MSG_PER_SEC = const(20)

MSG_RSP = const(0)
MSG_LOGIN = const(2)
MSG_PING  = const(6)
MSG_TWEET = const(12)
MSG_EMAIL = const(13)
MSG_NOTIFY = const(14)
MSG_BRIDGE = const(15)
MSG_HW_SYNC = const(16)
MSG_HW_INFO = const(17)
MSG_HW = const(20)

STA_SUCCESS = const(200)

HB_PERIOD = const(10)
NON_BLK_SOCK = const(0)
MIN_SOCK_TO = const(1) # 1 second
MAX_SOCK_TO = const(5) # 5 seconds, must be < HB_PERIOD
RECONNECT_DELAY = const(1) # 1 second
TASK_PERIOD_RES = const(50) # 50 ms
IDLE_TIME_MS = const(5) # 5 ms

RE_TX_DELAY = const(2)
MAX_TX_RETRIES = const(3)

MAX_VIRTUAL_PINS = const(32)

DISCONNECTED = const(0)
CONNECTING = const(1)
AUTHENTICATING = const(2)
AUTHENTICATED = const(3)
CLOSED = const(4)

EAGAIN = const(11)

class VrPin:
    def __init__(self, read=None, write=None):
        self.read = read
        self.write = write

class BlynkProtocol(asyncio.Protocol):
    def __init__(self, token, component):
        self.token = token
        self._rx_data = b''
        self._vr_pins = {}
        self.component = component
        self.transport = None
        self.reset()
        asyncio.ensure_future(self._heartbeat())

    def reset(self):
        self._msg_id = 1
        self._last_hb_id = 0
        self.state = DISCONNECTED
        self._m_time = 0
        self._hb_time = 0

    async def _heartbeat(self):
        while True:
            try:
                if self.state in {DISCONNECTED, CLOSED}:
                    await self.component.asyncRun()
                isOnline = self._server_alive()
                if not isOnline:
                    logger.warning("server not online when sending heartbeat")
                await asyncio.sleep(HB_PERIOD)
            except OSError as e:
                logger.warning(e)

    def _new_msg_id(self):
        self._msg_id += 1
        if self._msg_id > 0xFFFF:
            self._msg_id = 1
        return self._msg_id

    def _format_msg(self, msg_type, *args):
        data = ('\0'.join(map(str, args))).encode('ascii')
        return struct.pack(HDR_FMT, msg_type, self._new_msg_id(), len(data)) + data

    def _send(self, data, send_anyway=False):
        try:
            self.transport.write(data)
        except:
            logger.warning("Blynk failed to write to transport")


    def _recv(self, length, timeout=0):
        if len(self._rx_data) >= length:
            data = self._rx_data[:length]
            self._rx_data = self._rx_data[length:]
            return data
        else:
            return b''

    def _close(self, emsg=None):
        self.transport.close()
        self.state = CLOSED
        # time.sleep(RECONNECT_DELAY)
        logger.warning("closing blynk for some reason")
        if emsg:
            logger.warning('Error: %s, connection closed' % emsg)

    def _handle_hw(self, data):
        params = list(map(lambda x: x.decode('ascii'), data.split(b'\0')))
        cmd = params.pop(0)
        if cmd == 'info':
            pass
        elif cmd == 'pm':
            pass
        elif cmd == 'vw':
            pin = int(params.pop(0))
            self.component.writeRequest(pin, params)
            # if pin in self._vr_pins and self._vr_pins[pin].write:
            #     for param in params:
            #         self._vr_pins[pin].write(param)
            # else:
            #     print("Warning: Virtual write to unregistered pin %d" % pin)
        elif cmd == 'vr':
            pin = int(params.pop(0))
            self.component.readRequest(pin, params)
            # if pin in self._vr_pins and self._vr_pins[pin].read:
            #     self._vr_pins[pin].read()
            # else:
            #     print("Warning: Virtual read from unregistered pin %d" % pin)
        else:
            raise ValueError("Unknown message cmd: %s" % cmd)

    def _server_alive(self):
        if self.state in {DISCONNECTED, CLOSED}:
            return False
        c_time = int(time.time())
        if self._m_time != c_time:
            self._m_time = c_time
            self._tx_count = 0
            if self._last_hb_id != 0 and c_time - self._hb_time >= MAX_SOCK_TO:
                return False
            if c_time - self._hb_time >= HB_PERIOD and self.state == AUTHENTICATED:
                self._hb_time = c_time
                self._last_hb_id = self._new_msg_id()
                self._send(struct.pack(HDR_FMT, MSG_PING, self._last_hb_id, 0), True)
        return True



    def connection_made(self, transport):
        logger.info("connection_made")
        self.transport = transport
        hdr = struct.pack(HDR_FMT, MSG_LOGIN, self._new_msg_id(), len(self.token))
        self._send(hdr+self.token.encode('ascii'))
        self.state = AUTHENTICATING

    def data_received(self, data):
        self._rx_data += data

        while len(self._rx_data)>0:
            self.run()

    def virtual_write(self, pin, val):
        if self.state == AUTHENTICATED:
            self._send(self._format_msg(MSG_HW, 'vw', pin, val))

    def sync_all(self):
        if self.state == AUTHENTICATED:
            self._send(self._format_msg(MSG_HW_SYNC))

    def run(self):
        data = self._recv(HDR_LEN)
        msg_type, msg_id, status = struct.unpack(HDR_FMT, data)
        
        if self.state == AUTHENTICATING:
            if status != STA_SUCCESS or msg_id == 0:
                logger.warning('Blynk authentication failed')
                return

            self.state = AUTHENTICATED
            self._send(self._format_msg(MSG_HW_INFO, 'ver', '0.0.1+py', 'h-beat', HB_PERIOD, 'dev', sys.platform))
            logger.info('Access granted, happy Blynking!')
            #self.sync_all()
        elif self.state == AUTHENTICATED:
            msg_len = status
            if msg_id == 0:
                self.transport.close()
                logger.warning('invalid msg id %d' % msg_id)
                return
            if msg_type == MSG_RSP:
                if msg_id == self._last_hb_id:
                    self._last_hb_id = 0
            elif msg_type == MSG_PING:
                self._send(struct.pack(HDR_FMT, MSG_RSP, msg_id, STA_SUCCESS))
            elif msg_type == MSG_HW or msg_type == MSG_BRIDGE:
                data = self._recv(msg_len, MIN_SOCK_TO)
                if data:
                    self._handle_hw(data)
            else:
                logger.warning('unknown message type %d' % msg_type)
                #self._close('unknown message type %d' % msg_type)
                return


    def connection_lost(self, exc):
        logger.warning("Blynk got connection lost")
        self.transport.close()
        self.state = CLOSED
        if exc:
            logger.exception(exc)

    def VIRTUAL_READ(blynk, pin):
        class Decorator():
            def __init__(self, func):
                self.func = func
                blynk._vr_pins[pin] = VrPin(func, None)
                #print(blynk, func, pin)
            def __call__(self):
                return self.func()
        return Decorator

    def VIRTUAL_WRITE(blynk, pin):
        class Decorator():
            def __init__(self, func):
                self.func = func
                blynk._vr_pins[pin] = VrPin(None, func)
            def __call__(self):
                return self.func()
        return Decorator


class BlynkComponent(interfaces.Component):
    def __init__(self, name, server, port, token):
        self.name = name
        self.server = server
        self.port = port
        self.token = token
        self.blynk = BlynkProtocol(self.token, self)

    async def asyncRun(self):
        try:
            self.blynk.reset()
            transport, protocol = await asyncio.get_event_loop().create_connection(lambda: self.blynk, self.server, self.port)
            self.blynk = protocol
        except (ConnectionError, TimeoutError) as e:
            logger.warning("Error connecting to Blynk server: %s"%str(e))

    def run(self):
       asyncio.ensure_future(self.asyncRun())
 
    def writeRequest(self, pin, params):
        notify(Event(source=self.name, endpoint='v%d'%pin, data=float(params.pop(0))))

    def readRequest(self, pin, params):
        logger.info("Read request for v%d: %s"%(pin, str(params)))

    def callback(self, endpoint, data):
        pinNr = int(endpoint[1:])
        logger.info ("writing pin %s with %s"%(pinNr, data))
        #print("%s : %s"%(type,event))
        self.blynk.virtual_write(pinNr, data)
