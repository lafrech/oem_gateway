# This script demonstrates how to communicate with an 
# OemGatewayRFM2PiListenerRepeater

# Frames are repeated to the RFM2Pi board. 
# The typical application is to send a data frame to a Node on the RF network.
# It could also be used to configure the RFM2Pi board.

import socket

##############
# Parameters #
##############

# HOST: hosname or IP address of the machine running the gateway
HOST = 'raspberrypi'
#HOST = '192.168.1.2'

# PORT: port number to the listener, as configured in the gateway
PORT = 50012

#########
# Frame #
#########

#frame = 'Enter your frame here'
# The following example frame sets the RF frequency to 433 MHz
frame = '4b'

########
# Code #
########

# Append line ending
frame = frame + '\r\n'

# Send frame
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
s.send(frame)
s.close()

