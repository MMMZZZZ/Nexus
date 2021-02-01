# Nexus

## Description

Nexus - short for **Nex**tion **U**pload **S**cript - is a python script that allows the upload of TFT files to a Nextion screen over serial. Unlike most other scripts out there this one uses the Nextion Upload Protocol v1.2. This is the newer version used by the Nextion Editor itself that allows skipping parts of the TFT file if those have not been modified. 

Nextion will probably never publish any details about this newer version because it requires some knowledge about the TFT file format (obviously you need to know what part you should skip). However, it's been [reverse-engineered and documented](https://unofficialnextion.com/t/nextion-upload-protocol-v1-2-the-fast-one/1044).

## Usage

### Requirements

* [Python 3](https://www.python.org/downloads/) (3.9 or higher recommended)
* [PySerial](https://pypi.org/project/pyserial/)

### Command Line Arguments

Complete documentation of the command line options is available using

```
python Nexus.py -h
```

To upload a file at 512000baud/s type

```
pyhton Nexus.py -i PATH_TO_YOUR_TFT_FILE -u 512000
```

The script will automatically scan all available ports for a Nextion screen. You can manually specify a port using `-p PORT`. To list all available ports use 

```
python Nexus.py -l
```
