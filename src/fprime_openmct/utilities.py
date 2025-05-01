
from itertools import chain
from typing import Type
from fprime.common.models.serialize.type_base import BaseType
from fprime.common.models.serialize.array_type import ArrayType
from fprime.common.models.serialize.serializable_type import SerializableType


def flatten(value: BaseType | Type[BaseType], suffix: str):
    """ Flatten the given object into a iterable of non-complex (name, leaf nodes) tuples
    
    Will take Array and SerializableType objects and flatten them into an iterable of BaseType objects that represent
    each node in the tree. If a class is provided, class objects will be returned.  If an instance is provided, value
    instances will be returned. Data will be returns as a list of tuples of the form (name, leaf) where name is
    constructed from the suffix appending [index] for arrays and .field for serializable types, and leaf is the class
    or value instance.

    This algorithm is recursive.

    Args:
        value (BaseType | Type[BaseType]): Data object to flatten
        suffix (str): suffix to pair with data object
    Returns:
        iterable  of flattened objects of the form (name, leaf)
    Raises:
        AssertionError: If value is not a BaseType instance nor a subclass of BaseType
    """
    assert isinstance(value, BaseType) or (isinstance(value, type) and issubclass(value, BaseType)), \
        f"flatten requires a BaseType instance or subclass not {value.__class__.__name__}"
    if isinstance(value, ArrayType):
        return chain.from_iterable([flatten(item, f"{suffix}[{i}]") for i, item in enumerate(value)])
    elif isinstance(value, type) and issubclass(value, ArrayType):
        return chain.from_iterable([flatten(value.MEMBER_TYPE, f"{suffix}[{i}]") for i in range(0, value.LENGTH)])
    elif isinstance(value, SerializableType):
        return chain.from_iterable([flatten(item, f"{suffix}.{field}") for field, item in value.items()])
    elif isinstance(value, type) and issubclass(value, SerializableType):
        return chain.from_iterable([flatten(mtype, f"{suffix}.{name}") for name, mtype, _, _ in value.MEMBER_LIST])
    return [(suffix, value)]