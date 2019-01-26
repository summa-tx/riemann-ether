import eth_abi

from ether.crypto import keccak256

from typing import Any, Dict, List
from ether.ether_types import EthABI


def make_type_list(function: Dict[str, Any]) -> str:
    '''
    makes a comma-delimted type list
    for use in the signature and encoding
    e.g. '(bytes,bytes,bytes)'
    '''
    return '({})'.format(
        ','.join(t['type'] for t in function['inputs']))


def make_signature(function: Dict[str, Any]) -> str:
    '''
    Makes the function signature
    e.g. transfer(address,value)
    '''
    return '{name}{types}'.format(
        name=function['name'],
        types=make_type_list(function))


def make_selector(function: Dict[str, Any]) -> bytes:
    '''
    makes the 4-byte function selector for encoding data blobs
    '''
    function_signature = make_signature(function)
    return keccak256(function_signature.encode('utf8'))[:4]


def encode_function_args(
        function: Dict[str, Any],
        function_args: List[Any]) -> bytes:
    '''
    encodes function arguments into a data blob
    This gets prepended with the function selector
    '''
    return eth_abi.encode_single(
        make_type_list(function),
        function_args)


def matches_args(
        function,
        function_args) -> bool:
    '''
    Checks whether eth_abi will encode each argument with the expected type
    '''
    for i in range(len(function_args)):
        inputs = function['inputs']
        if not eth_abi.is_encodable(inputs[i]['type'], function_args[i]):
            return False
    return True


def find_function(
        function_name: str,
        function_args: List[any],
        abi: EthABI) -> Dict[str, Any]:
    '''
    Find a function within the ABI based on
    a) its name
    b) the number of args
    c) whether the args provided match that function's interface
    '''
    funcs = [e for e in abi if e['type'] == 'function']
    funcs = [f for f in funcs if f['name'] == function_name]
    funcs = [f for f in funcs if len(f['inputs']) == len(function_args)]
    funcs = [f for f in funcs if matches_args(f, function_args)]

    if len(funcs) == 0:
        raise ValueError('no functions with acceptable interface')
    elif len(funcs) != 1:
        print(funcs)
        raise ValueError('multiple functions with acceptable interface.')
    return funcs[0]


def encode_call(function: Dict[str, Any], function_args: List[Any]) -> bytes:
    '''
    Makes the data blob for a solidity contract function call
    This is a 4 byte selector, and then any number of bytes
    '''
    return (make_selector(function)
            + encode_function_args(function, function_args))


def call(function_name: str, function_args: List[Any], abi: EthABI) -> bytes:
    '''
    Call a function by name
    '''
    function = find_function(function_name, function_args, abi)
    return encode_call(function, function_args)
