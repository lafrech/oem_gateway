"""

  This code is released under the GNU Affero General Public License.
  
  OpenEnergyMonitor project:
  http://openenergymonitor.org

"""

import serial
import time, datetime
import logging
import socket, select

"""class OemGatewayListener

Monitors a data source. 

This almost empty class is meant to be inherited by subclasses specific to
their data source.

"""
class OemGatewayListener(object):

    def __init__(self):
        
        # Initialize logger
        self._log = logging.getLogger("OemGateway")
        
    def close(self):
        """Close socket."""
        pass

    def read(self):
        """Read data from socket and process if complete line received.

        Return data as a list: [NodeID, val1, val2]
        
        """
        pass

    def set(self, **kwargs):
        """Set configuration parameters.

        **kwargs (dict): settings to be sent. Example:
        {'setting_1': 'value_1', 'setting_2': 'value_2'}
        
        """
        pass

    def run(self):
        """Placeholder for background tasks. 
        
        Allows subclasses to specify actions that need to be done on a 
        regular basis. This should be called in main loop by instantiater.
        
        """
        pass



"""class OemGatewayRFM2PiListener

Monitors the serial port for data from RFM2Pi

"""
class OemGatewayRFM2PiListener(OemGatewayListener):

    def __init__(self, com_port):
        
        # Initialization
        super(OemGatewayRFM2PiListener, self).__init__()

        # Serial port
        self._log.debug('Opening serial port: %s', com_port)
        
        try:
            self._ser = serial.Serial(com_port, 9600, timeout = 0)
        except serial.SerialException as e:
            self._log.error(e)
            raise OemGatewayListenerInitError('Could not open COM port %s' %
                                              com_port)
        # Initialize RX buffer
        self._rx_buf = ''

        # Initialize settings
        self._settings = {'baseid': '', 'frequency': '', 'sgroup': '', 
            'sendtimeinterval': ''}
        
        # Initialize time updata timestamp
        self._time_update_timestamp = 0

    def close(self):
        """Close socket."""
        
        # Close serial port
        if self._ser is not None:
            self._log.debug("Closing serial port.")
            self._ser.close()

    def read(self):
        """Read data from socket and process if complete line received.

        Return data as a list: [NodeID, val1, val2]
        
        """
        
        # Read serial RX
        self._rx_buf = self._rx_buf + self._ser.readline()
        
        # If line incomplete, exit
        if '\r\n' not in self._rx_buf:
            return

        # Otherwise, process line:

        # Remove CR,LF
        self._rx_buf = self._rx_buf[:-2]
        
        # Log data
        self._log.info("Serial RX: " + self._rx_buf)
        
        # Get an array out of the space separated string
        received = self._rx_buf.strip().split(' ')
        
        # Empty serial_rx_buf
        self._rx_buf = ''
        
        # If information message, discard
        if ((received[0] == '>') or (received[0] == '->')):
            return

        # Else, discard if frame not of the form 
        # [node val1_lsb val1_msb val2_lsb val2_msb ...]
        # with number of elements odd and at least 3
        elif ((not (len(received) & 1)) or (len(received) < 3)):
            self._log.warning("Misformed RX frame: " + str(received))
        
        # Else, process frame
        else:
            try:
                received = [int(val) for val in received]
            except Exception:
                self._log.warning("Misformed RX frame: " + str(received))
            else:
                # Get node ID
                node = received[0]
                
                # Recombine transmitted chars into signed int
                values = []
                for i in range(1, len(received),2):
                    value = received[i] + 256 * received[i+1]
                    if value > 32768:
                        value -= 65536
                    values.append(value)
                
                self._log.debug("Node: " + str(node))
                self._log.debug("Values: " + str(values))
    
                # Insert node ID before data
                values.insert(0, node)

                return values

    def set(self, **kwargs):
        """Send configuration parameters to the RFM2Pi through COM port.

        **kwargs (dict): settings to be modified. Available settings are
        'baseid', 'frequency', 'sgroup'. Example: 
        {'baseid': '15', 'frequency': '4', 'sgroup': '210'}
        
        """
        
        for key, value in kwargs.iteritems():
            # If radio setting modified, transmit on serial link
            if key in ['baseid', 'frequency', 'sgroup']:
                if value != self._settings[key]:
                    self._settings[key] = value
                    self._log.info("Setting RFM2Pi | %s: %s" % (key, value))
                    string = value
                    if key == 'baseid':
                        string += 'i'
                    elif key == 'frequency':
                        string += 'b'
                    elif key == 'sgroup':
                        string += 'g'
                    self._ser.write(string)
                    # Wait a sec between two settings
                    time.sleep(1)
            elif key == 'sendtimeinterval':
                if value != self._settings[key]:
                    self._log.info("Setting send time interval to %s", value)
                    self._settings[key] = value

    def run(self):
        """Actions that need to be done on a regular basis. 
        
        This should be called in main loop by instantiater.
        
        """

        now = time.time()

        # Broadcast time to synchronize emonGLCD
        interval = int(self._settings['sendtimeinterval'])
        if (interval): # A value of 0 means don't do anything
            if (now - self._time_update_timestamp > interval):
                self._send_time()
                self._time_update_timestamp = now
    
    def _send_time(self):
        """Send time over radio link to synchronize emonGLCD.

        The radio module can be used to broadcast time, which is useful
        to synchronize emonGLCD in particular.
        Beware, this is know to garble the serial link on RFM2Piv1
        sendtimeinterval defines the interval in seconds between two time
        broadcasts. 0 means never.

        """

        now = datetime.datetime.now()

        self._log.debug("Broadcasting time: %d:%d" % (now.hour, now.minute))

        self._ser.write("%02d,00,%02d,00,s" % (now.hour, now.minute))

"""class OemGatewaySocketListener

Monitors a socket for data, typically from ethernet link

"""
class OemGatewaySocketListener(OemGatewayListener):

    def __init__(self, port_nb):
        
        # Initialization
        super(OemGatewaySocketListener, self).__init__()

        # Open socket
        self._log.debug('Opening socket on port %s', port_nb)
        
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.bind(('', int(port_nb)))
            self._socket.listen(1)
        except socket.error as e:
            self._log.error(e)
            raise OemGatewayListenerInitError('Could not open port %s' %
                                            port_nb)
        # Initialize RX buffer
        self._rx_buf = ''

    def close(self):
        """Close socket."""
        
        # Close socket
        if self._socket is not None:
           self._log.debug('Closing socket')
           self._socket.close()

    def read(self):
        """Read data from socket and process if complete line received.

        Return data as a list: [NodeID, val1, val2]
        
        """
        
        # Check if data received
        ready_to_read, ready_to_write, in_error = \
            select.select([self._socket], [], [], 0)

        # If data received, add it to RX buffer
        if self._socket in ready_to_read:

            # Accept connection
            conn, addr = self._socket.accept()
            
            # Read data
            self._rx_buf = self._rx_buf + conn.recv(1024)
            
            # Close connection
            conn.close()

        # If no complete frame, exit
        if '\r\n' not in self._rx_buf:
            return

        # Otherwise, process first frame in buffer:
        f, self._rx_buf = self._rx_buf.split('\r\n', 1)

        # Log data
        self._log.info("Serial RX: " + f)
        
        # Get an array out of the space separated string
        received = f.strip().split(' ')
        
        # Discard if frame not of the form [node val1 ...]
        # with number of elements at least 2
        if (len(received) < 2):
            self._log.warning("Misformed RX frame: " + str(received))
        
        # Else, process frame
        else:
            try:
                received = [int(val) for val in received]
            except Exception:
                self._log.warning("Misformed RX frame: " + str(received))
            else:
                self._log.debug("Node: " + str(received[0]))
                self._log.debug("Values: " + str(received[1:]))
                return received

"""class OemGatewayListenerInitError

Raise this when init fails.

"""
class OemGatewayListenerInitError(Exception):
    pass

