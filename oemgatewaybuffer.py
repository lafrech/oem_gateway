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

    def __init__(self, logger=None):
        """Create a server data buffer initialized with server settings.
        
        domain (string): domain name (eg: 'domain.tld')
        path (string): emoncms path with leading slash (eg: '/emoncms')
        apikey (string): API key with write access
        period (int): sending interval in seconds
        active (bool): whether the data buffer is active
        logger (string): the logger's name (default None)
        
        """
        
        self._logger = logging.getLogger(logger)
        self._data_buffer = []
        self._last_send = time.time()

        self._settings = {}
        
    def set(self, **kwargs):
        """Update settings.
        
        **kwargs (dict): settings to be modified.
        
        """

        for key, value in kwargs.iteritems():
            self._settings[key] = value

    def add_data(self, data):
        """Append timestamped dataset to buffer.

        data (list): node and values (eg: '[node,val1,val2,...]')

        """
       
        if not self._settings['active']:
            return
        
        self._logger.debug("Server " + 
                           self._settings['domain'] + self._settings['path'] + 
                           " -> add data: " + str(data))
        
        # Insert timestamp before data
        dataset = list(data) # Distinct copy: we don't want to modify data
        dataset.insert(0,time.time())
        # Append new data set [timestamp, node, val1, val2, val3,...] 
        # to _data_buffer
        self._data_buffer.append(dataset)

    def check_time(self):
        """Check if it is time to send data to server.
        
        Return True if sending interval has passed since last time

        """
        now = time.time()
        if (now - self._last_send > self._settings['period']):
            return True
    
    def has_data(self):
        """Check if buffer has data.
        
        Return True if data buffer is not empty.
        
        """
        return (self._data_buffer != [])

    def send_data(self):
        """Send data to server.

        To be implemented in sub-class.

        """
        pass


"""class OemGatewayEmoncmsBuffer

Stores server parameters and buffers the data between two HTTP requests

"""
class OemGatewayEmoncmsBuffer(OemGatewayBuffer):

    def send_data(self):
        """Send data to server."""
        
        if not self._settings['active']:
            return

        # Prepare data string with the values in data buffer
        now = time.time()
        data_string = '['
        for data in self._data_buffer:
            data_string += '['
            data_string += str(int(round(data[0]-now)))
            for sample in data[1:]:
                data_string += ','
                data_string += str(sample)
            data_string += '],'
        # Remove trailing comma and close bracket 
        data_string = data_string[0:-1]+']'
        self._data_buffer = []
        self._logger.debug("Data string: " + data_string)
        
        # Prepare URL string of the form
        # 'http://domain.tld/emoncms/input/bulk.json?apikey=
        # 12345&data=[[-10,10,1806],[-5,10,1806],[0,10,1806]]'
        url_string = self._settings['protocol'] + self._settings['domain'] + \
                     self._settings['path'] + "/input/bulk.json?apikey=" + \
                     self._settings['apikey'] + "&data=" + data_string
        self._logger.debug("URL string: " + url_string)

        # Send data to server
        self._logger.info("Sending to " + 
                          self._settings['domain'] + self._settings['path'])
        try:
            result = urllib2.urlopen(url_string)
        except urllib2.HTTPError as e:
            self._logger.warning("Couldn't send to server, HTTPError: " + 
                                 str(e.code))
        except urllib2.URLError as e:
            self._logger.warning("Couldn't send to server, URLError: " + 
                                 str(e.reason))
        except httplib.HTTPException:
            self._logger.warning("Couldn't send to server, HTTPException")
        except Exception:
            import traceback
            self._logger.warning("Couldn't send to server, Exception: " + 
                                 traceback.format_exc())
        else:
            if (result.readline() == 'ok'):
                self._logger.info("Send ok")
            else:
                self._logger.warning("Send failure")
        
        # Update _last_send
        self._last_send = time.time()
     
