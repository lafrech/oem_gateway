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

The gateway can be paramterized through a config file or through emoncms API.

### emoncms API

To use the emoncms API, pass the --config-emoncms flag.

### Configuration file

To use a config file, pass  --config-file CONFIG_FILE.

To create a config file, copy oemgateway.conf.dist and customize.

See decription of the listeners and buffer below for help on the parameters.

If no flag is passed, default is to search for oemgateway.conf.

The --show-settings lets oemgateway output the settings for verification.

## Logging

Logging can be output to a file or on the standard output. To log to a file, 
use the --logfile argument to specify a file path.

The logging level is a config parameter.

# Listeners

Listeners derive the OemGatewayListener class.

## OemGatewayRFM2PiListener 

Receives data on the serial port through the RFM2Pi module.

### Init settings

com_port

### Runtime settings

RFM settings:
* sgroup
* frequency
* baseid

sendtimeinterval: if not 0, period in seconds. The gateway will send time 
on the radio link to other devices, typically emonGLCD.

## OemGatewaySocketListener

Receives date through a socket. From another machine on the network or from 
another application on the same host.

Note that no authentification is implemented.

### Init settings

port_nb: port number

### Runtime settings

None

# Buffers

Buffers derive the OemGatewayBuffer class.

## OemGatewayEmoncmsBuffer

Send data to an emoncms server. If connection is lost, the data is buffered
until the network is up again.

### Init settings

None

### Runtime settings

Runtime settings are:
* protocol: http:// or https://
* domain (e.g. emoncms.org)
* path (e.g. /emoncms)
* apikey
* active: if False, neither record nor send data, but hold unsent data.

