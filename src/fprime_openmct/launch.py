""" fprime_openmct.dictionary_converter: convert fprime dictionaries to OpenMCT format

This module provides functionality to convert fprime dictionaries to OpenMCT format. It uses the built-in GDS parsers
to parse command line arguments for reading Dictionaries.

It will write-out the OpenMCT dictionary to a JavaScript file that can be used in the OpenMCT plugin.
"""
import functools
import sys
import subprocess
import time
import webbrowser
from pathlib import Path
from shutil import which
from typing import Dict, Any, Tuple
from fprime_gds.executables.cli import ParserBase, CompositeParser, DictionaryParser
from fprime_gds.executables.cli import CompositeParser, DictionaryParser
from fprime_openmct.dictionary_converter import OpenMCTDictionaryConverterParser

JAVASCRIPT_PATH = Path(__file__).parent / "javascript"
HOME = Path.home()

class OpenMCTLaunchParser(ParserBase):
    """ Parser for OpenMCT dictionary conversion
    
    This class provides functionality to parse command line arguments for reading the output OpenMCT dictionary JSON
    file as well as an optional name for the dictionary.

    Parsers should:
    1. Set a DESCRIPTION for sting used in help text,
    2. Implement get_arguments() to return a dictionary of argument definitions (argparse parameter format)
    3. Implement handle_arguments() to handle the arguments as parsed
    """
    DESCRIPTION = "Launch OpenMCT and plumb in fprime telemetry"

    def get_arguments(self) -> Dict[Tuple[str, ...], Dict[str, Any]]:
        """Arguments to handle deployments"""
        return {
            ("--openmct-port", ): {
                "type": int,
                "help": "Port to launch OpenMCT on",
                "required": False,
                "default": 8080
            },
        }

    def handle_arguments(self, args, **kwargs):
        """Handle arguments as parsed"""
        return args

OpenMCTCompositeParser = functools.partial(CompositeParser, [OpenMCTDictionaryConverterParser, OpenMCTLaunchParser])
def parse_arguments():
    """ Parse command line arguments
    
    This uses built-in GDS parsers to parse command line arguments for launching OPenMCT and the fprime/OpenMCT bridge.

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    argument_handlers = [OpenMCTCompositeParser]
    args, _ = ParserBase.parse_args(argument_handlers, description="Launch OpenMCT and plumb in fprime telemetry")
    if not which("npm") or not which("node"):
        raise FileNotFoundError("Node.js and npm must be installed to run OpenMCT")
    return args

def main():
    """ Entrypoint of the program
    
    This will parse command line arguments, convert fprime dictionaries to OpenMCT format, install OpenMCT via node, and
    finally launch OpenMCT.

    Arguments are provided via the default argparse input (sys.argv).

    Returns:
        0 on success, something else on failure, used as exit code for the process
    """
    try:
        arguments = parse_arguments()
        openmct_dictionary_converter_args = OpenMCTDictionaryConverterParser().reproduce_cli_args(arguments)
        subprocess.run(["fprime-openmct-dictionary-converter"] + openmct_dictionary_converter_args, check=True)
        subprocess.run(["npm", "install"], cwd=JAVASCRIPT_PATH, check=True)
        npm_args = [
            "--", # Switch from npm args to script args
            "--openmct-port", str(arguments.openmct_port),
            "--openmct-dictionary", str(arguments.openmct_output.absolute())
        ]
        #node_process = subprocess.Popen(["npm", "start"] + npm_args, cwd="/home/desmos/ARA-openmct")#JAVASCRIPT_PATH)
        node_process = subprocess.Popen(["npm", "start"], cwd=(f"{HOME}/ARA_DPF_FlightAvionics/ARA-openmct"))#JAVASCRIPT_PATH)
        print(f"[INFO] Ensuring stability of OpenMCT launch for 1 second")
        time.sleep(1)
        assert node_process.poll() is None, "OpenMCT failed to launch"
        webbrowser.open(f"http://localhost:{arguments.openmct_port}")
        node_process.wait()
    except KeyboardInterrupt:
        print("[INFO] Shutting down OpenMCT bridge")
        node_process.terminate()
        node_process.wait()
        return 0
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1

    return 0  # Success exit code

if __name__ == "__main__":
    sys.exit(main())
