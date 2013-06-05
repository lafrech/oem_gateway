"""

  This code is released under the GNU Affero General Public License.
  
  OpenEnergyMonitor project:
  http://openenergymonitor.org

"""

import serial
import time, datetime
import logging
import re

"""class OemGatewayListener

Monitors a data source. 

This almost empty class is meant to be inherited by subclasses specific to
their data source.

"""
class OemGatewayListener(object):

    def __init__(self, logger=None):
        
        # Initialize logger
        self._logger = logging.getLogger(logger)
        
    def open_socket(self):
        """Open socket to read data from.
        
        Returns True in case of success, False in case of failure.
        
        """
        pass

    def close(self):
        """Close socket."""
        pass

    def read(self):
        """Read data from socket.

        Returns True if full line read

        """
        pass

    def process(self):
        """Process data in buffer.
        
        Returns a set of values as a list [NodeID, val1, val2]
        
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

    def __init__(self, logger = None):
        
        # Initialization
        super(OemGatewayRFM2PiListener, self).__init__(logger=logger)

        # Serial port
        self._ser = None

        # Initialize RX buffer
        self._rx_buf = ''

        # Initialize settings
        self._settings = {'baseid': '', 'frequency': '', 'sgroup': '', 
            'sendtimeinterval': ''}
        
        # Initialize time updata timestamp
        self._time_update_timestamp = 0

    def open_socket(self):
        """Open socket to read data from."""

        self._logger.debug("Opening serial port: /dev/ttyAMA0")
        
        try:
            self._ser = serial.Serial('/dev/ttyAMA0', 9600, timeout = 0)
        except serial.SerialException as e:
            self._logger.error(e)
            return False
        except Exception:
            import traceback
            self._logger.error(
                "Couldn't open serial port, Exception: " 
                + traceback.format_exc())
            return False
        
        return True

    def close(self):
        """Close socket."""
        
        # Close serial port
        if self._ser is not None:
            self._logger.debug("Closing serial port.")
            self._ser.close()

    def read(self):
        """Read data from socket.

        Returns True if full line read

        """
        
        # Read serial RX
        self._rx_buf = self._rx_buf + self._ser.readline()
        
        # If full line was read, return True
        if ((self._rx_buf != '') and 
            (self._rx_buf[len(self._rx_buf)-1] == '\n')):
                return True

    def process(self):

        # Remove CR,LF
        self._rx_buf = re.sub('\\r\\n', '', self._rx_buf)
        
        # Log data
        self._logger.info("Serial RX: " + self._rx_buf)
        
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
            self._logger.warning("Misformed RX frame: " + str(received))
        
        # Else, process frame
        else:
            try:
                received = [int(val) for val in received]
            except Exception:
                self._logger.warning("Misformed RX frame: " + str(received))
            else:
                # Get node ID
                node = received[0]
                
                # Recombine transmitted chars into signed int
                values = []
                for i in range(1,len(received),2):
                    value = received[i] + 256 * received[i+1]
                    if value > 32768:
                        value -= 65536
                    values.append(value)
                
                self._logger.debug("Node: " + str(node))
                self._logger.debug("Values: " + str(values))
    
                # Add data to send buffers
                values.insert(0,node)

                return values

    def set(self, **kwargs):
        """Send configuration parameters to the RFM2Pi through COM port.

        **kwargs (dict): settings to be sent. Available settings are
        'baseid', 'frequency', 'sgroup'. Example: 
        {'baseid': '15', 'frequency': '4', 'sgroup': '210'}
        
        """
        
        for key, value in kwargs.iteritems():
            # If radio setting modified, transmit on serial link
            if key in ['baseid', 'frequency', 'sgroup']:
                if value != self._settings[key]:
                    self._settings[key] = value
                    self._logger.info("Setting RFM2Pi | %s: %s" % (key, value))
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
                    self._settings[key] = value
                    self._logger.debug("Send time interval is now %s", value)

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

        self._logger.debug("Broadcasting time: %d:%d" % (now.hour, now.minute))

        self._ser.write("%02d,00,%02d,00,s" % (now.hour, now.minute))

