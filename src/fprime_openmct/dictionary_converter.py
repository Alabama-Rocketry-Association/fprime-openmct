""" fprime_openmct.dictionary_converter: convert fprime dictionaries to OpenMCT format

This module provides functionality to convert fprime dictionaries to OpenMCT format. It uses the built-in GDS parsers
to parse command line arguments for reading Dictionaries.

It will write-out the OpenMCT dictionary to a JavaScript file that can be used in the OpenMCT plugin.
"""
import json
import sys
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
from fprime_gds.executables.cli import ParserBase, DictionaryParser


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
            values = cls.get_values(channel.ch_type_obj)
            # Skip empty telemetry channels that did not convert
            if not values:
                continue
            # There is always a timestamp in OpenMCT
            values.append({
                    "key": 'utc',
                    "source": 'timestamp',
                    "name": 'Time',
                    "format": 'utc',
                    "hints": {"domain": 1}
                })

            measurement = {
                "key": channel.get_full_name(),
                "name": channel.get_full_name(),
                "values": values
            }
            measurements.append(measurement)
        return openmct_dictionary

    @classmethod
    def get_values(cls, value_cls_type: BaseType, suffix: str = ""):
        """ Get value fields from channel templates
        
        This will act as a router for the various channel template types (scalars, arrays, structures, enums, etc.).
        As each type is routed to this function, it will be converted to the OpenMCT format based in the fprime format.      

        Args:
            value_cls_type (BaseType): type of a channel's value
            suffix (str): suffix to prepend to the value name
        """
        assert issubclass(value_cls_type, BaseType), "value_cls_type must be a subclass of BaseType"
        if issubclass(value_cls_type, ArrayType):
            return cls.get_array_values(value_cls_type, suffix=suffix)
        elif issubclass(value_cls_type, EnumType):
            return cls.get_enum_values(value_cls_type, suffix=suffix)
        elif issubclass(value_cls_type, SerializableType):
            return cls.get_serializable_values(value_cls_type, suffix=suffix)
        elif issubclass(value_cls_type, StringType):
            return cls.get_string_values(value_cls_type, suffix=suffix)
        elif issubclass(value_cls_type, (IntegerType, FloatType)):
            return cls.get_scalar_values(value_cls_type, suffix=suffix)
        else:
            print(f"[WARNING] Unknown telemetry type: {value_cls_type.__name__}. Skipping.")
        return []

    @classmethod
    def get_array_values(cls, array_type: ArrayType, suffix: str = ""):
        """ Get OpenMCT values from array type
        
        This will convert an array type and convert them to the OpenMCT format. Arrays provide multiple range values
        in the OpenMCT format. Since arrays can be nested, this structure is recursive and will be flattened.

        Each entry in the array will result in one value in the value list.

        Args:
            array_type (ArrayType): subclass of ArrayType representing the specific array type
        """
        values = []
        for i in range(array_type.LENGTH):
            values.extend(cls.get_values(array_type.MEMBER_TYPE, f"{suffix.rstrip('.')}[{i}]."))
        return values
    
    @classmethod
    def get_enum_values(cls, enum_type: EnumType, suffix: str = ""):
        """ Get OpenMCT values from enum type
        
        This will convert an enum type and convert them to the OpenMCT format. Enums are a special format in OpenMCT
        that have a list of values.

        Args:
            enum_type (EnumType): subclass of EnumType representing the integer
        """
        return [{
            "key": f"{suffix}value",
            "name": f"{suffix}value",
            "format": "enum",
            "enumerations": [{"value": value, "string": string} for string, value in enum_type.ENUM_DICT.items()],
            "hints": {"range": 1}
        }]

    @classmethod
    def get_scalar_values(cls, scalar_type: Union[IntegerType, FloatType], suffix: str = ""):
        """ Get OpenMCT values from scalar type
        
        This will convert a scalar type to the OpenMCT format. Scalars are singular values and have format of "float",
        or "integer".

        Args:
            scalar_type: string representing the format
        """
        return [{
            "key": f"{suffix}value",
            "name": f"{suffix}value",
            "format": "integer" if issubclass(scalar_type, IntegerType) else "float",
            "hints": {"range": 1}
        }]

    @classmethod
    def get_serializable_values(cls, serializable_type: SerializableType, suffix: str = ""):
        """ Get OpenMCT values from serializable type
        
        This will convert a serializable type and convert them to the OpenMCT format. Serializables provide multiple
        range values in the OpenMCT format one for each field. This structure is recursive and and will be flattened.

        Args:
            serializable_type (SerializableType): subclass of SerializableType representing the specific serializable type
        """
        values = []
        for member_name, member_type, _, _ in serializable_type.MEMBER_LIST:
            values.extend(cls.get_values(member_type, f"{suffix}{member_name}."))
        return values

    @classmethod
    def get_string_values(cls, string_type: StringType, suffix: str = ""):
        """ Get OpenMCT values from enum type
        
        This will convert a string type and convert them to the OpenMCT format.

        Args:
            string_type (StringType): subclass of StringType representing the specific string type
        """
        return [{
            "key": f"{suffix}value",
            "name": f"{suffix}value",
            "format": "string",
        }]
    
class OpenMCTParser(ParserBase):
    """ Parser for OpenMCT dictionary conversion
    
    This class provides functionality to parse command line arguments for reading the output OpenMCT dictionary JSON
    file as well as an optional name for the dictionary.

    Parsers should:
    1. Set a DESCRIPTION for sting used in help text,
    2. Implement get_arguments() to return a dictionary of argument definitions (argparse parameter format)
    3. Implement handle_arguments() to handle the arguments as parsed
    """

    DESCRIPTION = "s"

    def get_arguments(self) -> Dict[Tuple[str, ...], Dict[str, Any]]:
        """Arguments to handle deployments"""
        return {
            **{
                ("--output",): {
                    "dest": "output",
                    "action": "store",
                    "required": True,
                    "type": Path,
                    "help": "Path to write JSON OpenMCT dictionary to.",
                },
                ("--name",): {
                    "dest": "name",
                    "action": "store",
                    "default": None,
                    "required": False,
                    "type": str,
                    "help": "Name to use in the OpenMCT dictionary.",
                }
            },
        }

    def handle_arguments(self, args, **kwargs):
        """Handle arguments as parsed"""
        args.output.parent.mkdir(parents=True, exist_ok=True)
        return args


def parse_arguments():
    """ Parse command line arguments
    
    This uses built-in GDS parsers to parse command line arguments for reading Dictionaries. This will enable use of
    the Dictionaries object to load the fprime dictionaries.

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    argument_handlers = [DictionaryParser, OpenMCTParser]
    args, _ = ParserBase.parse_args(argument_handlers, description="Convert fprime dictionaries to OpenMCT format")
    args.name = args.name if args.name is not None else Path(args.dictionary).stem
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
    dictionaries.load_dictionaries(arguments.dictionary, arguments.packet_spec)
    converted = OpenMCTBuilder.convert(arguments.name, dictionaries)
    with open(arguments.output, "w") as file_handle:
        json.dump(converted, file_handle, indent=4)
    print(f"OpenMCT dictionary written to {arguments.output}")
    return 0  # Success exit code

if __name__ == "__main__":
    sys.exit(main())