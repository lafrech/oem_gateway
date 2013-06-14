"""

  This code is released under the GNU Affero General Public License.
  
  OpenEnergyMonitor project:
  http://openenergymonitor.org

"""

import urllib2
import time
import logging
import csv
#import configobj

"""class OemGatewayInterface

User interface to communicate with the gateway.

The settings attribute stores the settings of the gateway. It is a
dictionnary with the following keys:

        'gateway': a dictionary containing the gateway settings
        'listeners': a dictionary containing the listeners
        'buffer': a dictionary containing the buffers

        The gateway settings are:
        'loglevel': the logging level
        
        Listeners and buffers are dictionaries with the folowing keys:
        'type': class name
        'init_settings': dictionary with initialization settings
        'runtime_settings': dictionary with runtime settings
        Initialization and runtime settings depend on the listener and
        buffer type.

The run() method is supposed to be run regularly by the instanciater, to
perform regular communication tasks.

The check_settings() method is run regularly as well. It checks the settings 
and returns True is settings were changed.

This almost empty class is meant to be inherited by subclasses specific to
each user interface.

"""
class OemGatewayInterface(object):

    def __init__(self):
        
        # Initialize logger
        self._log = logging.getLogger("OemGateway")
        
        # Initialize settings
        self.settings = None

    def run(self):
        """Run in background. 
        
        To be implemented in child class.

        """
        pass

    def check_settings(self):
        """Check settings
        
        Update attribute settings and return True if modified.
        
        To be implemented in child class.
        
        """
    
    def get_settings(self):
        """Get settings
        
        Returns None if settings couldn't be obtained.

        To be implemented in child class.
        
        """
        pass

class OemGatewayEmoncmsInterface(OemGatewayInterface):

    def __init__(self):
        
        # Initialization
        super(OemGatewayEmoncmsInterface, self).__init__()

        # Initialize status update timestamp
        self._status_update_timestamp = 0
        self._settings_update_timestamp = 0

    def run(self):
        """Run in background. 
        
        Return True if settings changed, None otherwise.
        
        Update raspberry_pi running status.
        
        """
        
        # Update status every second
        now = time.time()
        if (now - self._status_update_timestamp > 1):
            # Update "running" status to inform emoncms the script is running
            self._gateway_running()
            # "Thanks for the status update. You've made it crystal clear."
            self._status_update_timestamp = now
            
    def check_settings(self):
        """Check settings
        
        Update attribute settings and return True if modified.
        
        """
        
        # Check settings only once per second
        now = time.time()
        if (now - self._settings_update_timestamp < 1):
            return
        # Update timestamp
        self._settings_update_timestamp = now
        
        # Get settings using emoncms API
        try:
            result = urllib2.urlopen(
                "http://localhost/emoncms/raspberrypi/get.json")
            result = result.readline()
            # result is of the form
            # {"userid":"1","sgroup":"210",...,"remoteprotocol":"http:\\/\\/"}
            result_array = result[1:-1].split(',')
            # result is now of the form
            # ['"userid":"1"',..., '"remoteprotocol":"http:\\/\\/"']
            emoncms_s = {}
            # For each setting, separate key and value
            for s in result_array:
                # We can't just use split(':') as there can be ":" inside 
                # a value (eg: "http://")
                s_split = csv.reader([s], delimiter=':').next() 
                emoncms_s[s_split[0]] = s_split[1].replace("\\","")

        except Exception:
            import traceback
            self._log.warning("Couldn't get settings, Exception: " + 
                traceback.format_exc())
            return
        
        settings = {}
        
        # Format OemGateway settings
        settings['gateway'] = {'loglevel': 'DEBUG'} # Stubbed until implemented
            
        # RFM2Pi listener
        settings['listeners'] = {'RFM2Pi': {}}
        settings['listeners']['RFM2Pi'] = \
            {'type': 'OemGatewayRFM2PiListener', 
            'init_settings': {'com_port': '/dev/ttyAMA0'},
            'runtime_settings': {}}
        for item in ['sgroup', 'frequency', 'baseid', 'sendtimeinterval']:
            settings['listeners']['RFM2Pi']['runtime_settings'][item] = \
                emoncms_s[item]

        # Emoncms servers
        settings['buffers'] = {'emoncms_local': {}, 'emoncms_remote': {}}
        # Local
        settings['buffers']['emoncms_local'] = \
            {'type': 'OemGatewayEmoncmsBuffer',
            'init_settings': {},
            'runtime_settings': {}}
        settings['buffers']['emoncms_local']['runtime_settings'] = \
            {'protocol': 'http://',
            'domain': 'localhost',
            'path': '/emoncms',
            'apikey': emoncms_s['apikey'],
            'period': '0',
            'active': 'True'}
        # Remote
        settings['buffers']['emoncms_remote'] = \
            {'type': 'OemGatewayEmoncmsBuffer',
            'init_settings': {},
            'runtime_settings': {}}
        settings['buffers']['emoncms_remote']['runtime_settings'] = \
            {'protocol': emoncms_s['remoteprotocol'],
            'domain': emoncms_s['remotedomain'],
            'path': emoncms_s['remotepath'],
            'apikey': emoncms_s['remoteapikey'],
            'period': '30',
            'active': emoncms_s['remotesend']}

        # Return True if settings modified
        if settings != self.settings:
            self.settings = settings
            return True

    def _gateway_running(self):
        """Update "script running" status."""
        
        try:
            result = urllib2.urlopen(
                "http://localhost/emoncms/raspberrypi/setrunning.json")
        except Exception:
            import traceback
            self._log.warning(
                "Couldn't update \"running\" status, Exception: " + 
                traceback.format_exc())

