"""
Nexus - Nextion Upload Script by Max Zuidberg

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import argparse
import struct
import serial
from serial.tools.list_ports import comports as availablePorts
from pathlib import Path
from math import ceil
from time import sleep


class Nexus:
    NXEOL = b"\xff\xff\xff"
    NXACK = b"\x05"
    NXSKP = b"\x08\x00\x00\x11\x00"
    modelData = {
        0x9aa696a7: {"modelName": "TJC3224T022_011", "xorKey": 0x189a66fb, },
        0xea4c3169: {"modelName": "TJC3224T024_011", "xorKey": 0x54cd4ea3, },
        0x72930b67: {"modelName": "TJC4024T032_011", "xorKey": 0x022df60d, },
        0xade186d6: {"modelName": "TJC4832T035_011", "xorKey": 0xd21759a3, },
        0xd5f3287f: {"modelName": "TJC4827T043_011", "xorKey": 0x270e0627, },
        0x98777c2d: {"modelName": "TJC8048T050_011", "xorKey": 0x02dac5b5, },
        0x17c5fb02: {"modelName": "TJC8048T070_011", "xorKey": 0xf9c5080c, },
        0x334e7201: {"modelName": "TJC3224K022_011", "xorKey": 0x66cff11e, },
        0x43a4d5cf: {"modelName": "TJC3224K024_011", "xorKey": 0x2a98d946, },
        0xa2719a53: {"modelName": "TJC3224K028_011", "xorKey": 0xd1b53a74, },
        0xdb7befc1: {"modelName": "TJC4024K032_011", "xorKey": 0x7c7861e8, },
        0x04096270: {"modelName": "TJC4832K035_011", "xorKey": 0xac42ce46, },
        0x7c1bccd9: {"modelName": "TJC4827K043_011", "xorKey": 0x595b91c2, },
        0x319f988b: {"modelName": "TJC8048K050_011", "xorKey": 0x7c8f5250, },
        0xbe2d1fa4: {"modelName": "TJC8048K070_011", "xorKey": 0x87909fe9, },
        0xf52fdc1d: {"modelName": "TJC4827X343_011", "xorKey": 0x767c3bae, },
        0xb8ab884f: {"modelName": "TJC8048X350_011", "xorKey": 0x53a8f83c, },
        0x37190f60: {"modelName": "TJC8048X370_011", "xorKey": 0xa8b73585, },
        0xa7ff9055: {"modelName": "TJC1060X3A1_011", "xorKey": 0x2c3a9902, },
        0x51841ccd: {"modelName": "TJC4827X543_011", "xorKey": 0x66999185, },
        0x1c00489f: {"modelName": "TJC8048X550_011", "xorKey": 0x434d5217, },
        0x93b2cfb0: {"modelName": "TJC8048X570_011", "xorKey": 0xb8529fae, },
        0x8da106d5: {"modelName": "TJC1060X570_011", "xorKey": 0xb3fbd54d, },
        0x03545085: {"modelName": "TJC1060X5A1_011", "xorKey": 0x3cdf3329, },
        0xf59677a7: {"modelName":  "NX3224T024_011", "xorKey": 0x6d713e32, },
        0x1443383b: {"modelName":  "NX3224T028_011", "xorKey": 0x965cdd00, },
        0x6d494da9: {"modelName":  "NX4024T032_011", "xorKey": 0x3b91869c, },
        0xb23bc018: {"modelName":  "NX4832T035_011", "xorKey": 0xebab2932, },
        0xca296eb1: {"modelName":  "NX4827T043_011", "xorKey": 0x1eb276b6, },
        0x87ad3ae3: {"modelName":  "NX8048T050_011", "xorKey": 0x3b66b524, },
        0x081fbdcc: {"modelName":  "NX8048T070_011", "xorKey": 0xc079789d, },
        0x5c7e9301: {"modelName":  "NX3224K024_011", "xorKey": 0x1324a9d7, },
        0xbdabdc9d: {"modelName":  "NX3224K028_011", "xorKey": 0xe8094ae5, },
        0xc4a1a90f: {"modelName":  "NX4024K032_011", "xorKey": 0x45c41179, },
        0x1bd324be: {"modelName":  "NX4832K035_011", "xorKey": 0x95febed7, },
        0x63c18a17: {"modelName":  "NX4827K043_011", "xorKey": 0x60e7e153, },
        0x2e45de45: {"modelName":  "NX8048K050_011", "xorKey": 0x453322c1, },
        0xa1f7596a: {"modelName":  "NX8048K070_011", "xorKey": 0xbe2cef78, },
        0x55953d88: {"modelName":  "NX8048P050_011", "xorKey": 0xe80f01ca, },
        0xda27baa7: {"modelName":  "NX8048P070_011", "xorKey": 0x130ccc73, },
        0xc43473c2: {"modelName":  "NX1060P070_011", "xorKey": 0x18a58690, },
        0x4fc44fa0: {"modelName":  "NX1060P101_011", "xorKey": 0xdcb511f5, },
    }

    def __init__(self, port="", uploadSpeed=0, connectSpeed=0, connect=True):
        self.uploadSpeed  = uploadSpeed
        self.connectSpeed = connectSpeed
        self.connected    = False
        self.touch        = None
        self.address      = 0
        self.model        = ""
        self.fwVersion    = -1
        self.mcuCode      = -1
        self.serialNum    = ""
        self.flashSize    = -1
        self.ports        = [p.name for p in availablePorts()]
        if port:
            if port not in self.ports:
                raise Exception("Specified port not available ({} not in {})".format(port, self.ports))
            else:
                self.ports.remove(port)
                self.ports.insert(port, 0)

        self.ser  = serial.Serial()
        if connect:
            self.connect()

    def connect(self):
        defaultSpeeds = [2400, 4800, 9600, 19200, 31250, 38400, 57600, 74880, 115200, 230400, 250000, 256000, 460800, 500000, 512000, 921600]
        if self.connectSpeed:
            if self.connectSpeed in defaultSpeeds:
                defaultSpeeds.remove(self.connectSpeed)
            defaultSpeeds.insert(self.connectSpeed, 0)

        for port in self.ports:
            print(port)
            for speed in defaultSpeeds:
                print(speed)
                self.ser.close()
                self.ser.port = port
                self.ser.baudrate = speed
                try:
                    self.ser.timeout  = 1000/speed + 0.030
                    print(self.ser.timeout)
                except:
                    print(port, speed, self.ports, defaultSpeeds)
                    continue
                try:
                    self.ser.open()
                except:
                    break
                self.ser.reset_input_buffer()
                self.ser.write(b"DRAKJHSUYDGBNCJHGJKSHBDN\xff\xff\xffconnect\xff\xff\xff\xff\xffconnect\xff\xff\xff")
                data = b""
                available = -1
                while available != len(data):
                    available = self.ser.in_waiting
                    newData = self.ser.read_until(expected=self.NXEOL)
                    if newData:
                        data = newData
                    else:
                        break
                if not data.startswith(b"comok"):
                    continue
                self.connected=True
                data = data.lstrip(b"comok ").rstrip(self.NXEOL).split(b",")
                data[1] = data[1].split(b"-")[1] # discard reserved part of argument 1
                self.touch     = bool(int(data[0]))
                self.address   = int(data[1])
                self.model     = data[2].decode("ascii")
                self.fwVersion = int(data[3])
                self.mcuCode   = int(data[4])
                self.serialNum = data[5].decode("ascii")
                self.flashSize = int(data[6])
                self.port         = port
                self.connectSpeed = speed
                if not self.uploadSpeed:
                    self.uploadSpeed = self.connectSpeed
                self.connected    = True
                return True

        return False

    def sendCmd(self, cmd: str, *args):
        if not self.connected:
            raise Exception("Cannot send commands if not connected.")

        if args:
            cmd = str(cmd) + " " + "{}," * len(args)
            cmd = cmd[:-1]
        cmd = cmd.format(*args).encode("ascii")
        cmd += self.NXEOL
        if self.address:
            cmd = struct.pack("<H", self.address) + cmd
        self.ser.write(cmd)

    def ack(self):
        if not self.ser.read_until(self.NXACK):
            raise Exception("Acknowledge (0x05) not received.")

    def getTFTProperties(self, tftFilePath):
        with open(tftFilePath, "rb") as f:
            headers = f.read(0x190)
        modelCRC = struct.unpack_from("<I", headers, 0x2e)[0]
        fileSize = struct.unpack_from("<I", headers, 0x3c)[0]
        userCodeOffset = struct.unpack_from("<I", headers, 0xdc)[0] ^ self.modelData[modelCRC]["xorKey"]
        return self.modelData[modelCRC]["modelName"], fileSize, userCodeOffset

    def upload(self, tftFilePath):
        tftModel, fileSize, userCodeOffset = self.getTFTProperties(tftFilePath)
        if not self.model.startswith(tftModel):
            raise Exception("Cannot upload {} TFT file to {} device.".format(tftModel, self.model))

        if not self.connected:
            if not self.connect():
                raise Exception("Cannot connect to device.")

        self.sendCmd("dims=0")
        self.sendCmd("sleep=0")
        self.ser.reset_input_buffer()

        self.sendCmd("whm-wris", fileSize, self.uploadSpeed, 1)
        self.ser.close()
        self.ser.baudrate = self.uploadSpeed
        self.ser.timeout  = 0.500
        try:
            self.ser.open()
        except:
            raise Exception("Cannot reopen port at upload baudrate.")
        self.ack()

        blockSize = 4096
        remainingBlocks = ceil(fileSize / blockSize)
        firstBlock = True

        with open(tftFilePath, "rb") as f:
            while remainingBlocks:
                self.ser.write(f.read(blockSize))

                if firstBlock:
                    firstBlock = False
                    skip = self.ser.read(len(self.NXEOL))
                    if not skip:
                        raise Exception("First block acknowledge (0x08) not received.")
                    elif skip == self.NXSKP:
                        f.seek(userCodeOffset)
                        remainingBlocks = ceil((fileSize - userCodeOffset) / blockSize)
                else:
                    self.ack()


if __name__ == "__main__":
    nxu = Nexus()
    nxu.upload("example.tft")
    print("done")
