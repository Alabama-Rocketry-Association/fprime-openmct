""" fprime_openmct.dictionary_converter: convert fprime dictionaries to OpenMCT format

This module provides functionality to convert fprime dictionaries to OpenMCT format. It uses the built-in GDS parsers
to parse command line arguments for reading Dictionaries.

It will write-out the OpenMCT dictionary to a JavaScript file that can be used in the OpenMCT plugin.
"""
import json
import sys
import functools
from pathlib import Path
from typing import Dict, Any, Tuple, Union

from fprime.common.models.serialize.type_base import BaseType
from fprime.common.models.serialize.array_type import ArrayType
from fprime.common.models.serialize.enum_type import EnumType
from fprime.common.models.serialize.serializable_type import SerializableType
from fprime.common.models.serialize.numerical_types import IntegerType
from fprime.common.models.serialize.numerical_types import FloatType
from fprime.common.models.serialize.string_type import StringType

from fprime_gds.common.templates.ch_template import ChTemplate
from fprime_gds.common.pipeline.dictionaries import Dictionaries
from fprime_gds.executables.cli import ParserBase, CompositeParser, DictionaryParser

from .utilities import flatten

class OpenMCTBuilder(object):
    """ OpenMCTBuilder: build OpenMCT dictionary from fprime dictionaries
    
    This class provides functionality to convert fprime dictionaries to OpenMCT format. 
    """
    @classmethod
    def convert(cls, name: str, dictionaries: Dictionaries):
        """ Convert fprime dictionaries to OpenMCT format """
        openmct_dictionary = {
            "name": name,
            "key": name,
            "measurements": []
        }
        measurements = openmct_dictionary["measurements"]

        for channel in dictionaries.channel_id.values():
            for sub_channel in cls.get_channels(channel):
                # There is always a timestamp in OpenMCT
                values= [
                    {
                        **sub_channel,
                        **{
                           "key": "value",
                           "source": "value",
                        },
                    },
                    {
                        "key": 'utc',
                        "source": 'timestamp',
                        "name": 'Time',
                        "format": 'utc',
                        "hints": {"domain": 1}
                    }
                ]

                measurement = {
                    "key": sub_channel["key"],
                    "name": sub_channel["name"],
                    "origin": sub_channel["origin"],
                    "values": values
                }
                measurements.append(measurement)
        return openmct_dictionary

    @classmethod
    def get_channels(cls, channel: ChTemplate):
        """ Get OpenMCT channel(s) from fprime channel

        This will convert a fprime channel to the OpenMCT format. Channels can have either a single value or complex
        values. This function returns a list of channels with complex channels being flattened.

        Args:
            channel (ChTemplate): fprime channel to convert 
        """
        value_cls_type = channel.get_type_obj()
        sub_channels = flatten(value_cls_type, channel.get_full_name())
        values = [cls.get_value(cls_type, name) for name, cls_type in sub_channels]
        return [
            {
                **value,
                **{
                    "origin": channel.get_full_name(),
                }
            }
            for value in values
        ]

    @classmethod
    def get_value(cls, value_cls_type: BaseType, suffix):
        """ Get value fields from channel templates that are not complex
        
        This will act as a router for the various channel template types (scalars, arrays, enums, etc.).
        As each type is routed to this function, it will be converted to the OpenMCT format based in the fprime format.      

        Args:
            value_cls_type (BaseType): type of a channel's value (not complex)
            suffix (str): suffix to prepend to the value name
        """
        assert issubclass(value_cls_type, BaseType), "value_cls_type must be a subclass of BaseType"
        if issubclass(value_cls_type, EnumType):
            return cls.get_enum_value(value_cls_type, suffix=suffix)
        elif issubclass(value_cls_type, StringType):
            return cls.get_string_value(value_cls_type, suffix=suffix)
        elif issubclass(value_cls_type, (IntegerType, FloatType)):
            return cls.get_scalar_value(value_cls_type, suffix=suffix)
        assert False, f"Unsupported type {value_cls_type.__name__}"
    
    @classmethod
    def get_enum_value(cls, enum_type: EnumType, suffix: str):
        """ Get OpenMCT value from enum type
        
        This will convert an enum type and convert them to the OpenMCT format. Enums are a special format in OpenMCT
        that have a list of enumerations.

        Args:
            enum_type (EnumType): subclass of EnumType representing the integer
            suffix (str): suffix to prepend to the value identifiers
        """
        scalar_default = cls.get_scalar_value(enum_type, suffix)
        scalar_default["format"] = "enum"
        scalar_default["enumerations"] = [{"value": value, "string": string} for string, value in enum_type.ENUM_DICT.items()]
        return scalar_default

    @classmethod
    def get_scalar_value(cls, scalar_type: Union[IntegerType, FloatType], suffix):
        """ Get OpenMCT value from scalar type
        
        This will convert a scalar type to the OpenMCT format. Scalars are singular values and have format of "float",
        or "integer".

        Args:
            scalar_type: string representing the format
            suffix (str): suffix to prepend to the value identifiers
        """
        format_type = None
        if issubclass(scalar_type, IntegerType):
            format_type = "integer"
        elif issubclass(scalar_type, FloatType):
            format_type = "float"

        return {
            "key": suffix,
            "name": suffix,
            "format": format_type,
            "hints": {"range": 1}
        }

    @classmethod
    def get_string_value(cls, string_type: StringType, suffix: str = ""):
        """ Get OpenMCT value from string type
        
        This will convert a string type and convert them to the OpenMCT format.

        Args:
            string_type (StringType): subclass of StringType representing the specific string type
        """
        scalar_default = cls.get_scalar_value(string_type, suffix)
        scalar_default["format"] = "string"
        return scalar_default
    
class OpenMCTDictionaryParser(ParserBase):
    """ Parser for OpenMCT dictionary conversion
    
    This class provides functionality to parse command line arguments for reading the output OpenMCT dictionary JSON
    file as well as an optional name for the dictionary.

    Parsers should:
    1. Set a DESCRIPTION for sting used in help text,
    2. Implement get_arguments() to return a dictionary of argument definitions (argparse parameter format)
    3. Implement handle_arguments() to handle the arguments as parsed
    """

    DESCRIPTION = "Convert fprime dictionaries to OpenMCT format"

    def get_arguments(self) -> Dict[Tuple[str, ...], Dict[str, Any]]:
        """Arguments to handle deployments"""
        return {
            ("--openmct-output",): {
                "action": "store",
                "default": Path(__file__).parent / "javascript" / "dictionary.json",
                "type": Path,
                "help": "Path to write JSON OpenMCT dictionary to.",
            },
            ("--openmct-name",): {
                "action": "store",
                "default": None,
                "required": False,
                "type": str,
                "help": "Name to use in the OpenMCT dictionary.",
            }
        }

    def handle_arguments(self, args, **kwargs):
        """Handle arguments as parsed"""
        if args.openmct_output.suffix != ".json":
            raise ValueError("OpenMCT output file must have .json extension")
        if args.dictionary is None or not Path(args.dictionary).exists():
            raise ValueError("Dictionary file must be provided and exist")
        args.openmct_output.parent.mkdir(parents=True, exist_ok=True)
        args.openmct_name = args.openmct_name if args.openmct_name is not None else Path(args.dictionary).stem
        return args

OpenMCTDictionaryConverterParser = functools.partial(CompositeParser, [DictionaryParser, OpenMCTDictionaryParser])


def parse_arguments():
    """ Parse command line arguments
    
    This uses built-in GDS parsers to parse command line arguments for reading Dictionaries. This will enable use of
    the Dictionaries object to load the fprime dictionaries.

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    argument_handlers = [OpenMCTDictionaryConverterParser]
    args, _ = ParserBase.parse_args(argument_handlers, description="Convert fprime dictionaries to OpenMCT format")
    return args

def main():
    """ Entrypoint of the program
    
    This will load the commandline arguments needed for dictionary processing. It will then load the dictionaries and
    convert them to OpenMCT format.

    Arguments are provided via the default argparse input (sys.argv).

    Returns:
        0 on success, something else on failure, used as exit code for the process
    """
    arguments = parse_arguments()
    dictionaries = Dictionaries()
    dictionaries.load_dictionaries(arguments.dictionary, arguments.packet_spec, arguments.packet_set_name)
    converted = OpenMCTBuilder.convert(arguments.openmct_name, dictionaries)
    with open(arguments.openmct_output, "w") as file_handle:
        json.dump(converted, file_handle, indent=4)
    print(f"OpenMCT dictionary written to {arguments.openmct_output}")
    return 0  # Success exit code

if __name__ == "__main__":
    sys.exit(main())