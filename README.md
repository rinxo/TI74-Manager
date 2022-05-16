# TI74-Manager
This is my first PYTHON programme, I have done my best for a simple User Interface.

To communicate the fashion TI74 Basicalc and the modern PCs. 

The communication can be done through the CASSETTE interface or the ARDUINO Leonardo.
The software converts between the different file format as needed:

CASSETTE <---> RAW DATA <---> CBASIC <---> BASIC TEXT

The arrows represents the conversion direction. Where:
  - CASSETTE: Wave format file as recorded. Natural format from CAS Interface (extension:*.wav). 
  - RAW DATA: The Wave data conveted to bits as a collection of bytes. Natural format from ARDUINO (extension:*.r74)
  - CBASIC: Compressed BASIC format, it is a cleaning of the RAW data, removing the syncro blocks, check sums and duplicated data (extension:*.c74).
  - BASIC: Basic TEXT file (extensions:*.bas *.b74).
It has the alternative to save in any of the mentioned above file formats.
For ARDUINO Leonardo, please refer to:https://github.com/molleraj/ti95interface get the instructions.

Use TI-74-Main.py to execute the main program.

Give a try and let me know your issues.
