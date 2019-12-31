from ether import abi, crypto

from typing import Any, Dict, List
from ether.ether_types import EthABI


def make_selector(f: Dict[str, Any]) -> bytes:
    '''
    Parses a function ABI into a function selector
    This is the first 4 bytes of the hash of the signature

    Args:
        f (dict): the function ABI
    Returns:
        (bytes): the function selector
    '''
    return crypto.keccak256(abi.make_signature(f).encode('utf8'))[:4]


def _encode_function_args(
        function: Dict[str, Any],
        function_args: List[Any]) -> bytes:
    '''
    encodes function arguments into a data blob
    This gets prepended with the function selector
    '''
    return abi.encode_tuple(
        abi._make_type_tuple(function),
        function_args)


def _find_by_name(
        function_name: str,
        num_args: int,
        abi: EthABI) -> List[Dict[str, Any]]:
    '''
    Find a function within the ABI based on
    a) its name
    b) the number of args
    c) whether the args provided match that function's interface
    '''
    funcs = [e for e in abi if e['type'] == 'function']
    funcs = [f for f in funcs if f['name'] == function_name]
    funcs = [f for f in funcs if len(f['inputs']) == num_args]

    if len(funcs) == 0:
        raise ValueError('no functions with acceptable interface')

    return funcs


def encode_call(function: Dict[str, Any], function_args: List[Any]) -> bytes:
    '''
    Makes the data blob for a solidity contract function call
    This is a 4 byte selector, and then any number of bytes
    '''
    return (make_selector(function)
            + _encode_function_args(function, function_args))


def call(
        function_name: str,
        function_args: List[Any],
        contract_abi: EthABI) -> bytes:
    '''
    Call a function by name
    '''
    functions = _find_by_name(function_name, len(function_args), contract_abi)
    for function in functions:
        # return the first one that works
        try:
            return encode_call(function, function_args)
        except abi.ABIEncodingError:
            continue
    raise ValueError('no functions with acceptable interface')
