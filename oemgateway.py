#!/usr/bin/env python

"""

  This code is released under the GNU Affero General Public License.
  
  OpenEnergyMonitor project:
  http://openenergymonitor.org

"""

import serial
import urllib2, httplib
import time
import logging, logging.handlers
import re
import signal
import csv
import argparse

from oemgatewaybuffer import OemGatewayEmoncmsBuffer
from oemgatewaylistener import OemGatewayRFM2PiListener

"""class RFM2PiGateway

Monitors the serial port for data from RFM2Pi and sends data to local or remote 
emoncms servers through OemGatewayEmoncmsBuffer instances.

"""
class RFM2PiGateway():
    
    def __init__(self, logpath=None):
        """Setup an RFM2Pi gateway.
        
        logpath (path): Path to the file the log should be written into.
            If Null, log to STDERR.

        """

        # Initialize exit request flag
        self._exit = False

        # Initialize logging
        self.log = logging.getLogger(__name__)
        if (logpath is None):
            # If no path was specified, everything goes to sys.stderr
            loghandler = logging.StreamHandler()
        else:
            # Otherwise, rotating logging over two 5 MB files
            loghandler = logging.handlers.RotatingFileHandler(logpath,
                                                           'a', 5000 * 1024, 1)
        loghandler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s %(message)s'))
        self.log.addHandler(loghandler)
        self.log.setLevel(logging.DEBUG)
        
        # Initialize socket listeners
        self._listeners = {}
        self._listeners['rfm2pi'] = OemGatewayRFM2PiListener(logger = __name__)
        for l in self._listeners.itervalues():
            if (l.open_socket() == False):
                self.close()
                raise Exception('COM port opening failed.')
 
        # Initialize target server buffer set
        self._buffers = {}
       
        # Initialize status update timestamp
        self._status_update_timestamp = 0

        # Get emoncms server buffers and RFM2Pi settings
        self._settings = None
        self._update_settings()
    
        # If settings can't be obtained, exit
        while (self._settings is None):
            self.log.warning("Couldn't get settings. Retrying in 10 sec...")
            time.sleep(10)
            self._update_settings()
        
    def run(self):
        """Launch the gateway.
        
        Monitor the COM port and process data.
        Check settings on a regular basis.

        """

       # Set signal handler to catch SIGINT and shutdown gracefully
        signal.signal(signal.SIGINT, self._sigint_handler)
        
        # Until asked to stop
        while not self._exit:
            
            # Update settings and status every second
            now = time.time()
            if (now - self._status_update_timestamp > 1):
                # Update "running" status to inform emoncms the script is running
                self._raspberrypi_running()
                # Update settings
                self._update_settings()
                # "Thanks for the status update. You've made it crystal clear."
                self._status_update_timestamp = now
            
            # For all listeners
            for l in self._listeners.itervalues():
                # Execture run method
                l.run()
                # If complete line received
                if(l.read() == True):
                    # Process line
                    values = l.process()
                    # If data is valid
                    if (values):
                        # Buffer data
                        for server_buf in self._buffers.itervalues():
                            server_buf.add_data(values)
            
            # For all buffers, if time has come, send data
            for s in self._buffers.itervalues():
                if s.check_time():
                    if s.has_data():
                        s.send_data()
        
            # Sleep until next iteration
            time.sleep(0.2);
         
    def close(self):
        """Close gateway. Do some cleanup before leaving."""
        
        # TODO: what if it is not open ?
        for l in self._listeners.itervalues():
            l.close()
        
        self.log.info("Exiting...")
        logging.shutdown()

    def _sigint_handler(self, signal, frame):
        """Catch SIGINT (Ctrl+C)."""
        
        self.log.debug("SIGINT received.")
        # gateway should exit at the end of current iteration.
        self._exit = True

    def get_settings(self):
        """Get settings
        
        Returns a dictionnary

        """
        try:
            result = urllib2.urlopen("http://localhost/emoncms/raspberrypi/get.json")
            result = result.readline()
            # result is of the form
            # {"userid":"1","sgroup":"210",...,"remoteprotocol":"http:\\/\\/"}
            result = result[1:-1].split(',')
            # result is now of the form
            # ['"userid":"1"',..., '"remoteprotocol":"http:\\/\\/"']
            settings = {}
            # For each setting, separate key and value
            for s in result:
                # We can't just use split(':') as there can be ":" inside a value 
                # (eg: "http://")
                s = csv.reader([s], delimiter=':').next() 
                settings[s[0]] = s[1].replace("\\","")
            return settings

        except Exception:
            import traceback
            self.log.warning("Couldn't get settings, Exception: " + traceback.format_exc())
            return

    def _update_settings(self):
        """Check settings and update if needed."""
        
        # Get settings
        s_new = self.get_settings()

        # If s_new is None, no answer to settings request
        if s_new is None:
            return

        # RFM2PiListener settings
        kwargs = {}
        for param in ['baseid', 'frequency', 'sgroup', 'sendtimeinterval']:
            kwargs[param] = str(s_new[param])
        self._listeners['rfm2pi'].set(**kwargs)

        # Server settings
        if 'local' not in self._buffers:
            self._buffers['local'] = OemGatewayEmoncmsBuffer(
                    protocol = 'http://',
                    domain = 'localhost',
                    path = '/emoncms', 
                    apikey = s_new['apikey'], 
                    period = 0, 
                    active = True,
                    logger = __name__)
        else:
            self._buffers['local'].update_settings(
                    apikey = s_new['apikey'])
        
        if 'remote' not in self._buffers:
            self._buffers['remote'] = OemGatewayEmoncmsBuffer(
                    protocol = s_new['remoteprotocol'], 
                    domain = s_new['remotedomain'], 
                    path = s_new['remotepath'],
                    apikey = s_new['remoteapikey'],
                    period = 30,
                    active = bool(s_new['remotesend']),
                    logger = __name__)
        else: 
            self._buffers['remote'].update_settings(
                    protocol = s_new['remoteprotocol'], 
                    domain = s_new['remotedomain'],
                    path = s_new['remotepath'],
                    apikey = s_new['remoteapikey'],
                    active = bool(int(s_new['remotesend'])))
        
        self._settings = s_new
    
    def _raspberrypi_running(self):
        """Update "script running" status."""
        
        try:
            result = urllib2.urlopen("http://localhost/emoncms/raspberrypi/setrunning.json")
        except Exception:
            import traceback
            self.log.warning("Couldn't update \"running\" status, Exception: " + traceback.format_exc())
           

if __name__ == "__main__":

    # Command line arguments parser
    parser = argparse.ArgumentParser(description='RFM2Pi Gateway')
    parser.add_argument('--logfile', action='store', type=argparse.FileType('a'),
        help='path to optional log file (default: log to Standard error stream STDERR)')
    parser.add_argument('--show-settings', action='store_true',
        help='show RFM2Pi settings and exit (for debugging purposes)')
    args = parser.parse_args()
    
    # If logfile is supplied, argparse opens the file in append mode, 
    # this ensures it is writable
    # Close the file for now and get its path
    if args.logfile is None:
        logfile = None
    else:
        args.logfile.close()
        logfile = args.logfile.name

    # Create, run, and close RFM2Pi Gateway instance
    try:
        gateway = RFM2PiGateway(logfile)
    except Exception as e:
        print(e)
    else:    
        # If in "Show settings" mode, print RFM2Pi settings and exit
        if args.show_settings:
            print(gateway.get_settings())
        # Else, run normally
        else:
            gateway.run()
        # When done, close gateway
        gateway.close()
 
