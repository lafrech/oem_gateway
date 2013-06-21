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
        """Create a server data buffer initialized with server settings."""
        
        # Initialize logger
        self._log = logging.getLogger("OemGateway")
        
        # Initialize variables
        # self._data_buffer = []
        self._settings = {}
        
    def set(self, **kwargs):
        """Update settings.
        
        **kwargs (dict): settings to be modified.
        
        domain (string): domain name (eg: 'domain.tld')
        path (string): emoncms path with leading slash (eg: '/emoncms')
        apikey (string): API key with write access
        active (string): whether the data buffer is active (True/False)
        
        """

        for key, value in kwargs.iteritems():
            self._settings[key] = value

    def send(self, data):
        """Send data to server.

        TODO: In case of send error, buffer data to retry later.

        data (list): node and values (eg: '[node,val1,val2,...]')

        """
       
        if not bool(self._settings['active']):
            return
        
        self._log.debug("Server " + 
                           self._settings['domain'] + self._settings['path'] + 
                           " -> send data: " + str(data))
        
        # Distinct copy: we don't want to modify data
        datacopy = list(data) 
        
        # Try to send data, if failure, store to resend later
        self.send_data(datacopy)
        # TODO: 
        # - detect failure, store data in buffer array
        # - retry sending and flush buffer regularly
        # - write to file when buffer size too big
        #if not self.send_data(datacopy):
            # Insert timestamp before data
            # datacopy.insert(0,time.time())
            # Append data set [timestamp, node, val1, val2, val3,...] 
            # to _data_buffer
            # self._data_buffer.append(datacopy)

    def send_data(self, data):
        """Send data to server.

        data (list): node and values (eg: '[node,val1,val2,...]')

        return True if data sent correctly
        
        To be implemented in subclass.

        """
        pass


"""class OemGatewayEmoncmsBuffer

Stores server parameters and buffers the data between two HTTP requests

"""
class OemGatewayEmoncmsBuffer(OemGatewayBuffer):

    def send_data(self, data):
        """Send data to server."""
        
        # Prepare data string with the values in data buffer
        # Node ID
        data_string = 'node=' + str(data[0]) + '&json={'
        # Data
        for i, val in enumerate(data[1:]):
            data_string += str(i+1) + ':' + str(val)
            data_string += ','
        # Remove trailing comma and close braces
        data_string = data_string[0:-1]+'}'
        self._log.debug("Data string: " + data_string)
        
        # Prepare URL string of the form
        # 'http://domain.tld/emoncms/input/post.json?apikey=12345
        # &node=10&json={1:1806, 2:1664}'
        url_string = self._settings['protocol'] + self._settings['domain'] + \
                     self._settings['path'] + '/input/post.json?apikey=' + \
                     self._settings['apikey'] + '&' + data_string
        self._log.debug("URL string: " + url_string)

        # Send data to server
        self._log.info("Sending to " + 
                          self._settings['domain'] + self._settings['path'])
        try:
            result = urllib2.urlopen(url_string)
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
                return True
            else:
                self._log.warning("Send failure")
        
