"""

  This code is released under the GNU Affero General Public License.
  
  OpenEnergyMonitor project:
  http://openenergymonitor.org

"""

import urllib2, httplib
import time
import logging
import oemgatewaydispatchbuffer as ogdb
  
"""class OemGatewayDispatcher

Stores server parameters and buffers the data between two HTTP requests

This class is meant to be inherited by subclasses specific to their 
destination server.

"""
class OemGatewayDispatcher(object):

    def __init__(self, dispatcherName, bufferMethod="memory", **kwargs):
        """Create a server data buffer initialized with server settings."""
        
        # Initialize logger
        self._log = logging.getLogger("OemGateway")

        # Initialize variables
        self._settings = {}
        
        # Create underlying buffer implementation
        self.buffer = getattr(ogdb, ogdb.AbstractBuffer.bufferMethodMap[bufferMethod])(dispatcherName, **kwargs)
        
        self._log.info ("Set up dispatcher '%s' (buffer: %s)" % (dispatcherName, bufferMethod))
        
    def set(self, **kwargs):
        """Update settings.
        
        **kwargs (dict): settings to be modified.
        
        domain (string): domain name (eg: 'domain.tld')
        path (string): emoncms path with leading slash (eg: '/emoncms')
        apikey (string): API key with write access
        active (string): whether the dispatcher is active (True/False)
        
        """

        for key, value in kwargs.iteritems():
            self._settings[key] = value

    def add(self, data):
        """Append data to buffer.

        data (list): node and values (eg: '[node,val1,val2,...]')

        """
       
        if self._settings['active'] == 'False':
            return
        
        # Timestamp = now
        t = round(time.time(),2)
        
        self._log.debug("Server " + 
                           self._settings['domain'] + self._settings['path'] + 
                           " -> buffer data: " + str(data) + 
                           ", timestamp: " + str(t))
               
        self.buffer.storeItem([t, data])

    def _send_data(self, data, time):
        """Send data to server.

        data (list): node and values (eg: '[node,val1,val2,...]')
        time (int): timestamp, time when sample was recorded

        return True if data sent correctly
        
        To be implemented in subclass.

        """
        pass

    def flush(self):
        """Send oldest data in buffer, if any."""
        
        # Buffer management
        # If data buffer not empty, send a set of values
        if (self.buffer.hasItems()):
            time, data = self.buffer.retrieveItem()
            self._log.debug("Server " + 
                           self._settings['domain'] + self._settings['path'] + 
                           " -> send data: " + str(data) + 
                           ", timestamp: " + str(time))
            if self._send_data(data, time):
                # In case of success, delete sample set from buffer
                self.buffer.discardLastRetrievedItem()

"""class OemGatewayEmoncmsDispatcher

Stores server parameters and buffers the data between two HTTP requests

"""
class OemGatewayEmoncmsDispatcher(OemGatewayDispatcher):

    def _send_data(self, data, time):
        """Send data to server."""
        
        # Prepare data string with the values in data buffer
        data_string = ''
        # Timestamp
        data_string += '&time=' + str(time)
        # Node ID
        data_string += '&node=' + str(data[0])
        # Data
        data_string += '&json={'
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
                     self._settings['apikey'] + data_string
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
                return True
            else:
                self._log.warning("Send failure")
        
