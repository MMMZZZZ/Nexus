# Nexus

## Description

**Important info** currently this script does not work reliably for some baudrates. I'm still investigating the issue. If you got any ideas about why, let me know!

Nexus - short for **Nex**tion **U**pload **S**cript - is a python script that allows the upload of TFT files to a Nextion screen over serial. Unlike most other scripts out there this one uses the Nextion Upload Protocol v1.2. This is the newer version used by the Nextion Editor itself that allows skipping parts of the TFT file if those have not been modified. 

Nextion never published any details about this newer version but it's been [reverse-engineered and documented](https://unofficialnextion.com/t/nextion-upload-protocol-v1-2-the-fast-one/1044).

If you happen to have a device so old that it doesn't support this new upload protocol, the script will automatically fall back to the well-known v1.1. 

## Requirements

* [Python 3](https://www.python.org/downloads/) (3.9 or higher recommended)
* [PySerial](https://pypi.org/project/pyserial/)

## Usage

Complete documentation of the command line options is available using

```
python Nexus.py -h
```

To upload a file at 512000baud/s type

```
python Nexus.py -i PATH_TO_YOUR_TFT_FILE -u 512000
```

The script will automatically scan all available ports for a Nextion screen. You can manually specify a port using `-p PORT`. To list all available ports use 

```
python Nexus.py -l
```

## Troubleshooting

If you get an error like `Expected acknowledge (b'\x05'), got b''.` it means that Nextion did not respond as expected or not at all. Most likely reasons are a wrong model (TFT file has been compiled for another model) or a too high baudrate.
