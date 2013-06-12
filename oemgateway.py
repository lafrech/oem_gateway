#!/usr/bin/env python

"""

  This code is released under the GNU Affero General Public License.
  
  OpenEnergyMonitor project:
  http://openenergymonitor.org

"""

import time
import logging, logging.handlers
import signal
import argparse
import pprint

from oemgatewayinterface import OemGatewayEmoncmsInterface
from oemgatewaybuffer import OemGatewayEmoncmsBuffer
from oemgatewaylistener import OemGatewayRFM2PiListener

"""class OemGateway

Monitors the serial port for data from RFM2Pi and sends data to local or remote 
emoncms servers through OemGatewayEmoncmsBuffer instances.

"""
class OemGateway(object):
    
    def __init__(self, interface):
        """Setup an RFM2Pi gateway.
        
        interface (OemGatewayInterface): User interface to the gateway.
        
        """

        # Initialize exit request flag
        self._exit = False

        # Initialize logging
        self._log = logging.getLogger("OemGateway")
        self._log.info("Opening gateway...")
        
        # Initialize gateway interface
        self._interface = interface

        #Initialize buffers and listeners dictionaries
        self._buffers = {}
        self._listeners = {}
        
    def run(self):
        """Launch the gateway.
        
        Monitor the COM port and process data.
        Check settings on a regular basis.

        """

       # Set signal handler to catch SIGINT and shutdown gracefully
        signal.signal(signal.SIGINT, self._sigint_handler)
        
        # Until asked to stop
        while not self._exit:
            
            # Run interface and update settings if modified
            if self._interface.run():
                self._update_settings(self._interface.settings)
            
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
        
        self._log.info("Exiting gateway...")
        logging.shutdown()

    def _sigint_handler(self, signal, frame):
        """Catch SIGINT (Ctrl+C)."""
        
        self._log.debug("SIGINT received.")
        # gateway should exit at the end of current iteration.
        self._exit = True

    def _update_settings(self, settings):
        """Check settings and update if needed."""
        
        # Gateway
        #TODO: Add logging level, etc.

        # Buffers
        for name, buf in settings['buffers'].iteritems():
            # If buffer does not exist, create it
            if name not in self._buffers:
                # This gets the class from the 'type' string
                self._log.info("Creating buffer %s", name)
                self._buffers[name] = \
                    globals()[buf['type']](**buf['init_settings'])
            # Set runtime settings
            self._buffers[name].set(**buf['runtime_settings'])
        # If existing buffer is not in settings anymore, delete it
        for name in self._buffers:
            if name not in settings['buffers']:
                del(self._buffers[name])

        # Listeners
        for name, lis in settings['listeners'].iteritems():
            # If listener does not exist, create it
            if name not in self._listeners:
                # This gets the class from the 'type' string
                self._log.info("Creating listener %s", name)
                self._listeners[name] = \
                    globals()[lis['type']](**lis['init_settings'])
                self._listeners[name].open() #TODO: catch opening error
            # Set runtime settings
            self._listeners[name].set(**lis['runtime_settings'])
        # If existing listener is not in settings anymore, delete it
        for name in self._listeners:
            if name not in settings['listeners']:
                self._listeners[name].close()
                del(self._listeners[name])

if __name__ == "__main__":

    # Command line arguments parser
    parser = argparse.ArgumentParser(description='RFM2Pi Gateway')
    parser.add_argument('--logfile', action='store', type=argparse.FileType('a'),
        help='path to optional log file (default: log to Standard error stream STDERR)')
    parser.add_argument('--show-settings', action='store_true',
        help='show RFM2Pi settings and exit (for debugging purposes)')
    args = parser.parse_args()
    
    # Logging configuration
    logger = logging.getLogger("OemGateway")
    if args.logfile is None:
        # If no path was specified, everything goes to sys.stderr
        loghandler = logging.StreamHandler()
    else:
        # Otherwise, rotating logging over two 5 MB files
        # If logfile is supplied, argparse opens the file in append mode,
        # this ensures it is writable
        # Close the file for now and get its path
        args.logfile.close()
        loghandler = logging.handlers.RotatingFileHandler(args.logfile.name,
                                                       'a', 5000 * 1024, 1)
    # Format log strings
    loghandler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(loghandler)
    logger.setLevel(logging.DEBUG)

    # Initialize gateway interface
    # TODO: cmd line arg to choose another type of interface
    interface = OemGatewayEmoncmsInterface()
    
    # If in "Show settings" mode, print settings and exit
    if args.show_settings:
        pprint.pprint(interface.get_settings())
    
    # Otherwise, create, run, and close OemGateway instance
    else:
        try:
            gateway = OemGateway(interface)
        except Exception as e:
            print(e)
        else:
            gateway.run()
            # When done, close gateway
            gateway.close()
 
