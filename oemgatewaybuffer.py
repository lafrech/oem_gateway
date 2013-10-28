"""

  This code is released under the GNU Affero General Public License.
  
  OpenEnergyMonitor project:
  http://openenergymonitor.org

"""

import urllib2, httplib
import time
import logging

"""class OemGatewayBuffer

Stores server parameters and buffers the data between two HTTP requests

This class is meant to be inherited by subclasses specific to their 
destination server.

"""
class OemGatewayBuffer(object):

    def __init__(self):
        """Create a server data buffer."""
        
        # Initialize logger
        self._log = logging.getLogger("OemGateway")
        
        # Initialize variables
        self._data_buffer = []
        self._last_send = time.time()
        self._settings = {}
        
    def set(self, **kwargs):
        """Update settings.
        
        **kwargs (dict): settings to be modified.
        
        domain (string): domain name (eg: 'domain.tld')
        path (string): emoncms path with leading slash (eg: '/emoncms')
        apikey (string): API key with write access
        period (string): sending interval in seconds
        active (string): whether the data buffer is active (True/False)
        
        """

        for key, value in kwargs.iteritems():
            self._settings[key] = value

    def add(self, data):
        """Append data to buffer.

        data (list): node and values (eg: '[node,val1,val2,...]')

        """
       
        # Check buffer is active
        if self._settings['active'] == 'False':
            return
        
        # Timestamp = now
        timestamp = round(time.time(),2)
        
        self._log.debug("Server " + 
                           self._settings['domain'] + self._settings['path'] + 
                           " -> buffer data: " + str(data) + 
                           ", timestamp: " + str(timestamp))
        
        # Append data set [timestamp, [node, val1, val2, val3,...]] 
        # to _data_buffer
        self._data_buffer.append([timestamp, data])

    def _send_data(self):
        """Send data to server.

        return True if data sent correctly
        
        To be implemented in subclass.

        """
        pass

    def flush(self):
        """Send data in buffer, if any."""
        
        # Check buffer is active
        if self._settings['active'] == 'False':
            return
        
        # Check sending period
        if (time.time() - self._last_send < int(self._settings['period'])):
            return
        
        # If data buffer not empty, send data
        if self._data_buffer != []:
            self._log.debug("Server " + self._settings['domain'] + 
                            self._settings['path'] + " -> flush buffer")
            
            self._send_data()
        
        # Update time of last data sending
        self._last_send = time.time()
        
        # If buffer size reaches maximum, trash oldest values
        # TODO: optionnal write to file instead of losing data
        MAX_DATA_SETS_IN_BUFFER = 1000
        size = len(self._data_buffer)
        if size > MAX_DATA_SETS_IN_BUFFER:
            self._data_buffer = \
                self._data_buffer[size - MAX_DATA_SETS_IN_BUFFER:]

"""class OemGatewayEmoncmsBuffer

Stores server parameters and buffers the data between two HTTP requests

"""
class OemGatewayEmoncmsBuffer(OemGatewayBuffer):

    def _send_data(self):
        """Send data to server."""
       
        # Do not send more than 100 datasets each time (totally arbitrary)
        MAX_DATA_SETS_PER_POST = 100
        data_to_send = self._data_buffer[0:MAX_DATA_SETS_PER_POST]
        data_to_keep = self._data_buffer[MAX_DATA_SETS_PER_POST:]

        # Prepare data string with the values in data buffer
        now = time.time()
        data_string = '[' 
        for (timestamp, data) in data_to_send:
            data_string += '['
            data_string += str(round(timestamp-now,2))
            for sample in data:
                data_string += ','
                data_string += str(sample)
            data_string += '],'
        # Remove trailing comma and close bracket
        data_string = data_string[0:-1]+']'

        self._log.debug("Data string: " + data_string)
        
        # Prepare URL string of the form
        # 'http://domain.tld/emoncms/input/bulk.json?apikey=
        # 12345&data=[[-10,10,1806],[-5,10,1806],[0,10,1806]]'
        url_string = self._settings['protocol'] + self._settings['domain'] + \
                     self._settings['path'] + "/input/bulk.json?apikey=" + \
                     self._settings['apikey'] + "&data=" + data_string
        self._log.debug("URL string: " + url_string)

        # Send data to server
        self._log.info("Sending to " + 
                          self._settings['domain'] + self._settings['path'])
        try:
            result = urllib2.urlopen(url_string, timeout=60)
        except urllib2.HTTPError as e:
            self._log.warning("Couldn't send to server, HTTPError: " + 
                                 str(e.code))
        except urllib2.URLError as e:
            self._log.warning("Couldn't send to server, URLError: " + 
                                 str(e.reason))
        except httplib.HTTPException:
            self._log.warning("Couldn't send to server, HTTPException")
        except Exception:
            import traceback
            self._log.warning("Couldn't send to server, Exception: " + 
                                 traceback.format_exc())
        else:
            if (result.readline() == 'ok'):
                self._log.debug("Send ok")
                # Send ok -> empty buffer
                self._data_buffer = data_to_keep
                return True
            else:
                self._log.warning("Send failure")
        
