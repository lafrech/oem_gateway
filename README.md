OemGateway
==========

This software is part of OpenEnergyMonitor project.

It runs as a gateway from one or more data sources (listeners)
to one or more target databases (buffers). See below for the description
of existing listeners and buffers.

# Usage

Make oemgateway.py executable:

     chmod +x oemgateway.py

Run: 

    ./oemgateway.py

Use 

    ./oemgateway.py --help 

for help on command line arguments.

## Configuration

The gateway can be paramterized through a config file or through emoncms GUI.

### emoncms GUI

To use the emoncms GUI, pass the --config-emoncms flag.

### Configuration file

Use the --config-file argument to specify a file path.

To create a config file, copy oemgateway.conf.dist and customize.

See decription of the listeners and buffer below for help on the parameters.

If no flag is passed, default is to search for oemgateway.conf.

The --show-settings lets oemgateway output the settings for verification.

## Logging

Logging can be output to a file or on the standard output (default). 
To log to a file, use the --logfile argument to specify a file path.

The logging level is a config parameter.

# Listeners

Listeners derive the OemGatewayListener class:

    OemGatewayListener
      |
      |-- OemGatewaySerialListener
      |     |
      |     |-- OemGatewayRFM2PiListener
      |
      |-- OemGatewaySocketListener

## OemGatewaySerialListener 

Receives data on the serial port.

### Init settings

* com_port: path to the COM port (e.g. /dev/ttyAMA0)

### Runtime settings

None

## OemGatewayRFM2PiListener 

Receives data on the serial port through the RFM2Pi module.

### Init settings

* com_port: path to the COM port (e.g. /dev/ttyAMA0)

### Runtime settings

RFM settings:
* sgroup
* frequency
* baseid

* sendtimeinterval: if not 0, period in seconds. The gateway will send time 
on the radio link with this period, for other devices, typically emonGLCD.

## OemGatewaySocketListener

Receives date through a socket. From another machine on the network or from 
another application on the same host.

Note that neither acknowledgement nor authentication is implemented.

### Init settings

* port_nb: port number

### Runtime settings

None

# Buffers

Buffers derive the OemGatewayBuffer class.

    OemGatewayBuffer
      |
      |-- OemGatewayEmoncmsBuffer

## OemGatewayEmoncmsBuffer

Send data to an emoncms server. If connection is lost, the data is buffered
until the network is up again.

### Init settings

None

### Runtime settings

* protocol: http:// or https://
* domain (e.g. emoncms.org)
* path (e.g. /emoncms)
* apikey
* active: if False, neither record nor send data, but hold unsent data.

