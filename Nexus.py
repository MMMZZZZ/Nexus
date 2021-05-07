"""
Nexus - Nextion Upload Script by Max Zuidberg

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import argparse
import struct
import time
import serial
from serial.tools.list_ports import comports as availablePorts
from pathlib import Path
from math import ceil


class Nexus:
    NXEOL = b"\xff\xff\xff"
    NXACK = b"\x05"
    NXSKP = b"\x08"

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
                self.ports = [port]

        self.ser  = serial.Serial()
        if connect:
            if not self.connect():
                raise Exception("Cannot connect to device.")

    def connect(self):
        # Time to check baudrate is proportional to 1/baudrate. Therefore reversing the list leads on
        # average to a faster connection (with 115200 it is "instant" instead of ~1s).
        defaultSpeeds = [2400, 4800, 9600, 19200, 31250, 38400, 57600, 74880, 115200, 230400,
                                  250000, 256000, 460800, 500000, 512000, 921600]
        defaultSpeeds.reverse()
        if self.connectSpeed:
            if self.connectSpeed in defaultSpeeds:
                defaultSpeeds.remove(self.connectSpeed)
            defaultSpeeds.insert(0, self.connectSpeed)

        for port in self.ports:
            print("Scanning port " + port)
            for speed in defaultSpeeds:
                print("  at {}baud/s... ".format(speed), end="")
                self.ser.close()
                self.ser.port = port
                self.ser.baudrate = speed
                self.ser.timeout  = 1000/speed + 0.030
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
                    print("Failed (Got \"{}\").".format(data))
                    continue
                self.ser.write(self.NXEOL)
                self.ser.read(42)
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
                if not self.model:
                    raise Exception("Invalid model! Data: {}".format(data))
                if not self.uploadSpeed:
                    self.uploadSpeed = self.connectSpeed
                print("Success.\n")
                d = {"Model": self.model, "Flash Size": self.flashSize, "Address": self.address,
                     "Firmware Version": self.fwVersion, "MCU Code": self.mcuCode, "Serial Number:": self.serialNum}
                maxLen = max([len(k) for k in d.keys()]) + 1
                for k,v in d.items():
                    k += ":"
                    print(k.ljust(maxLen, " "), v)
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

    def ack(self, a = None):
        if not a:
            a = self.ser.read_until(self.NXACK)
        if not a.endswith(self.NXACK):
            # Prevent overwriting of previous line
            print("")
            raise Exception("Expected acknowledge ({}), got {}.".format(self.NXACK, a))

    def getFileSize(self, tftFilePath):
        with open(tftFilePath, "rb") as f:
            f.seek(0x3c)
            rawSize = f.read(struct.calcsize("<I"))
        fileSize = struct.unpack("<I", rawSize)[0]
        return fileSize

    def upload(self, tftFilePath):
        # Visual separation in the console log
        print("")
        if not self.connected:
            raise Exception("Successful connection required for upload.")

        fileSize = self.getFileSize(tftFilePath)

        self.sendCmd("bs=42") # For some reason the first command after self.connect() always fails. Can be anything.
        self.sendCmd("dims=100")
        self.sendCmd("sleep=0")
        self.ser.reset_input_buffer()

        print("Initiating upload... ", end="")

        # Use v1.2 by default except if the firmware hasn't support for it yet. The actual upload
        # code below works for both v1.2 and v1.1. Only difference is that v1.1 doesn't require a
        # 2s timeout but it doesn't hurt either.
        # Note: v1.2 in its current form was introduced with (TJC) editor version 0.54. But for some
        # reason those firmwares report the same firmware version to a connect command as 0.53
        # (both 155). Therefore I had to increase the minimum firmware version to 126, which
        # corresponds to editor version 0.55. For most Nextion users this shouldn't matter anyways
        # since Nextion skipped all these versions up to 0.58.
        cmd = "whmi-wris"
        if self.fwVersion < 126:
            cmd = "whmi-wri"
            print("\nFirmware doesn't support upload protocol v1.2, using v1.1 instead.")
        self.sendCmd(cmd, fileSize, self.uploadSpeed, 1)
        self.ser.close()
        self.ser.baudrate = self.uploadSpeed
        self.ser.timeout = 2  # Apparently the 0x08 response needs more time than the 0x05 response - about 1s.
        try:
            self.ser.open()
        except:
            raise Exception("Cannot reopen port at upload baudrate.")
        self.ack()
        print("Success.")

        blockSize = 4096
        remainingBlocks = ceil(fileSize / blockSize)
        blocksSent, lastProgress, lastEta = 0, 0, 0
        with open(tftFilePath, "rb") as f:
            startTime = time.time()
            while remainingBlocks:
                self.ser.write(f.read(blockSize))
                remainingBlocks -= 1
                blocksSent += 1

                proceed = self.ser.read(1)
                if proceed == self.NXSKP:
                    offset = self.ser.read(4)
                    if len(offset) != 4:
                        raise Exception("Incomplete offset for skip command (0x08).")
                    offset = struct.unpack("<I", offset)[0]
                    if (offset):
                        # A value of 0 doesn't mean "seek to position 0" but "don't seek anywhere".
                        jumpSize = offset - f.tell()
                        f.seek(offset)
                        remainingBlocks = ceil((fileSize - offset) / blockSize)
                        print("Skipped {} bytes.".format(jumpSize))
                else:
                    self.ack(proceed)

                progress = 100 * f.tell() // fileSize
                eta = ceil((time.time() - startTime) / blocksSent * remainingBlocks)
                if progress != lastProgress or eta != lastEta:
                    lastEta = eta
                    lastProgress = progress
                    eta = "{}m{:02}s".format(eta // 60, eta % 60)
                    print("Progress: {}%  ETA: {}".format(progress, eta), end="\r")


if __name__ == "__main__":
    desc = """Nexus - Nextion Upload Script
              Upload TFT files to your Nextion screen using the advantages of the newer and faster
              upload protocol v1.2. Details at https://bit.do/unuf-nexus  
              Developped by Max Zuidberg, licensed under MPL-2.0"""
    parser = argparse.ArgumentParser(description=desc)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-l", "--list", action="store_true",
                        help="List all available serial ports.")
    group.add_argument("-i", "--input", metavar="TFT_FILE", type=str,
                        help="Path to the TFT file")
    parser.add_argument("-p", "--port", metavar="PORT", type=str, default="",
                        help="Optional serial port to use. By default Nexus scans all ports and uses "
                             "the first one where it finds a Nextion decive. Use -l to list all available "
                             "ports. ")
    parser.add_argument("-c", "--connect", metavar="BAUDRATE", type=int, required=False, default=0,
                        help="Preferred baudrate for the initial connection to the screen. If a connection at this "
                             "baudrate fails or if this argument is not given the script will try a list "
                             "of default baudrates")
    parser.add_argument("-u", "--upload", metavar="BAUDRATE", type=int, required=False, default=0,
                        help="Optional baudrate for the actual upload. If not specified, the baudrate at which the "
                             "connection has been established will be used for the upload, too (can be slow!).")

    args = parser.parse_args()
    ports = [p.name for p in availablePorts()]
    portsStr = ", ".join(ports)
    if args.list:
        print("List of available serial ports:")
        print(portsStr)
        exit()

    ports.append("")
    if args.port not in ports:
        parser.error("Port {} not found among the available ports: {}.".format(args.port, portsStr))

    tftPath = Path(args.input)
    if not tftPath.exists():
        parser.error("Invalid source file!")

    nxu = Nexus(port=args.port, connectSpeed=args.connect, uploadSpeed=args.upload)
    nxu.upload(tftPath)
