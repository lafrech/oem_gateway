OemGateway
==========

This software is part of OpenEnergyMonitor project.

It runs as a gateway from one or more data sources (listeners)
to one or more target databases (buffers). See below for the description
of existing listeners and buffers.

## Installation

### Install dependencies

This software depends on:

* python-serial for the serial port management
* python-configobj for the config file parsing

    sudo aptitude install python-serial python-configobj

### Make oemgateway executable

    chmod +x oemgateway

The gateway can be run with no argument

    ./oemgateway

For help on command line arguments

    ./oemgateway --help 

### Run as a daemon (optionnal)

#### Grant write privilege to logging file (skip if logging is not used)

Create groupe emoncms and make user pi part of it 
   
    sudo groupadd emoncms 
    sudo usermod -a -G emoncms pi

Create a directory for the logfile and give ownership to user pi, group emoncms

    sudo mkdir /var/log/oemgateway
    sudo chown pi:emoncms /var/log/oemgateway
    sudo chmod 750 /var/log/oemgateway

#### Make script run as daemon on startup

Copy and customize init script
    
    sudo cp oemgateway.init.dist /etc/init.d/oemgateway
    sudo vi /etc/init.d/oemgateway # Customize init script: path, command line arguments
    sudo chmod 755 /etc/init.d/oemgateway

The gateway can be started or stopped anytime with following commands:

    sudo /etc/init.d/oemgataway start
    sudo /etc/init.d/oemgataway stop
    sudo /etc/init.d/oemgataway restart

To run automatically on startup

    sudo update-rc.d oemgateway defaults 99

To stop running automatically on startup

    sudo update-rc.d -f oemgateway remove

## Configuration

### Configuration parameters

The gateway can be paramterized through a config file or through emoncms GUI.

#### emoncms GUI

To use the emoncms GUI, use --config-emoncms to specify an URL.

E.g., --config-emoncms http://localhost/emoncms/

#### Configuration file

Use --config-file argument to specify a file path.

To create a config file, copy oemgateway.conf.dist and customize.

See decription of the listeners and buffer below for help on the parameters.

If no flag is passed, default is to search for oemgateway.conf.

The --show-settings lets oemgateway output the settings for verification.

### Logging

Logging can be output to a file or on the standard output (default). 
To log to a file, use the --logfile argument to specify a file path.

The logging level is a config parameter.

## Under the hood: listeners and buffers

Listerners and buffers are classes that are instanciated by the gateway.

Listeners manage data inputs and forward data to buffers. Buffers send data to processing/display applications.

The gateway links one or more listeners to one or more buffers.

### Listeners

Listeners derive the OemGatewayListener class:

    OemGatewayListener
      |
      |-- OemGatewaySerialListener
      |     |
      |     |-- OemGatewayRFM2PiListener
      |           |
      |           |-- OemGatewayRFM2PiListenerRepeater
      |
      |-- OemGatewaySocketListener

#### OemGatewaySerialListener 

Receives data on the serial port.

##### Init settings

* com_port: path to the COM port (e.g. /dev/ttyAMA0)

##### Runtime settings

None

#### OemGatewayRFM2PiListener 

Receives data on the serial port through the RFM2Pi module.

##### Init settings

* com_port: path to the COM port (e.g. /dev/ttyAMA0)

##### Runtime settings

RFM settings:
* sgroup
* frequency
* baseid

* sendtimeinterval: if not 0, period in seconds. The gateway will send time 
on the radio link with this period, for other devices, typically emonGLCD.

#### OemGatewayRFM2PiListenerRepeater

Receives data on the serial port through the RFM2Pi module, and transmits 
messages received throught a socket on the RF link.

Note that neither acknowledgement nor authentication is implemented.

##### Init settings

* com_port: path to the COM port (e.g. /dev/ttyAMA0)
* port_nb: port number

##### Runtime settings

Same as OemGatewayRFM2PiListener

#### OemGatewaySocketListener

Receives data through a socket. From another machine on the network or from 
another application on the same host.

Note that neither acknowledgement nor authentication is implemented.

##### Init settings

* port_nb: port number

##### Runtime settings

None

### Buffers

Buffers derive the OemGatewayBuffer class.

    OemGatewayBuffer
      |
      |-- OemGatewayEmoncmsBuffer

#### OemGatewayEmoncmsBuffer

Send data to an emoncms server. If connection is lost, the data is buffered
until the network is up again.

##### Init settings

None

##### Runtime settings

* protocol: http:// or https://
* domain (e.g. emoncms.org)
* path (e.g. /emoncms)
* apikey
* active: if False, neither record nor send data, but hold unsent data.

