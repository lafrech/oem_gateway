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

import oemgatewayinterface as ogi
import oemgatewaybuffer as ogb
import oemgatewaylistener as ogl

"""class OemGateway

Monitors data inputs through OemGatewayListener instances, and sends data to
target servers through OemGatewayEmoncmsBuffer instances.

Communicates with the user through an OemGatewayInterface

"""
class OemGateway(object):
    
    def __init__(self, interface):
        """Setup an RFM2Pi gateway.
        
        interface (OemGatewayInterface): User interface to the gateway.
        
        """

        # Initialize exit request flag
        self._exit = False

        # Initialize gateway interface and get settings
        self._interface = interface
        self._interface.check_settings()
        settings = self._interface.settings
        
        # Initialize logging
        self._log = logging.getLogger("OemGateway")
        self._set_logging_level(settings['gateway']['loglevel'])
        self._log.info("Opening gateway...")
        
        # Initialize buffers and listeners
        self._buffers = {}
        self._listeners = {}
        self._update_settings(settings)
        
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
            self._interface.run()
            if self._interface.check_settings():
                self._update_settings(self._interface.settings)
            
            # For all listeners
            for l in self._listeners.itervalues():
                # Execture run method
                l.run()
                # Read socket
                values = l.read()
                # If complete and valid data was received
                if values is not None:
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
        # Logging level
        self._set_logging_level(settings['gateway']['loglevel'])
        
        # Buffers
        for name, buf in settings['buffers'].iteritems():
            # If buffer does not exist, create it
            if name not in self._buffers:
                # This gets the class from the 'type' string
                self._log.info("Creating buffer %s", name)
                self._buffers[name] = \
                    getattr(ogb, buf['type'])(**buf['init_settings'])
            # Set runtime settings
            self._buffers[name].set(**buf['runtime_settings'])
        # If existing buffer is not in settings anymore, delete it
        for name in self._buffers:
            if name not in settings['buffers']:
                self._log.info("Deleting buffer %s", name)
                del(self._buffers[name])

        # Listeners
        for name, lis in settings['listeners'].iteritems():
            # If listener does not exist, create it
            if name not in self._listeners:
                self._log.info("Creating listener %s", name)
                try:
                    # This gets the class from the 'type' string
                    listener = getattr(ogl, lis['type'])(**lis['init_settings'])
                except ogl.OemGatewayListenerInitError as e:
                    # If listener can't be created, log error and skip to next
                    self._log.error(e)
                    continue
                else:
                    self._listeners[name] = listener
            # Set runtime settings
            self._listeners[name].set(**lis['runtime_settings'])
        # If existing listener is not in settings anymore, delete it
        for name in self._listeners:
            if name not in settings['listeners']:
                self._listeners[name].close()
                self._log.info("Deleting listener %s", name)
                del(self._listeners[name])

    def _set_logging_level(self, level):
        """Set logging level.
        
        level (string): log level name in 
        ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        
        """
        try:
            loglevel = getattr(logging, level)
        except AttributeError:
            self._log.error('Logging level %s invalid' % level)
        else:
            self._log.setLevel(level)

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
    logger.setLevel(logging.CRITICAL)

    # Initialize gateway interface
    # TODO: cmd line arg to choose another type of interface
    interface = ogi.OemGatewayEmoncmsInterface()
    
    # If in "Show settings" mode, print settings and exit
    if args.show_settings:
        interface.check_settings()
        pprint.pprint(interface.settings)
    
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
 
