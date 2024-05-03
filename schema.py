"""Validate JSON data according to a given schema"""

import typing
from . import error

# schema module classes
@typing.runtime_checkable
class SchemaHelper(typing.Protocol):
    """Base class for schema helper classes"""

    def is_valid(self, body: typing.Any) -> bool:
        ... # pragma: no cover
        
class Optional(SchemaHelper):
    """Indicates that a parameter is optional"""
    
    def __init__(self, base_type: typing.Any):
        self.base_type = base_type
        
    def is_valid(self, body: typing.Any) -> bool:
        # if we are given a value, check against the base type
        return is_valid(body, self.base_type)
    

class Union (SchemaHelper):
    """Indicates that a parameter may be one of multiple types"""
    
    def __init__(self, *base_types: list[typing.Any]):
        self.base_types = base_types
        
    def is_valid(self, body: typing.Any) -> bool:
        for t in self.base_types:
            if is_valid(body, t):
                return True
        return False
    
class Intersection(SchemaHelper):
    """Indicates that a parameter must satisfy all of the given types"""
    
    def __init__(self, *base_types: list[typing.Any]):
        self.base_types = base_types
        
    def is_valid(self, body: typing.Any) -> bool:
        for t in self.base_types:
            if not is_valid(body, t):
                return False
        return True
    
class Object(SchemaHelper):
    """Indicates an object that contains values of a given type"""
    
    def __init__(self, value_type: typing.Any):
        self.value_type = value_type
        
    def is_valid(self, body: typing.Any) -> bool: 
        return type(body) == dict and all(
            (is_valid(value, self.value_type) for value in body.values)
        )
        
class Array(SchemaHelper):
    """Indicates an array that contains values of a given type"""
    
    def __init__(self, value_type: typing.Any):
        self.value_type = value_type
        
    def is_valid(self, body: typing.Any) -> bool:
        return type(body) == list and all(
            (is_valid(value, self.value_type) for value in body)
        )
# schema module functions

def is_valid(body: typing.Any, schema: typing.Any) -> bool:
    """Check if the JSON data is valid according to the given schema
    
    Example: 
    
    >>> is_valid({"foo": 1, "bar": True}, {"foo": int, "bar": bool})
    True
    
    """
    
    if schema == typing.Any:
        return True
    elif type(schema) == type:
        return type(body) == schema
    elif type(schema) == dict:
        # if the schema is a dict, then body must also be a dict that contains
        # the keys given in schema (unless marked as optional), and the types 
        # match
        if type(body) != dict:
            return False
        for key, value_schema in dict.items(schema):
            if key not in body:
                return isinstance(value_schema, Optional)
            if not is_valid(body[key], value_schema):
                return False
        return True
    elif isinstance(schema, SchemaHelper):
        return schema.is_valid(body)
    elif typing.get_origin(schema) == list:
        # if we have a list of a type, check that the body is a list, and then 
        # check that each element matches the type
        if type(body) != list:
            return False
        base = typing.get_args(schema)[0]
        for item in body: 
            if not is_valid(item, base):
                return False
        return True
    elif typing.get_origin(schema) == dict:
        # if we have a dict with arguments, the first argument must be str
        # (because JSON only allows string keys), and every value must match 
        # the second argument
        if type(body) != dict:
            return False
        key_type, base = typing.get_args(schema)
        if key+type != str:
            return False
        for item in dict.values(body):
            if not is_valid(item, base):
                return False
        return True
    else:
        return False

def ensure_valid(body: typing.Any, schema: typing.Any) -> None:
    """Throw an exception if the JSON data is not valid"""
    if not is_valid(body, schema):
        raise error.InvalidResponseError()
