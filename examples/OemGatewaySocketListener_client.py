# This script demonstrates how to communicate with an 
# OemGatewaySocketListener

# The listener expects frames or the form 
#
# NodeID val1 val2 ...
#
# ended by \r\n.

import socket

##############
# Parameters #
##############

# HOST: hosname or IP address of the machine running the gateway
HOST = 'raspberrypi'
#HOST = '192.168.1.2'

# PORT: port number to the listener, as configured in the gateway
PORT = 50011

#########
# Frame #
#########

#frame = 'NodeID val1 val2'
frame = '15 69 1664'

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

