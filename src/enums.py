from enum import Enum

class NodeType(Enum):
    FUNCTION = 'function'
    CLASS = 'class'
    VARIABLE = 'variable'
    MODULE = 'module'
    CONSTANT = 'constant'
    BUILTIN = 'builtin'
    FILE = 'file'
    ATTRIBUTE = 'attribute'
    DIRECTORY = 'directory'
    UNKNOWN = 'unknown'

class EdgeType(Enum):
    FUNCTION_CALL = 'function_call'
    INHERITANCE = 'inheritance'
    ASSIGNMENT = 'assignment'
    GET = 'get'
    RETURN = 'return'
    IMPORT = 'import'
