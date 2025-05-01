""" GDS App plugin used to launch OpenMCT

This is a GDS app plugin that will launch OpenMCT as part of the GDS startup.
"""
import argparse
from fprime_gds.plugin.definitions import gds_plugin_implementation
from fprime_gds.executables.apps import GdsApp
from fprime_openmct.launch import OpenMCTCompositeParser


class OpenMCT(GdsApp):
    """ OpenMCT GDS app plugin 
    
    This class is used to launch OpenMCT as part of the GDS startup which is done via a process invocation found
    in the get_process_invocation function. The other functions within this class provide the plugin system information
    such as the name of the plugin and the arguments that are passed to it.
    """


    def __init__(self, **kwargs):
        """ Plugin constructor provided with all plugin arguments """
        super().__init__()
        self.kwargs = kwargs

    def get_process_invocation(self):
        """ Provides the process invocation line for this application
        
        This process invocation is used to launch OpenMCT as part of the GDS startup. The process invocation is a list
        of command line arguments that are used to launch the application. In the case of this plugin, the process
        invocation uses a stand-alone python script "fprime-openmct-launch".
        """
        # Inject message into command line to print
        args_ns = argparse.Namespace(**self.kwargs)
        return ["fprime-openmct-launch"] + OpenMCTCompositeParser().reproduce_cli_args(args_ns) 

    @classmethod
    def get_name(cls):
        """ Return the name of the app plugin """
        return "fprime-openmct"

    @classmethod
    def get_arguments(cls):
        """ Return argument specification
        
        OpenMCT is launched on a port that is specified by the user. This function provides the argument specification
        for the port that is used to launch OpenMCT.
        """
        return OpenMCTCompositeParser().get_arguments()

    @classmethod
    def check_arguments(cls, **kwargs):
        """ Validate arguments supplied via get_arguments
        
        Currently this function ensures that port "6000" is always used to launch OpenMCT. This is because the OpenMCT
        launches on this port.
        """
        pass
        

    @classmethod
    @gds_plugin_implementation
    def register_gds_app_plugin(cls):
        """ Register a good plugin """
        return cls