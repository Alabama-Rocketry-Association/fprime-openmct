import json
import zmq
from fprime_gds.common.handlers import DataHandlerPlugin
from fprime_gds.plugin.definitions import gds_plugin

from fprime_openmct.utilities import flatten

@gds_plugin(DataHandlerPlugin)
class OpenMCTPush(DataHandlerPlugin):
    """ Plugin to push data to OpenMCT

    This plugin will open up a ZeroMQ connection to the openmct express server and push data to it. Data will be
    reformatted to match the expected OpenMCT format.
    """

    def __init__(self, openmct_zmq_connection):
        """ Initialize the plugin with the ZMQ connection string """
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(openmct_zmq_connection)

    def get_handled_descriptors(self):
        """ List descriptors of F Prime data types that this plugin can handle """
        return ["FW_PACKET_TELEM"]
    
    @classmethod
    def get_name(cls):
        """ Return the name of the plugin """
        return "openmct-push"
    
    @classmethod
    def get_arguments(cls):
        """ Return argument spec for ZMQ connection string """
        return {
            ("--openmct-zmq-connection",): {
                "type": str,
                "default": "ipc:///tmp/fprime-openmct-push",
               "help": "ZMQ connection string for OpenMCT",
            }
        }


    def data_callback(self, data, source):
        """ Handle data objects plugged into the GDS
        """
        timestamp =  data.get_time().get_datetime().timestamp() * 1000
        items = flatten(data.get_val_obj(), data.template.get_full_name())
        openmct_data = [
            {"timestamp": timestamp, "key": name, "name": name, "value": value_object.val}
            for name, value_object in items
        ]
        try:
            self.socket.send_multipart([
                "fprime-openmct".encode("utf-8"),
                f"{json.dumps(openmct_data, allow_nan=False)}".encode("utf-8")
            ])
        # Exclude NaN, Infinity, and -Infinity from JSON serialization
        except ValueError as e:
            pass
